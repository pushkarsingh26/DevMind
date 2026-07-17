"""Unit tests for Memory & Learning Engine — Phase 8.7."""

from __future__ import annotations

import tempfile
import shutil
from pathlib import Path
import pytest

from app.services.memory.memory_models import RepositoryMemory, WorkflowMemory
from app.services.memory.memory_storage import MemoryStorage
from app.services.memory.workflow_memory import build_workflow_memory
from app.services.memory.repository_memory import update_repository_memory
from app.services.memory.pattern_engine import detect_patterns
from app.services.memory.recommendation_engine import generate_recommendations
from app.services.memory.learning_engine import LearningEngine


@pytest.fixture
def temp_storage():
    """Fixture that patches MemoryStorage memory directories to use a temp directory."""
    temp_dir = tempfile.mkdtemp()
    storage = MemoryStorage()
    # Override get_memory_dir to point to our temp folder
    original_get_memory_dir = storage.get_memory_dir
    storage.get_memory_dir = lambda repo_id: Path(temp_dir) / repo_id / "memory"
    
    yield storage, temp_dir
    
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_memory_models_and_serialization():
    # Verify RepositoryMemory instantiation and roundtrip
    memory = RepositoryMemory(
        repository_id="test_repo",
        repository_hash="h1",
        recurring_files=["app/main.py"],
        frequently_modified_modules=["main"],
        hotspot_history={"app/main.py": 5},
        dependency_history=["fastapi"],
        architecture_history=["refactoring"],
        language_history={"python": 5}
    )
    
    data = memory.to_dict()
    assert data["repository_id"] == "test_repo"
    assert data["repository_hash"] == "h1"
    assert "app/main.py" in data["recurring_files"]
    assert data["hotspot_history"]["app/main.py"] == 5

    loaded = RepositoryMemory.from_dict(data)
    assert loaded.repository_id == "test_repo"
    assert loaded.repository_hash == "h1"
    assert loaded.recurring_files == ["app/main.py"]
    assert loaded.hotspot_history["app/main.py"] == 5


def test_memory_storage_save_load_and_invalidation(temp_storage):
    storage, _ = temp_storage
    repo_id = "storage_repo"
    repo_hash = "h1"

    memory = RepositoryMemory(repository_id=repo_id, repository_hash=repo_hash)
    workflow = build_workflow_memory(
        workflow_id="wf_001",
        goal="Test security scanner",
        intent="Security Audit",
        execution_plan={"steps": [{"step_id": "s1", "agent": "Security Agent", "files": ["app/auth.py"]}]},
        execution_metrics={"retry_count": 0, "cache_hits": 2, "cache_misses": 1, "tokens_used": 500},
        collaboration_summary={"overall_confidence": 0.9},
        findings=[{"title": "JWT secret vulnerability", "file_path": "app/auth.py", "category": "Security"}],
        duration=12.5,
        provider_usage=["Google AI Studio"],
        success=True
    )

    # Save
    ok = storage.save(
        repository_id=repo_id,
        memory=memory,
        patterns=[],
        recommendations=[],
        metrics=LearningEngine()._calculate_metrics([workflow], []),
        history=[workflow]
    )
    assert ok is True

    # Validate cache
    assert storage.validate_cache(repo_id, repo_hash) is True
    assert storage.validate_cache(repo_id, "wrong_hash") is False

    # Load
    loaded = storage.load(repo_id)
    assert loaded is not None
    loaded_mem, loaded_pats, loaded_recs, loaded_metrics, loaded_hist = loaded
    assert loaded_mem.repository_id == repo_id
    assert loaded_mem.repository_hash == repo_hash
    assert len(loaded_hist) == 1
    assert loaded_hist[0].workflow_id == "wf_001"
    assert loaded_metrics.workflow_success_rate == 1.0

    # Invalidate
    storage.invalidate(repo_id)
    assert storage.load(repo_id) is None
    assert storage.validate_cache(repo_id, repo_hash) is False


def test_repository_memory_accumulation():
    memory = RepositoryMemory(repository_id="acc_repo", repository_hash="h1")
    
    # Run 1: Adds some hotspots
    wf1 = build_workflow_memory(
        workflow_id="wf1",
        goal="Refactor controllers",
        intent="Refactoring",
        execution_plan={"steps": [{"step_id": "s1", "agent": "Refactor Agent", "files": ["controllers/user.py"]}]},
        execution_metrics={},
        collaboration_summary={},
        findings=[{"title": "High coupling in User Controller", "file_path": "controllers/user.py", "category": "Refactoring"}],
        duration=10.0,
        provider_usage=[],
        success=True
    )
    
    update_repository_memory(memory, wf1)
    assert memory.hotspot_history["controllers/user.py"] == 2  # 1 from finding, 1 from plan steps
    assert "Refactoring" in memory.architecture_history
    assert memory.language_history["python"] == 1

    # Run 2: Same controller file modifies hotspots
    wf2 = build_workflow_memory(
        workflow_id="wf2",
        goal="Refactor user models",
        intent="Refactoring",
        execution_plan={"steps": [{"step_id": "s1", "agent": "Refactor Agent", "files": ["controllers/user.py"]}]},
        execution_metrics={},
        collaboration_summary={},
        findings=[],
        duration=5.0,
        provider_usage=[],
        success=True
    )
    update_repository_memory(memory, wf2)
    assert memory.hotspot_history["controllers/user.py"] == 3  # Now >=3, should become a recurring file
    assert "controllers/user.py" in memory.recurring_files


def test_pattern_detection_and_merging():
    # 2 workflow runs with similar bugs/hotspots
    wf1 = build_workflow_memory(
        workflow_id="wf1",
        goal="Fix JWT authentication issue",
        intent="Bug Fix",
        execution_plan={"steps": [{"step_id": "s1", "agent": "Write Code Agent", "files": ["app/auth.py"]}]},
        execution_metrics={},
        collaboration_summary={},
        findings=[{"title": "JWT Token validation crash", "file_path": "app/auth.py", "category": "Bug Fix", "severity": "high"}],
        duration=5.0,
        provider_usage=[],
        success=True
    )
    wf2 = build_workflow_memory(
        workflow_id="wf2",
        goal="Fix token validity check",
        intent="Bug Fix",
        execution_plan={"steps": [{"step_id": "s1", "agent": "Write Code Agent", "files": ["app/auth.py"]}]},
        execution_metrics={},
        collaboration_summary={},
        findings=[{"title": "JWT Token validation crash", "file_path": "app/auth.py", "category": "Bug Fix", "severity": "high"}],
        duration=8.0,
        provider_usage=[],
        success=True
    )

    patterns = detect_patterns([wf1, wf2])
    # Should detect 1 repeated bug pattern and 1 hotspot pattern
    categories = [p.category for p in patterns]
    assert "repeated_bug" in categories
    assert "repeated_hotspot" in categories

    bug_pat = next(p for p in patterns if p.category == "repeated_bug")
    assert bug_pat.frequency == 2
    assert bug_pat.severity == "high"
    assert bug_pat.confidence > 0.8  # elevated confidence due to frequency


def test_recommendation_generation_and_learning_metrics():
    # 2 successful and 1 failed run
    wf1 = build_workflow_memory(
        workflow_id="wf1",
        goal="Run security check",
        intent="Security Audit",
        execution_plan={"steps": []},
        execution_metrics={"retry_count": 0},
        collaboration_summary={},
        findings=[],
        duration=10.0,
        provider_usage=["Google AI Studio"],
        success=True
    )
    wf2 = build_workflow_memory(
        workflow_id="wf2",
        goal="Run security audit on auth",
        intent="Security Audit",
        execution_plan={"steps": []},
        execution_metrics={"retry_count": 1},
        collaboration_summary={},
        findings=[],
        duration=12.0,
        provider_usage=["Google AI Studio"],
        success=True
    )
    wf3 = build_workflow_memory(
        workflow_id="wf3",
        goal="Refactor JWT",
        intent="Refactoring",
        execution_plan={"steps": [{"step_id": "s1", "agent": "Refactor Agent", "files": ["app/auth.py"]}]},
        execution_metrics={"retry_count": 3},
        collaboration_summary={},
        findings=[],
        duration=15.0,
        provider_usage=["Groq"],
        success=False
    )

    history = [wf1, wf2, wf3]
    memory = RepositoryMemory(repository_id="rec_repo", repository_hash="h1")
    patterns = detect_patterns(history)
    
    # Calculate learning metrics
    engine = LearningEngine()
    metrics = engine._calculate_metrics(history, patterns)
    assert metrics.workflow_success_rate == 0.67  # 2 out of 3 successful
    assert metrics.average_execution_time == 12.3  # (10 + 12 + 15)/3
    assert metrics.average_retries == 1.33  # (0 + 1 + 3)/3
    assert metrics.provider_reliability["google ai studio"] == 1.0
    assert metrics.provider_reliability["groq"] == 0.0

    # Generate recommendations
    recs = generate_recommendations(memory, history, patterns)
    rec_types = [r.type for r in recs]
    # Should suggest 'Security Audit' as a successful workflow
    assert "suggested_workflow" in rec_types
    # Should suggest 'app/auth.py' as common failure location
    assert "common_failure_locations" in rec_types
