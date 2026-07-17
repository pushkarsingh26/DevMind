"""Workflow Memory Management."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from app.services.memory.memory_models import WorkflowMemory


def build_workflow_memory(
    workflow_id: str,
    goal: str,
    intent: str,
    execution_plan: Dict[str, Any],
    execution_metrics: Dict[str, Any],
    collaboration_summary: Dict[str, Any],
    findings: List[Dict[str, Any]],
    duration: float,
    provider_usage: List[str],
    success: bool,
) -> WorkflowMemory:
    """Factory to construct a WorkflowMemory record with current timestamp."""
    return WorkflowMemory(
        workflow_id=workflow_id,
        goal=goal,
        intent=intent,
        execution_plan=execution_plan,
        execution_metrics=execution_metrics,
        collaboration_summary=collaboration_summary,
        findings=findings,
        duration=duration,
        provider_usage=provider_usage,
        success=success,
        completed_at=datetime.now(timezone.utc).isoformat(),
    )
