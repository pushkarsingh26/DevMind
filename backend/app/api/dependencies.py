from app.services.job_service import JobService, job_service
from app.services.repository_service import RepositoryService, repository_service
from app.services.scanner_service import ScannerService, scanner_service
from app.services.chunk_service import ChunkService, chunk_service

def get_job_service() -> JobService:
    return job_service

def get_repository_service() -> RepositoryService:
    return repository_service

def get_scanner_service() -> ScannerService:
    return scanner_service

def get_chunk_service() -> ChunkService:
    return chunk_service
