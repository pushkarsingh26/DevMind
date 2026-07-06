import os
import sys

# Configure python path to find app directory relative to tests
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    """
    Verifies that the root health check endpoint is active.
    """
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "DevMind"

def test_analyze_url_success():
    """
    Verifies submitting a GitHub URL successfully creates a job_id.
    """
    payload = {
        "repo_url": "https://github.com/pushkarsingh26/DevMind",
        "task": "review"
    }
    response = client.post("/review", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "job_id" in data
    assert data["job_id"].startswith("job_")

def test_analyze_url_validation_error():
    """
    Verifies that invalid task type strings trigger schema validation errors.
    """
    payload = {
        "repo_url": "https://github.com/pushkarsingh26/DevMind",
        "task": "invalid-task-type"
    }
    response = client.post("/review", json=payload)
    assert response.status_code == 422 # Unprocessable Entity

def test_get_job_status_success():
    """
    Verifies that we can poll status, progress percentage, and active stage.
    """
    # Create a job first
    payload = {
        "repo_url": "https://github.com/pushkarsingh26/DevMind",
        "task": "explain"
    }
    create_res = client.post("/review", json=payload)
    job_id = create_res.json()["job_id"]

    # Query status
    status_res = client.get(f"/status/{job_id}")
    assert status_res.status_code == 200
    data = status_res.json()
    
    assert "status" in data
    assert "progress" in data
    assert "stage" in data
    
    assert data["status"] in ("running", "completed")
    assert isinstance(data["progress"], int)
    assert isinstance(data["stage"], str)

def test_get_job_result_processing():
    """
    Verifies that results initially return status processing before pipeline completes.
    """
    # Register a job directly to memory without starting the background task thread
    from app.services.job_service import job_service
    job_id = job_service.create_job("tests", "https://github.com/pushkarsingh26/DevMind")

    # Query result
    result_res = client.get(f"/result/{job_id}")
    assert result_res.status_code == 200
    data = result_res.json()
    
    assert data["status"] == "processing"
    assert data["result"] is None

def test_get_job_status_not_found():
    """
    Verifies that non-existent job IDs return a 404 HTTP exception.
    """
    response = client.get("/status/job_does_not_exist")
    assert response.status_code == 404
