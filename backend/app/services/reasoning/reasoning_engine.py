"""Reasoning Engine — master orchestrator.

Features:
- Per-repository build locks (different repos build concurrently)
- Lazy cache: validate_cache() before every build
- Double-checked locking after acquiring the per-repo lock
- Full pipeline timing per stage stored in ReasoningMetrics
- Disk-only read API (get_summary, get_metrics, etc.) — no re-computation
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logger import logger
from app.services.reasoning import reasoning_storage
from app.services.reasoning.context_builder import context_builder
from app.services.reasoning.dependency_reasoner import dependency_reasoner
from app.services.reasoning.evidence_ranker import evidence_ranker
from app.services.reasoning.historical_reasoner import historical_reasoner
from app.services.reasoning.impact_reasoner import impact_reasoner
from app.services.reasoning.reasoning_models import (
    ReasoningChain,
    ReasoningContext,
    ReasoningMetrics,
    ReasoningSummary,
)


class ReasoningEngine:
    """Singleton orchestrator for the reasoning pipeline."""

    def __init__(self):
        # Per-repository build locks
        self._locks: Dict[str, threading.Lock] = {}
        self._lock_registry = threading.Lock()  # protects _locks dict

    # ------------------------------------------------------------------
    # Lock management
    # ------------------------------------------------------------------

    def _get_lock(self, repository_id: str) -> threading.Lock:
        with self._lock_registry:
            if repository_id not in self._locks:
                self._locks[repository_id] = threading.Lock()
            return self._locks[repository_id]

    # ------------------------------------------------------------------
    # Public read API — disk-only, no computation
    # ------------------------------------------------------------------

    def get_summary(self, repository_id: str) -> Optional[ReasoningSummary]:
        """Load ReasoningSummary from disk. None if not built yet."""
        result = reasoning_storage.load(repository_id)
        return result[0] if result else None

    def get_chains(self, repository_id: str) -> List[ReasoningChain]:
        """Load chains from disk."""
        data = reasoning_storage.load_chains_list(repository_id)
        if not data:
            return []
        return [ReasoningChain.from_dict(c) for c in data]

    def get_metrics(self, repository_id: str) -> Optional[ReasoningMetrics]:
        """Load ReasoningMetrics from disk."""
        data = reasoning_storage.load_metrics_dict(repository_id)
        return ReasoningMetrics.from_dict(data) if data else None

    def get_metrics_dict(self, repository_id: str) -> Optional[Dict[str, Any]]:
        """Load raw metrics dict (for API responses)."""
        return reasoning_storage.load_metrics_dict(repository_id)

    def get_full_dict(self, repository_id: str) -> Optional[Dict[str, Any]]:
        """Load full reasoning.json as dict (for API responses)."""
        return reasoning_storage.load_full_dict(repository_id)

    def get_section(self, repository_id: str, section: str) -> Optional[Dict[str, Any]]:
        """Load a specific section of reasoning.json (for API responses)."""
        return reasoning_storage.load_section(repository_id, section)

    def invalidate(self, repository_id: str) -> None:
        """Invalidate cached reasoning for a repository."""
        reasoning_storage.invalidate(repository_id)

    # ------------------------------------------------------------------
    # Lazy ensure — checks cache before building
    # ------------------------------------------------------------------

    def ensure(
        self,
        repository_id: str,
        goal: str,
        repo_hash: str,
        intel_path: str,
    ) -> ReasoningSummary:
        """Return cached ReasoningSummary if valid, otherwise rebuild."""
        if reasoning_storage.validate_cache(repository_id, repo_hash):
            result = reasoning_storage.load(repository_id)
            if result:
                logger.debug(f"[ReasoningEngine] Cache hit for {repository_id}")
                return result[0]
        return self.build(repository_id, goal, repo_hash, intel_path)

    # ------------------------------------------------------------------
    # Full pipeline build (with per-repo lock + double-checked locking)
    # ------------------------------------------------------------------

    def build(
        self,
        repository_id: str,
        goal: str,
        repo_hash: str,
        intel_path: str,
    ) -> ReasoningSummary:
        """Build the full reasoning pipeline. Thread-safe per repository."""
        repo_lock = self._get_lock(repository_id)
        with repo_lock:
            # Double-check after acquiring the lock — another thread may have built while we waited
            if reasoning_storage.validate_cache(repository_id, repo_hash):
                result = reasoning_storage.load(repository_id)
                if result:
                    logger.debug(f"[ReasoningEngine] Cache hit after lock acquire for {repository_id}")
                    return result[0]

            return self._run_pipeline(repository_id, goal, repo_hash, intel_path)

    def _run_pipeline(
        self,
        repository_id: str,
        goal: str,
        repo_hash: str,
        intel_path: str,
    ) -> ReasoningSummary:
        """Execute the full reasoning pipeline and persist results."""
        total_start = time.time()
        logger.info(f"[ReasoningEngine] Building reasoning for {repository_id}")

        telemetry: Dict[str, Any] = {}

        # Stage 1: Context Builder
        t = time.time()
        reasoning_ctx = context_builder.build(repository_id, intel_path, repo_hash)
        context_build_ms = (time.time() - t) * 1000
        telemetry["context_build_ms"] = round(context_build_ms, 2)

        # Detect current intent from goal
        current_intent = _detect_intent(goal)

        # Stage 2: Dependency Reasoner
        t = time.time()
        dep_reasoning = dependency_reasoner.reason(reasoning_ctx)
        dependency_reasoning_ms = (time.time() - t) * 1000
        telemetry["dependency_reasoning_ms"] = round(dependency_reasoning_ms, 2)

        # Stage 3: Impact Reasoner
        t = time.time()
        imp_reasoning = impact_reasoner.reason(reasoning_ctx, dep_reasoning)
        impact_reasoning_ms = (time.time() - t) * 1000
        telemetry["impact_reasoning_ms"] = round(impact_reasoning_ms, 2)

        # Stage 4: Evidence Ranker
        t = time.time()
        evi_ranking = evidence_ranker.rank(reasoning_ctx, dep_reasoning)
        evidence_ranking_ms = (time.time() - t) * 1000
        telemetry["evidence_ranking_ms"] = round(evidence_ranking_ms, 2)

        # Stage 5: Historical Reasoner
        t = time.time()
        his_reasoning = historical_reasoner.reason(reasoning_ctx, current_intent)
        historical_reasoning_ms = (time.time() - t) * 1000
        telemetry["historical_reasoning_ms"] = round(historical_reasoning_ms, 2)

        # Stage 6: Assemble ReasoningSummary
        reasoning_score = _compute_reasoning_score(dep_reasoning, imp_reasoning, his_reasoning)
        confidence = _compute_confidence(dep_reasoning, evi_ranking, his_reasoning)
        critical_paths = sorted(dep_reasoning.critical_files[:10])
        affected_modules = sorted(list(dep_reasoning.architecture_influence.keys())[:20])
        risk_indicators = _compute_risk_indicators(imp_reasoning, his_reasoning)

        total_ms = (time.time() - total_start) * 1000

        summary = ReasoningSummary(
            repository_id=repository_id,
            repository_hash=repo_hash,
            reasoning_score=round(reasoning_score, 4),
            confidence=round(confidence, 4),
            critical_paths=critical_paths,
            affected_modules=affected_modules,
            risk_indicators=risk_indicators,
            reasoning_context=reasoning_ctx,
            dependency_reasoning=dep_reasoning,
            impact_reasoning=imp_reasoning,
            evidence_ranking=evi_ranking,
            historical_reasoning=his_reasoning,
            generated_at=datetime.now(timezone.utc).isoformat(),
            build_time_ms=round(total_ms, 2),
        )

        # Extract chains from dependency reasoning
        chains = dep_reasoning.dependency_chains

        # Stage 7: Metrics
        metrics = ReasoningMetrics(
            reasoning_build_ms=round(total_ms, 2),
            context_build_ms=round(context_build_ms, 2),
            dependency_reasoning_ms=round(dependency_reasoning_ms, 2),
            impact_reasoning_ms=round(impact_reasoning_ms, 2),
            evidence_ranking_ms=round(evidence_ranking_ms, 2),
            historical_reasoning_ms=round(historical_reasoning_ms, 2),
            serialization_ms=0.0,  # filled after save
            cache_hit=False,
            cache_miss=True,
            reasoning_score=round(reasoning_score, 4),
            reasoning_confidence=round(confidence, 4),
            critical_path_count=len(critical_paths),
            affected_files=len(dep_reasoning.critical_files) + len(dep_reasoning.transitive_impact),
            affected_symbols=len(dep_reasoning.affected_symbols),
        )

        # Stage 8: Persist
        t = time.time()
        telemetry["reasoning_score"] = round(reasoning_score, 4)
        telemetry["reasoning_confidence"] = round(confidence, 4)
        telemetry["critical_path_count"] = len(critical_paths)
        telemetry["affected_files"] = metrics.affected_files
        telemetry["affected_symbols"] = metrics.affected_symbols
        telemetry["cache_hit"] = False
        telemetry["cache_miss"] = True

        reasoning_storage.save(repository_id, summary, chains, metrics, telemetry)
        serialization_ms = (time.time() - t) * 1000
        metrics.serialization_ms = round(serialization_ms, 2)
        telemetry["serialization_ms"] = round(serialization_ms, 2)

        logger.info(
            f"[ReasoningEngine] Built reasoning for {repository_id} in {total_ms:.0f}ms "
            f"(score={reasoning_score:.3f}, confidence={confidence:.3f})"
        )
        return summary


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _detect_intent(goal: str) -> str:
    """Minimal intent detection (mirrors PlanningEngine.detect_intent)."""
    g = goal.lower()
    if any(w in g for w in ("dependency", "import", "package", "cycle")):
        return "Dependency Analysis"
    if any(w in g for w in ("security", "vulnerability", "cve")):
        return "Security Audit"
    if any(w in g for w in ("document", "docs", "readme")):
        return "Documentation"
    if any(w in g for w in ("refactor", "coupling", "simplify")):
        return "Refactoring"
    if any(w in g for w in ("performance", "latency", "optimize")):
        return "Performance"
    if any(w in g for w in ("test", "coverage", "pytest")):
        return "Testing"
    if any(w in g for w in ("bug", "fix", "issue", "error", "crash")):
        return "Bug Fix"
    if any(w in g for w in ("architecture", "design", "structure")):
        return "Architecture Review"
    return "General Analysis"


def _compute_reasoning_score(dep, imp, his) -> float:
    """Weighted composite score [0,1] from dependency, impact, and history."""
    dep_score = min(1.0, len(dep.critical_files) / 10.0) * 0.3
    imp_score = (1.0 - imp.breaking_change_probability) * 0.4
    his_score = his.success_probability * 0.3
    return min(1.0, max(0.0, dep_score + imp_score + his_score))


def _compute_confidence(dep, evi, his) -> float:
    """Average confidence from evidence top score and historical probability."""
    scores = [
        evi.top_confidence if evi.ranked_items else 0.5,
        his.success_probability,
        min(1.0, len(dep.dependency_chains) / max(len(dep.critical_files), 1)),
    ]
    return round(sum(scores) / len(scores), 4)


def _compute_risk_indicators(imp, his) -> List[str]:
    """Deterministic risk indicator labels, sorted."""
    indicators = []
    if imp.breaking_change_probability > 0.7:
        indicators.append("HIGH_BREAKING_CHANGE_RISK")
    if imp.repository_wide_impact:
        indicators.append("REPOSITORY_WIDE_IMPACT")
    if his.success_probability < 0.5:
        indicators.append("LOW_HISTORICAL_SUCCESS")
    if his.historical_failures:
        indicators.append("PREVIOUS_FAILURES_DETECTED")
    if imp.refactor_impact_score > 0.6:
        indicators.append("HIGH_REFACTOR_COMPLEXITY")
    return sorted(indicators)


reasoning_engine = ReasoningEngine()
