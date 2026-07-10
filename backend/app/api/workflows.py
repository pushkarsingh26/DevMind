import json
import asyncio
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload
from app.db.session import get_db
from app.models.workflow import WorkflowExecutionORM
from app.models.repository import Repository
from app.services.workflow_manager import workflow_manager
from app.utils import workflow_storage
from app.core.logger import logger

router = APIRouter(prefix="/api/workflows", tags=["Workflows"])

class WorkflowExecuteRequest(BaseModel):
    repository_id: str = Field(..., description="ID of indexed repository to scan")
    goal: str = Field(..., description="Natural language objective")
    workflow_type: str = Field(..., description="Workflow template preset or Custom Goal")

class ApprovalRequest(BaseModel):
    approved: bool = Field(..., description="True to apply changes, False to discard")
    reason: Optional[str] = Field(None, description="Notes from the developer")

@router.post(
    "/start",
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Autonomous Agentic Workflow (Decoupled Background Execution)"
)
async def start_workflow(
    payload: WorkflowExecuteRequest,
    db: Session = Depends(get_db)
):
    repo = db.query(Repository).filter(Repository.id == payload.repository_id).first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{payload.repository_id}' does not exist."
        )

    try:
        workflow_id = workflow_manager.start_workflow(
            repository_id=payload.repository_id,
            goal=payload.goal,
            workflow_type=payload.workflow_type
        )
        return {"workflow_id": workflow_id, "status": "running"}
    except Exception as e:
        logger.error(f"Error starting workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow execution: {str(e)}"
        )

@router.get(
    "/stream",
    summary="Global Live Workflows Execution SSE Stream"
)
async def stream_workflows():
    """
    Subscribes the client to a single global channel delivering events (started, logs,
    progress, completed, failed, cancelled) for all active background executions.
    Must be defined BEFORE /{workflow_id} routes to avoid FastAPI routing conflict.
    """
    async def sse_generator():
        # Subscribe queue
        queue = workflow_manager.subscribe_global()
        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
                queue.task_done()
        except asyncio.CancelledError:
            # Client disconnected
            pass
        finally:
            workflow_manager.unsubscribe_global(queue)

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get(
    "",
    summary="List all workflow executions"
)
async def list_workflows(
    repository_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(WorkflowExecutionORM).options(joinedload(WorkflowExecutionORM.repository))
    if repository_id:
        query = query.filter(WorkflowExecutionORM.repository_id == repository_id)
        
    runs = query.order_by(WorkflowExecutionORM.created_at.desc()).all()
    
    results = []
    for r in runs:
        repo_name = r.repository.name if r.repository else "Deleted Repository"
        try:
            agents_list = json.loads(r.agents_used) if r.agents_used else []
        except Exception:
            agents_list = []
            
        results.append({
            "id": r.id,
            "repository_id": r.repository_id,
            "repository_name": repo_name,
            "goal": r.goal,
            "workflow_type": r.workflow_type,
            "status": r.status,
            "progress": r.progress or 0,
            "current_step": r.current_step,
            "duration": r.duration,
            "created_at": r.created_at,
            "agents_used": agents_list,
            "diff": r.diff,
            "approval_status": r.approval_status
        })
    return results

@router.get(
    "/running",
    summary="List active or queued workflow executions"
)
async def list_running_workflows(
    db: Session = Depends(get_db)
):
    active_statuses = ["queued", "starting", "retrieving", "planning", "executing", "waiting_approval", "paused"]
    runs = db.query(WorkflowExecutionORM).options(
        joinedload(WorkflowExecutionORM.repository)
    ).filter(
        WorkflowExecutionORM.status.in_(active_statuses)
    ).order_by(WorkflowExecutionORM.created_at.desc()).all()
    
    results = []
    for r in runs:
        repo_name = r.repository.name if r.repository else "Deleted Repository"
        try:
            agents_list = json.loads(r.agents_used) if r.agents_used else []
        except Exception:
            agents_list = []
            
        results.append({
            "id": r.id,
            "repository_id": r.repository_id,
            "repository_name": repo_name,
            "goal": r.goal,
            "workflow_type": r.workflow_type,
            "status": r.status,
            "progress": r.progress or 0,
            "current_step": r.current_step,
            "duration": r.duration,
            "created_at": r.created_at,
            "agents_used": agents_list,
            "diff": r.diff,
            "approval_status": r.approval_status
        })
    return results

@router.get(
    "/{workflow_id}",
    summary="Get workflow details (Metadata, Graph and Report)"
)
async def get_workflow(
    workflow_id: str,
    db: Session = Depends(get_db)
):
    # Fetch DB metadata record
    wf = db.query(WorkflowExecutionORM).options(
        joinedload(WorkflowExecutionORM.repository)
    ).filter(WorkflowExecutionORM.id == workflow_id).first()
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow execution {workflow_id} not found."
        )

    # Reconstruct details using file system values
    report_data = workflow_storage.load_json(workflow_id, "report.json") or {}
    graph_data = workflow_storage.load_json(workflow_id, "graph.json") or {}
    telemetry_data = workflow_storage.load_json(workflow_id, "telemetry.json") or {}

    steps_list = graph_data.get("steps", [])
    
    # If completed steps exists in ORM (legacy compatibility) or active context, load them
    executor = workflow_manager.get_executor(workflow_id)
    if executor:
        steps_list = executor.context.completed_steps
    elif wf.steps:
        try:
            steps_list = json.loads(wf.steps)
        except Exception:
            pass

    affected_files_list = []
    if wf.affected_files:
        try:
            affected_files_list = json.loads(wf.affected_files)
        except Exception:
            pass

    # Read diff patch from file if available, otherwise fallback to DB column
    diff_patch = workflow_storage.load_text(workflow_id, "diff.patch") or wf.diff

    return {
        "id": wf.id,
        "repository_id": wf.repository_id,
        "repository_name": wf.repository.name if wf.repository else "Unknown Repo",
        "goal": wf.goal,
        "workflow_type": wf.workflow_type,
        "status": wf.status,
        "progress": wf.progress or 0,
        "current_step": wf.current_step,
        "duration": wf.duration or telemetry_data.get("elapsed", 0.0),
        "created_at": wf.created_at,
        "diff": diff_patch,
        "affected_files": affected_files_list,
        "approval_status": wf.approval_status,
        "approval_reason": wf.approval_reason,
        "steps": steps_list,
        "report": report_data,
        "analytics": telemetry_data
    }

@router.get(
    "/{workflow_id}/logs",
    summary="Get workflow execution logs"
)
async def get_workflow_logs(
    workflow_id: str,
    db: Session = Depends(get_db)
):
    # Check if active in memory
    executor = workflow_manager.get_executor(workflow_id)
    if executor:
        return {"logs": executor.context.logs}

    # Load from filesystem logs.jsonl
    logs = workflow_storage.read_logs(workflow_id)
    return {"logs": logs}

@router.get(
    "/{workflow_id}/status",
    summary="Get lightweight workflow status & progress"
)
async def get_workflow_status(
    workflow_id: str,
    db: Session = Depends(get_db)
):
    wf = db.query(WorkflowExecutionORM).filter(WorkflowExecutionORM.id == workflow_id).first()
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow execution {workflow_id} not found."
        )
    return {
        "workflow_id": wf.id,
        "status": wf.status,
        "progress": wf.progress or 0,
        "current_step": wf.current_step
    }

@router.get(
    "/{workflow_id}/report",
    summary="Get finished report payload"
)
async def get_workflow_report(
    workflow_id: str
):
    report_data = workflow_storage.load_json(workflow_id, "report.json")
    if not report_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report for workflow {workflow_id} not found on server filesystem."
        )
    return {"report": report_data}

@router.post(
    "/{workflow_id}/pause",
    summary="Pause active execution step flow"
)
async def pause_workflow(workflow_id: str):
    success = workflow_manager.pause_workflow(workflow_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow {workflow_id} is not running or cannot be paused."
        )
    return {"status": "success", "detail": f"Workflow {workflow_id} paused."}

@router.post(
    "/{workflow_id}/resume",
    summary="Resume paused execution step flow"
)
async def resume_workflow(workflow_id: str):
    success = workflow_manager.resume_workflow(workflow_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow {workflow_id} is not paused or cannot be resumed."
        )
    return {"status": "success", "detail": f"Workflow {workflow_id} resumed."}

@router.post(
    "/{workflow_id}/cancel",
    summary="Cancel active background workflow execution"
)
async def cancel_workflow(workflow_id: str):
    success = workflow_manager.cancel_workflow(workflow_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow {workflow_id} is not in an active execution state."
        )
    return {"status": "success", "detail": f"Workflow {workflow_id} cancellation triggered."}

@router.post(
    "/{workflow_id}/approve",
    summary="Submit approval or rejection for proposed refactoring"
)
async def approve_workflow(
    workflow_id: str,
    payload: ApprovalRequest
):
    success = workflow_manager.submit_approval(
        workflow_id=workflow_id,
        approved=payload.approved,
        reason=payload.reason
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workflow {workflow_id} is not awaiting code refactoring approvals."
        )
    return {"status": "success", "detail": f"Decided approved={payload.approved}."}

@router.delete(
    "/{workflow_id}",
    summary="Delete workflow metadata and file directory"
)
async def delete_workflow(
    workflow_id: str,
    db: Session = Depends(get_db)
):
    wf = db.query(WorkflowExecutionORM).filter(WorkflowExecutionORM.id == workflow_id).first()
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow run not found."
        )
    
    # Delete database record
    db.delete(wf)
    db.commit()

    # Delete filesystem files
    wdir = workflow_storage.get_workflow_dir(workflow_id)
    import shutil
    try:
        shutil.rmtree(wdir, ignore_errors=True)
    except Exception:
        pass

    return {"status": "success", "detail": f"Workflow {workflow_id} deleted."}


