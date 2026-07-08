import time
import threading
from typing import Dict, Optional, Any
from app.core.constants import TaskType
from app.models.job import AnalysisJob
from app.models.response import StatusResponse, ResultResponse
from app.services.pipeline_service import pipeline_service
from app.services.scanner_service import RepositoryMetadata
from app.services.chunk_service import CodeChunk
from app.core.logger import logger

class JobService:
    def __init__(self):
        self._jobs: Dict[str, AnalysisJob] = {}
        self._lock = threading.Lock()

    def _update_db_job(self, job_id: str, status: str, progress: int = None, stage: str = None, result_json: Dict[str, Any] = None, error: str = None):
        try:
            from app.db.session import SessionLocal
            from app.models.job import AnalysisJobORM
            import json
            with SessionLocal() as db:
                db_job = db.query(AnalysisJobORM).filter(AnalysisJobORM.id == job_id).first()
                if db_job:
                    db_job.status = status
                    if progress is not None:
                        db_job.progress = progress
                    if stage is not None:
                        db_job.current_stage = stage
                    if result_json is not None:
                        db_job.result = json.dumps(result_json)
                    if error is not None:
                        db_job.error = error
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to update database job {job_id}: {e}")

    def create_job(self, task_type: TaskType, repo_identifier: str) -> str:
        """
        Creates and registers a new job structure in-memory and database.
        """
        import uuid
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = time.time()
        
        with self._lock:
            self._jobs[job_id] = AnalysisJob(
                id=job_id,
                task_type=task_type,
                repo_identifier=repo_identifier,
                start_time=now,
                status="running",
                progress=5,
                current_stage="Initializing Pipeline",
                created_at=now,
                updated_at=now
            )
            
        # DB persistence
        try:
            from app.db.session import SessionLocal
            from app.models.job import AnalysisJobORM
            with SessionLocal() as db:
                db_job = AnalysisJobORM(
                    id=job_id,
                    repository_id=None,
                    task_type=str(task_type.value) if hasattr(task_type, "value") else str(task_type),
                    status="running",
                    progress=5,
                    current_stage="Initializing Pipeline"
                )
                db.add(db_job)
                db.commit()
        except Exception as e:
            logger.error(f"Failed to persist job {job_id} to database: {e}")

        logger.info(f"Registered analysis job: {job_id} for {repo_identifier}")
        return job_id

    def update_status(self, job_id: str, status: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = status
                job.updated_at = time.time()
        self._update_db_job(job_id, status=status)

    def update_progress(self, job_id: str, progress: int, stage: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.progress = progress
                job.current_stage = stage
                job.updated_at = time.time()
        self._update_db_job(job_id, status="running", progress=progress, stage=stage)

    def complete_job(self, job_id: str, result_json: Dict[str, Any], metadata: RepositoryMetadata, chunks: list[CodeChunk]):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "completed"
                job.progress = 100
                job.current_stage = "Analysis completed successfully"
                job.result = result_json
                job.repository_metadata = metadata
                job.chunks = chunks
                job.updated_at = time.time()
        self._update_db_job(job_id, status="completed", progress=100, stage="Analysis completed successfully", result_json=result_json)
        logger.info(f"Completed analysis job: {job_id}")

    def fail_job(self, job_id: str, error_message: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = "failed"
                job.progress = 0
                job.current_stage = "Failed"
                job.error = error_message
                job.updated_at = time.time()
        self._update_db_job(job_id, status="failed", progress=0, stage="Failed", error=error_message)
        logger.error(f"Failed analysis job {job_id}: {error_message}")


    def get_job(self, job_id: str) -> Optional[AnalysisJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def get_job_status(self, job_id: str) -> Optional[StatusResponse]:
        """
        Retrieves the current running status of a job. Maps current_stage to stage.
        """
        job = self.get_job(job_id)
        if not job:
            return None
            
        return StatusResponse(
            status=job.status,
            progress=job.progress,
            stage=job.current_stage
        )

    def get_job_result(self, job_id: str) -> Optional[ResultResponse]:
        """
        Retrieves the final results for a job, converting structured JSON to Markdown.
        """
        job = self.get_job(job_id)
        if not job:
            return None
            
        if job.status == "completed":
            from app.report_builders.review_report import ReviewReportBuilder
            from app.report_builders.explain_report import ExplainReportBuilder
            from app.report_builders.tests_report import TestsReportBuilder
            from app.report_builders.bugs_report import BugsReportBuilder

            builders = {
                "review": ReviewReportBuilder(),
                "explain": ExplainReportBuilder(),
                "tests": TestsReportBuilder(),
                "bugs": BugsReportBuilder()
            }

            task_type = job.task_type if hasattr(job, "task_type") else "review"
            task_key = str(task_type).lower().strip()
            builder = builders.get(task_key, builders["review"])

            # Call report builder on the JSON payload
            markdown_report = builder.build_report(job.result or {})
            return ResultResponse(status="completed", result=markdown_report)
        elif job.status == "failed":
            return ResultResponse(status="failed", result=f"Analysis failed: {job.error or job.current_stage}")
        else:
            return ResultResponse(status="processing", result=None)

    def run_analysis_pipeline(self, job_id: str, source_path_or_url: str, is_zip: bool):
        """
        Background task thread. Decouples job registry updates from the Pipeline execution logic.
        """
        try:
            job = self.get_job(job_id)
            task_type = job.task_type if job else "review"
            
            # Delegate pipeline sequence execution to PipelineService
            result_json = pipeline_service.run_pipeline(
                job_id=job_id,
                source_path_or_url=source_path_or_url,
                is_zip=is_zip,
                task_type=task_type,
                progress_callback=lambda progress, stage: self.update_progress(job_id, progress, stage)
            )
            
            # Map dictionaries back to Pydantic models for storage
            metadata = RepositoryMetadata(**result_json["metadata"])
            chunks = [CodeChunk(**c) for c in result_json["chunks"]]
            
            # Record success state
            self.complete_job(job_id, result_json, metadata, chunks)
            
        except Exception as e:
            self.fail_job(job_id, str(e))

    def _serialize_json_to_markdown(self, result: Dict[str, Any], task_type: str = "review") -> str:
        from app.report_builders.review_report import ReviewReportBuilder
        from app.report_builders.explain_report import ExplainReportBuilder
        from app.report_builders.tests_report import TestsReportBuilder
        from app.report_builders.bugs_report import BugsReportBuilder

        builders = {
            "review": ReviewReportBuilder(),
            "explain": ExplainReportBuilder(),
            "tests": TestsReportBuilder(),
            "bugs": BugsReportBuilder()
        }
        task_key = str(task_type).lower().strip()
        builder = builders.get(task_key, builders["review"])
        return builder.build_report(result)

job_service = JobService()



