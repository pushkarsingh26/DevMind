import uuid
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.logger import logger
from app.db.session import SessionLocal
from app.models.workflow import WorkflowExecutionORM
from app.services.workflow_executor import WorkflowExecutor
from app.utils import workflow_storage

class WorkflowManager:
    """
    Global service managing background execution queues, active executors,
    concurrency limit pools, and the unified global EventSource stream subscriptions.
    """
    def __init__(self, concurrency_limit: int = 2):
        self._concurrency_limit = concurrency_limit
        self._executors: Dict[str, WorkflowExecutor] = {}
        self._listeners: List[asyncio.Queue] = []
        self._queue: List[str] = []  # FIFO list of queued workflow_ids

    def subscribe_global(self) -> asyncio.Queue:
        """Subscribes a client to the global SSE event channel."""
        queue = asyncio.Queue()
        self._listeners.append(queue)
        return queue

    def unsubscribe_global(self, queue: asyncio.Queue):
        """Unsubscribes a client from the global event channel."""
        if queue in self._listeners:
            self._listeners.remove(queue)

    def publish_event(self, workflow_id: str, event_type: str, data: Any):
        """Broadcasts a workflow event to all active SSE subscribers."""
        event = {
            "workflow_id": workflow_id,
            "type": event_type,
            "data": data
        }
        for q in list(self._listeners):
            asyncio.create_task(q.put(event))

    def get_executor(self, workflow_id: str) -> Optional[WorkflowExecutor]:
        return self._executors.get(workflow_id)

    def start_workflow(self, repository_id: str, goal: str, workflow_type: str) -> str:
        """
        Creates a workflow run record in state 'queued' and places it in the FIFO queue.
        Returns the new workflow ID.
        """
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}"
        
        # Save initially to database in 'queued' status
        try:
            with SessionLocal() as db:
                db_wf = WorkflowExecutionORM(
                    id=workflow_id,
                    repository_id=repository_id,
                    goal=goal,
                    workflow_type=workflow_type,
                    status="queued",
                    progress=0,
                    created_at=datetime.now(timezone.utc).replace(tzinfo=None)
                )
                db.add(db_wf)
                db.commit()
                logger.info(f"Registered workflow {workflow_id} as QUEUED in DB.")
        except Exception as e:
            logger.error(f"Failed to write queued workflow {workflow_id} to DB: {e}")

        # Create executor instance
        executor = WorkflowExecutor(
            workflow_id=workflow_id,
            repository_id=repository_id,
            goal=goal,
            workflow_type=workflow_type,
            on_event_cb=self.publish_event,
            on_finished_cb=self._on_executor_finished
        )
        self._executors[workflow_id] = executor
        self._queue.append(workflow_id)

        # Notify global listeners that the workflow was queued
        self.publish_event(workflow_id, "workflow_started", {
            "id": workflow_id,
            "repository_id": repository_id,
            "goal": goal,
            "workflow_type": workflow_type,
            "status": "queued",
            "progress": 0,
            "created_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
        })

        # Check if queue has available execution slots
        self._check_queue()

        return workflow_id

    def pause_workflow(self, workflow_id: str) -> bool:
        executor = self.get_executor(workflow_id)
        if executor:
            return executor.pause()
        return False

    def resume_workflow(self, workflow_id: str) -> bool:
        executor = self.get_executor(workflow_id)
        if executor:
            return executor.resume()
        return False

    def cancel_workflow(self, workflow_id: str) -> bool:
        # Check if in queue (not started yet)
        if workflow_id in self._queue:
            self._queue.remove(workflow_id)
            
            # Sync cancelled status to DB
            try:
                with SessionLocal() as db:
                    db_wf = db.query(WorkflowExecutionORM).filter(WorkflowExecutionORM.id == workflow_id).first()
                    if db_wf:
                        db_wf.status = "cancelled"
                        db.commit()
            except Exception as e:
                logger.error(f"Failed to cancel queued workflow: {e}")

            # Notify cancellation event
            self.publish_event(workflow_id, "workflow_cancelled", {"status": "cancelled"})
            
            if workflow_id in self._executors:
                del self._executors[workflow_id]
            return True

        # Check if running/active
        executor = self.get_executor(workflow_id)
        if executor:
            executor.cancel()
            return True

        return False

    def submit_approval(self, workflow_id: str, approved: bool, reason: Optional[str] = None) -> bool:
        executor = self.get_executor(workflow_id)
        if executor:
            executor.submit_approval(approved, reason)
            return True
        return False

    def _check_queue(self):
        """Starts next queued workflows if concurrent execution limit slots are free."""
        active_count = sum(
            1 for ex in self._executors.values() if ex.status not in ["queued", "completed", "failed", "cancelled"]
        )

        while active_count < self._concurrency_limit and len(self._queue) > 0:
            next_id = self._queue.pop(0)
            executor = self.get_executor(next_id)
            if executor:
                logger.info(f"Starting execution of queued workflow {next_id}...")
                executor.start()
                active_count += 1
            else:
                # Executor was deleted or missing, check next
                pass

    def _on_executor_finished(self, workflow_id: str):
        """Callback fired by WorkflowExecutor upon execution termination."""
        logger.info(f"WorkflowExecutor finished for workflow: {workflow_id}")
        if workflow_id in self._executors:
            del self._executors[workflow_id]
        
        # Schedule the next queue item
        self._check_queue()

# Instantiate global manager singleton
workflow_manager = WorkflowManager(concurrency_limit=2)
