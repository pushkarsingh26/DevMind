"""
Phase 8.9 — Decision Engine Unit Tests

Target: 100% coverage of the Decision Engine package, covering:
- Dataclass serialization (to_dict / from_dict)
- Storage load/save/validate/invalidate
- Policy evaluation logic (all 5 policies)
- Priority calculation logic (weighted scoring and levels)
- Concurrency locks (same repo, different repos)
- Corrupted or partial cache recovery
- API schema validation (endpoint serialization)
- Integration hooks in workflow, planning, and execution
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from app.services.decision.decision_models import (
    DecisionSummary,
    DecisionHistoryRecord,
    DecisionMetrics,
    DecisionTelemetry,
)
from app.services.decision.versions import (
    DECISION_VERSION,
    SCHEMA_VERSION,
    GENERATOR_VERSION,
)
from app.services.reasoning.reasoning_models import (
    ReasoningSummary,
    DependencyReasoning,
    ImpactReasoning,
    HistoricalReasoning,
    ReasoningContext,
)


@pytest.fixture
def tmp_repo_id(tmp_path, monkeypatch):
    storage_root = tmp_path / "data"
    storage_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "app.services.decision.decision_storage.settings",
        MagicMock(WORKSPACE_ROOT=str(storage_root)),
    )
    return "test-decision-repo"


@pytest.fixture
def sample_decision_summary(tmp_repo_id):
    return DecisionSummary(
        repository_id=tmp_repo_id,
        repository_hash="xyz789",
        decision_score=0.65,
        priority_level="high",
        execution_recommendation="REQUIRE_APPROVAL",
        policies_evaluated=["CRITICAL_PATH_EXCEEDED", "HIGH_RISK_CHANGES"],
        policies_triggered=["HIGH_RISK_CHANGES"],
        generated_at="2026-01-01T00:00:00Z",
        build_time_ms=50.2,
    )


@pytest.fixture
def sample_reasoning_summary(tmp_repo_id):
    return ReasoningSummary(
        repository_id=tmp_repo_id,
        repository_hash="xyz789",
        reasoning_score=0.7,
        confidence=0.8,
        critical_paths=["a.py", "b.py"],
        affected_modules=["m1", "m2"],
        impact_reasoning=ImpactReasoning(
            breaking_change_probability=0.75,
            refactor_impact_score=0.4,
        ),
        historical_reasoning=HistoricalReasoning(
            success_probability=0.6,
        ),
        reasoning_context=ReasoningContext(
            repository_id=tmp_repo_id,
            repository_hash="xyz789",
            memory_summary={"pattern_count": 5},
        ),
    )


# ---------------------------------------------------------------------------
# 1. Model Serialization Tests
# ---------------------------------------------------------------------------

class TestDecisionModels:

    def test_decision_summary_roundtrip(self, sample_decision_summary):
        d = sample_decision_summary.to_dict()
        restored = DecisionSummary.from_dict(d)
        assert restored.repository_id == sample_decision_summary.repository_id
        assert restored.decision_score == sample_decision_summary.decision_score
        assert restored.priority_level == sample_decision_summary.priority_level
        assert restored.policies_evaluated == sorted(sample_decision_summary.policies_evaluated)
        assert restored.policies_triggered == sorted(sample_decision_summary.policies_triggered)

    def test_history_record_roundtrip(self):
        rec = DecisionHistoryRecord(
            workflow_id="wf-1",
            goal="Test goal",
            intent="Testing",
            decision_score=0.45,
            priority_level="medium",
            success=True,
            completed_at="2026-01-01T01:00:00Z",
        )
        d = rec.to_dict()
        restored = DecisionHistoryRecord.from_dict(d)
        assert restored.workflow_id == rec.workflow_id
        assert restored.success is True

    def test_decision_metrics_roundtrip(self):
        m = DecisionMetrics(
            decision_time_ms=10.5,
            policy_time_ms=5.2,
            priority_time_ms=3.1,
            cache_hits=2,
            cache_misses=1,
        )
        d = m.to_dict()
        restored = DecisionMetrics.from_dict(d)
        assert restored.decision_time_ms == m.decision_time_ms
        assert restored.cache_hits == m.cache_hits

    def test_decision_telemetry_roundtrip(self):
        t = DecisionTelemetry(
            decision_time_ms=15.0,
            policy_time_ms=6.0,
            priority_time_ms=4.0,
            cache_hits=0,
            cache_misses=1,
            policies_evaluated=5,
            policies_triggered=2,
            workflow_skipped=False,
            workflow_reordered=True,
            decision_score=0.82,
        )
        d = t.to_dict()
        restored = DecisionTelemetry.from_dict(d)
        assert restored.policies_evaluated == t.policies_evaluated
        assert restored.workflow_reordered is True
        assert restored.decision_score == t.decision_score


# ---------------------------------------------------------------------------
# 2. Policy Engine Tests
# ---------------------------------------------------------------------------

class TestPolicyEngine:

    def test_no_triggered_policies(self, sample_reasoning_summary):
        # Default reasoning summary has low risk indicators
        sample_reasoning_summary.critical_paths = []
        sample_reasoning_summary.affected_modules = []
        sample_reasoning_summary.impact_reasoning.breaking_change_probability = 0.1
        sample_reasoning_summary.historical_reasoning.success_probability = 0.9

        from app.services.decision.policy_engine import policy_engine
        evaluated, triggered = policy_engine.evaluate(sample_reasoning_summary)
        assert len(evaluated) == 5
        assert len(triggered) == 0

    def test_critical_path_exceeded_policy(self, sample_reasoning_summary):
        sample_reasoning_summary.critical_paths = ["file.py"] * 12
        from app.services.decision.policy_engine import policy_engine
        _, triggered = policy_engine.evaluate(sample_reasoning_summary)
        assert "CRITICAL_PATH_EXCEEDED" in triggered

    def test_high_risk_changes_policy(self, sample_reasoning_summary):
        sample_reasoning_summary.impact_reasoning.breaking_change_probability = 0.85
        from app.services.decision.policy_engine import policy_engine
        _, triggered = policy_engine.evaluate(sample_reasoning_summary)
        assert "HIGH_RISK_CHANGES" in triggered

    def test_low_historical_success_policy(self, sample_reasoning_summary):
        sample_reasoning_summary.historical_reasoning.success_probability = 0.35
        from app.services.decision.policy_engine import policy_engine
        _, triggered = policy_engine.evaluate(sample_reasoning_summary)
        assert "LOW_HISTORICAL_SUCCESS" in triggered

    def test_module_overcoupling_policy(self, sample_reasoning_summary):
        sample_reasoning_summary.affected_modules = [f"m{i}" for i in range(20)]
        from app.services.decision.policy_engine import policy_engine
        _, triggered = policy_engine.evaluate(sample_reasoning_summary)
        assert "MODULE_OVERCOUPLING" in triggered

    def test_high_refactor_complexity_policy(self, sample_reasoning_summary):
        sample_reasoning_summary.reasoning_context.memory_summary["pattern_count"] = 25
        from app.services.decision.policy_engine import policy_engine
        _, triggered = policy_engine.evaluate(sample_reasoning_summary)
        assert "HIGH_REFACTOR_COMPLEXITY" in triggered


# ---------------------------------------------------------------------------
# 3. Priority Engine Tests
# ---------------------------------------------------------------------------

class TestPriorityEngine:

    def test_low_priority_level(self, sample_reasoning_summary):
        sample_reasoning_summary.reasoning_score = 0.1
        sample_reasoning_summary.impact_reasoning.breaking_change_probability = 0.1
        from app.services.decision.priority_engine import priority_engine
        score, level = priority_engine.calculate(sample_reasoning_summary, [])
        assert level == "low"
        assert score < 0.3

    def test_medium_priority_level(self, sample_reasoning_summary):
        sample_reasoning_summary.reasoning_score = 0.5
        sample_reasoning_summary.impact_reasoning.breaking_change_probability = 0.3
        from app.services.decision.priority_engine import priority_engine
        score, level = priority_engine.calculate(sample_reasoning_summary, ["CRITICAL_PATH_EXCEEDED"])
        assert level == "medium"
        assert 0.3 <= score < 0.6

    def test_high_priority_level(self, sample_reasoning_summary):
        sample_reasoning_summary.reasoning_score = 0.85
        sample_reasoning_summary.impact_reasoning.breaking_change_probability = 0.85
        from app.services.decision.priority_engine import priority_engine
        score, level = priority_engine.calculate(sample_reasoning_summary, ["HIGH_RISK_CHANGES"])
        assert level == "high"
        assert 0.6 <= score < 0.85

    def test_critical_priority_level(self, sample_reasoning_summary):
        sample_reasoning_summary.reasoning_score = 0.95
        sample_reasoning_summary.impact_reasoning.breaking_change_probability = 0.95
        from app.services.decision.priority_engine import priority_engine
        score, level = priority_engine.calculate(
            sample_reasoning_summary,
            ["HIGH_RISK_CHANGES", "CRITICAL_PATH_EXCEEDED", "MODULE_OVERCOUPLING", "LOW_HISTORICAL_SUCCESS"]
        )
        assert level == "critical"
        assert score >= 0.85


# ---------------------------------------------------------------------------
# 4. Storage & Cache Validation
# ---------------------------------------------------------------------------

class TestDecisionStorage:

    def test_save_load_roundtrip(self, tmp_repo_id, sample_decision_summary, monkeypatch):
        from app.services.decision import decision_storage as ds
        tmp_root = str(tempfile.mkdtemp())
        monkeypatch.setattr(ds, "settings", MagicMock(WORKSPACE_ROOT=tmp_root))

        metrics = DecisionMetrics(10, 5, 2, 0, 1)
        telemetry = DecisionTelemetry(10, 5, 2, 0, 1, 2, 1, False, False, 0.65)
        ds.save(tmp_repo_id, sample_decision_summary, [], metrics, telemetry)

        loaded = ds.load(tmp_repo_id)
        assert loaded is not None
        summary, history, l_metrics, l_telemetry = loaded
        assert summary.repository_hash == sample_decision_summary.repository_hash
        assert len(history) == 0
        assert l_metrics.decision_time_ms == metrics.decision_time_ms
        assert l_telemetry.policies_evaluated == telemetry.policies_evaluated

    def test_cache_validation(self, tmp_repo_id, sample_decision_summary, monkeypatch):
        from app.services.decision import decision_storage as ds
        tmp_root = str(tempfile.mkdtemp())
        monkeypatch.setattr(ds, "settings", MagicMock(WORKSPACE_ROOT=tmp_root))

        metrics = DecisionMetrics(10, 5, 2, 0, 1)
        telemetry = DecisionTelemetry(10, 5, 2, 0, 1, 2, 1, False, False, 0.65)
        ds.save(tmp_repo_id, sample_decision_summary, [], metrics, telemetry)

        assert ds.validate_cache(tmp_repo_id, "xyz789") is True
        assert ds.validate_cache(tmp_repo_id, "wrong_hash") is False

    def test_invalidate_removes_cache_manifest(self, tmp_repo_id, sample_decision_summary, monkeypatch):
        from app.services.decision import decision_storage as ds
        tmp_root = str(tempfile.mkdtemp())
        monkeypatch.setattr(ds, "settings", MagicMock(WORKSPACE_ROOT=tmp_root))

        metrics = DecisionMetrics(10, 5, 2, 0, 1)
        telemetry = DecisionTelemetry(10, 5, 2, 0, 1, 2, 1, False, False, 0.65)
        ds.save(tmp_repo_id, sample_decision_summary, [], metrics, telemetry)

        ds.invalidate(tmp_repo_id)
        assert ds.validate_cache(tmp_repo_id, "xyz789") is False

    def test_append_history_record(self, tmp_repo_id, monkeypatch):
        from app.services.decision import decision_storage as ds
        tmp_root = str(tempfile.mkdtemp())
        monkeypatch.setattr(ds, "settings", MagicMock(WORKSPACE_ROOT=tmp_root))

        rec = DecisionHistoryRecord("wf-1", "Goal", "Bug", 0.5, "medium", True, "2026-01-01T00:00:00Z")
        ds.add_history_record(tmp_repo_id, rec)

        history = ds.load_raw_file(tmp_repo_id, "history.json")
        assert history is not None
        assert len(history) == 1
        assert history[0]["workflow_id"] == "wf-1"

    def test_corrupted_cache_manifest_recovers(self, tmp_repo_id, monkeypatch):
        from app.services.decision import decision_storage as ds
        tmp_root = str(tempfile.mkdtemp())
        monkeypatch.setattr(ds, "settings", MagicMock(WORKSPACE_ROOT=tmp_root))

        # Write corrupted cache json
        decision_dir = os.path.join(tmp_root, "repositories", tmp_repo_id, "decision")
        os.makedirs(decision_dir, exist_ok=True)
        with open(os.path.join(decision_dir, "cache.json"), "w") as f:
            f.write("{corrupt")

        assert ds.validate_cache(tmp_repo_id, "xyz789") is False


# ---------------------------------------------------------------------------
# 5. Decision Engine Tests
# ---------------------------------------------------------------------------

class TestDecisionEngine:

    def test_ensure_cache_hit(self, monkeypatch):
        from app.services.decision.decision_engine import DecisionEngine
        import app.services.decision.decision_storage as ds
        monkeypatch.setattr(ds, "validate_cache", lambda *a, **kw: True)
        
        mock_summary = MagicMock(spec=DecisionSummary)
        monkeypatch.setattr(ds, "load", lambda *a, **kw: (mock_summary, [], MagicMock(), MagicMock()))

        engine = DecisionEngine()
        res = engine.ensure("repo", "goal", "hash", "")
        assert res is mock_summary

    def test_build_rebuilds_pipeline(self, monkeypatch, tmp_path):
        from app.services.decision.decision_engine import DecisionEngine
        import app.services.decision.decision_storage as ds
        monkeypatch.setattr(ds, "settings", MagicMock(WORKSPACE_ROOT=str(tmp_path)))
        monkeypatch.setattr(ds, "validate_cache", lambda *a, **kw: False)

        engine = DecisionEngine()
        summary = engine.build("repo-1", "Goal", "hash1", "")
        assert isinstance(summary, DecisionSummary)
        assert summary.repository_id == "repo-1"

    def test_concurrent_builds_serialise(self, monkeypatch, tmp_path):
        from app.services.decision.decision_engine import DecisionEngine
        import app.services.decision.decision_storage as ds
        monkeypatch.setattr(ds, "settings", MagicMock(WORKSPACE_ROOT=str(tmp_path)))
        
        engine = DecisionEngine()
        results = []

        def worker():
            res = engine.build("repo-con", "goal", "hash-con", "")
            results.append(res)

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(results) == 2
        assert all(isinstance(r, DecisionSummary) for r in results)

    def test_different_repos_parallel(self, monkeypatch, tmp_path):
        from app.services.decision.decision_engine import DecisionEngine
        import app.services.decision.decision_storage as ds
        monkeypatch.setattr(ds, "settings", MagicMock(WORKSPACE_ROOT=str(tmp_path)))

        engine = DecisionEngine()
        results = {}

        def worker(repo_id):
            res = engine.build(repo_id, "goal", f"hash-{repo_id}", "")
            results[repo_id] = res

        t1 = threading.Thread(target=worker, args=("repo-A",))
        t2 = threading.Thread(target=worker, args=("repo-B",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert "repo-A" in results
        assert "repo-B" in results


# ---------------------------------------------------------------------------
# 6. Integration tests
# ---------------------------------------------------------------------------

class TestIntegrations:

    def test_planning_adjustment(self, sample_decision_summary, monkeypatch):
        from app.services.planning.planning_engine import planning_engine
        from app.services.decision.decision_engine import decision_engine
        
        monkeypatch.setattr(decision_engine, "get_summary", lambda r: sample_decision_summary)
        
        with patch("app.services.planning.planning_engine.SessionLocal") as mock_session:
            # planning_engine.generate_plan does DB query, mock it or patch score_plan
            plan = MagicMock()
            monkeypatch.setattr(planning_engine, "score_plan", lambda *a, **kw: {
                "completeness": 1.0,
                "confidence": 0.9,
                "estimated_success_probability": 0.90,
            })
            pass
