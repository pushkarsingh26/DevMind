import os
import shutil
import zipfile
import git
from app.core.config import settings
from app.core.logger import logger
import stat

def handle_remove_readonly(func, path, exc_info):
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass

class RepositoryService:
    def __init__(self, workspace_root: str = str(settings.WORKSPACE_ROOT)):
        self.temp_dir = workspace_root
        os.makedirs(self.temp_dir, exist_ok=True)

    def clone_repository(self, repo_url: str, job_id: str) -> dict:
        """
        Clones a remote git repository into WORKSPACE_ROOT/{job_id} using GitPython.
        Validates repository exists and checks out depth 1.
        """
        logger.info(f"Cloning repository: {repo_url} for job {job_id}")
        local_path = os.path.join(self.temp_dir, job_id)
        
        # Clean up any leftover folders
        if os.path.exists(local_path):
            shutil.rmtree(local_path, onerror=handle_remove_readonly)
            
        os.makedirs(local_path, exist_ok=True)
        
        repository_name = repo_url.split("/")[-1].replace(".git", "")
        if not repository_name:
            repository_name = "cloned_repo"
            
        try:
            # Clone with depth=1
            repo = git.Repo.clone_from(repo_url, local_path, depth=1)
            
            # Retrieve active branch name safely
            try:
                branch = repo.active_branch.name
            except TypeError:
                # Occurs if HEAD is detached
                branch = "detached-HEAD"
                
            logger.info(f"Git clone succeeded for {repo_url} on branch {branch}")
            return {
                "local_path": local_path,
                "repository_name": repository_name,
                "branch": branch,
                "clone_success": True
            }
        except git.exc.GitCommandError as e:
            logger.error(f"Git command error cloning {repo_url}: {e.stderr or str(e)}")
            self.delete_repository(job_id)
            return {
                "local_path": "",
                "repository_name": repository_name,
                "branch": "",
                "clone_success": False
            }
        except Exception as e:
            logger.error(f"Unexpected error cloning {repo_url}: {e}")
            self.delete_repository(job_id)
            return {
                "local_path": "",
                "repository_name": repository_name,
                "branch": "",
                "clone_success": False
            }

    def delete_repository(self, job_id: str):
        """
        Deletes the temporary repository files for a completed or failed job.
        Also cleans up any leftover ZIP file.
        """
        local_path = os.path.join(self.temp_dir, job_id)
        if os.path.exists(local_path):
            try:
                shutil.rmtree(local_path, onerror=handle_remove_readonly)
                logger.info(f"Successfully cleaned up temporary directory: {local_path}")
            except Exception as e:
                logger.error(f"Failed to delete directory {local_path}: {e}")
        # Also clean up any leftover ZIP file
        self.delete_zip_file(job_id)

    def ingest_zip(self, job_id: str, file_bytes: bytes, original_filename: str) -> dict:
        """
        Receives uploaded ZIP bytes, extracts into WORKSPACE_ROOT/{job_id},
        detects the actual repository root, and returns metadata identical
        to clone_repository() so the downstream pipeline is unified.
        """
        logger.info(f"Ingesting ZIP upload: {original_filename} for job {job_id}")

        zip_path = os.path.join(self.temp_dir, f"{job_id}.zip")
        extract_dir = os.path.join(self.temp_dir, job_id)

        # 1. Save ZIP bytes to disk
        try:
            os.makedirs(self.temp_dir, exist_ok=True)
            with open(zip_path, "wb") as f:
                f.write(file_bytes)
        except Exception as e:
            logger.error(f"Failed to save uploaded ZIP to disk: {e}")
            raise ValueError(f"Failed to save uploaded archive: {str(e)}")

        # 2. Validate that the file is a real ZIP archive
        if not zipfile.is_zipfile(zip_path):
            self.delete_zip_file(job_id)
            raise ValueError("Uploaded archive could not be extracted. The file is not a valid ZIP archive.")

        # 3. Extract ZIP contents
        try:
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir, onerror=handle_remove_readonly)
            os.makedirs(extract_dir, exist_ok=True)

            with zipfile.ZipFile(zip_path, "r") as zf:
                members = zf.namelist()
                if not members:
                    self.delete_zip_file(job_id)
                    raise ValueError("Uploaded ZIP is empty.")
                zf.extractall(extract_dir)
        except ValueError:
            # Re-raise our own ValueErrors (empty zip, etc.)
            raise
        except Exception as e:
            logger.error(f"Failed to extract ZIP archive: {e}")
            self.delete_zip_file(job_id)
            raise ValueError(f"Uploaded archive could not be extracted: {str(e)}")

        # 4. Remove the .zip file now that extraction succeeded
        self.delete_zip_file(job_id)

        # 5. Detect the real repository root
        repo_root = self._detect_repo_root(extract_dir)
        if not repo_root:
            raise ValueError("Repository root could not be detected. Unsupported archive structure.")

        # 6. Infer repository name from original filename or detected root folder
        repo_name = os.path.basename(repo_root)
        if repo_name == job_id or not repo_name:
            # Fall back to original filename without extension
            repo_name = os.path.splitext(original_filename)[0] if original_filename else "uploaded_repo"

        logger.info(f"ZIP ingestion complete for job {job_id}: root={repo_root}, name={repo_name}")
        return {
            "local_path": repo_root,
            "repository_name": repo_name,
            "branch": "uploaded",
            "clone_success": True
        }

    def _detect_repo_root(self, extract_dir: str) -> str:
        """
        Detects the actual repository root inside an extracted ZIP.

        Some ZIPs extract directly into the target folder, others wrap
        everything inside a single subfolder (e.g., project-main/).
        This method unwraps one level of wrapper folder if present.
        """
        try:
            entries = os.listdir(extract_dir)
        except Exception:
            return ""

        # Filter out macOS resource fork artifacts
        entries = [e for e in entries if e != "__MACOSX"]

        if not entries:
            return ""

        # If exactly one directory and zero files → unwrap the wrapper
        if len(entries) == 1:
            sole_entry = os.path.join(extract_dir, entries[0])
            if os.path.isdir(sole_entry):
                return sole_entry

        # Otherwise the extraction root itself is the repo root
        return extract_dir

    def delete_zip_file(self, job_id: str):
        """
        Removes the uploaded .zip file from the workspace if it still exists.
        """
        zip_path = os.path.join(self.temp_dir, f"{job_id}.zip")
        if os.path.exists(zip_path):
            try:
                os.remove(zip_path)
                logger.info(f"Removed ZIP file: {zip_path}")
            except Exception as e:
                logger.error(f"Failed to remove ZIP file {zip_path}: {e}")

repository_service = RepositoryService()
