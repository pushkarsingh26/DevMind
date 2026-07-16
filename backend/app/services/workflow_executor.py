from app.services.retrieval_service import retrieval_service
import os
import json
import time
import shutil
import asyncio
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
            finally:
                retrieval_db.close()
            
            retrieval_time = time.time() - retrieval_started
            console.success(f"Retrieval complete in {retrieval_time:.2f}s")

            # 3. Planning phase
            await self._pause_event.wait()
            self._update_status("planning", 20)
            self.on_event(self.workflow_id, "workflow_progress", {"progress": 20, "status": "planning"})
            
            console.workflow("Starting Planning Phase...")
            planning_started = time.time()
            plan_steps: List[Dict[str, Any]] = []
            rationale = "Custom execution"

            if self.workflow_type in WORKFLOW_TEMPLATES:
                template_steps = WORKFLOW_TEMPLATES[self.workflow_type]
                plan_steps = template_steps
                rationale = f"Executing predefined '{self.workflow_type}' template agent chain."
                console.workflow(f"Loaded preset workflow template: {self.workflow_type}")
            else:
                try:
                    from app.agents.agent_registry import agent_registry
                    planner_cls = agent_registry.get_agent_class("Planner Agent")
                    planner = planner_cls()
                    plan_schema, telemetry = await planner.plan_goal(self.goal, repo_meta)
                    plan_steps = [s.model_dump() for s in plan_schema.plan]
                    rationale = plan_schema.rationale
                    self.context.tokens_used += telemetry.get("total_tokens", 0)
                    if telemetry.get("provider"):
                        self.context.providers_used.append(telemetry["provider"])
                except Exception as e:
                    console.warning(f"Planner failed: {e}. Falling back to default Architecture Review.")
                    plan_steps = WORKFLOW_TEMPLATES["Architecture Review"]

            # Save plan to graph.json atomically on background thread
            dw_start = time.time()
            graph_path = await asyncio.to_thread(
                workflow_storage.save_json, self.workflow_id, "graph.json", {
                    "steps": plan_steps,
                    "rationale": rationale
                }
            )
            disk_write_time += time.time() - dw_start
            
            planning_time = time.time() - planning_started
            console.success(f"Planning complete in {planning_time:.2f}s")

            # Write initial paths metadata to DB
            with SessionLocal() as db:
                db_wf = db.query(WorkflowExecutionORM).filter(WorkflowExecutionORM.id == self.workflow_id).first()
                if db_wf:
                    db_wf.graph_path = graph_path
                    db_wf.logs_path = os.path.join(workflow_storage.get_workflow_dir(self.workflow_id), "logs.jsonl")
                    db.commit()

            self.on_event(self.workflow_id, "workflow_log", f"System: Execution Plan formulated. Rationale: {rationale}")

            # 4. Executing phase with Concurrency Tiers
            self._update_status("executing", 25)
            self._print_execution_status(plan_steps)
            
            # Map agents to Tiers
            AGENT_TIERS = {
                "Repository Agent": 1,
                "Security Agent": 2,
                "Performance Agent": 2,
                "Testing Agent": 2,
                "Review Agent": 2,
                "Documentation Agent": 2,
                "Refactor Agent": 3,
                "Summary Agent": 4
            }
            
            # Group steps
            tier_groups = {1: [], 2: [], 3: [], 4: []}
            for step in plan_steps:
                agent_name = step.get("agent", "Review Agent")
                tier = AGENT_TIERS.get(agent_name, 2)
                tier_groups[tier].append(step)

            completed_count = 0
            total_steps = len(plan_steps)
            sem = asyncio.Semaphore(3)

            async def run_step_with_concurrency(step_obj):
                async with sem:
                    await self._pause_event.wait()
                    step_name = step_obj.get("name")
                    agent_name = step_obj.get("agent")
                    
                    self.context.current_step = step_name
                    self._print_execution_status(plan_steps)
                    
                    # If step is Repository Agent, check if memory is reusable to skip LLM calls
                    if agent_name == "Repository Agent" and memory_reusable:
                        self.context.add_log(f"Skipping duplicate scan for Repository Agent (Memory is Reusable).")
                        self.context.record_step_complete(step_name, "completed", "Loaded from past Repository Memory.")
                        self._print_execution_status(plan_steps)
                        return "completed", {"cached": True, "total_tokens": 0}
                    
                    # Run actual step with isolated db session and tool registry
                    with SessionLocal() as step_db:
                        step_tools = ToolRegistry(workspace_path, self.repository_id, step_db)
                        status, telemetry = await self.engine.execute_step(step_obj, self.context, step_tools, step_db)
                    self._print_execution_status(plan_steps)
                    
                    if status == "failed":
                        raise Exception(f"Step '{step_name}' failed.")
                        
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
                        "average_agent_duration": (sum(self.context.agent_durations.values()) / len(self.context.agent_durations)) if self.context.agent_durations else 0.0
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
                        "completed_steps": self.context.completed_steps
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
