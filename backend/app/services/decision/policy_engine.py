"""Policy Engine — rule-based policy evaluation.

Applies 5 deterministic rules against Reasoning Engine outputs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
from app.core.logger import logger
from app.services.reasoning.reasoning_models import ReasoningSummary


class PolicyEngine:
    """Evaluates rule-based policies against reasoning and memory metadata."""

    def evaluate(self, r_summary: ReasoningSummary) -> Tuple[List[str], List[str]]:
        """Evaluate policies and return (evaluated_list, triggered_list)."""
        logger.debug(f"[PolicyEngine] Evaluating policies for {r_summary.repository_id}")
        
        evaluated = [
            "CRITICAL_PATH_EXCEEDED",
            "HIGH_RISK_CHANGES",
            "LOW_HISTORICAL_SUCCESS",
            "MODULE_OVERCOUPLING",
            "HIGH_REFACTOR_COMPLEXITY",
        ]
        triggered = []

        # 1. CRITICAL_PATH_EXCEEDED
        # Triggered if critical path count > 10
        critical_paths = r_summary.critical_paths or []
        if len(critical_paths) > 10:
            triggered.append("CRITICAL_PATH_EXCEEDED")

        # 2. HIGH_RISK_CHANGES
        # Triggered if breaking change probability > 0.7
        breaking_prob = 0.0
        if r_summary.impact_reasoning:
            breaking_prob = r_summary.impact_reasoning.breaking_change_probability
        if breaking_prob > 0.7:
            triggered.append("HIGH_RISK_CHANGES")

        # 3. LOW_HISTORICAL_SUCCESS
        # Triggered if historical success rate < 0.5
        success_prob = 0.8
        if r_summary.historical_reasoning:
            success_prob = r_summary.historical_reasoning.success_probability
        if success_prob < 0.5:
            triggered.append("LOW_HISTORICAL_SUCCESS")

        # 4. MODULE_OVERCOUPLING
        # Triggered if affected modules count > 15
        affected_mods = r_summary.affected_modules or []
        if len(affected_mods) > 15:
            triggered.append("MODULE_OVERCOUPLING")

        # 5. HIGH_REFACTOR_COMPLEXITY
        # Triggered if memory context has pattern count > 20
        pattern_count = 0
        if r_summary.reasoning_context:
            pattern_count = r_summary.reasoning_context.memory_summary.get("pattern_count", 0)
        if pattern_count > 20:
            triggered.append("HIGH_REFACTOR_COMPLEXITY")

        return sorted(evaluated), sorted(triggered)


policy_engine = PolicyEngine()
