"""Historical Reasoner — memory-driven workflow history analysis.

Consumes Memory Engine only. Zero LLM calls. Zero network I/O.
All output lists are sorted before return for deterministic output.
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.core.logger import logger
from app.services.reasoning.reasoning_models import (
    HistoricalReasoning,
    ReasoningContext,
)


class HistoricalReasoner:

    def reason(self, context: ReasoningContext, current_intent: str) -> HistoricalReasoning:
        logger.debug(f"[HistoricalReasoner] Running for {context.repository_id}, intent={current_intent}")

        try:
            from app.services.memory import memory_storage
            mem_data = memory_storage.load(context.repository_id)
        except Exception:
            mem_data = None

        if not mem_data:
            return HistoricalReasoning(success_probability=0.8)

        memory, patterns, recommendations, metrics, history = mem_data

        # 1. Similar workflows — same intent, sorted by workflow_id
        similar_workflows = sorted([
            h.workflow_id for h in history
            if h.intent == current_intent
        ])

        # 2. Historical failures — same intent + failed, sorted
        historical_failures = sorted([
            h.workflow_id for h in history
            if h.intent == current_intent and not h.success
        ])

        # 3. Historical fixes — unique file paths from successful runs of same intent
        fix_files: List[str] = []
        for h in history:
            if h.intent == current_intent and h.success:
                for finding in h.findings:
                    fpath = finding.get("file_path", "") if isinstance(finding, dict) else ""
                    if fpath and fpath not in fix_files:
                        fix_files.append(fpath)
        historical_fixes = sorted(fix_files)

        # 4. Common risks — patterns with severity high/critical, unique categories, sorted + deduped
        risk_set: List[str] = []
        for pat in patterns:
            if pat.severity in ("high", "critical"):
                label = f"{pat.category}: {pat.key_signature}"
                if label not in risk_set:
                    risk_set.append(label)
        common_risks = sorted(risk_set)

        # 5. Success probability — successes / total for same intent; default 0.8 if no history
        intent_runs = [h for h in history if h.intent == current_intent]
        if intent_runs:
            successes = sum(1 for h in intent_runs if h.success)
            success_probability = round(successes / len(intent_runs), 4)
        else:
            success_probability = 0.8

        # 6. Provider history — from LearningMetrics, keys sorted
        provider_history = {
            k: round(v, 4)
            for k, v in sorted(metrics.provider_reliability.items())
        }

        return HistoricalReasoning(
            similar_workflows=similar_workflows,
            historical_failures=historical_failures,
            historical_fixes=historical_fixes,
            common_risks=common_risks,
            success_probability=success_probability,
            provider_history=provider_history,
        )


historical_reasoner = HistoricalReasoner()
