from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from app.core.constants import TaskType
from app.models.request import ReviewRequest
from app.models.response import ReviewResponse, StatusResponse, ResultResponse
from app.api.dependencies import get_job_service, get_repository_service
from app.services.job_service import JobService
from app.services.repository_service import RepositoryService
from app.core.logger import logger
import os

router = APIRouter()

@router.post(
    "/review",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit GitHub URL for Analysis"
)
async def analyze_url(
    payload: ReviewRequest,
    background_tasks: BackgroundTasks,
    job_service: JobService = Depends(get_job_service)
):
    """
    Submits a GitHub repository URL to initiate background evaluation.
    """
    logger.info(f"Received URL analysis request: {payload.repo_url} for task: {payload.task}")
    try:
        # Register new analysis tracking job ID
        job_id = job_service.create_job(payload.task, payload.repo_url)
        
        # Add analysis run to background tasks
        background_tasks.add_task(
            job_service.run_analysis_pipeline, 
            job_id, 
            payload.repo_url, 
            is_zip=False
        )
        
        return ReviewResponse(job_id=job_id)
    except Exception as e:
        logger.error(f"Error starting URL analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit URL for analysis: {str(e)}"
        )

@router.post(
    "/upload",
    response_model=ReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Repository ZIP Archive"
)
async def analyze_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="ZIP repository archive"),
    task: TaskType = Form(..., description="The analysis task to perform"),
    job_service: JobService = Depends(get_job_service),
    repo_service: RepositoryService = Depends(get_repository_service)
):
    """
    Uploads a repository ZIP package. Unpacks contents and registers progress.
    """
    logger.info(f"Received archive upload request: {file.filename} for task: {task}")
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid archive. Please upload a ZIP format archive (.zip) only."
        )

    try:
        # Register job ID first
        job_id = job_service.create_job(task, file.filename)
        
        # Read uploaded file bytes and ingest via RepositoryService
        content = await file.read()
        ingest_result = repo_service.ingest_zip(job_id, content, file.filename)

        # Add analysis run to background tasks
        background_tasks.add_task(
            job_service.run_analysis_pipeline,
            job_id,
            file.filename,
            is_zip=True
        )
        
        return ReviewResponse(job_id=job_id)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err)
        )
    except Exception as e:
        logger.error(f"Error saving uploaded ZIP archive: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unpack repository: {str(e)}"
        )

@router.get(
    "/status/{job_id}",
    response_model=StatusResponse,
    summary="Query Agent Pipeline Status"
)
async def get_job_status(
    job_id: str,
    job_service: JobService = Depends(get_job_service)
):
    """
    Retrieves current pipeline status, progress and stage description.
    """
    status_report = job_service.get_job_status(job_id)
    if not status_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job identifier {job_id} not found."
        )
    return status_report

@router.get(
    "/result/{job_id}",
    response_model=ResultResponse,
    summary="Retrieve Scan Result Report"
)
async def get_job_result(
    job_id: str,
    job_service: JobService = Depends(get_job_service)
):
    """
    Retrieves final markdown analysis report for completed jobs.
    """
    result_report = job_service.get_job_result(job_id)
    if not result_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job identifier {job_id} not found."
        )
    return result_report
