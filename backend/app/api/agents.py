import json
import asyncio
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.workflow import WorkflowExecutionORM
from app.models.repository import Repository
from app.agents.agent_orchestrator import orchestrator
from app.core.logger import logger

router = APIRouter(prefix="/agents", tags=["Agents"])

class WorkflowExecuteRequest(BaseModel):
    repository_id: str = Field(..., description="ID of indexed repository to scan")
    goal: str = Field(..., description="Natural language objective")
    workflow_type: str = Field(..., description="Workflow template preset or Custom Goal")

class ApprovalRequest(BaseModel):
    approved: bool = Field(..., description="True to apply refactoring edits to files, False to discard")
    reason: Optional[str] = Field(None, description="Reasoning or notes from developer")

@router.post(
    "/execute",
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Autonomous Agentic Workflow"
)
async def execute_workflow(
    payload: WorkflowExecuteRequest,
    db: Session = Depends(get_db)
):
    # Verify repository exists
    repo = db.query(Repository).filter(Repository.id == payload.repository_id).first()
    if not repo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{payload.repository_id}' does not exist."
        )

    try:
        workflow_id = orchestrator.trigger_workflow(
            repository_id=payload.repository_id,
            goal=payload.goal,
            workflow_type=payload.workflow_type
        )
        return {"workflow_id": workflow_id}
    except Exception as e:
        logger.error(f"Error starting workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start workflow execution: {str(e)}"
        )

@router.get(
    "/stream/{workflow_id}",
    summary="Stream Live Execution Timeline & Outputs"
)
async def stream_workflow(workflow_id: str):
    """
    Returns an SSE stream of log, step, context, and report packets.
    """
    async def sse_generator():
        queue = orchestrator.subscribe(workflow_id)
        context = orchestrator.get_context(workflow_id)
        
        # If context is not active in memory, check if it exists in DB as completed
        if not context:
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'Workflow session not active.'}})}\n\n"
            return

        yield f"data: {json.dumps({'type': 'init', 'data': context.to_dict()})}\n\n"

        try:
            while True:
                event = await queue.get()
                yield f"data: {json.dumps(event)}\n\n"
                queue.task_done()
                
                # Check for termination events
                if event.get("type") in ("done", "error"):
                    break
        except asyncio.CancelledError:
            logger.info(f"SSE client disconnected from stream {workflow_id}")
        except Exception as e:
            logger.error(f"Error streaming workflow {workflow_id}: {e}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@router.post(
    "/history/{workflow_id}/approve",
    summary="Approve or Reject Proposed Refactoring Changes"
)
async def approve_workflow_modifications(
    workflow_id: str,
    payload: ApprovalRequest
):
    try:
        await orchestrator.approve_workflow(
            workflow_id=workflow_id,
            approved=payload.approved,
            reason=payload.reason
        )
        return {"status": "success", "detail": f"Decided approved={payload.approved} for workflow."}
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(val_err)
        )
    except Exception as e:
        logger.error(f"Error approving workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Approval action failed: {str(e)}"
        )

@router.get(
    "/history",
    summary="List all workflow executions"
)
async def list_workflow_history(
    repository_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(WorkflowExecutionORM)
    if repository_id:
        query = query.filter(WorkflowExecutionORM.repository_id == repository_id)
        
    runs = query.order_by(WorkflowExecutionORM.created_at.desc()).all()
    
    results = []
    for r in runs:
        # Fetch repository name
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
            "duration": r.duration,
            "created_at": r.created_at,
            "agents_used": agents_list,
            "diff": r.diff,
            "approval_status": r.approval_status
        })
    return results

@router.get(
    "/history/{workflow_id}",
    summary="Get execution detail report"
)
async def get_workflow_detail(
    workflow_id: str,
    db: Session = Depends(get_db)
):
    wf = db.query(WorkflowExecutionORM).filter(WorkflowExecutionORM.id == workflow_id).first()
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow execution {workflow_id} not found."
        )

    # Decode JSON blocks
    try:
        report_data = json.loads(wf.report) if wf.report else {}
    except Exception:
        report_data = {}
        
    try:
        steps_data = json.loads(wf.steps) if wf.steps else []
    except Exception:
        steps_data = []
        
    try:
        files_data = json.loads(wf.affected_files) if wf.affected_files else []
    except Exception:
        files_data = []

    return {
        "id": wf.id,
        "repository_id": wf.repository_id,
        "repository_name": wf.repository.name if wf.repository else "Unknown Repo",
        "goal": wf.goal,
        "workflow_type": wf.workflow_type,
        "status": wf.status,
        "duration": wf.duration,
        "created_at": wf.created_at,
        "diff": wf.diff,
        "affected_files": files_data,
        "approval_status": wf.approval_status,
        "approval_reason": wf.approval_reason,
        "steps": steps_data,
        "report": report_data
    }

@router.delete(
    "/history/{workflow_id}",
    summary="Delete a workflow run record"
)
async def delete_workflow_run(
    workflow_id: str,
    db: Session = Depends(get_db)
):
    wf = db.query(WorkflowExecutionORM).filter(WorkflowExecutionORM.id == workflow_id).first()
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow run not found."
        )
    db.delete(wf)
    db.commit()
    return {"status": "success", "detail": f"Workflow run {workflow_id} deleted."}
