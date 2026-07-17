"""REST API endpoints for Phase 8.5 Adaptive Workflow Execution.
"""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

from app.core.logger import logger
from app.db.session import SessionLocal
from app.models.workflow import WorkflowExecutionORM
from app.services.workflow_manager import workflow_manager
from app.services.execution.checkpoint_storage import checkpoint_storage

router = APIRouter(prefix="/api/execution", tags=["Adaptive Workflow Execution"])


@router.get("/{workflow_id}/status", summary="Get execution status, state, metrics, and budget")
async def get_status(workflow_id: str) -> Dict[str, Any]:
    state, metrics, budget = checkpoint_storage.load_state(workflow_id)
    
    # Load steps from graph.json
    steps = []
    try:
        from app.utils import workflow_storage
        graph_data = workflow_storage.load_json(workflow_id, "graph.json") or {}
        steps = graph_data.get("steps", [])
    except Exception:
        pass

    if state is None:
        # Fall back to checking if database record exists
        with SessionLocal() as db:
            db_wf = db.query(WorkflowExecutionORM).filter(WorkflowExecutionORM.id == workflow_id).first()
            if not db_wf:
                raise HTTPException(status_code=404, detail="Workflow execution state not found.")
            return {
                "workflow_id": workflow_id,
                "status": db_wf.status,
                "progress": db_wf.progress,
                "current_step": db_wf.current_step,
                "steps": steps,
            }
            
    return {
        "state": state.to_dict(),
        "metrics": metrics.to_dict(),
        "budget": budget.to_dict(),
        "steps": steps,
    }


@router.get("/{workflow_id}/metrics", summary="Get runtime execution metrics and budget")
async def get_metrics(workflow_id: str) -> Dict[str, Any]:
    state, metrics, budget = checkpoint_storage.load_state(workflow_id)
    if metrics is None or budget is None:
        raise HTTPException(status_code=404, detail="Execution metrics not found.")
    return {
        "metrics": metrics.to_dict(),
        "budget": budget.to_dict(),
    }


@router.post("/{workflow_id}/pause", summary="Pause execution run")
async def pause_run(workflow_id: str) -> Dict[str, Any]:
    success = workflow_manager.pause_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to pause workflow. Is it active?")
    return {"status": "success", "message": "Execution paused."}


@router.post("/{workflow_id}/resume", summary="Resume paused execution or restart from checkpoints")
async def resume_run(workflow_id: str) -> Dict[str, Any]:
    # 1. Try to resume if it was paused
    if workflow_manager.resume_workflow(workflow_id):
        return {"status": "success", "message": "Paused execution resumed."}
        
    # 2. Restart from checkpoints if it was terminated/failed
    with SessionLocal() as db:
        db_wf = db.query(WorkflowExecutionORM).filter(WorkflowExecutionORM.id == workflow_id).first()
        if not db_wf:
            raise HTTPException(status_code=404, detail="Workflow execution not found.")
        repo_id = db_wf.repository_id
        goal = db_wf.goal
        wf_type = db_wf.workflow_type

    from app.services.workflow_executor import WorkflowExecutor
    executor = WorkflowExecutor(
        workflow_id=workflow_id,
        repository_id=repo_id,
        goal=goal,
        workflow_type=wf_type,
        on_event_cb=workflow_manager.publish_event,
        on_finished_cb=workflow_manager._on_executor_finished
    )
    
    workflow_manager._executors[workflow_id] = executor
    executor.start()
    return {"status": "success", "message": "Workflow restarted from checkpoints successfully."}


@router.post("/{workflow_id}/cancel", summary="Cancel execution run")
async def cancel_run(workflow_id: str) -> Dict[str, Any]:
    success = workflow_manager.cancel_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to cancel workflow.")
    return {"status": "success", "message": "Execution cancelled."}


@router.post("/{workflow_id}/retry", summary="Retry the last failed step")
async def retry_run(workflow_id: str) -> Dict[str, Any]:
    state, metrics, budget = checkpoint_storage.load_state(workflow_id)
    if not state or state.status != "failed" or not state.failed_step:
        raise HTTPException(status_code=400, detail="Workflow is not in a failed state with a failing step.")
        
    # Reset failed flags
    state.status = "running"
    state.resume_from_step = state.failed_step
    state.failed_step = None
    checkpoint_storage.save_state(workflow_id, state, metrics, budget)
    
    # Restart workflow run
    return await resume_run(workflow_id)


@router.get("/{workflow_id}/checkpoints", summary="Get list of step checkpoints")
async def get_checkpoints(workflow_id: str) -> List[Dict[str, Any]]:
    cps = checkpoint_storage.load_checkpoints(workflow_id)
    return [cp.to_dict() for cp in cps]


@router.get("/{workflow_id}/events", summary="Get log events timeline")
async def get_events(workflow_id: str) -> List[Dict[str, Any]]:
    events = checkpoint_storage.load_events(workflow_id)
    return [e.to_dict() for e in events]
