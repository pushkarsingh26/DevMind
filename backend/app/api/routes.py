from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from app.core.constants import TaskType
from app.models.request import ReviewRequest
from app.models.response import ReviewResponse, StatusResponse, ResultResponse
from app.api.dependencies import get_job_service, get_repository_service
from app.services.job_service import JobService
from app.services.repository_service import RepositoryService
from app.core.logger import logger
import os

from sqlalchemy.orm import Session
from app.db.session import get_db
from pydantic import BaseModel, Field
from typing import List

class RetrieveRequest(BaseModel):
    repository_id: str = Field(..., description="The repository ID to search in")
    query: str = Field(..., description="The semantic search query")
    top_k: int = Field(5, description="Number of top relevant chunks to return")

class RetrieveResult(BaseModel):
    path: str
    score: float
    start_line: int
    end_line: int
    content: str

class RetrieveResponse(BaseModel):
    results: List[RetrieveResult]


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

@router.get(
    "/repositories",
    summary="List all indexed repositories"
)
async def list_repositories(db: Session = Depends(get_db)):
    from app.models.repository import Repository
    from datetime import datetime
    repos = db.query(Repository).all()
    
    # Deduplicate: return only the latest record for each unique (owner, name) combo
    unique_repos = {}
    for r in sorted(repos, key=lambda x: x.created_at or datetime.min):
        unique_repos[(r.owner.lower(), r.name.lower())] = r
        
    return [
        {
            "id": r.id,
            "name": r.name,
            "owner": r.owner,
            "source": r.source,
            "framework": r.framework,
            "language": r.language,
            "repository_hash": r.repository_hash,
            "status": r.status,
            "created_at": r.created_at
        } for r in unique_repos.values()
    ]

@router.get(
    "/repositories/{id}",
    summary="Get repository metadata by ID"
)
async def get_repository(id: str, db: Session = Depends(get_db)):
    from app.models.repository import Repository
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    return {
        "id": repo.id,
        "name": repo.name,
        "owner": repo.owner,
        "source": repo.source,
        "framework": repo.framework,
        "language": repo.language,
        "repository_hash": repo.repository_hash,
        "status": repo.status,
        "created_at": repo.created_at
    }

@router.delete(
    "/repositories/{id}",
    summary="Delete a repository and its indices"
)
async def delete_repository(id: str, db: Session = Depends(get_db)):
    from app.models.repository import Repository
    from app.services.vector_store_service import vector_store_service
    from app.ai.cache import ai_cache
    
    repo = db.query(Repository).filter(Repository.id == id).first()
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    
    # Delete FAISS files
    try:
        vector_store_service.delete_vector_store(id)
    except Exception as e:
        logger.warning(f"Failed to delete vector store for {id}: {e}")

    # Delete AI Cache entries
    if repo.repository_hash:
        try:
            ai_cache.delete_cache_for_repo(repo.repository_hash)
        except Exception as e:
            logger.warning(f"Failed to delete cache for hash {repo.repository_hash}: {e}")
    try:
        ai_cache.delete_cache_for_repo(repo.id)
    except Exception as e:
        logger.warning(f"Failed to delete cache for id {repo.id}: {e}")

    # Delete database record (Cascade deletes Chunks, Embeddings, Conversations, Messages, Jobs)
    db.delete(repo)
    db.commit()
    return {"status": "success", "detail": f"Repository {id} deleted successfully."}

@router.delete(
    "/repositories",
    summary="Delete all repositories and reset the system"
)
async def delete_all_repositories(db: Session = Depends(get_db)):
    from app.models.repository import Repository
    from app.services.vector_store_service import vector_store_service
    from app.ai.cache import ai_cache
    
    repos = db.query(Repository).all()
    for repo in repos:
        try:
            vector_store_service.delete_vector_store(repo.id)
        except Exception as e:
            logger.warning(f"Failed to delete vector store for {repo.id}: {e}")
            
    for repo in repos:
        db.delete(repo)
    db.commit()
    
    try:
        ai_cache.clear()
    except Exception as e:
        logger.warning(f"Failed to clear AI cache: {e}")
        
    return {"status": "success", "detail": "All repositories and associated data deleted successfully."}

@router.post(
    "/retrieve",
    response_model=RetrieveResponse,
    summary="Semantic retrieval of code chunks"
)
async def retrieve(
    payload: RetrieveRequest,
    db: Session = Depends(get_db)
):
    from app.services.retrieval_service import retrieval_service
    from app.services.context_builder import context_builder
    
    retrieved = retrieval_service.retrieve_chunks(
        db=db,
        repository_id=payload.repository_id,
        query=payload.query,
        top_k=payload.top_k
    )
    
    context_results = context_builder.build_context(retrieved)
    return {"results": context_results}

