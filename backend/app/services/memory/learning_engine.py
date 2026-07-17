"""Orchestrates learning metrics updates and memory cache management."""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logger import logger
from app.services.memory import (
    memory_storage,
    pattern_engine,
    recommendation_engine,
    repository_memory,
)
from app.services.memory.memory_models import (
    LearningMetrics,
    MemoryStatistics,
    PatternRecord,
    Recommendation,
    RepositoryMemory,
    WorkflowMemory,
)


class LearningEngine:
    """Calculates learning metrics and manages cache updates on workflow completions."""

    def update_workflow_run(
        self,
        repository_id: str,
        repo_hash: str,
        workflow_run: WorkflowMemory,
    ) -> bool:
        """Invoked after a workflow completes. Updates all persisted memory engines."""
        try:
            logger.info(f"[LearningEngine] Recording completed workflow {workflow_run.workflow_id} for {repository_id}")

            # 1. Load existing structures, or initialize empty ones
            loaded = memory_storage.load(repository_id)
            if loaded:
                memory, patterns, recommendations, metrics, history = loaded
            else:
                memory = RepositoryMemory(repository_id=repository_id, repository_hash=repo_hash)
                patterns = []
                recommendations = []
                metrics = LearningMetrics()
                history = []

            # Update repository hash if changed
            memory.repository_hash = repo_hash

            # 2. Append to workflow execution history (deduplicated by ID)
            history = [h for h in history if h.workflow_id != workflow_run.workflow_id]
            history.append(workflow_run)

            # 3. Update Repository Memory stats
            repository_memory.update_repository_memory(memory, workflow_run)

            # 4. Trigger Pattern Engine
            patterns = pattern_engine.detect_patterns(history)

            # 5. Trigger Recommendation Engine
            recommendations = recommendation_engine.generate_recommendations(
                memory, history, patterns
            )

            # 6. Re-calculate Learning Metrics
            metrics = self._calculate_metrics(history, patterns)

            # 7. Persist to disk
            ok = memory_storage.save(
                repository_id=repository_id,
                memory=memory,
                patterns=patterns,
                recommendations=recommendations,
                metrics=metrics,
                history=history,
            )
            return ok
        except Exception as exc:
            logger.error(f"[LearningEngine] Failed to update workflow run: {exc}")
            return False

    def rebuild(self, repository_id: str, repo_hash: str) -> bool:
        """Force rebuild of patterns and recommendations from history logs."""
        try:
            loaded = memory_storage.load(repository_id)
            if not loaded:
                # No history to rebuild from
                return False

            memory, patterns, recommendations, metrics, history = loaded

            # Recalculate
            patterns = pattern_engine.detect_patterns(history)
            recommendations = recommendation_engine.generate_recommendations(
                memory, history, patterns
            )
            metrics = self._calculate_metrics(history, patterns)

            memory_storage.save(
                repository_id=repository_id,
                memory=memory,
                patterns=patterns,
                recommendations=recommendations,
                metrics=metrics,
                history=history,
            )
            return True
        except Exception as exc:
            logger.error(f"[LearningEngine] Rebuild failed for {repository_id}: {exc}")
            return False

    def get_statistics(self, repository_id: str) -> Optional[MemoryStatistics]:
        """Collects memory summary statistics."""
        try:
            loaded = memory_storage.load(repository_id)
            if not loaded:
                return None

            memory, patterns, recommendations, metrics, history = loaded
            memory_dir = memory_storage.get_memory_dir(repository_id)
            mtime = datetime.fromtimestamp(
                (memory_dir / "memory.json").stat().st_mtime, tz=timezone.utc
            ).isoformat() if (memory_dir / "memory.json").exists() else ""

            return MemoryStatistics(
                repository_id=repository_id,
                workflow_count=len(history),
                pattern_count=len(patterns),
                recommendation_count=len(recommendations),
                last_updated=mtime,
            )
        except Exception:
            return None

    def _calculate_metrics(
        self,
        history: List[WorkflowMemory],
        patterns: List[PatternRecord],
    ) -> LearningMetrics:
        """Averages and resolves trends from workflow runs."""
        if not history:
            return LearningMetrics()

        successful_count = sum(1 for h in history if h.success)
        success_rate = successful_count / len(history)

        total_duration = sum(h.duration for h in history)
        avg_duration = total_duration / len(history)

        # Average retries extraction
        total_retries = 0
        for h in history:
            total_retries += h.execution_metrics.get("retry_count", 0)
        avg_retries = total_retries / len(history)

        # Provider reliability
        # Calculated as: successful requests / total requests per provider
        provider_runs: Dict[str, List[bool]] = {}
        for h in history:
            for p in h.provider_usage:
                provider_runs.setdefault(p.lower(), []).append(h.success)

        reliability = {}
        for prov, outcomes in provider_runs.items():
            reliability[prov] = sum(1 for o in outcomes if o) / len(outcomes)

        # Repository Health Trend: computed over time
        # Starts at 100%, deducts score based on recurring findings frequency and failures
        health_trend: List[float] = []
        for i in range(1, len(history) + 1):
            subset = history[:i]
            failures = sum(1 for h in subset if not h.success)
            subset_patterns = pattern_engine.detect_patterns(subset)
            severe_patterns = sum(
                p.frequency for p in subset_patterns if p.severity.lower() in ("critical", "high")
            )
            # Health score calculation
            score = 100.0 - (failures * 15.0) - (severe_patterns * 5.0)
            score = max(10.0, min(100.0, score))
            health_trend.append(round(score, 1))

        return LearningMetrics(
            workflow_success_rate=round(success_rate, 2),
            average_execution_time=round(avg_duration, 1),
            average_retries=round(avg_retries, 2),
            provider_reliability=reliability,
            recurring_findings_count=len(patterns),
            repository_health_trend=health_trend,
        )


learning_engine = LearningEngine()
