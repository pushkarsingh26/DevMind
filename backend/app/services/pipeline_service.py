import os
import time
from typing import Callable, Optional, Dict, Any

from app.core.config import settings
from app.core.logger import logger
from app.services.vector_store_service import vector_store_service
from app.services.chunk_service import chunk_service
from app.services.intelligence.intelligence_manager import intelligence_manager
from app.services.intelligence.intelligence_service import intelligence_service
from app.services.knowledge_graph import graph_manager  # Phase 8.2
from app.services.repository_service import repository_service
from app.services.scanner_service import scanner_service


class PipelineService:

    def _get_git_commit_hash(self, local_path: str) -> str:
        try:
            import git
            repo = git.Repo(local_path)
            return repo.head.commit.hexsha
        except Exception:
            return ""

    def _get_dir_hash(self, local_path: str) -> str:
        import hashlib
        try:
            hasher = hashlib.sha256()
            for root, _, files in os.walk(local_path):
                for file in sorted(files):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, local_path)
                    hasher.update(rel_path.encode('utf-8'))
                    try:
                        stat = os.stat(full_path)
                        hasher.update(str(stat.st_size).encode('utf-8'))
                    except Exception:
                        pass
            return hasher.hexdigest()[:32]
        except Exception:
            import uuid
            return uuid.uuid4().hex[:12]

    def _compute_repo_hash(self, local_path: str, is_zip: bool) -> str:
        if not is_zip:
            commit_hash = self._get_git_commit_hash(local_path)
            if commit_hash:
                return commit_hash
        return self._get_dir_hash(local_path)

    def _get_remote_commit_hash(self, repo_url: str) -> Optional[str]:
        import subprocess
        try:
            logger.info(f"Querying remote HEAD commit hash for: {repo_url}")
            result = subprocess.run(
                ["git", "ls-remote", repo_url, "HEAD"],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10
            )
            output = result.stdout.strip()
            if output:
                parts = output.split()
                if parts:
                    return parts[0]
        except Exception as e:
            logger.warning(f"Failed to query remote HEAD commit hash for {repo_url}: {e}")
        return None

    def run_pipeline(
        self,
        job_id: str,
        source_path_or_url: str,
        is_zip: bool,
        task_type: str = "review",
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Executes repository analysis pipeline (Cloning/ZIP -> Scanning -> Chunking -> RAG Indexing -> Report).
        Returns a structured dictionary (JSON) and deletes temporary directories.
        """
        logger.info(f"Pipeline started for job: {job_id} task: {task_type}")
        local_path = ""
        
        # Real-time backend processing stages
        stages = {
            15: "Planner: Repository discovery and metadata preparation",
            35: "Retriever: Chunk retrieval, embedding generation, and retrieval preparation",
            60: "Reviewer: Aggregating repository metadata, retrieved context, and task-specific information",
            85: "Critic: Report assembly, validation, and consistency checks",
            100: "Completed: Analysis successfully completed"
        }

        def notify_progress(prog: int):
            if progress_callback:
                stage_desc = stages.get(prog, "Processing pipeline execution")
                progress_callback(prog, stage_desc)

        try:
            notify_progress(15)

            from app.db.session import SessionLocal
            from app.models.repository import Repository
            from app.models.job import AnalysisJobORM
            from app.models.chunk import Chunk
            from app.services.chunk_service import CodeChunk

            # 1. Caching Check: Query remote commit hash BEFORE cloning (for git URLs only)
            if not is_zip:
                remote_hash = self._get_remote_commit_hash(source_path_or_url)
                if remote_hash:
                    with SessionLocal() as db:
                        existing_repo = (
                            db.query(Repository)
                            .filter(
                                Repository.source == source_path_or_url,
                                Repository.repository_hash == remote_hash,
                                Repository.status == "READY"
                            )
                            .first()
                        )

                        if existing_repo:
                            logger.info(f"Cache Hit! Skipping clone for READY repo {existing_repo.id}")
                            
                            # Align intermediate stages quickly
                            notify_progress(35)
                            notify_progress(60)
                            notify_progress(85)

                            # Associate job with this repository
                            db_job = db.query(AnalysisJobORM).filter(AnalysisJobORM.id == job_id).first()
                            if not db_job:
                                db_job = AnalysisJobORM(
                                    id=job_id,
                                    repository_id=existing_repo.id,
                                    task_type=task_type,
                                    status="completed",
                                    progress=100,
                                    current_stage="Analysis completed successfully"
                                )
                                db.add(db_job)
                                db.commit()
                            else:
                                db_job.repository_id = existing_repo.id
                                db_job.task_type = task_type
                                db.commit()

                            # Fetch chunks from DB
                            db_chunks = db.query(Chunk).filter(Chunk.repository_id == existing_repo.id).all()
                            
                            chunks = []
                            for c in db_chunks:
                                original_id = c.id.split(":", 1)[1] if ":" in c.id else c.id
                                chunks.append(CodeChunk(
                                    id=original_id,
                                    path=c.path,
                                    language=c.language,
                                    start_line=c.start_line,
                                    end_line=c.end_line,
                                    content=c.content,
                                    job_id=job_id
                                ))
                            
                            chunk_service._store[job_id] = chunks

                            result_json = {
                                "repository": {
                                    "id": existing_repo.id,
                                    "name": existing_repo.name,
                                    "owner": existing_repo.owner,
                                    "default_branch": existing_repo.default_branch or "Unknown"
                                },
                                "metadata": {
                                    "repository_name": existing_repo.name,
                                    "repository_owner": existing_repo.owner,
                                    "default_branch": existing_repo.default_branch or "Unknown",
                                    "primary_language": existing_repo.language or "Unknown",
                                    "framework": existing_repo.framework or "None",
                                    "package_managers": existing_repo.package_managers or [],
                                    "readme_present": existing_repo.readme_present if existing_repo.readme_present is not None else False,
                                    "license": existing_repo.license or "None",
                                    "docker_support": existing_repo.docker_support if existing_repo.docker_support is not None else False,
                                    "github_actions": existing_repo.github_actions if existing_repo.github_actions is not None else False,
                                    "cicd": existing_repo.cicd if existing_repo.cicd is not None else False,
                                    "tests_present": existing_repo.tests_present if existing_repo.tests_present is not None else False,
                                    "dependencies": existing_repo.dependencies or {},
                                    "total_files": existing_repo.total_files or 0,
                                    "directories": existing_repo.directories or 0,
                                    "extensions": existing_repo.extensions or {},
                                    "largest_files": existing_repo.largest_files or []
                                },
                                "statistics": {
                                    "total_files": existing_repo.total_files or 0,
                                    "total_directories": existing_repo.directories or 0,
                                    "extensions": existing_repo.extensions or {},
                                    "largest_files": existing_repo.largest_files or []
                                },
                                "chunks": [c.model_dump() for c in chunks],
                                "task_type": task_type,
                                "source_path_or_url": source_path_or_url
                            }
                            return result_json

            # 2. Cache Miss: Obtain local repository path
            if is_zip:
                extract_dir = os.path.abspath(os.path.join(str(settings.WORKSPACE_ROOT), job_id))
                if not os.path.exists(extract_dir):
                    raise Exception("Extracted repository workspace not found. Upload may have failed.")
                local_path = repository_service._detect_repo_root(extract_dir)
                if not local_path:
                    raise Exception("Repository root could not be detected. Unsupported archive structure.")
                branch = "uploaded"
                time.sleep(1)
            else:
                clone_res = repository_service.clone_repository(source_path_or_url, job_id)
                if not clone_res["clone_success"]:
                    raise Exception("Failed to clone target repository URL. Check repository visibility.")
                local_path = clone_res["local_path"]
                branch = clone_res["branch"]
                time.sleep(1)

            if not local_path or not os.path.exists(local_path):
                raise Exception("Local workspace checkout path could not be resolved.")

            repo_hash = self._compute_repo_hash(local_path, is_zip)

            with SessionLocal() as db:
                existing_repo = (
                    db.query(Repository)
                    .filter(
                        Repository.source == source_path_or_url,
                        Repository.repository_hash == repo_hash,
                        Repository.status == "READY"
                    )
                    .first()
                )

                if existing_repo:
                    logger.info(f"Cache Hit (post-ingest)! Re-using READY repository: {existing_repo.id}")
                    notify_progress(35)
                    notify_progress(60)
                    notify_progress(85)
                    
                    db_job = db.query(AnalysisJobORM).filter(AnalysisJobORM.id == job_id).first()
                    if not db_job:
                        db_job = AnalysisJobORM(
                            id=job_id,
                            repository_id=existing_repo.id,
                            task_type=task_type,
                            status="completed",
                            progress=100,
                            current_stage="Analysis completed successfully"
                        )
                        db.add(db_job)
                        db.commit()
                    else:
                        db_job.repository_id = existing_repo.id
                        db_job.task_type = task_type
                        db.commit()

                    db_chunks = db.query(Chunk).filter(Chunk.repository_id == existing_repo.id).all()
                    chunks = []
                    for c in db_chunks:
                        original_id = c.id.split(":", 1)[1] if ":" in c.id else c.id
                        chunks.append(CodeChunk(
                            id=original_id,
                            path=c.path,
                            language=c.language,
                            start_line=c.start_line,
                            end_line=c.end_line,
                            content=c.content,
                            job_id=job_id
                        ))
                    
                    chunk_service._store[job_id] = chunks

                    result_json = {
                        "repository": {
                            "id": existing_repo.id,
                            "name": existing_repo.name,
                            "owner": existing_repo.owner,
                            "default_branch": existing_repo.default_branch or "Unknown"
                        },
                        "metadata": {
                            "repository_name": existing_repo.name,
                            "repository_owner": existing_repo.owner,
                            "default_branch": existing_repo.default_branch or "Unknown",
                            "primary_language": existing_repo.language or "Unknown",
                            "framework": existing_repo.framework or "None",
                            "package_managers": existing_repo.package_managers or [],
                            "readme_present": existing_repo.readme_present if existing_repo.readme_present is not None else False,
                            "license": existing_repo.license or "None",
                            "docker_support": existing_repo.docker_support if existing_repo.docker_support is not None else False,
                            "github_actions": existing_repo.github_actions if existing_repo.github_actions is not None else False,
                            "cicd": existing_repo.cicd if existing_repo.cicd is not None else False,
                            "tests_present": existing_repo.tests_present if existing_repo.tests_present is not None else False,
                            "dependencies": existing_repo.dependencies or {},
                            "total_files": existing_repo.total_files or 0,
                            "directories": existing_repo.directories or 0,
                            "extensions": existing_repo.extensions or {},
                            "largest_files": existing_repo.largest_files or []
                        },
                        "statistics": {
                            "total_files": existing_repo.total_files or 0,
                            "total_directories": existing_repo.directories or 0,
                            "extensions": existing_repo.extensions or {},
                            "largest_files": existing_repo.largest_files or []
                        },
                        "chunks": [c.model_dump() for c in chunks],
                        "task_type": task_type,
                        "source_path_or_url": source_path_or_url
                    }
                    return result_json

            # 3. Fresh Scan & Chunk (Retriever stage)
            notify_progress(35)
            metadata = scanner_service.scan_repository(
                local_path=local_path,
                repo_url=None if is_zip else source_path_or_url,
                branch=branch
            )
            time.sleep(1)

            chunks = chunk_service.chunk_repository(local_path, job_id)
            time.sleep(1)

            # 4. Persistence (Reviewer stage)
            notify_progress(60)
            import uuid
            with SessionLocal() as db:
                if is_zip:
                    existing_repo = db.query(Repository).filter(
                        Repository.name == metadata.repository_name,
                        Repository.owner == metadata.repository_owner
                    ).first()
                else:
                    existing_repo = db.query(Repository).filter(
                        Repository.source == source_path_or_url
                    ).first()

                if existing_repo:
                    repo_id = existing_repo.id
                    existing_repo.name = metadata.repository_name
                    existing_repo.owner = metadata.repository_owner
                    existing_repo.framework = metadata.framework
                    existing_repo.language = metadata.primary_language
                    existing_repo.repository_hash = repo_hash
                    existing_repo.status = "INDEXING"
                    existing_repo.default_branch = metadata.default_branch
                    existing_repo.readme_present = metadata.readme_present
                    existing_repo.license = metadata.license
                    existing_repo.docker_support = metadata.docker_support
                    existing_repo.github_actions = metadata.github_actions
                    existing_repo.cicd = metadata.cicd
                    existing_repo.tests_present = metadata.tests_present
                    existing_repo.total_files = metadata.total_files
                    existing_repo.directories = metadata.directories
                    existing_repo.extensions = metadata.extensions
                    existing_repo.largest_files = [f.model_dump() for f in metadata.largest_files]
                    existing_repo.dependencies = metadata.dependencies
                    existing_repo.package_managers = metadata.package_managers
                    db.commit()
                    vector_store_service.invalidate_cache(repo_id)
                else:
                    repo_id = f"repo_{uuid.uuid4().hex[:12]}"
                    repo = Repository(
                        id=repo_id,
                        name=metadata.repository_name,
                        owner=metadata.repository_owner,
                        source=source_path_or_url,
                        framework=metadata.framework,
                        language=metadata.primary_language,
                        repository_hash=repo_hash,
                        status="INDEXING",
                        default_branch=metadata.default_branch,
                        readme_present=metadata.readme_present,
                        license=metadata.license,
                        docker_support=metadata.docker_support,
                        github_actions=metadata.github_actions,
                        cicd=metadata.cicd,
                        tests_present=metadata.tests_present,
                        total_files=metadata.total_files,
                        directories=metadata.directories,
                        extensions=metadata.extensions,
                        largest_files=[f.model_dump() for f in metadata.largest_files],
                        dependencies=metadata.dependencies,
                        package_managers=metadata.package_managers
                    )
                    db.add(repo)
                    db.commit()

                db_job = db.query(AnalysisJobORM).filter(AnalysisJobORM.id == job_id).first()
                if not db_job:
                    db_job = AnalysisJobORM(
                        id=job_id,
                        repository_id=repo_id,
                        task_type=task_type,
                        status="running",
                        progress=60,
                        current_stage="Reviewer stage"
                    )
                    db.add(db_job)
                    db.commit()
                else:
                    db_job.repository_id = repo_id
                    db_job.task_type = task_type
                    db.commit()

                from app.services.rag_service import rag_service
                rag_service.index_repository(db, repo_id, job_id, chunks)

            # 4b. Build Repository Intelligence
            try:
                intel_result = intelligence_service.build_intelligence(
                    repo_path=local_path,
                    repo_id=repo_id,
                    repo_hash=repo_hash,
                )
                intelligence_manager.load(
                    repo_id=repo_id,
                    intelligence_path=intel_result["intelligence_path"],
                    repo_hash=intel_result["repo_hash"],
                )
                # Persist intelligence_path in DB
                with SessionLocal() as db:
                    from app.models.repository import Repository
                    repo_row = db.query(Repository).filter(Repository.id == repo_id).first()
                    if repo_row is not None:
                        repo_row.intelligence_path = intel_result["intelligence_path"]
                        db.commit()
                logger.info(
                    f"[Pipeline] Intelligence built for {repo_id} "
                    f"in {intel_result['build_time_ms']} ms"
                )
            except Exception as intel_exc:
                logger.warning(f"[Pipeline] Intelligence build failed for {repo_id}: {intel_exc}")

            # 4c. Build Knowledge Graph (delegated to GraphManager)
            try:
                intel_path = intel_result.get("intelligence_path", "") if 'intel_result' in dir() else ""
                if intel_path:
                    graph_manager.ensure_graph(repo_id, intel_path, repo_hash)
                    logger.info(f"[Pipeline] Knowledge graph ensured for {repo_id}")
            except Exception as graph_exc:
                logger.warning(f"[Pipeline] Knowledge graph build failed for {repo_id}: {graph_exc}")

            # 4d. Build Repository Analysis
            try:
                intel_path = intel_result.get("intelligence_path", "") if 'intel_result' in dir() else ""
                if intel_path:
                    from app.services.repository_analysis.analysis_engine import repository_analysis_engine
                    repository_analysis_engine.ensure_analysis(repo_id, intel_path, repo_hash)
                    logger.info(f"[Pipeline] Repository analysis ensured for {repo_id}")
            except Exception as analysis_exc:
                logger.warning(f"[Pipeline] Repository analysis build failed for {repo_id}: {analysis_exc}")

            # 5. Critic Report Formatting
            notify_progress(85)
            time.sleep(1)

            result_json = {
                "repository": {
                    "id": repo_id,
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
                "chunks": [c.model_dump() for c in chunks],
                "task_type": task_type,
                "source_path_or_url": source_path_or_url
            }
            
            return result_json

        except Exception as e:
            logger.error(f"Error in pipeline run for job {job_id}: {e}")
            raise e
        finally:
            repository_service.delete_repository(job_id)

pipeline_service = PipelineService()
