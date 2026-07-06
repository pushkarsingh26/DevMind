import os
import shutil
import zipfile
from app.core.logger import logger

def unzip_archive(zip_path: str, extract_path: str) -> bool:
    """
    Safely extracts a ZIP archive to a destination directory.
    """
    try:
        logger.info(f"Extracting zip {zip_path} into {extract_path}")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Prevent zip-slip vulnerability by verifying names
            for member in zip_ref.namelist():
                member_path = os.path.abspath(os.path.join(extract_path, member))
                target_dir = os.path.abspath(extract_path)
                if not member_path.startswith(target_dir):
                    raise Exception("Zip entry path traverses out of target directory bounds.")
            
            zip_ref.extractall(extract_path)
        return True
    except Exception as e:
        logger.error(f"Unpacking ZIP failed: {e}")
        return False

def clean_directory(dir_path: str) -> bool:
    """
    Completely deletes all contents inside a directory.
    """
    try:
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            os.makedirs(dir_path, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Cleaning directory failed: {e}")
        return False
