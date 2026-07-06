import os
import time
from typing import Callable, Optional, Dict, Any
from app.core.config import settings
from app.services.repository_service import repository_service
from app.services.scanner_service import scanner_service
from app.services.chunk_service import chunk_service
from app.core.logger import logger

class PipelineService:
    def run_pipeline(
        self,
        job_id: str,
        source_path_or_url: str,
        is_zip: bool,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes repository analysis pipeline (Cloning -> Scanning -> Chunking -> Report).
        Returns a structured dictionary (JSON) and deletes temporary directories.
        """
        logger.info(f"Pipeline started for job: {job_id}")
        local_path = ""
        
        try:
            # 1. Obtain local repository path
            if is_zip:
                if progress_callback:
                    progress_callback(15, "Processing uploaded repository archive")
                # ZIP was already extracted by routes.py via ingest_zip().
                # Detect the repo root within the existing extraction directory.
                extract_dir = os.path.abspath(os.path.join(str(settings.WORKSPACE_ROOT), job_id))
                if not os.path.exists(extract_dir):
                    raise Exception("Extracted repository workspace not found. Upload may have failed.")
                local_path = repository_service._detect_repo_root(extract_dir)
                if not local_path:
                    raise Exception("Repository root could not be detected. Unsupported archive structure.")
                branch = "uploaded"
                time.sleep(1)  # Visual pacing for UI monitor
            else:
                if progress_callback:
                    progress_callback(15, "Cloning remote GitHub repository")
                clone_res = repository_service.clone_repository(source_path_or_url, job_id)
                if not clone_res["clone_success"]:
                    raise Exception("Failed to clone target repository URL. Check repository visibility.")
                local_path = clone_res["local_path"]
                branch = clone_res["branch"]
                time.sleep(1)

            if not local_path or not os.path.exists(local_path):
                raise Exception("Local workspace checkout path could not be resolved.")

            # 2. Scan repository metadata
            if progress_callback:
                progress_callback(45, "Scanning codebase and collecting metadata")
            metadata = scanner_service.scan_repository(
                local_path=local_path,
                repo_url=None if is_zip else source_path_or_url,
                branch=branch
            )
            time.sleep(1)

            # 3. Chunk source code files
            if progress_callback:
                progress_callback(75, "Chunking source code files for retrieval index")
            chunks = chunk_service.chunk_repository(local_path, job_id)
            time.sleep(1)

            if progress_callback:
                progress_callback(95, "Compiling analysis reports")

            # 4. Compile structured JSON result
            result_json = {
                "repository": {
                    "name": metadata.repository_name,
                    "owner": metadata.repository_owner,
                    "default_branch": metadata.default_branch
                },
                "metadata": metadata.model_dump(),
                "statistics": {
                    "total_files": metadata.total_files,
                    "total_directories": metadata.directories,
                    "extensions": metadata.extensions,
                    "largest_files": [f.model_dump() for f in metadata.largest_files]
                },
                "chunks": [c.model_dump() for c in chunks]
            }
            
            return result_json

        except Exception as e:
            logger.error(f"Error in pipeline run for job {job_id}: {e}")
            raise e
        finally:
            # Purge local temp repo folder
            repository_service.delete_repository(job_id)

pipeline_service = PipelineService()
