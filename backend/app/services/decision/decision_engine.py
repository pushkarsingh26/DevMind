"""Decision Engine — master orchestrator.

Orchestrates policy evaluation and priority calculation based on Phase 8.8 Reasoning output.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.logger import logger
from app.services.reasoning.reasoning_engine import reasoning_engine
from app.services.decision import decision_storage
from app.services.decision.policy_engine import policy_engine
from app.services.decision.priority_engine import priority_engine
from app.services.decision.decision_models import (
    DecisionSummary,
    DecisionHistoryRecord,
    DecisionMetrics,
    DecisionTelemetry,
)


class DecisionEngine:
    """Singleton orchestrator for repository decision evaluations."""

    def __init__(self):
        self._locks: Dict[str, threading.Lock] = {}
        self._lock_registry = threading.Lock()

    def _get_lock(self, repository_id: str) -> threading.Lock:
        with self._lock_registry:
            if repository_id not in self._locks:
                self._locks[repository_id] = threading.Lock()
            return self._locks[repository_id]

    # ------------------------------------------------------------------
    # Public Read API (disk-only)
    # ------------------------------------------------------------------

    def get_summary(self, repository_id: str) -> Optional[DecisionSummary]:
        res = decision_storage.load(repository_id)
        return res[0] if res else None

    def get_raw_dict(self, repository_id: str, filename: str) -> Optional[Any]:
        return decision_storage.load_raw_file(repository_id, filename)

    def invalidate(self, repository_id: str) -> None:
        decision_storage.invalidate(repository_id)

    # ------------------------------------------------------------------
    # Ensure & Build Execution Pipeline
    # ------------------------------------------------------------------

    def ensure(
        self,
        repository_id: str,
        goal: str,
        repo_hash: str,
        intel_path: str,
    ) -> DecisionSummary:
        """Return cached DecisionSummary if valid, otherwise rebuild."""
        if decision_storage.validate_cache(repository_id, repo_hash):
            res = decision_storage.load(repository_id)
            if res:
                logger.debug(f"[DecisionEngine] Cache hit for {repository_id}")
                return res[0]
        return self.build(repository_id, goal, repo_hash, intel_path)

    def build(
        self,
        repository_id: str,
        goal: str,
        repo_hash: str,
        intel_path: str,
    ) -> DecisionSummary:
        """Evaluate decision policies and priorities. Thread-safe per repo."""
        t_start = time.time()
        lock = self._get_lock(repository_id)
        
        with lock:
            # Double-check cache inside lock
            if decision_storage.validate_cache(repository_id, repo_hash):
                res = decision_storage.load(repository_id)
                if res:
                    logger.debug(f"[DecisionEngine] Cache hit after lock acquisition for {repository_id}")
                    return res[0]

            logger.info(f"[DecisionEngine] Evaluating decisions for {repository_id}")

            cache_hit = False
            cache_miss = True

            # Ensure prerequisite reasoning summary is constructed
            # (ReasoningEngine has its own lazy build cache/ensure checks)
            t_reason = time.time()
            r_summary = reasoning_engine.ensure(repository_id, goal, repo_hash, intel_path)
            reason_ms = (time.time() - t_reason) * 1000

            # 1. Policy Evaluation (timed)
            t_policy = time.time()
            evaluated_policies, triggered_policies = policy_engine.evaluate(r_summary)
            policy_time_ms = (time.time() - t_policy) * 1000

            # 2. Priority Engine (timed)
            t_priority = time.time()
            score, priority_level = priority_engine.calculate(r_summary, triggered_policies)
            priority_time_ms = (time.time() - t_priority) * 1000

            # 3. Execution Recommendation mapping
            # Rules:
            # - If HIGH_RISK_CHANGES triggered: REQUIRE_APPROVAL
            # - If LOW_HISTORICAL_SUCCESS and CRITICAL_PATH_EXCEEDED: SKIP_WORKFLOW
            # - If LOW_HISTORICAL_SUCCESS or MODULE_OVERCOUPLING: REORDER_STEPS
            # - Else: PROCEED
            if "HIGH_RISK_CHANGES" in triggered_policies:
                execution_rec = "REQUIRE_APPROVAL"
            elif "LOW_HISTORICAL_SUCCESS" in triggered_policies and "CRITICAL_PATH_EXCEEDED" in triggered_policies:
                execution_rec = "SKIP_WORKFLOW"
            elif "LOW_HISTORICAL_SUCCESS" in triggered_policies or "MODULE_OVERCOUPLING" in triggered_policies:
                execution_rec = "REORDER_STEPS"
            else:
                execution_rec = "PROCEED"

            total_ms = (time.time() - t_start) * 1000

            # Load history or start fresh
            loaded = decision_storage.load(repository_id)
            history = loaded[1] if loaded else []

            summary = DecisionSummary(
                repository_id=repository_id,
                repository_hash=repo_hash,
                decision_score=score,
                priority_level=priority_level,
                execution_recommendation=execution_rec,
                policies_evaluated=evaluated_policies,
                policies_triggered=triggered_policies,
                generated_at=datetime.now(timezone.utc).isoformat(),
                build_time_ms=total_ms,
            )

            metrics = DecisionMetrics(
                decision_time_ms=total_ms,
                policy_time_ms=policy_time_ms,
                priority_time_ms=priority_time_ms,
                cache_hits=1 if cache_hit else 0,
                cache_misses=1 if cache_miss else 0,
            )

            telemetry = DecisionTelemetry(
                decision_time_ms=total_ms,
                policy_time_ms=policy_time_ms,
                priority_time_ms=priority_time_ms,
                cache_hits=0,
                cache_misses=1,
                policies_evaluated=len(evaluated_policies),
                policies_triggered=len(triggered_policies),
                workflow_skipped=execution_rec == "SKIP_WORKFLOW",
                workflow_reordered=execution_rec == "REORDER_STEPS",
                decision_score=score,
            )

            # Persist results atomically
            decision_storage.save(repository_id, summary, history, metrics, telemetry)

            return summary


decision_engine = DecisionEngine()
