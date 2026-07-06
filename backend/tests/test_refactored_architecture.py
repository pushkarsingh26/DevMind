import os
import sys
import pytest

# Configure python path to find app directory relative to tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from app.services.pipeline_service import pipeline_service
from app.services.job_service import job_service
from app.services.scanner_service import scanner_service
from app.services.chunk_service import chunk_service

def test_pipeline_service_returns_structured_json():
    """
    Verifies that PipelineService.run_pipeline produces structured JSON results
    with correct repository info, metadata, stats, and chunk attributes.
    """
    # Use our current repository workspace for a local pipeline run
    job_id = "test_job_123"
    current_dir = os.path.abspath(os.path.dirname(__file__))
    local_path = os.path.abspath(os.path.join(current_dir, "../../"))
    
    # Run scanner directly
    metadata = scanner_service.scan_repository(local_path)
    
    # Verify metadata fields
    assert metadata.repository_name == "DevMind"
    assert metadata.repository_owner in ("pushkarsingh26", "Unknown")
    assert metadata.license in ("MIT", "None", "Custom License")
    assert metadata.total_files > 0
    assert metadata.directories > 0
    assert isinstance(metadata.extensions, dict)
    assert len(metadata.largest_files) <= 5
    
    # Run chunks directly
    chunks = chunk_service.chunk_repository(local_path, job_id)
    if chunks:
        chunk = chunks[0]
        assert chunk.job_id == job_id
        assert chunk.start_line > 0
        assert chunk.end_line >= chunk.start_line
        assert len(chunk.content) > 0
        
    # Set up temp folder to match what is_zip expects
    from app.core.config import settings
    test_temp_dir = os.path.abspath(os.path.join(str(settings.WORKSPACE_ROOT), job_id))
    os.makedirs(test_temp_dir, exist_ok=True)
    with open(os.path.join(test_temp_dir, "hello.py"), "w") as f:
        f.write("def hello():\n    print('Hello World')\n")

    # Run the full pipeline directly (using is_zip=True to use local path bypass)
    result = pipeline_service.run_pipeline(
        job_id=job_id,
        source_path_or_url="hello.zip",
        is_zip=True
    )
    
    # Assert JSON structure keys
    assert "repository" in result
    assert "metadata" in result
    assert "statistics" in result
    assert "chunks" in result
    
    repo = result["repository"]
    assert repo["name"] == "test_job_123"
    
    stats = result["statistics"]
    assert stats["total_files"] == 1
    
    # Clean up chunks
    chunk_service.delete_chunks(job_id)

def test_job_service_registry_state():
    """
    Verifies JobService registers, completes, and fails jobs without running the background thread.
    """
    job_id = job_service.create_job("review", "test_repo")
    
    # Check initial values
    job = job_service.get_job(job_id)
    assert job is not None
    assert job.status == "running"
    assert job.progress == 5
    assert job.current_stage == "Initializing Pipeline"
    
    # Test update progress
    job_service.update_progress(job_id, 50, "Scanning files")
    job = job_service.get_job(job_id)
    assert job.progress == 50
    assert job.current_stage == "Scanning files"
    
    # Test complete job
    mock_result = {
        "repository": {"name": "test_repo", "owner": "Unknown", "default_branch": "Unknown"},
        "metadata": {},
        "statistics": {"total_files": 0, "total_directories": 0, "extensions": {}, "largest_files": []},
        "chunks": []
    }
    
    from app.services.scanner_service import RepositoryMetadata
    mock_metadata = RepositoryMetadata(
        repository_name="test_repo",
        repository_owner="Unknown",
        default_branch="Unknown",
        primary_language="Python",
        framework="None",
        package_managers=[],
        readme_present=False,
        license="None",
        docker_support=False,
        github_actions=False,
        cicd=False,
        tests_present=False,
        dependencies={},
        total_files=0,
        directories=0,
        extensions={},
        largest_files=[]
    )
    
    job_service.complete_job(job_id, mock_result, mock_metadata, [])
    job = job_service.get_job(job_id)
    assert job.status == "completed"
    assert job.progress == 100
    assert job.result == mock_result
    
    # Test result rendering
    result_response = job_service.get_job_result(job_id)
    assert result_response.status == "completed"
    assert "# DevMind Real-Time Workspace Scan" in result_response.result
