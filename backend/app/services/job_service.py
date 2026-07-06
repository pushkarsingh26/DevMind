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

    def create_job(self, task_type: TaskType, repo_identifier: str) -> str:
        """
        Creates and registers a new job structure in-memory.
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
            
        logger.info(f"Registered analysis job: {job_id} for {repo_identifier}")
        return job_id

    def update_status(self, job_id: str, status: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.status = status
                job.updated_at = time.time()

    def update_progress(self, job_id: str, progress: int, stage: str):
        with self._lock:
            job = self._jobs.get(job_id)
            if job:
                job.progress = progress
                job.current_stage = stage
                job.updated_at = time.time()

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
            # Convert internal JSON result format to Markdown for legacy UI compatibility
            markdown_report = self._serialize_json_to_markdown(job.result or {})
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
            # Delegate pipeline sequence execution to PipelineService
            result_json = pipeline_service.run_pipeline(
                job_id=job_id,
                source_path_or_url=source_path_or_url,
                is_zip=is_zip,
                progress_callback=lambda progress, stage: self.update_progress(job_id, progress, stage)
            )
            
            # Map dictionaries back to Pydantic models for storage
            metadata = RepositoryMetadata(**result_json["metadata"])
            chunks = [CodeChunk(**c) for c in result_json["chunks"]]
            
            # Record success state
            self.complete_job(job_id, result_json, metadata, chunks)
            
        except Exception as e:
            self.fail_job(job_id, str(e))

    def _serialize_json_to_markdown(self, result: Dict[str, Any]) -> str:
        repo = result.get("repository", {})
        metadata = result.get("metadata", {})
        stats = result.get("statistics", {})
        chunks = result.get("chunks", [])
        
        pkg_managers_str = ", ".join(metadata.get("package_managers", [])) if metadata.get("package_managers") else "None detected"
        
        deps_lines = []
        for name, ver in metadata.get("dependencies", {}).items():
            deps_lines.append(f"- `{name}`: `{ver}`")
        deps_str = "\n".join(deps_lines) if deps_lines else "None parsed"

        largest_files_lines = []
        for f in stats.get("largest_files", []):
            largest_files_lines.append(f"- `{f.get('path')}` ({f.get('size')} bytes)")
        largest_files_str = "\n".join(largest_files_lines) if largest_files_lines else "None recorded"

        extensions_lines = []
        for ext, count in stats.get("extensions", {}).items():
            extensions_lines.append(f"- `{ext}`: {count} files")
        extensions_str = "\n".join(extensions_lines) if extensions_lines else "None"

        return f"""# DevMind Real-Time Workspace Scan
- **Repository Name**: `{repo.get("name")}`
- **Repository Owner**: `{repo.get("owner")}`
- **Default Branch**: `{repo.get("default_branch")}`
- **Status**: `SUCCESS`

---

## 1. Codebase Architecture Summary
- **Primary Language**: `{metadata.get("primary_language")}`
- **Detected Framework**: `{metadata.get("framework")}`
- **Test Files Present**: `{"Yes" if metadata.get("tests_present") else "No"}`
- **Dockerfile Present**: `{"Yes" if metadata.get("docker_support") else "No"}`
- **GitHub Actions**: `{"Yes" if metadata.get("github_actions") else "No"}`
- **CI/CD Pipeline**: `{"Yes" if metadata.get("cicd") else "No"}`
- **License**: `{metadata.get("license")}`

## 2. Directory & File Stats
- **Total Files**: `{stats.get("total_files")}`
- **Total Folders**: `{stats.get("total_directories")}`
- **Retrieved Chunk Spans**: `{len(chunks)} chunks` *(stored in memory)*

### File Extensions Distribution
{extensions_str}

### Largest Files
{largest_files_str}

## 3. Package Managers & Dependencies
- **Package Managers**: `{pkg_managers_str}`

### Core Dependency Details
{deps_str}

---
*DevMind Real-Time Infrastructure - Phase 1*
"""

job_service = JobService()
