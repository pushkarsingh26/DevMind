from datetime import timezone
from app.services.retrieval_service import retrieval_service
import os
import json
import time
import shutil
import asyncio
import threading
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable

from app.core.config import settings
from app.core.logger import logger
from app.db.session import SessionLocal
from app.models.repository import Repository
from app.models.memory import RepositoryMemoryORM
from app.models.workflow import WorkflowExecutionORM
from app.agents.execution_context import ExecutionContext
from app.agents.execution_report import ExecutionReport
from app.agents.tool_registry import ToolRegistry
from app.agents.workflow_templates import WORKFLOW_TEMPLATES
from app.agents.workflow_engine import WorkflowEngine
from app.utils import workflow_storage

# Phase 8.7 Memory Engine Integration
from app.services.memory import learning_engine
from app.services.memory.workflow_memory import build_workflow_memory

# Detect asyncio.TaskGroup availability once at module load (Python 3.11+)
_HAS_TASK_GROUP = hasattr(asyncio, "TaskGroup")

class FileBackedExecutionContext(ExecutionContext):
    """
    Subclass of ExecutionContext that appends logs to filesystem logs.jsonl in real-time.
    """
    def __init__(self, workflow_id: str, goal: str, workflow_type: str, repository_id: str):
        self.workflow_id = workflow_id
        super().__init__(goal, workflow_type, repository_id)

    def add_log(self, message: str, level: str = "INFO"):
        super().add_log(message, level)
        if len(self.logs) > 0:
            log_entry = self.logs[-1]
            workflow_storage.append_log(self.workflow_id, log_entry)

class WorkflowExecutor:
    """
    Executes a single autonomous agent workflow in the background.
    Supports pausing, resuming, human approvals, and cancellation.
    """
    def __init__(
        self,
        workflow_id: str,
        repository_id: str,
        goal: str,
        workflow_type: str,
        on_event_cb: Callable[[str, str, Any], None],
        on_finished_cb: Callable[[str], None]
    ):
        self.workflow_id = workflow_id
        self.repository_id = repository_id
        self.goal = goal
        self.workflow_type = workflow_type
        self.on_event = on_event_cb
        self.on_finished = on_finished_cb

        self.context = FileBackedExecutionContext(workflow_id, goal, workflow_type, repository_id)
        self.engine = WorkflowEngine()
        self.task: Optional[asyncio.Task] = None

        # Synchronisation primitives for Pause/Resume and Approval
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Initial state: not paused

        self._approval_event = asyncio.Event()

        self._status = "queued"
        self._progress = 0
        self._lock = threading.RLock()
        self._repository_hash = ""

    @property
    def status(self) -> str:
        return self._status

    @property
    def progress(self) -> int:
        return self._progress

    def start(self):
        """Starts the background execution task."""
        self.task = asyncio.create_task(self._run_loop())

    def pause(self) -> bool:
        """Pauses execution (will halt before starting the next step)."""
        if self._status in ["starting", "planning", "retrieving", "executing"]:
            self._pause_event.clear()
            self._update_status("paused")
            self.context.add_log("Workflow execution PAUSED by user.")
            self.on_event(self.workflow_id, "workflow_progress", {"progress": self._progress, "status": self._status})
            return True
        return False

    def resume(self) -> bool:
        """Resumes a paused execution."""
        if self._status == "paused":
            self._pause_event.set()
            self._update_status("executing")
            self.context.add_log("Workflow execution RESUMED by user.")
            self.on_event(self.workflow_id, "workflow_progress", {"progress": self._progress, "status": self._status})
            return True
        return False

    def cancel(self):
        """Cancels/terminates the execution task."""
        if self.task and not self.task.done():
            self.task.cancel()

    def submit_approval(self, approved: bool, reason: Optional[str] = None):
        """Resumes a workflow suspended for human approval."""
        if self._status != "waiting_approval":
            return

        self.context.approval_status = "approved" if approved else "rejected"
        self.context.approval_reason = reason or ("Approved by developer" if approved else "Rejected by developer")

        if approved and self.context.diff:
            self.context.add_log("Code modifications APPROVED. Applying edits to workspace...")
            self._apply_refactorings()
        else:
            self.context.add_log("Code modifications REJECTED. Skipping workspace edits.")

        # Signal completion of approval phase
        self._approval_event.set()

    def _update_status(self, new_status: str, progress: Optional[int] = None):
        self._status = new_status
        if progress is not None:
            self._progress = progress

        # Sync back to DB
        try:
            with SessionLocal() as db:
                db_wf = db.query(WorkflowExecutionORM).filter(WorkflowExecutionORM.id == self.workflow_id).first()
                if db_wf:
                    db_wf.status = self._status
                    db_wf.progress = self._progress
                    db_wf.duration = self.context.get_elapsed_time()
                    db_wf.current_step = self.context.current_step
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to sync status for {self.workflow_id} to DB: {e}")

    def _apply_refactorings(self):
        """
        Saves approved edits from refactor agent back to the workspace.
        """
        for out in self.context.agent_outputs:
            if out.get("agent") == "Refactor Agent":
                refactorings = out.get("result", {}).get("refactorings", [])
                for item in refactorings:
                    file_path = item.get("file")
                    new_code = item.get("refactored_code")
                    if file_path and new_code:
                        full_path = os.path.join(
                            settings.WORKSPACE_ROOT, "workflows", self.repository_id, file_path.lstrip("/\\")
                        )
                        try:
                            os.makedirs(os.path.dirname(full_path), exist_ok=True)
                            with open(full_path, "w", encoding="utf-8") as f:
                                f.write(new_code)
                            self.context.add_log(f"Successfully wrote modified code to '{file_path}'")
                        except Exception as e:
                            self.context.add_log(f"Failed to write changes to '{file_path}': {str(e)}", level="ERROR")

    def _record_workflow_memory(self, success: bool, repo_hash: str):
        """Compiles and registers WorkflowMemory to learning engine on completion/failure."""
        try:
            findings = []
            for out in self.context.agent_outputs:
                if isinstance(out, dict) and "result" in out:
                    res = out["result"]
                    if isinstance(res, dict):
                        findings.extend(res.get("findings", []) or res.get("key_findings", []))

            prov_used = list(set(self.context.providers_used))
            exec_metrics = {
                "retry_count": self.context.retry_count,
                "cache_hits": self.context.cache_hits,
                "cache_misses": self.context.cache_misses,
                "tokens_used": self.context.tokens_used,
            }

            execution_plan_dict = {
                "steps": [
                    {
                        "step_id": s.get("step"),
                        "agent": s.get("agent"),
                        "files": s.get("files", []),
                    }
                    for s in self.context.completed_steps
                ]
            }

            wf_mem = build_workflow_memory(
                workflow_id=self.workflow_id,
                goal=self.goal,
                intent=self.workflow_type,
                execution_plan=execution_plan_dict,
                execution_metrics=exec_metrics,
                collaboration_summary={
                    "overall_confidence": getattr(self.context, "collaboration_snapshot", {}).get("confidence", 0.8)
                },
                findings=findings,
                duration=self.context.get_elapsed_time(),
                provider_usage=prov_used,
                success=success,
            )

            learning_engine.update_workflow_run(self.repository_id, repo_hash, wf_mem)
            self.context.add_log(f"Successfully recorded workflow outcomes to Memory & Learning Engine.")

            # Phase 8.9 — Record Decision History
            try:
                from app.services.decision.decision_storage import add_history_record
                from app.services.decision.decision_models import DecisionHistoryRecord
                from datetime import datetime, timezone
                
                score = 0.0
                priority = "low"
                if self.context.decision_summary:
                    score = self.context.decision_summary.decision_score
                    priority = self.context.decision_summary.priority_level

                dec_record = DecisionHistoryRecord(
                    workflow_id=self.workflow_id,
                    goal=self.goal,
                    intent=self.workflow_type,
                    decision_score=score,
                    priority_level=priority,
                    success=success,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )
                add_history_record(self.repository_id, dec_record)
                self.context.add_log("Successfully recorded workflow outcomes to Decision History.")
            except Exception as dec_exc:
                logger.warning(f"Failed to record decision history: {dec_exc}")
        except Exception as exc:
            logger.error(f"Failed to record workflow memory for {self.workflow_id}: {exc}")

    def _print_execution_status(self, plan_steps: List[Dict[str, Any]]):
        from app.core.console import console
        agents_status = {}
        for step in plan_steps:
            name = step.get("name")
            agent = step.get("agent")
            completed = any(cs.get("step") == name for cs in self.context.completed_steps)
            if completed:
                agents_status[f"{agent} ({name})"] = "✓ Complete"
            elif self.context.current_step == name:
                agents_status[f"{agent} ({name})"] = "Running..."
            else:
                agents_status[f"{agent} ({name})"] = "Queued..."
        
        console.display_workflow_execution(
            wf_name=self.workflow_type,
            repo_name=self.repository_id,
            wf_id=self.workflow_id,
            stage=2,
            stage_name="Autonomous Agent Execution",
            agents_status=agents_status
        )

    async def _run_loop(self):
        workspace_path = os.path.join(settings.WORKSPACE_ROOT, "workflows", self.workflow_id)
        # Async background write
        await asyncio.to_thread(os.makedirs, workspace_path, exist_ok=True)

        started_timestamp = time.time()
        queue_time = 0.0
        retrieval_time = 0.0
        planning_time = 0.0
        disk_write_time = 0.0
        # Declared here so the finally block can always attempt to close it.
        retrieval_db = None

        try:
            # 1. Starting / Initialise DB metadata record
            self._update_status("starting", 5)
            self.context.add_log("Starting background workflow executor")
            
            # Retrieve queue time
            with SessionLocal() as db:
                db_wf = db.query(WorkflowExecutionORM).filter(WorkflowExecutionORM.id == self.workflow_id).first()
                if db_wf:
                    queue_time = started_timestamp - db_wf.created_at.timestamp()
            
            init_data = self.context.to_dict()
            self.on_event(self.workflow_id, "workflow_started", init_data)

            # 2. Retrieving / Ingestion
            await self._pause_event.wait()
            self._update_status("retrieving", 10)
            self.on_event(self.workflow_id, "workflow_progress", {"progress": 10, "status": "retrieving"})
            
            retrieval_started = time.time()
            from app.core.console import console
            console.workflow(f"Starting Stage 1: Repository Analysis for {self.workflow_type} (wf_id: {self.workflow_id})")
            
            # Keep ONE db session open for the entire retrieval phase so that all
            # objects (repo, chunks, tools) remain bound to a live session.
            retrieval_db = SessionLocal()
            try:
                from app.models.chunk import Chunk
                import re

                repo = retrieval_db.query(Repository).filter(Repository.id == self.repository_id).first()
                if not repo:
                    raise ValueError(f"Repository {self.repository_id} not found.")

                console.workflow("Reconstructing workspace files from database indexes...")
                
                # Retrieve all chunks in a single query (no N+1)
                chunks = retrieval_db.query(Chunk).filter(Chunk.repository_id == self.repository_id).all()
                
                # File reconstruction inside thread executor
                def reconstruct_files():
                    for chunk in chunks:
                        file_dest = os.path.join(workspace_path, chunk.path.lstrip("/\\"))
                        os.makedirs(os.path.dirname(file_dest), exist_ok=True)
                        mode = "a" if os.path.exists(file_dest) else "w"
                        with open(file_dest, mode, encoding="utf-8") as f:
                            if mode == "a":
                                f.write("\n")
                            f.write(chunk.content)
                
                dw_start = time.time()
                await asyncio.to_thread(reconstruct_files)
                disk_write_time += time.time() - dw_start

                # Smart Memory Validation (Compare repository hashes)
                past_mem_str = ""
                memory_reusable = False
                try:
                    past_mems = retrieval_db.query(RepositoryMemoryORM).filter(
                        RepositoryMemoryORM.repository_id == self.repository_id
                    ).order_by(RepositoryMemoryORM.created_at.desc()).limit(3).all()
                    
                    if past_mems:
                        console.workflow("Validating repository hash consistency against Repository Memory...")
                        for pm in past_mems:
                            try:
                                data = json.loads(pm.content)
                                # Only reuse if commit hash or content hash matches
                                if repo.repository_hash and data.get("repository_hash") == repo.repository_hash:
                                    memory_reusable = True
                                    console.success(f"Memory '{pm.memory_key}' hash matches ({repo.repository_hash[:8]}). Reusing cached layout analysis.")
                                    self.context.add_summary(f"Reused {pm.memory_key} summary: {data.get('summary')}")
                                    past_mem_str += f"\n- Reused {pm.memory_key} analysis: {data.get('summary')} recommendations: {data.get('recommendations')}\n"
                                else:
                                    console.warning(f"Memory '{pm.memory_key}' hash changed. Recalculating analysis.")
                            except Exception:
                                pass
                except Exception as e:
                    logger.error(f"Error validating repo memory hash: {e}")

                # Group Cache Operations logging (Task 6)
                console.display_cache_group(
                    ai_cache="HIT" if self.context.cache_hits > 0 else "MISS",
                    retrieval="HIT" if memory_reusable else "MISS",
                    repo_mem="HIT" if memory_reusable else "MISS",
                    vector="HIT" if memory_reusable else "MISS"
                )

                # Get file tree for SharedContextBundle
                all_chunk_paths = retrieval_db.query(Chunk.path).filter(Chunk.repository_id == self.repository_id).distinct().all()
                file_tree = [p[0] for p in all_chunk_paths]
                
                # FAISS Broad Retrieval once to construct SharedContextBundle
                total_files = repo.total_files if repo.total_files else 100
                if total_files <= 50:
                    base_k = 8
                elif total_files <= 250:
                    base_k = 12
                else:
                    base_k = 18
                
                broad_chunks = retrieval_service.retrieve_chunks(
                    db=retrieval_db,
                    repository_id=self.repository_id,
                    query=self.goal,
                    top_k=base_k,
                    workflow_type=self.workflow_type
                )
                
                # Extract symbol index
                symbols = set()
                pattern = re.compile(r'\b(def|class|function|const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)')
                for chunk, _ in broad_chunks:
                    for match in pattern.finditer(chunk.content):
                        symbols.add(match.group(2))
                
                # Create rich SharedContextBundle on Context
                self.context.shared_context_bundle = {
                    "relevant_chunks": broad_chunks,
                    "symbols": list(symbols)[:50],
                    "dependency_graph": repo.dependencies or {},
                    "repository_statistics": {
                        "total_files": repo.total_files,
                        "directories": repo.directories,
                        "framework": repo.framework,
                        "language": repo.language,
                    },
                    "language_map": repo.extensions or {},
                    "file_tree": file_tree
                }
                
                repo_meta = {
                    "primary_language": repo.language,
                    "framework": repo.framework,
                    "total_files": repo.total_files,
                    "dependencies": repo.dependencies or {},
                    "largest_files": repo.largest_files or []
                }
                # Extract scalar values from repo ORM before we close the session
                repo_repository_hash = repo.repository_hash
                self._repository_hash = repo_repository_hash
            finally:
                retrieval_db.close()
            
            retrieval_time = time.time() - retrieval_started
            console.success(f"Retrieval complete in {retrieval_time:.2f}s")

            # 3. Planning phase
            await self._pause_event.wait()
            self._update_status("planning", 20)
            self.on_event(self.workflow_id, "workflow_progress", {"progress": 20, "status": "planning"})
            
            console.workflow("Starting Intelligent Planning Phase...")
            planning_started = time.time()
            
            from app.services.planning.planning_engine import planning_engine
            from app.services.planning.planning_storage import planning_storage

            # Check cache
            plan = planning_storage.validate_cache(self.repository_id, self.goal, repo_repository_hash)
            if plan:
                console.success(f"Planning cache HIT. Reusing plan {plan.plan_id}")
                self.context.add_log(f"Reused cached execution plan {plan.plan_id}")
            else:
                console.workflow("Planning cache MISS. Generating optimized execution plan...")
                plan = planning_engine.generate_plan(self.repository_id, self.goal)
                planning_storage.save_plan(self.repository_id, plan)
                self.context.add_log(f"Generated new execution plan {plan.plan_id}")

            plan_steps = []
            for s in plan.steps:
                plan_steps.append({
                    "step_id": s.step_id,
                    "name": s.title,  # map title to name for backward compatibility
                    "agent": s.agent,
                    "description": s.description,
                    "execution_group": s.execution_group,
                    "estimated_duration": s.estimated_duration,
                    "estimated_token_cost": s.estimated_token_cost
                })

            rationale = plan.rationale
            
            # Save plan to graph.json atomically on background thread
            dw_start = time.time()
            graph_path = await asyncio.to_thread(
                workflow_storage.save_json, self.workflow_id, "graph.json", plan.to_dict()
            )
            disk_write_time += time.time() - dw_start
            
            planning_time = time.time() - planning_started
            console.success(f"Planning complete in {planning_time:.2f}s")

            # Phase 8.8 — Attach Reasoning Context to ExecutionContext (non-blocking)
            try:
                intel_path_for_reasoning = ""
                with SessionLocal() as db:
                    _repo_r = db.query(Repository).filter(Repository.id == self.repository_id).first()
                    if _repo_r:
                        intel_path_for_reasoning = _repo_r.intelligence_path or ""
                from app.services.reasoning.reasoning_engine import reasoning_engine as _re
                _summary = await asyncio.to_thread(
                    _re.ensure,
                    self.repository_id,
                    self.goal,
                    repo_repository_hash,
                    intel_path_for_reasoning,
                )
                self.context.reasoning_summary = _summary
                self.context.reasoning_metrics = _re.get_metrics(self.repository_id)
                self.context.reasoning_context = _summary.reasoning_context if _summary else None
                self.context.add_log(
                    f"Reasoning Engine: score={getattr(_summary, 'reasoning_score', 0):.3f}, "
                    f"confidence={getattr(_summary, 'confidence', 0):.3f}"
                )
            except Exception as _re_exc:
                logger.warning(f"[WorkflowExecutor] Reasoning engine non-blocking failure: {_re_exc}")

            # Phase 8.9 — Attach Decision Engine context to ExecutionContext (non-blocking)
            try:
                from app.services.decision.decision_engine import decision_engine as _de
                _d_summary = await asyncio.to_thread(
                    _de.ensure,
                    self.repository_id,
                    self.goal,
                    repo_repository_hash,
                    intel_path_for_reasoning,
                )
                self.context.decision_summary = _d_summary
                self.context.add_log(
                    f"Decision Engine: score={getattr(_d_summary, 'decision_score', 0):.3f}, "
                    f"level={getattr(_d_summary, 'priority_level', 'low')}, "
                    f"recommendation={getattr(_d_summary, 'execution_recommendation', 'PROCEED')}"
                )
            except Exception as _de_exc:
                logger.warning(f"[WorkflowExecutor] Decision engine non-blocking failure: {_de_exc}")

            # Write initial paths metadata to DB
            with SessionLocal() as db:
                db_wf = db.query(WorkflowExecutionORM).filter(WorkflowExecutionORM.id == self.workflow_id).first()
                if db_wf:
                    db_wf.graph_path = graph_path
                    db_wf.logs_path = os.path.join(workflow_storage.get_workflow_dir(self.workflow_id), "logs.jsonl")
                    db.commit()

            self.on_event(self.workflow_id, "workflow_log", f"System: Dynamic Execution Plan formulated. Rationale: {rationale}")

            # 4. Executing phase with Concurrency Tiers derived from topological order levels
            self._update_status("executing", 25)
            self._print_execution_status(plan_steps)
            
            # Group steps dynamically by parallel_groups metrics (topological sort levels)
            tier_groups = {}
            for level_idx, group_str in enumerate(plan.metrics.parallel_groups):
                level_step_ids = group_str.split(",")
                tier_steps = [s for s in plan_steps if s["step_id"] in level_step_ids]
                if tier_steps:
                    tier_groups[level_idx + 1] = tier_steps

            # Initialize execution state, metrics, and budget
            from app.services.execution.execution_manager import execution_manager
            from app.services.execution.checkpoint_storage import checkpoint_storage
            from app.services.execution.retry_policy import retry_policy
            from app.services.execution.provider_selector import provider_selector
            from app.services.execution.execution_models import ExecutionCheckpoint, ExecutionEvent

            state, metrics, budget = execution_manager.initialize_run(self.workflow_id, self.repository_id, plan_steps)
            state.status = "running"
            checkpoint_storage.save_state(self.workflow_id, state, metrics, budget)

            checkpoints = checkpoint_storage.load_checkpoints(self.workflow_id)
            completed_ids = [cp.step_id for cp in checkpoints if cp.status == "completed"]
            completed_count = len(completed_ids)
            total_steps = len(plan_steps)
            sem = asyncio.Semaphore(3)

            async def run_step_with_concurrency(step_obj):
                async with sem:
                    await self._pause_event.wait()
                    step_id = step_obj.get("step_id")
                    step_name = step_obj.get("name")
                    agent_name = step_obj.get("agent")
                    
                    self.context.current_step = step_name
                    self._print_execution_status(plan_steps)

                    # Check checkpoint recovery status
                    if step_id in completed_ids:
                        self.context.add_log(f"Skipping completed step '{step_name}' (restored from checkpoint).")
                        self.context.record_step_complete(step_name, "completed", "Restored from checkpoint storage.")
                        self._print_execution_status(plan_steps)
                        return "completed", {"cached": True, "total_tokens": 0}

                    # Determine active provider
                    current_provider = metrics.active_provider
                    status = "failed"
                    telemetry = {}
                    
                    max_attempts = 3
                    attempt = 0
                    
                    while attempt < max_attempts:
                        await self._pause_event.wait()
                        start_time_sec = time.time()
                        
                        # Log started event
                        checkpoint_storage.log_event(self.workflow_id, ExecutionEvent(
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            step_id=step_id,
                            event="started",
                            provider=current_provider,
                            duration_ms=0,
                            retry=attempt
                        ))

                        try:
                            # If step is Repository Agent, check if memory is reusable to skip LLM calls
                            if agent_name == "Repository Agent" and memory_reusable:
                                self.context.add_log(f"Skipping duplicate scan for Repository Agent (Memory is Reusable).")
                                self.context.record_step_complete(step_name, "completed", "Loaded from past Repository Memory.")
                                status, telemetry = "completed", {"cached": True, "total_tokens": 0}
                            else:
                                old_provider = settings.AI_PROVIDER
                                old_chain = settings.AI_PROVIDER_CHAIN
                                settings.AI_PROVIDER = current_provider
                                chain_list = [p.strip().lower() for p in old_chain.split(",")]
                                if current_provider in chain_list:
                                    chain_list.remove(current_provider)
                                chain_list.insert(0, current_provider)
                                settings.AI_PROVIDER_CHAIN = ",".join(chain_list)
                                
                                try:
                                    with SessionLocal() as step_db:
                                        step_tools = ToolRegistry(workspace_path, self.repository_id, step_db)
                                        status, telemetry = await self.engine.execute_step(step_obj, self.context, step_tools, step_db)
                                finally:
                                    settings.AI_PROVIDER = old_provider
                                    settings.AI_PROVIDER_CHAIN = old_chain
                            
                            if status == "failed":
                                raise Exception("Agent returned failed execution status.")
                            
                            # Step completed successfully
                            break
                        except Exception as e:
                            logger.warning(f"Step {step_id} execution failed (attempt {attempt + 1}): {e}")
                            attempt += 1
                            
                            if attempt < max_attempts and retry_policy.should_retry(e):
                                delay = retry_policy.get_delay(attempt)
                                self.context.add_log(f"Retryable error encountered. Retrying step {step_id} in {delay:.2f}s...")
                                checkpoint_storage.log_event(self.workflow_id, ExecutionEvent(
                                    timestamp=datetime.now(timezone.utc).isoformat(),
                                    step_id=step_id,
                                    event="retry",
                                    provider=current_provider,
                                    duration_ms=int((time.time() - start_time_sec) * 1000),
                                    retry=attempt
                                ))
                                metrics.retry_count += 1
                                checkpoint_storage.save_state(self.workflow_id, state, metrics, budget)
                                await asyncio.sleep(delay)
                            else:
                                # Failover to next provider
                                new_provider = provider_selector.select_best_provider(agent_name, current_provider)
                                if new_provider != current_provider:
                                    self.context.add_log(f"Failover: switching provider from '{current_provider}' to '{new_provider}'...")
                                    checkpoint_storage.log_event(self.workflow_id, ExecutionEvent(
                                        timestamp=datetime.now(timezone.utc).isoformat(),
                                        step_id=step_id,
                                        event="failover",
                                        provider=new_provider,
                                        duration_ms=int((time.time() - start_time_sec) * 1000),
                                        retry=attempt
                                    ))
                                    current_provider = new_provider
                                    metrics.active_provider = new_provider
                                    checkpoint_storage.save_state(self.workflow_id, state, metrics, budget)
                                    attempt = 0  # reset attempt counter for failover provider
                                else:
                                    status = "failed"
                                    break

                    self._print_execution_status(plan_steps)

                    if status == "failed":
                        checkpoint_storage.log_event(self.workflow_id, ExecutionEvent(
                            timestamp=datetime.now(timezone.utc).isoformat(),
                            step_id=step_id,
                            event="failed",
                            provider=current_provider,
                            duration_ms=int((time.time() - start_time_sec) * 1000),
                            retry=attempt
                        ))
                        state.status = "failed"
                        state.failed_step = step_id
                        checkpoint_storage.save_state(self.workflow_id, state, metrics, budget)
                        raise Exception(f"Step '{step_name}' failed after attempts and failovers.")

                    step_duration = int(time.time() - start_time_sec)
                    tokens_used = telemetry.get("total_tokens", 1000)
                    cost_used = tokens_used * 0.000002

                    budget.used_tokens += tokens_used
                    budget.used_cost_usd += cost_used
                    budget.remaining_tokens = max(0, budget.max_tokens - budget.used_tokens)
                    budget.remaining_cost = max(0.0, budget.max_cost_usd - budget.used_cost_usd)

                    state.last_completed_step = step_id
                    state.current_step_id = None

                    # Save Checkpoint
                    checkpoint = ExecutionCheckpoint(
                        step_id=step_id,
                        status="completed",
                        completed_at=datetime.now(timezone.utc).isoformat(),
                        telemetry={"tokens": tokens_used, "cost": cost_used, "duration_sec": step_duration},
                        outputs={}
                    )
                    checkpoint_storage.save_checkpoint(self.workflow_id, checkpoint)

                    # Run collaboration pipeline after checkpoint saved
                    if agent_name != "Summary Agent":
                        from app.services.collaboration.collaboration_pipeline import run_collaboration_pipeline

                        def _run_collab():
                            with self._lock:
                                snapshot, validated_text = run_collaboration_pipeline(
                                    workflow_id=self.workflow_id,
                                    repository_id=self.repository_id,
                                    repository_hash=self._repository_hash,
                                    step_obj=step_obj,
                                    context=self.context,
                                    agent_name=agent_name,
                                )
                                self.context.collaboration_snapshot = snapshot
                                if validated_text:
                                    if not hasattr(self.context, "collaboration_context"):
                                        self.context.collaboration_context = {}
                                    self.context.collaboration_context["validated_findings_text"] = validated_text

                        await asyncio.to_thread(_run_collab)

                        if self.context.collaboration_snapshot:
                            self.on_event(self.workflow_id, "workflow_progress", {
                                "progress": self._progress,
                                "status": "executing",
                                "completed_steps": self.context.completed_steps,
                                "collaboration": self.context.collaboration_snapshot,
                            })

                    # Update metrics
                    metrics.completed_steps += 1
                    fresh_cps = checkpoint_storage.load_checkpoints(self.workflow_id)
                    fresh_completed_ids = [cp.step_id for cp in fresh_cps if cp.status == "completed"]
                    
                    metrics.remaining_duration_sec_eta = execution_manager.calculate_eta(
                        plan_steps, fresh_completed_ids, fresh_cps
                    )
                    metrics.total_duration_sec += step_duration

                    checkpoint_storage.save_state(self.workflow_id, state, metrics, budget)

                    checkpoint_storage.log_event(self.workflow_id, ExecutionEvent(
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        step_id=step_id,
                        event="completed",
                        provider=current_provider,
                        duration_ms=int(step_duration * 1000),
                        retry=attempt
                    ))

                    # Save intermediate telemetry to disk in background thread
                    nonlocal disk_write_time
                    telemetry_dict = {
                        "queue_time": queue_time,
                        "retrieval_time": retrieval_time,
                        "planning_time": planning_time,
                        "disk_write_time": disk_write_time,
                        "tokens_used": self.context.tokens_used,
                        "providers_used": list(set(self.context.providers_used)),
                        "retry_count": self.context.retry_count,
                        "cache_hits": self.context.cache_hits,
                        "cache_misses": self.context.cache_misses,
                        "agent_durations": self.context.agent_durations,
                        "elapsed": self.context.get_elapsed_time(),
                        "cache_hit_ratio": (self.context.cache_hits / (self.context.cache_hits + self.context.cache_misses) * 100) if (self.context.cache_hits + self.context.cache_misses) > 0 else 0.0,
                        "average_agent_duration": (sum(self.context.agent_durations.values()) / len(self.context.agent_durations)) if self.context.agent_durations else 0.0,
                        "graph_build_time_ms": getattr(self.context, "graph_build_time", 0.0),
                        "graph_cache_hit": getattr(self.context, "graph_cache_hit", False),
                        "graph_candidates_selected": getattr(self.context, "graph_candidates_selected", 0),
                        "graph_nodes": getattr(self.context, "graph_nodes", 0),
                        "graph_edges": getattr(self.context, "graph_edges", 0),
                        "graph_traversal_time_ms": getattr(self.context, "graph_traversal_time", 0.0)
                    }
                    
                    dw_start = time.time()
                    telemetry_path = await asyncio.to_thread(
                        workflow_storage.save_json, self.workflow_id, "telemetry.json", telemetry_dict
                    )
                    disk_write_time += time.time() - dw_start

                    # Sync database ORM state in background thread
                    def sync_db_state():
                        with SessionLocal() as db:
                            db_wf = db.query(WorkflowExecutionORM).filter(WorkflowExecutionORM.id == self.workflow_id).first()
                            if db_wf:
                                db_wf.telemetry = json.dumps(telemetry_dict)
                                db_wf.telemetry_path = telemetry_path
                                db_wf.status = self._status
                                db_wf.progress = self._progress
                                db_wf.duration = self.context.get_elapsed_time()
                                db_wf.current_step = self.context.current_step
                                if status == "pending_approval":
                                    db_wf.diff = self.context.diff
                                    db_wf.affected_files = json.dumps(self.context.affected_files)
                                    db_wf.approval_status = "pending"
                                db.commit()
                    
                    await asyncio.to_thread(sync_db_state)
                    
                    if status == "pending_approval":
                        self._approval_event.clear()
                        self._update_status("waiting_approval", self._progress)
                        self.on_event(self.workflow_id, "workflow_progress", {
                            "progress": self._progress,
                            "status": "waiting_approval",
                            "diff": self.context.diff,
                            "affected_files": self.context.affected_files,
                            "approval_reason": self.context.approval_reason or "Approval check required"
                        })
                        
                        await self._approval_event.wait()
                        self._pause_event.set()
                        self._update_status("executing", self._progress)
                        
                    return status, telemetry

            # Execute Tiers sequentially, running concurrent steps inside each tier
            for tier_id in sorted(tier_groups.keys()):
                steps_in_tier = tier_groups[tier_id]
                if not steps_in_tier:
                    continue
                
                self.context.add_log(f"Starting execution of Tier {tier_id} steps ({len(steps_in_tier)} parallel tasks)...")
                
                # Check for Pause/Resume
                await self._pause_event.wait()
                
                if _HAS_TASK_GROUP:
                    # Python 3.11+: structured concurrency via TaskGroup
                    async with asyncio.TaskGroup() as tg:
                        for step in steps_in_tier:
                            tg.create_task(run_step_with_concurrency(step))
                else:
                    # Python < 3.11: fall back to asyncio.gather
                    await asyncio.gather(
                        *[run_step_with_concurrency(step) for step in steps_in_tier]
                    )
                
                for _ in steps_in_tier:
                    completed_count += 1
                    progress_pct = int(25 + (completed_count / total_steps) * 60)
                    self._update_status("executing", progress_pct)
                    self.on_event(self.workflow_id, "workflow_progress", {
                        "progress": progress_pct,
                        "status": "executing",
                        "completed_steps": self.context.completed_steps,
                        "collaboration": getattr(self.context, "collaboration_snapshot", {}),
                    })

            # 5. Completed Report Generation
            await self._pause_event.wait()
            self._update_status("executing", 90)
            self.context.add_log("Synthesizing final report...")
            
            report_obj = ExecutionReport(self.goal, plan_steps, self.context.to_dict())
            report_dict = report_obj.to_dict()
            report_markdown = report_dict.get("executive_summary", "No executive summary generated.")

            # Save report files atomically in background threads
            dw_start = time.time()
            report_path = await asyncio.to_thread(
                workflow_storage.save_text, self.workflow_id, "report.md", report_markdown
            )
            await asyncio.to_thread(
                workflow_storage.save_json, self.workflow_id, "report.json", report_dict
            )
            disk_write_time += time.time() - dw_start

            # Persist completed metrics to DB in thread
            def write_completion_db():
                with SessionLocal() as db:
                    db_wf = db.query(WorkflowExecutionORM).filter(WorkflowExecutionORM.id == self.workflow_id).first()
                    if db_wf:
                        db_wf.status = "completed"
                        db_wf.progress = 100
                        db_wf.duration = self.context.get_elapsed_time()
                        db_wf.summary = report_markdown
                        db_wf.report_path = report_path
                        db_wf.agents_used = json.dumps(list(set([s.get("agent") for s in self.context.completed_steps if s.get("agent")])))
                        db_wf.steps = json.dumps(self.context.completed_steps)
                        db.commit()

            await asyncio.to_thread(write_completion_db)

            # Write outcomes to persistent Repository Memory db table in thread.
            # Use the scalar repo_repository_hash captured before the session could close.
            _repo_hash_snapshot = repo_repository_hash
            def write_repo_memory():
                with SessionLocal() as db:
                    db.query(RepositoryMemoryORM).filter(
                        RepositoryMemoryORM.repository_id == self.repository_id,
                        RepositoryMemoryORM.memory_key == self.workflow_type
                    ).delete()
                    new_memory = RepositoryMemoryORM(
                        repository_id=self.repository_id,
                        memory_key=self.workflow_type,
                        content=json.dumps({
                            "goal": self.goal,
                            "summary": report_markdown,
                            "recommendations": report_dict.get("recommendations", []) or report_dict.get("key_findings", []),
                            "repository_hash": _repo_hash_snapshot
                        })
                    )
                    db.add(new_memory)
                    db.commit()
            
            await asyncio.to_thread(write_repo_memory)
            self.context.add_log(f"Saved report findings to persistent Repository Memory under category '{self.workflow_type}'")

            # Phase 8.7: Record successful workflow run to Memory Engine
            await asyncio.to_thread(self._record_workflow_memory, True, _repo_hash_snapshot)

            self._update_status("completed", 100)
            self.on_event(self.workflow_id, "workflow_finished", {
                "progress": 100,
                "status": "completed",
                "report": report_dict,
                "duration": self.context.get_elapsed_time(),
                "tokens_used": self.context.tokens_used
            })

        except asyncio.CancelledError:
            logger.warning(f"Workflow execution {self.workflow_id} CANCELLED by user.")
            self.context.add_log("Workflow execution was manually cancelled", level="WARNING")
            self._update_status("cancelled")
            self.on_event(self.workflow_id, "workflow_cancelled", {"status": "cancelled"})

        except Exception as e:
            # Log the FULL traceback so failures are diagnosable from logs.
            tb = traceback.format_exc()
            logger.exception(
                f"Workflow {self.workflow_id} FAILED — "
                f"{type(e).__name__}: {e}\n{tb}"
            )
            err_message = f"{type(e).__name__}: {e}"
            self.context.add_log(f"Workflow execution failed: {err_message}", level="ERROR")
            self.context.add_log(f"Traceback:\n{tb}", level="ERROR")
            self._update_status("failed")
            self.on_event(self.workflow_id, "workflow_failed", {"status": "failed", "error": err_message})

            # Persist failure state to disk so the user can inspect logs/telemetry in the UI.
            try:
                await asyncio.to_thread(
                    workflow_storage.save_json, self.workflow_id, "telemetry.json", {
                        "status": "failed",
                        "error": err_message,
                        "traceback": tb,
                        "elapsed": self.context.get_elapsed_time(),
                        "tokens_used": self.context.tokens_used,
                        "providers_used": list(set(self.context.providers_used)),
                        "retry_count": self.context.retry_count,
                        "cache_hits": self.context.cache_hits,
                        "cache_misses": self.context.cache_misses,
                        "agent_durations": self.context.agent_durations,
                        "graph_build_time_ms": getattr(self.context, "graph_build_time", 0.0),
                        "graph_cache_hit": getattr(self.context, "graph_cache_hit", False),
                        "graph_candidates_selected": getattr(self.context, "graph_candidates_selected", 0),
                        "graph_nodes": getattr(self.context, "graph_nodes", 0),
                        "graph_edges": getattr(self.context, "graph_edges", 0),
                        "graph_traversal_time_ms": getattr(self.context, "graph_traversal_time", 0.0)
                    }
                )
                # Persist failure record to DB
                def write_failed_db():
                    with SessionLocal() as db:
                        db_wf = db.query(WorkflowExecutionORM).filter(WorkflowExecutionORM.id == self.workflow_id).first()
                        if db_wf:
                            db_wf.status = "failed"
                            db_wf.duration = self.context.get_elapsed_time()
                            db_wf.current_step = self.context.current_step
                            db.commit()
                await asyncio.to_thread(write_failed_db)

                # Phase 8.7: Record failed workflow run to Memory Engine
                _repo_hash_snapshot = getattr(self, "_repository_hash", "") or "unknown_hash"
                await asyncio.to_thread(self._record_workflow_memory, False, _repo_hash_snapshot)
            except Exception as persist_err:
                logger.error(f"Failed to persist failure state for {self.workflow_id}: {persist_err}")

        finally:
            # Close the retrieval DB session that was kept alive during execution.
            if retrieval_db is not None:
                try:
                    retrieval_db.close()
                except Exception:
                    pass
            # Delete temporary workspaces directory in background thread
            await asyncio.to_thread(shutil.rmtree, workspace_path, ignore_errors=True)
            self.context.add_log("Cleaned up temporary workspace directories.")
            self.on_finished(self.workflow_id)
