"""Priority Engine — deterministic priority score calculation.

Calculates priority score and maps to priority level (low/medium/high/critical).
"""

from __future__ import annotations

from typing import List
from app.core.logger import logger
from app.services.reasoning.reasoning_models import ReasoningSummary


class PriorityEngine:
    """Calculates priority details based on deterministic rules."""

    def calculate(self, r_summary: ReasoningSummary, triggered_policies: List[str]) -> tuple[float, str]:
        """Compute score [0.0, 1.0] and level (low/medium/high/critical)."""
        logger.debug(f"[PriorityEngine] Computing priority for {r_summary.repository_id}")
        
        # 1. Reasoning Score (35%)
        r_score = r_summary.reasoning_score or 0.0

        # 2. Breaking Change Probability (35%)
        breaking_prob = 0.0
        if r_summary.impact_reasoning:
            breaking_prob = r_summary.impact_reasoning.breaking_change_probability

        # 3. Triggered Policies (30%)
        # Scale based on fraction of maximum 5 policies
        policy_ratio = len(triggered_policies) / 5.0

        score = (r_score * 0.35) + (breaking_prob * 0.35) + (policy_ratio * 0.30)
        score = min(1.0, max(0.0, score))

        # Map to priority level
        if score < 0.3:
            level = "low"
        elif score < 0.6:
            level = "medium"
        elif score < 0.85:
            level = "high"
        else:
            level = "critical"

        return round(score, 4), level


priority_engine = PriorityEngine()
