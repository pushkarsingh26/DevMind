import os
import json
import time
import asyncio
import shutil
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logger import logger
from app.db.session import SessionLocal

from app.models.repository import Repository
from app.models.workflow import WorkflowExecutionORM
from app.agents.execution_context import ExecutionContext
from app.agents.execution_report import ExecutionReport
from app.agents.tool_registry import ToolRegistry
from app.agents.workflow_templates import WORKFLOW_TEMPLATES
from app.agents.workflow_engine import WorkflowEngine

class AgentOrchestrator:
    """
    Coordinates agent planning, sequential step run execution, tools, approvals,
    SSE streaming updates, and persistent DB storage.
    """
    def __init__(self):
        self._active_queues: Dict[str, asyncio.Queue] = {}
        self._active_contexts: Dict[str, ExecutionContext] = {}
        self._approval_events: Dict[str, asyncio.Event] = {}
        self.engine = WorkflowEngine()
        self.planner = None

    def get_context(self, workflow_id: str) -> Optional[ExecutionContext]:
        return self._active_contexts.get(workflow_id)

    def subscribe(self, workflow_id: str) -> asyncio.Queue:
        if workflow_id not in self._active_queues:
            self._active_queues[workflow_id] = asyncio.Queue()
        return self._active_queues[workflow_id]

    def _push_event(self, workflow_id: str, event_type: str, data: Any):
        if workflow_id in self._active_queues:
            queue = self._active_queues[workflow_id]
            # Convert datetime, set, etc. to serializable objects
            try:
                serialized_data = json.loads(json.dumps(data, default=str))
            except Exception:
                serialized_data = str(data)
                
            asyncio.create_task(queue.put({
                "type": event_type,
                "data": serialized_data
            }))

    def trigger_workflow(
        self,
        repository_id: str,
        goal: str,
        workflow_type: str
    ) -> str:
        """
        Registers a new workflow and starts the background execution.
        Returns the workflow ID.
        """
        import uuid
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        
        # Create context
        context = ExecutionContext(goal, workflow_type, repository_id)
        self._active_contexts[workflow_id] = context
        self._approval_events[workflow_id] = asyncio.Event()
        self._active_queues[workflow_id] = asyncio.Queue()

        # Start background loop
        asyncio.create_task(self._run_workflow_loop(workflow_id))
        
        return workflow_id

    async def approve_workflow(self, workflow_id: str, approved: bool, reason: Optional[str] = None):
        """
        Signals approval/rejection of code modifications to resume background loop.
        """
        context = self.get_context(workflow_id)
        if not context:
            raise ValueError("Workflow not found or already completed")

        context.approval_status = "approved" if approved else "rejected"
        context.approval_reason = reason or ("Approved by developer" if approved else "Rejected by developer")
        
        # If approved, write files to disk
        if approved and context.diff:
            context.add_log("Code modifications APPROVED. Applying edits to workspace...")
            # Apply edits to files
            self._apply_refactorings(context)
        else:
            context.add_log("Code modifications REJECTED. Skipping code modifications.")

        # Trigger event to resume loop
        if workflow_id in self._approval_events:
            self._approval_events[workflow_id].set()

    def _apply_refactorings(self, context: ExecutionContext):
        """
        Saves approved edits from refactor agent back to workspace path.
        """
        for out in context.agent_outputs:
            if out.get("agent") == "Refactor Agent":
                refactorings = out.get("result", {}).get("refactorings", [])
                for item in refactorings:
                    file_path = item.get("file")
                    new_code = item.get("refactored_code")
                    if file_path and new_code:
                        full_path = os.path.join(
                            settings.WORKSPACE_ROOT, "workflows", context.repository_id, file_path.lstrip("/\\")
                        )
                        try:
                            os.makedirs(os.path.dirname(full_path), exist_ok=True)
                            with open(full_path, "w", encoding="utf-8") as f:
                                f.write(new_code)
                            context.add_log(f"Successfully wrote modified code to '{file_path}'")
                        except Exception as e:
                            context.add_log(f"Failed to write changes to '{file_path}': {str(e)}", level="ERROR")

    async def _run_workflow_loop(self, workflow_id: str):
        context = self._active_contexts[workflow_id]
        context.add_log("Starting workflow execution task")
        self._push_event(workflow_id, "init", context.to_dict())

        # 1. Setup temporary workspace path by reconstructing codebase files from DB chunks
        workspace_path = os.path.join(settings.WORKSPACE_ROOT, "workflows", workflow_id)
        os.makedirs(workspace_path, exist_ok=True)
        
        with SessionLocal() as db:
            repo = db.query(Repository).filter(Repository.id == context.repository_id).first()
            if not repo:
                err_msg = f"Repository {context.repository_id} not found."
                context.add_log(err_msg, "ERROR")
                context.record_step_complete("Initializing", "failed", err_msg)
                self._push_event(workflow_id, "error", {"message": err_msg})
                self._save_to_db(workflow_id, status="failed")
                return

            # Reconstruct workspace files from db chunks
            context.add_log("Reconstructing workspace files from database indexes...")
            self._push_event(workflow_id, "progress", "Searching repository...")
            from app.models.chunk import Chunk
            chunks = db.query(Chunk).filter(Chunk.repository_id == context.repository_id).all()
            for chunk in chunks:
                file_dest = os.path.join(workspace_path, chunk.path.lstrip("/\\"))
                os.makedirs(os.path.dirname(file_dest), exist_ok=True)
                try:
                    mode = "a" if os.path.exists(file_dest) else "w"
                    with open(file_dest, mode, encoding="utf-8") as f:
                        if mode == "a":
                            f.write("\n")
                        f.write(chunk.content)
                except Exception as e:
                    logger.warning(f"Failed writing chunk file: {chunk.path}: {e}")

            # Load past repository memories
            past_mem_str = ""
            try:
                from app.models.memory import RepositoryMemoryORM
                past_mems = db.query(RepositoryMemoryORM).filter(
                    RepositoryMemoryORM.repository_id == context.repository_id
                ).order_by(RepositoryMemoryORM.created_at.desc()).limit(3).all()
                if past_mems:
                    context.add_log(f"Recovered {len(past_mems)} past Repository Memories. Injected into context memory.")
                    for pm in past_mems:
                        try:
                            data = json.loads(pm.content)
                            context.add_log(f"PAST AUDIT MEMORY ({pm.memory_key}): Goal was '{data.get('goal')}'. Findings: {data.get('recommendations')}")
                            past_mem_str += f"\n- Past {pm.memory_key} memory (Goal: {data.get('goal')}): {data.get('summary')} recommendations: {data.get('recommendations')}\n"
                        except Exception:
                            context.add_log(f"PAST AUDIT MEMORY ({pm.memory_key}): {pm.content[:150]}...")
                            past_mem_str += f"\n- Past {pm.memory_key} memory: {pm.content[:300]}\n"
            except Exception as e:
                logger.error(f"Error loading past repo memories: {e}")

            # Instantiate tool registry
            tools = ToolRegistry(workspace_path, context.repository_id, db)
            
            repo_meta = {
                "primary_language": repo.language,
                "framework": repo.framework,
                "total_files": repo.total_files,
                "dependencies": repo.dependencies or {},
                "largest_files": repo.largest_files or []
            }

            # 2. Planning phase
            context.add_log("Formulating execution plan...")
            self._push_event(workflow_id, "progress", "Planning workflow...")
            self._push_event(workflow_id, "log", "Planner Agent: Analyzing goal and drafting steps")
            
            plan_steps: List[Dict[str, Any]] = []
            rationale = "Custom execution"
            
            if context.workflow_type in WORKFLOW_TEMPLATES:
                template_steps = WORKFLOW_TEMPLATES[context.workflow_type]
                plan_steps = template_steps
                rationale = f"Executing predefined '{context.workflow_type}' template agent chain."
                context.add_log(f"Loaded preset workflow template: {context.workflow_type}")
            else:
                try:
                    from app.agents.agent_registry import agent_registry
                    planner_cls = agent_registry.get_agent_class("Planner Agent")
                    planner = planner_cls()
                    plan_schema, telemetry = await planner.plan_goal(context.goal, repo_meta)
                    plan_steps = [s.model_dump() for s in plan_schema.plan]
                    rationale = plan_schema.rationale
                    context.tokens_used += telemetry.get("total_tokens", 0)
                    if telemetry.get("provider"):
                        context.providers_used.append(telemetry["provider"])
                except Exception as e:
                    context.add_log(f"Planner failed: {e}. Falling back to default architecture review preset.", "WARNING")
                    plan_steps = WORKFLOW_TEMPLATES["Architecture Review"]
            
            # Push plan event
            plan_data = {
                "steps": plan_steps,
                "rationale": rationale
            }
            self._push_event(workflow_id, "plan", plan_data)
            context.add_log(f"Plan created with {len(plan_steps)} steps")

            # 3. Execution phase
            step_idx = 0
            while step_idx < len(plan_steps):
                step = plan_steps[step_idx]
                step_name = step.get("name")
                agent_name = step.get("agent")
                
                self._push_event(workflow_id, "progress", f"Running {agent_name}...")
                self._push_event(workflow_id, "step_start", {
                    "step_index": step_idx,
                    "step": step,
                    "context": context.to_dict()
                })

                # Execute step
                status, telemetry = await self.engine.execute_step(step, context, tools, db)
                
                # Check for approval suspension
                if status == "pending_approval":
                    self._push_event(workflow_id, "progress", "Waiting for approval...")
                    self._push_event(workflow_id, "pending_approval", {
                        "diff": context.diff,
                        "affected_files": context.affected_files,
                        "approval_reason": context.approval_reason,
                        "step_index": step_idx
                    })
                    
                    # Update DB state to pending_approval
                    self._save_to_db(workflow_id, status="pending_approval", steps=plan_steps)
                    
                    # Suspend task until Event is set
                    event = self._approval_events[workflow_id]
                    context.add_log("Execution suspended. Waiting for human approval...")
                    await event.wait()
                    
                    # Log decision
                    context.add_log(f"Execution resumed. Developer response: {context.approval_status.upper()}")
                    self._push_event(workflow_id, "log", f"System: Resuming workflow loop after approval check.")

                elif status == "failed":
                    self._push_event(workflow_id, "step_complete", {
                        "step_index": step_idx,
                        "status": "failed",
                        "context": context.to_dict()
                    })
                    break
                else:
                    self._push_event(workflow_id, "step_complete", {
                        "step_index": step_idx,
                        "status": "completed",
                        "context": context.to_dict()
                    })
                
                step_idx += 1

            # 4. Generate Final Report
            context.add_log("Synthesizing final execution report...")
            self._push_event(workflow_id, "progress", "Generating report...")
            report = ExecutionReport(context.goal, plan_steps, context.to_dict())
            report_dict = report.to_dict()
            
            # Save final report to context
            context.current_step = "Completed"
            context.current_agent = "System"
            context.add_log("Workflow finished successfully")
            
            self._push_event(workflow_id, "report", report_dict)
            self._push_event(workflow_id, "done", report_dict)

            # 5. Persist Report to DB
            self._save_to_db(workflow_id, status="completed", steps=plan_steps, report=report_dict)

            # 6. Save final report outcomes to persistent Repository Memory db table
            try:
                from app.models.memory import RepositoryMemoryORM
                db.query(RepositoryMemoryORM).filter(
                    RepositoryMemoryORM.repository_id == context.repository_id,
                    RepositoryMemoryORM.memory_key == context.workflow_type
                ).delete()
                new_memory = RepositoryMemoryORM(
                    repository_id=context.repository_id,
                    memory_key=context.workflow_type,
                    content=json.dumps({
                        "goal": context.goal,
                        "summary": report_dict.get("executive_summary", ""),
                        "recommendations": report_dict.get("recommendations", []) or report_dict.get("key_findings", [])
                    })
                )
                db.add(new_memory)
                db.commit()
                context.add_log(f"Saved execution report to persistent Repository Memory under category '{context.workflow_type}'")
            except Exception as e:
                logger.error(f"Failed saving repo memory: {e}")

            # Cleanup workspace path
            try:
                shutil.rmtree(workspace_path, ignore_errors=True)
                context.add_log("Cleaned up temporary workspace folder.")
            except Exception:
                pass

    def _save_to_db(self, workflow_id: str, status: str, steps: List[Dict[str, Any]] = None, report: Dict[str, Any] = None):
        context = self._active_contexts.get(workflow_id)
        if not context:
            return
            
        try:
            with SessionLocal() as db:
                db_wf = db.query(WorkflowExecutionORM).filter(WorkflowExecutionORM.id == workflow_id).first()
                if not db_wf:
                    db_wf = WorkflowExecutionORM(
                        id=workflow_id,
                        repository_id=context.repository_id,
                        goal=context.goal,
                        workflow_type=context.workflow_type,
                        status=status,
                        created_at=datetime.utcnow()
                    )
                    db.add(db_wf)
                
                db_wf.status = status
                db_wf.duration = context.get_elapsed_time()
                db_wf.agents_used = json.dumps(list(set([s.get("agent") for s in context.completed_steps if s.get("agent")])))
                
                if steps:
                    db_wf.steps = json.dumps(steps)
                else:
                    db_wf.steps = json.dumps(context.completed_steps)
                    
                if report:
                    db_wf.report = json.dumps(report)
                    
                db_wf.diff = context.diff
                db_wf.affected_files = json.dumps(context.affected_files)
                db_wf.approval_status = context.approval_status
                db_wf.approval_reason = context.approval_reason
                
                db.commit()
                logger.info(f"Saved workflow execution {workflow_id} status={status} to DB")
        except Exception as e:
            logger.error(f"Failed to persist workflow execution {workflow_id} to DB: {e}")

orchestrator = AgentOrchestrator()
