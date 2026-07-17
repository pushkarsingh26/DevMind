"""Execution Manager coordinating resilient runs.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.core.logger import logger
from app.services.execution.execution_models import (
    ExecutionCheckpoint,
    ExecutionState,
    ExecutionMetrics,
    ExecutionBudget,
    ExecutionEvent,
)
from app.services.execution.checkpoint_storage import checkpoint_storage
from app.services.execution.provider_selector import provider_selector


class ExecutionManager:
    """Manages workflow execution lifecycle, ETA estimation, retries, and checkpoint tracking."""

    def calculate_eta(
        self,
        steps: List[Dict[str, Any]],
        completed_step_ids: List[str],
        checkpoints: List[ExecutionCheckpoint],
    ) -> int:
        """Calculates dynamic weighted ETA based on planning estimates and execution speed factor."""
        # 1. Sum up estimated durations for remaining steps
        remaining_est_duration = 0
        for step in steps:
            step_id = step.get("step_id")
            if step_id not in completed_step_ids:
                remaining_est_duration += step.get("estimated_duration", 15)

        if not completed_step_ids:
            return remaining_est_duration

        # 2. Calculate execution speed factor = average(actual_duration / estimated_duration)
        ratios = []
        for cp in checkpoints:
            if cp.status == "completed":
                # Find matching step in rules to get estimated duration
                step_est = next((s.get("estimated_duration", 15) for s in steps if s.get("step_id") == cp.step_id), 15)
                actual_dur = cp.telemetry.get("duration_sec", step_est)
                ratios.append(actual_dur / max(step_est, 1))

        speed_factor = (sum(ratios) / len(ratios)) if ratios else 1.0
        # Prevent division/multiplication extremes
        speed_factor = max(0.2, min(5.0, speed_factor))

        eta = int(remaining_est_duration * speed_factor)
        return max(5, eta)

    def initialize_run(
        self,
        workflow_id: str,
        repository_id: str,
        steps: List[Dict[str, Any]],
    ) -> Tuple[ExecutionState, ExecutionMetrics, ExecutionBudget]:
        """Creates initial execution state, metrics, and budget objects."""
        # Try loading existing checkpoint/state to resume if process restarted
        state, metrics, budget = checkpoint_storage.load_state(workflow_id)
        if state is not None and metrics is not None and budget is not None:
            logger.info(f"[ExecutionManager] Resuming execution state from file for workflow {workflow_id}")
            # Identify first non-completed step
            checkpoints = checkpoint_storage.load_checkpoints(workflow_id)
            completed_ids = [cp.step_id for cp in checkpoints if cp.status == "completed"]
            
            non_completed = [s.get("step_id") for s in steps if s.get("step_id") not in completed_ids]
            if non_completed:
                state.resume_from_step = non_completed[0]
                state.current_step_id = non_completed[0]
                state.status = "running"
            return state, metrics, budget

        now_str = datetime.now(timezone.utc).isoformat()
        state = ExecutionState(
            workflow_id=workflow_id,
            repository_id=repository_id,
            current_step_id=steps[0].get("step_id") if steps else None,
            current_tier_index=0,
            status="queued",
            start_time=now_str,
            last_updated_at=now_str,
        )

        metrics = ExecutionMetrics(
            total_duration_sec=0,
            remaining_duration_sec_eta=sum(s.get("estimated_duration", 15) for s in steps),
            total_steps=len(steps),
            completed_steps=0,
            failed_steps=0,
            retry_count=0,
            active_provider=provider_selector.select_best_provider("Repository Agent"),
        )

        budget = ExecutionBudget(
            max_tokens=1000000,
            max_cost_usd=5.0,
            used_tokens=0,
            used_cost_usd=0.0,
            remaining_tokens=1000000,
            remaining_cost=5.0,
        )

        # Phase 8.9 — Integrate priority level and execution recommendation from Decision Engine
        try:
            from app.services.decision.decision_engine import decision_engine
            d_summary = decision_engine.get_summary(repository_id)
            if d_summary:
                if d_summary.execution_recommendation == "SKIP_WORKFLOW":
                    state.status = "failed"
                elif d_summary.execution_recommendation == "REQUIRE_APPROVAL":
                    state.status = "paused"
        except Exception as exc:
            logger.warning(f"[ExecutionManager] Failed to apply Decision Engine recommendations: {exc}")

        checkpoint_storage.save_state(workflow_id, state, metrics, budget)
        return state, metrics, budget


execution_manager = ExecutionManager()
