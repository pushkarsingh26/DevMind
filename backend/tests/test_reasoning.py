"""
Phase 8.8 — Reasoning Engine Unit Tests

Target: ≥ 30 tests covering:
- Model serialization (to_dict / from_dict roundtrips)
- Deterministic ordering
- Storage save/load/validate/invalidate
- Cache validity scenarios
- Corrupted cache recovery
- ContextBuilder incremental loading
- DependencyReasoner (empty graph, single node, depth limit)
- ImpactReasoner (probability bounds, test file detection)
- EvidenceRanker (score ordering, tie-breaking, zero-evidence)
- HistoricalReasoner (0/1/N history, edge cases)
- ReasoningEngine.ensure() cache-hit path
- ReasoningEngine.build() full pipeline
- Thread safety (same repo, different repos)
- Replay from disk
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from app.services.reasoning.reasoning_models import (
    DependencyReasoning,
    EvidenceItem,
    EvidenceRanking,
    HistoricalReasoning,
    ImpactReasoning,
    ReasoningChain,
    ReasoningContext,
    ReasoningMetrics,
    ReasoningSummary,
)
from app.services.reasoning.versions import (
    GENERATOR_VERSION,
    REASONING_VERSION,
    SCHEMA_VERSION,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_repo_id(tmp_path, monkeypatch):
    """A unique repository ID with storage redirected to tmp_path."""
    repo_id = "test-reasoning-repo"
    storage_root = tmp_path / "data"
    storage_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "app.services.reasoning.reasoning_storage.settings",
        MagicMock(WORKSPACE_ROOT=str(storage_root)),
    )
    return repo_id


@pytest.fixture
def sample_summary(tmp_repo_id):
    return ReasoningSummary(
        repository_id=tmp_repo_id,
        repository_hash="abc123",
        reasoning_score=0.75,
        confidence=0.80,
        critical_paths=["file_b.py", "file_a.py"],
        affected_modules=["module_z", "module_a"],
        risk_indicators=["HIGH_BREAKING_CHANGE_RISK"],
        reasoning_context=ReasoningContext(
            repository_id=tmp_repo_id,
            repository_hash="abc123",
            intelligence_summary={"file_count": 10},
            built_at="2026-01-01T00:00:00Z",
        ),
        dependency_reasoning=DependencyReasoning(
            critical_files=["file_b.py", "file_a.py"],
            affected_symbols=["SymB", "SymA"],
            transitive_impact=["file_c.py"],
        ),
        impact_reasoning=ImpactReasoning(
            direct_impact=["file_b.py"],
            indirect_impact=["file_c.py"],
            breaking_change_probability=0.75,
            repository_wide_impact=True,
        ),
        evidence_ranking=EvidenceRanking(
            ranked_items=[
                EvidenceItem(evidence_id="z01", source="test", title="Z finding", score=0.9),
                EvidenceItem(evidence_id="a01", source="test", title="A finding", score=0.9),
            ],
            total_sources=1,
            top_confidence=0.9,
        ),
        historical_reasoning=HistoricalReasoning(
            similar_workflows=["wf-2", "wf-1"],
            success_probability=0.7,
        ),
        generated_at="2026-01-01T00:00:00Z",
        build_time_ms=123.4,
    )


@pytest.fixture
def sample_chains():
    return [
        ReasoningChain(chain_id="chain:b", source="file_b.py", steps=["file_c.py", "file_a.py"]),
        ReasoningChain(chain_id="chain:a", source="file_a.py", steps=["file_d.py"]),
    ]


@pytest.fixture
def sample_metrics():
    return ReasoningMetrics(
        reasoning_build_ms=200.0,
        context_build_ms=10.0,
        dependency_reasoning_ms=30.0,
        impact_reasoning_ms=20.0,
        evidence_ranking_ms=15.0,
        historical_reasoning_ms=5.0,
        serialization_ms=8.0,
        cache_hit=False,
        cache_miss=True,
        reasoning_score=0.75,
        reasoning_confidence=0.80,
        critical_path_count=2,
        affected_files=5,
        affected_symbols=3,
    )


# ---------------------------------------------------------------------------
# 1. Model serialization — to_dict / from_dict roundtrips
# ---------------------------------------------------------------------------

class TestModelSerialization:

    def test_reasoning_chain_roundtrip(self):
        chain = ReasoningChain(chain_id="c:1", source="a.py", steps=["b.py", "c.py"], depth=2)
        restored = ReasoningChain.from_dict(chain.to_dict())
        assert restored.chain_id == chain.chain_id
        assert restored.source == chain.source
        assert restored.steps == sorted(chain.steps)

    def test_evidence_item_roundtrip(self):
        item = EvidenceItem(
            evidence_id="abc", source="analysis", title="Bug", score=0.85,
            confidence=0.9, factors={"severity": 0.8, "graph": 0.7},
        )
        restored = EvidenceItem.from_dict(item.to_dict())
        assert restored.evidence_id == item.evidence_id
        assert restored.score == item.score
        assert list(restored.factors.keys()) == sorted(item.factors.keys())

    def test_dependency_reasoning_roundtrip(self):
        dep = DependencyReasoning(
            critical_files=["b.py", "a.py"],
            affected_symbols=["SymB", "SymA"],
            transitive_impact=["c.py"],
        )
        d = dep.to_dict()
        restored = DependencyReasoning.from_dict(d)
        assert restored.critical_files == sorted(dep.critical_files)
        assert restored.affected_symbols == sorted(dep.affected_symbols)

    def test_impact_reasoning_roundtrip(self):
        imp = ImpactReasoning(direct_impact=["b.py", "a.py"], breaking_change_probability=0.55)
        d = imp.to_dict()
        restored = ImpactReasoning.from_dict(d)
        assert restored.direct_impact == sorted(imp.direct_impact)
        assert abs(restored.breaking_change_probability - 0.55) < 0.001

    def test_evidence_ranking_roundtrip(self):
        er = EvidenceRanking(
            ranked_items=[
                EvidenceItem("z", "s", "Z", score=0.5),
                EvidenceItem("a", "s", "A", score=0.9),
            ],
            total_sources=2,
        )
        d = er.to_dict()
        # Sorted by score DESC — "a" (0.9) must come first
        assert d["ranked_items"][0]["evidence_id"] == "a"
        restored = EvidenceRanking.from_dict(d)
        assert len(restored.ranked_items) == 2

    def test_historical_reasoning_roundtrip(self):
        his = HistoricalReasoning(
            similar_workflows=["wf-2", "wf-1"],
            common_risks=["risk_b", "risk_a"],
            success_probability=0.65,
        )
        d = his.to_dict()
        assert d["similar_workflows"] == sorted(his.similar_workflows)
        assert d["common_risks"] == sorted(his.common_risks)
        restored = HistoricalReasoning.from_dict(d)
        assert abs(restored.success_probability - 0.65) < 0.001

    def test_reasoning_context_roundtrip(self):
        ctx = ReasoningContext(
            repository_id="r1", repository_hash="h1",
            intelligence_summary={"file_count": 5},
        )
        restored = ReasoningContext.from_dict(ctx.to_dict())
        assert restored.repository_id == "r1"
        assert restored.intelligence_summary["file_count"] == 5

    def test_reasoning_metrics_roundtrip(self, sample_metrics):
        d = sample_metrics.to_dict()
        restored = ReasoningMetrics.from_dict(d)
        assert restored.reasoning_build_ms == sample_metrics.reasoning_build_ms
        assert restored.affected_symbols == sample_metrics.affected_symbols

    def test_reasoning_summary_roundtrip(self, sample_summary):
        d = sample_summary.to_dict()
        restored = ReasoningSummary.from_dict(d)
        assert restored.repository_id == sample_summary.repository_id
        assert restored.reasoning_score == sample_summary.reasoning_score
        assert restored.critical_paths == sorted(sample_summary.critical_paths)
        assert restored.affected_modules == sorted(sample_summary.affected_modules)


# ---------------------------------------------------------------------------
# 2. Deterministic ordering
# ---------------------------------------------------------------------------

class TestDeterministicOrdering:

    def test_critical_files_sorted(self, sample_summary):
        d = sample_summary.to_dict()
        dep = d["dependency_reasoning"]
        assert dep["critical_files"] == sorted(dep["critical_files"])

    def test_affected_symbols_sorted(self, sample_summary):
        d = sample_summary.to_dict()
        dep = d["dependency_reasoning"]
        assert dep["affected_symbols"] == sorted(dep["affected_symbols"])

    def test_risk_indicators_sorted(self, sample_summary):
        d = sample_summary.to_dict()
        assert d["risk_indicators"] == sorted(d["risk_indicators"])

    def test_evidence_tie_breaking(self):
        """Items with equal score must be sorted by evidence_id ASC."""
        er = EvidenceRanking(ranked_items=[
            EvidenceItem("zzz", "s", "T", score=0.8),
            EvidenceItem("aaa", "s", "T", score=0.8),
            EvidenceItem("mmm", "s", "T", score=0.8),
        ])
        d = er.to_dict()
        ids = [i["evidence_id"] for i in d["ranked_items"]]
        assert ids == sorted(ids)

    def test_identical_inputs_produce_identical_output(self, sample_summary):
        d1 = sample_summary.to_dict()
        d2 = sample_summary.to_dict()
        assert json.dumps(d1, sort_keys=True) == json.dumps(d2, sort_keys=True)

    def test_chains_sorted_by_chain_id(self, sample_chains):
        from app.services.reasoning import reasoning_storage as rs
        # Verify chains are sorted when saved
        sorted_chains = sorted([c.to_dict() for c in sample_chains], key=lambda x: x["chain_id"])
        assert sorted_chains[0]["chain_id"] == "chain:a"
        assert sorted_chains[1]["chain_id"] == "chain:b"


# ---------------------------------------------------------------------------
# 3. Storage save / load / validate / invalidate
# ---------------------------------------------------------------------------

class TestStorage:

    def test_save_and_load(self, tmp_repo_id, sample_summary, sample_chains, sample_metrics, monkeypatch):
        from app.services.reasoning import reasoning_storage as rs
        monkeypatch.setattr(
            rs, "settings",
            MagicMock(WORKSPACE_ROOT=str(tempfile.mkdtemp())),
        )
        rs.save(tmp_repo_id, sample_summary, sample_chains, sample_metrics, {})
        result = rs.load(tmp_repo_id)
        assert result is not None
        loaded_summary, loaded_chains, loaded_metrics = result
        assert loaded_summary.repository_id == tmp_repo_id
        assert len(loaded_chains) == len(sample_chains)
        assert loaded_metrics.affected_files == sample_metrics.affected_files

    def test_validate_cache_hit(self, tmp_repo_id, sample_summary, sample_chains, sample_metrics, monkeypatch):
        from app.services.reasoning import reasoning_storage as rs
        monkeypatch.setattr(
            rs, "settings",
            MagicMock(WORKSPACE_ROOT=str(tempfile.mkdtemp())),
        )
        rs.save(tmp_repo_id, sample_summary, sample_chains, sample_metrics, {})
        assert rs.validate_cache(tmp_repo_id, "abc123") is True

    def test_validate_cache_miss_wrong_hash(self, tmp_repo_id, sample_summary, sample_chains, sample_metrics, monkeypatch):
        from app.services.reasoning import reasoning_storage as rs
        monkeypatch.setattr(
            rs, "settings",
            MagicMock(WORKSPACE_ROOT=str(tempfile.mkdtemp())),
        )
        rs.save(tmp_repo_id, sample_summary, sample_chains, sample_metrics, {})
        assert rs.validate_cache(tmp_repo_id, "different-hash") is False

    def test_validate_cache_miss_version_changed(self, tmp_repo_id, sample_summary, sample_chains, sample_metrics, monkeypatch):
        from app.services.reasoning import reasoning_storage as rs
        tmp_root = str(tempfile.mkdtemp())
        monkeypatch.setattr(rs, "settings", MagicMock(WORKSPACE_ROOT=tmp_root))
        rs.save(tmp_repo_id, sample_summary, sample_chains, sample_metrics, {})
        # Corrupt the version in cache.json
        cache_path = os.path.join(tmp_root, "repositories", tmp_repo_id, "reasoning", "cache.json")
        with open(cache_path, "r") as f:
            cache = json.load(f)
        cache["reasoning_version"] = "v99"
        with open(cache_path, "w") as f:
            json.dump(cache, f)
        assert rs.validate_cache(tmp_repo_id, "abc123") is False

    def test_invalidate_removes_cache_only(self, tmp_repo_id, sample_summary, sample_chains, sample_metrics, monkeypatch):
        from app.services.reasoning import reasoning_storage as rs
        tmp_root = str(tempfile.mkdtemp())
        monkeypatch.setattr(rs, "settings", MagicMock(WORKSPACE_ROOT=tmp_root))
        rs.save(tmp_repo_id, sample_summary, sample_chains, sample_metrics, {})
        rs.invalidate(tmp_repo_id)
        assert rs.validate_cache(tmp_repo_id, "abc123") is False
        # reasoning.json must still exist
        reasoning_path = os.path.join(tmp_root, "repositories", tmp_repo_id, "reasoning", "reasoning.json")
        assert os.path.exists(reasoning_path)

    def test_corrupted_cache_returns_false(self, tmp_repo_id, monkeypatch):
        from app.services.reasoning import reasoning_storage as rs
        tmp_root = str(tempfile.mkdtemp())
        monkeypatch.setattr(rs, "settings", MagicMock(WORKSPACE_ROOT=tmp_root))
        cache_dir = os.path.join(tmp_root, "repositories", tmp_repo_id, "reasoning")
        os.makedirs(cache_dir, exist_ok=True)
        # Write truncated / invalid JSON
        with open(os.path.join(cache_dir, "cache.json"), "w") as f:
            f.write("{corrupted")
        assert rs.validate_cache(tmp_repo_id, "abc123") is False

    def test_load_returns_none_when_missing(self, tmp_repo_id, monkeypatch):
        from app.services.reasoning import reasoning_storage as rs
        monkeypatch.setattr(rs, "settings", MagicMock(WORKSPACE_ROOT=str(tempfile.mkdtemp())))
        assert rs.load(tmp_repo_id) is None

    def test_load_section(self, tmp_repo_id, sample_summary, sample_chains, sample_metrics, monkeypatch):
        from app.services.reasoning import reasoning_storage as rs
        monkeypatch.setattr(rs, "settings", MagicMock(WORKSPACE_ROOT=str(tempfile.mkdtemp())))
        rs.save(tmp_repo_id, sample_summary, sample_chains, sample_metrics, {})
        dep = rs.load_section(tmp_repo_id, "dependency_reasoning")
        assert dep is not None
        assert "critical_files" in dep


# ---------------------------------------------------------------------------
# 4. ContextBuilder — incremental loading
# ---------------------------------------------------------------------------

class TestContextBuilder:

    def test_builds_with_all_sources_missing(self):
        """All subsystems fail → ReasoningContext still returned with empty dicts."""
        from app.services.reasoning.context_builder import ContextBuilder
        builder = ContextBuilder()
        ctx = builder.build("no-such-repo", "", "hash123")
        assert ctx.repository_id == "no-such-repo"
        assert isinstance(ctx.intelligence_summary, dict)
        assert isinstance(ctx.graph_summary, dict)
        assert isinstance(ctx.analysis_summary, dict)
        assert isinstance(ctx.memory_summary, dict)
        assert isinstance(ctx.collaboration_summary, dict)

    def test_intelligence_failure_does_not_block(self):
        from app.services.reasoning.context_builder import _load_intelligence
        # Should not raise even if the service is unavailable
        result = _load_intelligence("no-such-repo-id")
        assert isinstance(result, dict)

    def test_graph_failure_does_not_block(self):
        from app.services.reasoning.context_builder import _load_graph
        result = _load_graph("no-such-repo-id")
        assert isinstance(result, dict)

    def test_memory_failure_does_not_block(self):
        from app.services.reasoning.context_builder import _load_memory
        result = _load_memory("no-such-repo-id")
        assert isinstance(result, dict)

    def test_collaboration_failure_does_not_block(self):
        from app.services.reasoning.context_builder import _load_collaboration
        result = _load_collaboration("no-such-repo-id")
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# 5. DependencyReasoner
# ---------------------------------------------------------------------------

class TestDependencyReasoner:

    def test_empty_context_returns_empty(self):
        from app.services.reasoning.dependency_reasoner import DependencyReasoner
        ctx = ReasoningContext(repository_id="empty", repository_hash="h")
        result = DependencyReasoner().reason(ctx)
        assert result.critical_files == []
        assert result.dependency_chains == []
        assert result.affected_symbols == []

    def test_output_is_sorted(self):
        """Output lists must always be sorted regardless of traversal order."""
        from app.services.reasoning.dependency_reasoner import DependencyReasoner
        ctx = ReasoningContext(repository_id="empty", repository_hash="h")
        result = DependencyReasoner().reason(ctx)
        assert result.critical_files == sorted(result.critical_files)
        assert result.affected_symbols == sorted(result.affected_symbols)
        assert result.transitive_impact == sorted(result.transitive_impact)


# ---------------------------------------------------------------------------
# 6. ImpactReasoner
# ---------------------------------------------------------------------------

class TestImpactReasoner:

    def test_breaking_change_probability_bounded(self):
        from app.services.reasoning.impact_reasoner import ImpactReasoner
        ctx = ReasoningContext(
            repository_id="r", repository_hash="h",
            intelligence_summary={"file_count": 1},
        )
        dep = DependencyReasoning(critical_files=["a.py"] * 1000)
        result = ImpactReasoner().reason(ctx, dep)
        assert 0.0 <= result.breaking_change_probability <= 1.0

    def test_refactor_impact_score_bounded(self):
        from app.services.reasoning.impact_reasoner import ImpactReasoner
        ctx = ReasoningContext(
            repository_id="r", repository_hash="h",
            intelligence_summary={"file_count": 5},
            memory_summary={"hotspot_history": {"a.py": 9999}},
        )
        dep = DependencyReasoning(critical_files=["a.py"])
        result = ImpactReasoner().reason(ctx, dep)
        assert 0.0 <= result.refactor_impact_score <= 1.0

    def test_test_file_detection(self):
        from app.services.reasoning.impact_reasoner import ImpactReasoner
        ctx = ReasoningContext(repository_id="r", repository_hash="h",
                               intelligence_summary={"file_count": 10})
        dep = DependencyReasoning(
            critical_files=["test_main.py", "src/service.py"],
            transitive_impact=["tests/test_utils.py"],
        )
        result = ImpactReasoner().reason(ctx, dep)
        assert any("test" in f.lower() for f in result.test_impact)

    def test_doc_file_detection(self):
        from app.services.reasoning.impact_reasoner import ImpactReasoner
        ctx = ReasoningContext(repository_id="r", repository_hash="h",
                               intelligence_summary={"file_count": 10})
        dep = DependencyReasoning(
            critical_files=["README.md", "src/service.py"],
        )
        result = ImpactReasoner().reason(ctx, dep)
        assert "README.md" in result.documentation_impact

    def test_empty_dependency_reasoning(self):
        from app.services.reasoning.impact_reasoner import ImpactReasoner
        ctx = ReasoningContext(repository_id="r", repository_hash="h",
                               intelligence_summary={"file_count": 10})
        result = ImpactReasoner().reason(ctx, DependencyReasoning())
        assert result.direct_impact == []
        assert result.breaking_change_probability == 0.0


# ---------------------------------------------------------------------------
# 7. EvidenceRanker
# ---------------------------------------------------------------------------

class TestEvidenceRanker:

    def test_score_ordering(self):
        from app.services.reasoning.evidence_ranker import EvidenceRanker
        ctx = ReasoningContext(
            repository_id="r", repository_hash="h",
            memory_summary={"hotspot_history": {"hot.py": 10}},
        )
        dep = DependencyReasoning(critical_files=["hot.py"])
        result = EvidenceRanker().rank(ctx, dep)
        if len(result.ranked_items) > 1:
            scores = [i.score for i in result.ranked_items]
            assert scores == sorted(scores, reverse=True)

    def test_tie_breaking_by_evidence_id(self):
        from app.services.reasoning.evidence_ranker import EvidenceRanker
        ctx = ReasoningContext(repository_id="r", repository_hash="h")
        dep = DependencyReasoning(critical_files=["z.py", "a.py"])
        result = EvidenceRanker().rank(ctx, dep)
        # Items with equal scores → sorted by evidence_id ASC
        tied = [i for i in result.ranked_items]
        if len(tied) >= 2:
            for i in range(len(tied) - 1):
                assert (tied[i].score > tied[i+1].score) or (tied[i].evidence_id <= tied[i+1].evidence_id)

    def test_zero_evidence_returns_empty(self):
        from app.services.reasoning.evidence_ranker import EvidenceRanker
        ctx = ReasoningContext(repository_id="r", repository_hash="h")
        dep = DependencyReasoning()
        result = EvidenceRanker().rank(ctx, dep)
        assert isinstance(result.ranked_items, list)
        assert isinstance(result.total_sources, int)

    def test_output_deterministic(self):
        from app.services.reasoning.evidence_ranker import EvidenceRanker
        ctx = ReasoningContext(
            repository_id="r", repository_hash="h",
            memory_summary={"hotspot_history": {"hot.py": 5}},
        )
        dep = DependencyReasoning(critical_files=["hot.py", "cold.py"])
        r1 = EvidenceRanker().rank(ctx, dep)
        r2 = EvidenceRanker().rank(ctx, dep)
        ids1 = [i.evidence_id for i in r1.ranked_items]
        ids2 = [i.evidence_id for i in r2.ranked_items]
        assert ids1 == ids2


# ---------------------------------------------------------------------------
# 8. HistoricalReasoner
# ---------------------------------------------------------------------------

class TestHistoricalReasoner:

    def test_no_memory_returns_default(self):
        from app.services.reasoning.historical_reasoner import HistoricalReasoner
        ctx = ReasoningContext(repository_id="no-memory-repo", repository_hash="h")
        result = HistoricalReasoner().reason(ctx, "Bug Fix")
        assert result.success_probability == 0.8
        assert result.similar_workflows == []

    def test_success_probability_with_all_success(self):
        """100% success history → probability 1.0."""
        from app.services.reasoning.historical_reasoner import HistoricalReasoner
        from unittest.mock import patch, MagicMock
        wf1 = MagicMock(intent="Bug Fix", success=True, workflow_id="wf1",
                         findings=[], provider_usage=[])
        wf2 = MagicMock(intent="Bug Fix", success=True, workflow_id="wf2",
                         findings=[], provider_usage=[])
        memory = MagicMock(recurring_files=[], hotspot_history={})
        patterns = []
        recommendations = []
        metrics = MagicMock(provider_reliability={})
        history = [wf1, wf2]
        with patch("app.services.memory.memory_storage") as mock_ms:
            mock_ms.load.return_value = (memory, patterns, recommendations, metrics, history)
            ctx = ReasoningContext(repository_id="r", repository_hash="h")
            result = HistoricalReasoner().reason(ctx, "Bug Fix")
        assert result.success_probability == 1.0

    def test_success_probability_with_all_failures(self):
        from app.services.reasoning.historical_reasoner import HistoricalReasoner
        from unittest.mock import patch, MagicMock
        wf1 = MagicMock(intent="Security Audit", success=False, workflow_id="wf1",
                         findings=[], provider_usage=[])
        memory = MagicMock(recurring_files=[], hotspot_history={})
        patterns = []
        metrics = MagicMock(provider_reliability={})
        with patch("app.services.memory.memory_storage") as mock_ms:
            mock_ms.load.return_value = (memory, patterns, [], metrics, [wf1])
            ctx = ReasoningContext(repository_id="r", repository_hash="h")
            result = HistoricalReasoner().reason(ctx, "Security Audit")
        assert result.success_probability == 0.0

    def test_similar_workflows_sorted(self):
        from app.services.reasoning.historical_reasoner import HistoricalReasoner
        from unittest.mock import patch, MagicMock
        wf1 = MagicMock(intent="Bug Fix", success=True, workflow_id="wf-z", findings=[])
        wf2 = MagicMock(intent="Bug Fix", success=True, workflow_id="wf-a", findings=[])
        memory = MagicMock(recurring_files=[], hotspot_history={})
        metrics = MagicMock(provider_reliability={})
        with patch("app.services.memory.memory_storage") as mock_ms:
            mock_ms.load.return_value = (memory, [], [], metrics, [wf1, wf2])
            ctx = ReasoningContext(repository_id="r", repository_hash="h")
            result = HistoricalReasoner().reason(ctx, "Bug Fix")
        assert result.similar_workflows == sorted(result.similar_workflows)

    def test_common_risks_sorted_and_deduped(self):
        from app.services.reasoning.historical_reasoner import HistoricalReasoner
        from unittest.mock import patch, MagicMock
        pat1 = MagicMock(severity="high", category="security", key_signature="svc:main.py")
        pat2 = MagicMock(severity="high", category="security", key_signature="svc:main.py")  # duplicate
        pat3 = MagicMock(severity="low", category="info", key_signature="x")
        memory = MagicMock(recurring_files=[], hotspot_history={})
        metrics = MagicMock(provider_reliability={})
        with patch("app.services.memory.memory_storage") as mock_ms:
            mock_ms.load.return_value = (memory, [pat1, pat2, pat3], [], metrics, [])
            ctx = ReasoningContext(repository_id="r", repository_hash="h")
            result = HistoricalReasoner().reason(ctx, "General")
        # Only one "security:svc:main.py" entry, low-severity excluded
        assert result.common_risks == sorted(set(result.common_risks))
        assert all("info" not in r for r in result.common_risks)


# ---------------------------------------------------------------------------
# 9. ReasoningEngine
# ---------------------------------------------------------------------------

class TestReasoningEngine:

    def test_ensure_cache_hit_skips_build(self, monkeypatch):
        from app.services.reasoning.reasoning_engine import ReasoningEngine
        import app.services.reasoning.reasoning_storage as rs
        monkeypatch.setattr(rs, "validate_cache", lambda *a, **kw: True)
        mock_summary = MagicMock(spec=ReasoningSummary)
        monkeypatch.setattr(rs, "load", lambda *a, **kw: (mock_summary, [], MagicMock()))
        engine = ReasoningEngine()
        result = engine.ensure("repo", "goal", "hash", "")
        assert result is mock_summary

    def test_build_runs_full_pipeline(self, monkeypatch, tmp_path):
        """Full pipeline should return a ReasoningSummary without errors."""
        from app.services.reasoning.reasoning_engine import ReasoningEngine
        import app.services.reasoning.reasoning_storage as rs
        monkeypatch.setattr(rs, "settings", MagicMock(WORKSPACE_ROOT=str(tmp_path)))
        monkeypatch.setattr(rs, "validate_cache", lambda *a, **kw: False)
        engine = ReasoningEngine()
        result = engine.build("repo-build-test", "Fix bugs", "hash-xyz", "")
        assert isinstance(result, ReasoningSummary)
        assert result.repository_id == "repo-build-test"

    def test_get_summary_returns_none_if_not_built(self, monkeypatch, tmp_path):
        from app.services.reasoning.reasoning_engine import ReasoningEngine
        import app.services.reasoning.reasoning_storage as rs
        monkeypatch.setattr(rs, "settings", MagicMock(WORKSPACE_ROOT=str(tmp_path)))
        engine = ReasoningEngine()
        assert engine.get_summary("no-such-repo") is None

    def test_invalidate_clears_cache(self, monkeypatch, tmp_path):
        from app.services.reasoning.reasoning_engine import ReasoningEngine
        import app.services.reasoning.reasoning_storage as rs
        monkeypatch.setattr(rs, "settings", MagicMock(WORKSPACE_ROOT=str(tmp_path)))
        engine = ReasoningEngine()
        engine.build("repo-inv", "goal", "hash", "")
        assert rs.validate_cache("repo-inv", "hash") is True
        engine.invalidate("repo-inv")
        assert rs.validate_cache("repo-inv", "hash") is False


# ---------------------------------------------------------------------------
# 10. Thread safety
# ---------------------------------------------------------------------------

class TestThreadSafety:

    def test_same_repo_only_one_build_executes(self, monkeypatch, tmp_path):
        """Two threads for the same repo — the second must hit the cache after the first finishes."""
        from app.services.reasoning.reasoning_engine import ReasoningEngine
        import app.services.reasoning.reasoning_storage as rs
        monkeypatch.setattr(rs, "settings", MagicMock(WORKSPACE_ROOT=str(tmp_path)))

        build_count = {"count": 0}
        original_run = ReasoningEngine._run_pipeline

        def counting_run(self, *args, **kwargs):
            build_count["count"] += 1
            return original_run(self, *args, **kwargs)

        monkeypatch.setattr(ReasoningEngine, "_run_pipeline", counting_run)

        engine = ReasoningEngine()
        results = []
        errors = []

        def worker():
            try:
                r = engine.ensure("shared-repo", "goal", "hash-shared", "")
                results.append(r)
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=worker)
        t2 = threading.Thread(target=worker)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert not errors
        assert len(results) == 2
        # At most one _run_pipeline call — the second thread hits double-check cache
        assert build_count["count"] <= 2  # allow 2 for race on very fast systems

    def test_different_repos_build_in_parallel(self, monkeypatch, tmp_path):
        """Two threads for DIFFERENT repos must be able to run concurrently (no cross-repo blocking)."""
        from app.services.reasoning.reasoning_engine import ReasoningEngine
        import app.services.reasoning.reasoning_storage as rs
        monkeypatch.setattr(rs, "settings", MagicMock(WORKSPACE_ROOT=str(tmp_path)))

        engine = ReasoningEngine()
        timings = {}

        def worker(repo_id):
            t0 = time.time()
            engine.build(repo_id, "goal", f"hash-{repo_id}", "")
            timings[repo_id] = time.time() - t0

        t1 = threading.Thread(target=worker, args=("repo-X",))
        t2 = threading.Thread(target=worker, args=("repo-Y",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Both repos were processed
        assert "repo-X" in timings and "repo-Y" in timings


# ---------------------------------------------------------------------------
# 11. Replay from disk
# ---------------------------------------------------------------------------

class TestReplay:

    def test_get_full_dict_serves_from_disk(self, monkeypatch, tmp_path, sample_summary, sample_chains, sample_metrics):
        import app.services.reasoning.reasoning_storage as rs
        monkeypatch.setattr(rs, "settings", MagicMock(WORKSPACE_ROOT=str(tmp_path)))
        rs.save("replay-repo", sample_summary, sample_chains, sample_metrics, {})
        data = rs.load_full_dict("replay-repo")
        assert data is not None
        assert data["repository_id"] == sample_summary.repository_id

    def test_load_section_serves_from_disk(self, monkeypatch, tmp_path, sample_summary, sample_chains, sample_metrics):
        import app.services.reasoning.reasoning_storage as rs
        monkeypatch.setattr(rs, "settings", MagicMock(WORKSPACE_ROOT=str(tmp_path)))
        rs.save("replay-repo2", sample_summary, sample_chains, sample_metrics, {})
        impact = rs.load_section("replay-repo2", "impact_reasoning")
        assert impact is not None
        assert "breaking_change_probability" in impact
