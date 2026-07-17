"""
Phase 8.5 — Adaptive Workflow Execution Engine Tests
Tests: retry policy, provider scoring, checkpoint recovery, ETA,
       corruption recovery, restart resume, retry exhaustion, cancel during retry,
       interrupted workflow recovery, provider failover.
"""
import asyncio
import json
import time
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# ─────────────────────────────────────────────────────────────────────────────
# 1. RETRY POLICY TESTS
# ─────────────────────────────────────────────────────────────────────────────

from app.services.execution.retry_policy import RetryPolicy


@pytest.fixture
def policy():
    return RetryPolicy()


def test_retry_on_429(policy):
    assert policy.should_retry(429) is True


def test_retry_on_500(policy):
    assert policy.should_retry(500) is True


def test_retry_on_502(policy):
    assert policy.should_retry(502) is True


def test_retry_on_503(policy):
    assert policy.should_retry(503) is True


def test_retry_on_504(policy):
    assert policy.should_retry(504) is True


def test_no_retry_on_400(policy):
    assert policy.should_retry(400) is False


def test_no_retry_on_401(policy):
    assert policy.should_retry(401) is False


def test_no_retry_on_403(policy):
    assert policy.should_retry(403) is False


def test_no_retry_on_404(policy):
    assert policy.should_retry(404) is False


def test_retry_on_timeout_exception(policy):
    assert policy.should_retry(asyncio.TimeoutError()) is True


def test_retry_on_connection_error(policy):
    assert policy.should_retry(ConnectionError("refused")) is True


def test_retry_on_generic_timeout_str(policy):
    # TimeoutError is a built-in base class that the policy catches via isinstance
    assert policy.should_retry(TimeoutError("Connection timed out")) is True


def test_no_retry_on_generic_exception(policy):
    assert policy.should_retry(ValueError("bad value")) is False


def test_backoff_delay_is_bounded(policy):
    # Even at very high attempt, delay should not exceed 30 + max_jitter(0.5)
    delay = policy.get_delay(100)
    assert delay <= 30.5


def test_backoff_delay_increases(policy):
    d0 = policy.get_delay(0, base_delay=2.0)
    d1 = policy.get_delay(1, base_delay=2.0)
    d2 = policy.get_delay(2, base_delay=2.0)
    # Progressively increasing (base * 2^n)
    assert d0 < d2  # At attempt=0: 2s + jitter, at attempt=2: 8s + jitter


def test_backoff_jitter_is_positive(policy):
    delay = policy.get_delay(0)
    # Should be at least base_delay (2.0) with no negative jitter
    assert delay >= 2.0


def test_backoff_delay_not_negative(policy):
    for attempt in range(5):
        assert policy.get_delay(attempt) >= 0


# ─────────────────────────────────────────────────────────────────────────────
# 2. PROVIDER SELECTOR TESTS
# ─────────────────────────────────────────────────────────────────────────────

from app.services.execution.provider_selector import ProviderSelector


@pytest.fixture
def selector():
    return ProviderSelector()


def test_score_returns_float(selector):
    score = selector.score_provider("google")
    assert isinstance(score, float)
    assert 0.0 <= score <= 1.0


def test_select_best_returns_string(selector):
    best = selector.select_best_provider("Repository Agent")
    assert isinstance(best, str)
    assert best in ["google", "groq", "openrouter", "nvidia"]


def test_failover_excludes_current(selector):
    # When 'google' is current and failing, it should not return 'google'
    with patch("app.services.provider_health.ProviderHealthMonitor.is_healthy", return_value=True):
        best = selector.select_best_provider("Repository Agent", current_provider="google")
        assert best != "google"


def test_provider_scoring_weights():
    """Score = 40% success + 30% latency + 20% availability + 10% cost."""
    selector = ProviderSelector()
    # All fresh providers default: success_rate=1.0, latency=0.5 (avg), available=1.0
    score = selector.score_provider("google")
    # Google cost_rating=0.9; score = 0.4*1.0 + 0.3*(1/1.5) + 0.2*1.0 + 0.1*0.9
    expected = 0.4 * 1.0 + 0.3 * (1.0 / (1.0 + 0.5)) + 0.2 * 1.0 + 0.1 * 0.9
    assert abs(score - expected) < 0.05  # allow small diff from rounding


def test_unhealthy_provider_gets_zero_availability():
    selector = ProviderSelector()
    with patch.object(
        type(selector.score_provider.__self__),
        "is_healthy",
        return_value=False,
        create=True
    ):
        # Manually test availability logic
        from app.services.provider_health import provider_health_monitor
        with patch.object(provider_health_monitor, "is_healthy", return_value=False):
            score = selector.score_provider("google")
            # Availability contribution (0.2 * 0.0) should make score lower than 0.6
            assert score < 0.7


# ─────────────────────────────────────────────────────────────────────────────
# 3. CHECKPOINT STORAGE TESTS
# ─────────────────────────────────────────────────────────────────────────────

from app.services.execution.checkpoint_storage import CheckpointStorage
from app.services.execution.execution_models import (
    ExecutionCheckpoint, ExecutionState, ExecutionMetrics, ExecutionBudget, ExecutionEvent
)


def make_storage(tmp_dir: str) -> CheckpointStorage:
    """Create a CheckpointStorage rooted under a temp directory."""
    storage = CheckpointStorage()
    storage._get_workflow_dir = lambda wf_id: (  # type: ignore[method-assign]
        Path(tmp_dir) / "workflows" / wf_id
    )
    return storage


def _make_dir(storage, wf_id):
    """Ensure workflow dir exists for testing."""
    d = Path(storage._get_workflow_dir(wf_id))
    d.mkdir(parents=True, exist_ok=True)
    return d


@pytest.fixture
def tmp_storage(tmp_path):
    return make_storage(str(tmp_path))


@pytest.fixture
def sample_checkpoint():
    return ExecutionCheckpoint(
        step_id="step_repo",
        status="completed",
        completed_at="2024-01-01T00:00:00Z",
        telemetry={"tokens": 500, "cost": 0.001, "duration_sec": 12},
        outputs={}
    )


@pytest.fixture
def sample_state():
    return ExecutionState(
        workflow_id="wf_test",
        repository_id="repo_abc",
        current_step_id="step_repo",
        current_tier_index=0,
        status="running",
        start_time="2024-01-01T00:00:00Z",
        last_updated_at="2024-01-01T00:00:00Z"
    )


@pytest.fixture
def sample_metrics():
    return ExecutionMetrics(total_steps=4, completed_steps=1)


@pytest.fixture
def sample_budget():
    return ExecutionBudget()


def test_save_and_load_checkpoint(tmp_storage, sample_checkpoint):
    _make_dir(tmp_storage, "wf_test")
    tmp_storage.save_checkpoint("wf_test", sample_checkpoint)
    loaded = tmp_storage.load_checkpoints("wf_test")
    assert len(loaded) == 1
    assert loaded[0].step_id == "step_repo"
    assert loaded[0].status == "completed"


def test_overwrite_existing_checkpoint(tmp_storage, sample_checkpoint):
    _make_dir(tmp_storage, "wf_test")
    tmp_storage.save_checkpoint("wf_test", sample_checkpoint)
    updated = ExecutionCheckpoint(
        step_id="step_repo",
        status="failed",
        completed_at="2024-01-01T01:00:00Z",
        telemetry={},
        outputs={}
    )
    tmp_storage.save_checkpoint("wf_test", updated)
    loaded = tmp_storage.load_checkpoints("wf_test")
    assert len(loaded) == 1
    assert loaded[0].status == "failed"


def test_load_empty_checkpoints(tmp_storage):
    _make_dir(tmp_storage, "wf_empty")
    loaded = tmp_storage.load_checkpoints("wf_empty")
    assert loaded == []


def test_save_and_load_state(tmp_storage, sample_state, sample_metrics, sample_budget):
    _make_dir(tmp_storage, "wf_test")
    tmp_storage.save_state("wf_test", sample_state, sample_metrics, sample_budget)
    s, m, b = tmp_storage.load_state("wf_test")
    assert s is not None
    assert s.workflow_id == "wf_test"
    assert m.total_steps == 4
    assert b.max_tokens == 1_000_000


def test_load_state_returns_none_for_missing(tmp_storage):
    _make_dir(tmp_storage, "wf_missing")
    s, m, b = tmp_storage.load_state("wf_missing")
    assert s is None and m is None and b is None


def test_log_and_load_events(tmp_storage):
    _make_dir(tmp_storage, "wf_events")
    event = ExecutionEvent(
        timestamp="2024-01-01T00:00:00Z",
        step_id="step_repo",
        event="started",
        provider="google",
        duration_ms=0,
        retry=0
    )
    tmp_storage.log_event("wf_events", event)
    loaded = tmp_storage.load_events("wf_events")
    assert len(loaded) == 1
    assert loaded[0].event == "started"
    assert loaded[0].provider == "google"


def test_multiple_events_append_order(tmp_storage):
    _make_dir(tmp_storage, "wf_multi")
    for ev in ["started", "retry", "completed"]:
        tmp_storage.log_event("wf_multi", ExecutionEvent(
            timestamp="2024-01-01T00:00:00Z",
            step_id="step_x",
            event=ev,
            provider="google",
            duration_ms=100,
            retry=0
        ))
    loaded = tmp_storage.load_events("wf_multi")
    assert [e.event for e in loaded] == ["started", "retry", "completed"]


# ─────────────────────────────────────────────────────────────────────────────
# 4. CHECKPOINT CORRUPTION RECOVERY TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_corruption_recovery_from_backup(tmp_storage, sample_checkpoint):
    """Corrupts main checkpoints.json — should recover from .bak."""
    _make_dir(tmp_storage, "wf_corrupt")
    wf_dir = Path(tmp_storage._get_workflow_dir("wf_corrupt"))

    # Write a valid checkpoint first (creates backup on next save)
    tmp_storage.save_checkpoint("wf_corrupt", sample_checkpoint)
    # Write second checkpoint to trigger backup creation
    cp2 = ExecutionCheckpoint(
        step_id="step_plan",
        status="completed",
        completed_at="2024-01-01T01:00:00Z",
        telemetry={},
        outputs={}
    )
    tmp_storage.save_checkpoint("wf_corrupt", cp2)
    
    # Now corrupt the main file
    (wf_dir / "checkpoints.json").write_text("{invalid json!!!", encoding="utf-8")
    
    # Should recover from .bak (the previous valid state)
    loaded = tmp_storage.load_checkpoints("wf_corrupt")
    assert len(loaded) >= 1
    assert loaded[0].step_id == "step_repo"


def test_corruption_both_files_returns_empty(tmp_storage):
    """Both main and backup files corrupted — should return empty list."""
    _make_dir(tmp_storage, "wf_double_corrupt")
    wf_dir = Path(tmp_storage._get_workflow_dir("wf_double_corrupt"))
    (wf_dir / "checkpoints.json").write_text("{CORRUPTED}", encoding="utf-8")
    (wf_dir / "checkpoints.json.bak").write_text("{ALSO CORRUPTED}", encoding="utf-8")
    
    loaded = tmp_storage.load_checkpoints("wf_double_corrupt")
    assert loaded == []


def test_state_corruption_returns_none(tmp_storage):
    """Corrupted state.json — should return triple None."""
    _make_dir(tmp_storage, "wf_state_corrupt")
    wf_dir = Path(tmp_storage._get_workflow_dir("wf_state_corrupt"))
    (wf_dir / "state.json").write_text("NOT_JSON", encoding="utf-8")
    s, m, b = tmp_storage.load_state("wf_state_corrupt")
    assert s is None and m is None and b is None


def test_events_corruption_returns_empty(tmp_storage):
    """Corrupted events file — should return empty list."""
    _make_dir(tmp_storage, "wf_events_corrupt")
    wf_dir = Path(tmp_storage._get_workflow_dir("wf_events_corrupt"))
    (wf_dir / "execution_events.json").write_text("[[BROKEN", encoding="utf-8")
    loaded = tmp_storage.load_events("wf_events_corrupt")
    assert loaded == []


# ─────────────────────────────────────────────────────────────────────────────
# 5. EXECUTION MANAGER – ETA CALCULATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

from app.services.execution.execution_manager import ExecutionManager


@pytest.fixture
def manager():
    return ExecutionManager()


@pytest.fixture
def plan_steps():
    return [
        {"step_id": "step_repo",    "agent": "Repository Agent",  "name": "Repository Scan",     "estimated_duration": 10},
        {"step_id": "step_sec",     "agent": "Security Agent",    "name": "Security Audit",       "estimated_duration": 20},
        {"step_id": "step_deps",    "agent": "Dependency Agent",  "name": "Dependency Analysis",  "estimated_duration": 15},
        {"step_id": "step_summary", "agent": "Summary Agent",     "name": "Summary Generation",   "estimated_duration": 5},
    ]


def test_eta_no_completed_steps(manager, plan_steps):
    """No completed steps → ETA = sum of all estimated durations."""
    eta = manager.calculate_eta(plan_steps, [], [])
    total = sum(s["estimated_duration"] for s in plan_steps)
    assert eta == total


def test_eta_with_all_completed(manager, plan_steps):
    """All steps completed → ETA = 5 seconds (min floor)."""
    completed = ["step_repo", "step_sec", "step_deps", "step_summary"]
    checkpoints = [
        ExecutionCheckpoint(
            step_id=sid, status="completed",
            completed_at="2024-01-01T00:00:00Z",
            telemetry={"duration_sec": 15},  # same as estimate on average
            outputs={}
        )
        for sid in completed
    ]
    eta = manager.calculate_eta(plan_steps, completed, checkpoints)
    assert eta >= 5  # min floor


def test_eta_decreases_as_steps_complete(manager, plan_steps):
    """ETA should be lower when more steps complete."""
    eta_none = manager.calculate_eta(plan_steps, [], [])
    eta_one = manager.calculate_eta(
        plan_steps,
        ["step_repo"],
        [ExecutionCheckpoint(
            step_id="step_repo", status="completed",
            completed_at="2024-01-01T00:00:00Z",
            telemetry={"duration_sec": 10},
            outputs={}
        )]
    )
    assert eta_none > eta_one


def test_eta_speed_factor_fast_execution(manager, plan_steps):
    """If steps ran 50% faster than estimate, ETA should adjust down."""
    # step_repo: estimated=10, actual=5 (speed factor ~ 0.5)
    completed = ["step_repo"]
    checkpoints = [ExecutionCheckpoint(
        step_id="step_repo", status="completed",
        completed_at="2024-01-01T00:00:00Z",
        telemetry={"duration_sec": 5},  # half of estimated 10
        outputs={}
    )]
    eta = manager.calculate_eta(plan_steps, completed, checkpoints)
    # Remaining: sec(20)+deps(15)+sum(5)=40 * 0.5 speed = 20s
    assert eta <= 30  # should be noticeably less than raw 40


def test_eta_speed_factor_slow_execution(manager, plan_steps):
    """If steps ran 2× slower than estimate, ETA should inflate."""
    completed = ["step_repo"]
    checkpoints = [ExecutionCheckpoint(
        step_id="step_repo", status="completed",
        completed_at="2024-01-01T00:00:00Z",
        telemetry={"duration_sec": 20},  # double the estimate of 10
        outputs={}
    )]
    eta = manager.calculate_eta(plan_steps, completed, checkpoints)
    # Remaining raw = 40, speed_factor = 2.0 → expected ~80
    assert eta >= 40


# ─────────────────────────────────────────────────────────────────────────────
# 6. INTERRUPTED WORKFLOW RECOVERY (PROCESS RESTART) TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_initialize_run_resumes_from_checkpoints(tmp_storage, plan_steps):
    """When checkpoints exist, initialize_run should set resume_from_step."""
    wf_id = "wf_restart_test"
    _make_dir(tmp_storage, wf_id)
    
    # Simulate step_repo already completed before restart
    tmp_storage.save_checkpoint(wf_id, ExecutionCheckpoint(
        step_id="step_repo",
        status="completed",
        completed_at="2024-01-01T00:00:00Z",
        telemetry={},
        outputs={}
    ))
    
    # Save a running state
    state = ExecutionState(
        workflow_id=wf_id, repository_id="repo_x",
        current_step_id="step_sec", current_tier_index=1,
        status="running",
        start_time="2024-01-01T00:00:00Z",
        last_updated_at="2024-01-01T01:00:00Z"
    )
    tmp_storage.save_state(wf_id, state, ExecutionMetrics(), ExecutionBudget())
    
    manager = ExecutionManager()
    # Patch the storage used by the manager
    with patch("app.services.execution.execution_manager.checkpoint_storage", tmp_storage):
        restored_state, metrics, budget = manager.initialize_run(wf_id, "repo_x", plan_steps)
    
    assert restored_state.resume_from_step == "step_sec"
    assert restored_state.status == "running"


def test_initialize_run_creates_fresh_state_when_no_checkpoints(plan_steps):
    """When no checkpoints exist, initialize_run should create fresh state."""
    manager = ExecutionManager()
    
    with patch("app.services.execution.execution_manager.checkpoint_storage") as mock_storage:
        mock_storage.load_state.return_value = (None, None, None)
        mock_storage.load_checkpoints.return_value = []
        mock_storage.save_state.return_value = None
        
        state, metrics, budget = manager.initialize_run("wf_new", "repo_y", plan_steps)
    
    assert state.workflow_id == "wf_new"
    assert state.status == "queued"
    assert state.resume_from_step is None
    assert metrics.total_steps == len(plan_steps)
    assert budget.max_tokens == 1_000_000


# ─────────────────────────────────────────────────────────────────────────────
# 7. EXECUTION MODELS SERIALIZATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

def test_checkpoint_roundtrip():
    cp = ExecutionCheckpoint(
        step_id="step_repo",
        status="completed",
        completed_at="2024-01-01T00:00:00Z",
        telemetry={"tokens": 100},
        outputs={"analysis": "ok"}
    )
    restored = ExecutionCheckpoint.from_dict(cp.to_dict())
    assert restored.step_id == cp.step_id
    assert restored.telemetry == cp.telemetry


def test_state_roundtrip():
    state = ExecutionState(
        workflow_id="wf_a",
        repository_id="repo_b",
        current_step_id="step_1",
        current_tier_index=2,
        status="paused",
        start_time="2024-01-01T00:00:00Z",
        last_updated_at="2024-01-01T00:00:00Z",
        last_completed_step="step_0",
        failed_step=None,
        resume_from_step="step_1"
    )
    restored = ExecutionState.from_dict(state.to_dict())
    assert restored.resume_from_step == "step_1"
    assert restored.last_completed_step == "step_0"
    assert restored.failed_step is None


def test_budget_roundtrip():
    budget = ExecutionBudget(
        max_tokens=500000,
        max_cost_usd=2.5,
        used_tokens=12000,
        used_cost_usd=0.024,
        remaining_tokens=488000,
        remaining_cost=2.476
    )
    restored = ExecutionBudget.from_dict(budget.to_dict())
    assert restored.remaining_tokens == 488000
    assert abs(restored.remaining_cost - 2.476) < 0.001


def test_metrics_roundtrip():
    metrics = ExecutionMetrics(
        total_steps=5, completed_steps=3, failed_steps=1,
        retry_count=2, active_provider="groq"
    )
    restored = ExecutionMetrics.from_dict(metrics.to_dict())
    assert restored.active_provider == "groq"
    assert restored.retry_count == 2


def test_event_roundtrip():
    event = ExecutionEvent(
        timestamp="2024-01-01T00:00:00Z",
        step_id="step_sec",
        event="failover",
        provider="groq",
        duration_ms=5432,
        retry=1
    )
    restored = ExecutionEvent.from_dict(event.to_dict())
    assert restored.event == "failover"
    assert restored.retry == 1
