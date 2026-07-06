import subprocess
from app.core.logger import logger

def clone_repo(repo_url: str, destination_path: str) -> bool:
    """
    Clones a remote git repository to a local destination path.
    In Phase 1, we capture errors and log operations.
    """
    try:
        logger.info(f"Executing git clone for {repo_url} into {destination_path}")
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, destination_path],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        logger.info(f"Git clone succeeded: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Git clone process failed with return code {e.returncode}: {e.stderr}")
        return False
    except FileNotFoundError:
        logger.error("Git binary was not found in systems environment PATH.")
        return False
    except Exception as e:
        logger.error(f"Unexpected error cloning repository {repo_url}: {e}")
        return False
