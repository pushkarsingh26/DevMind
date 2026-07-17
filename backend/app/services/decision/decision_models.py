"""Decision Engine dataclass definitions.

Supports roundtrip JSON serialization.
All list and dict fields are sorted in to_dict() for deterministic outputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class DecisionSummary:
    """Consolidated deterministic summary of Decision Engine outcomes."""

    repository_id: str
    repository_hash: str
    decision_score: float
    priority_level: str  # low, medium, high, critical
    execution_recommendation: str  # SKIP_WORKFLOW, REORDER_STEPS, REQUIRE_APPROVAL, PROCEED
    policies_evaluated: List[str] = field(default_factory=list)
    policies_triggered: List[str] = field(default_factory=list)
    generated_at: str = ""
    build_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "repository_hash": self.repository_hash,
            "decision_score": round(self.decision_score, 4),
            "priority_level": self.priority_level,
            "execution_recommendation": self.execution_recommendation,
            "policies_evaluated": sorted(self.policies_evaluated),
            "policies_triggered": sorted(self.policies_triggered),
            "generated_at": self.generated_at,
            "build_time_ms": round(self.build_time_ms, 2),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DecisionSummary":
        return cls(
            repository_id=d.get("repository_id", ""),
            repository_hash=d.get("repository_hash", ""),
            decision_score=d.get("decision_score", 0.0),
            priority_level=d.get("priority_level", "low"),
            execution_recommendation=d.get("execution_recommendation", "PROCEED"),
            policies_evaluated=d.get("policies_evaluated", []),
            policies_triggered=d.get("policies_triggered", []),
            generated_at=d.get("generated_at", ""),
            build_time_ms=d.get("build_time_ms", 0.0),
        )


@dataclass
class DecisionHistoryRecord:
    """Historical trace of a single workflow's decision outcomes."""

    workflow_id: str
    goal: str
    intent: str
    decision_score: float
    priority_level: str
    success: bool
    completed_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "goal": self.goal,
            "intent": self.intent,
            "decision_score": round(self.decision_score, 4),
            "priority_level": self.priority_level,
            "success": self.success,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DecisionHistoryRecord":
        return cls(
            workflow_id=d.get("workflow_id", ""),
            goal=d.get("goal", ""),
            intent=d.get("intent", ""),
            decision_score=d.get("decision_score", 0.0),
            priority_level=d.get("priority_level", "low"),
            success=d.get("success", False),
            completed_at=d.get("completed_at", ""),
        )


@dataclass
class DecisionMetrics:
    """Performance execution timers for the Decision Engine pipeline."""

    decision_time_ms: float
    policy_time_ms: float
    priority_time_ms: float
    cache_hits: int
    cache_misses: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_time_ms": round(self.decision_time_ms, 2),
            "policy_time_ms": round(self.policy_time_ms, 2),
            "priority_time_ms": round(self.priority_time_ms, 2),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DecisionMetrics":
        return cls(
            decision_time_ms=d.get("decision_time_ms", 0.0),
            policy_time_ms=d.get("policy_time_ms", 0.0),
            priority_time_ms=d.get("priority_time_ms", 0.0),
            cache_hits=d.get("cache_hits", 0),
            cache_misses=d.get("cache_misses", 0),
        )


@dataclass
class DecisionTelemetry:
    """Standard system telemetry for decision evaluation."""

    decision_time_ms: float
    policy_time_ms: float
    priority_time_ms: float
    cache_hits: int
    cache_misses: int
    policies_evaluated: int
    policies_triggered: int
    workflow_skipped: bool
    workflow_reordered: bool
    decision_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_time_ms": round(self.decision_time_ms, 2),
            "policy_time_ms": round(self.policy_time_ms, 2),
            "priority_time_ms": round(self.priority_time_ms, 2),
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "policies_evaluated": self.policies_evaluated,
            "policies_triggered": self.policies_triggered,
            "workflow_skipped": self.workflow_skipped,
            "workflow_reordered": self.workflow_reordered,
            "decision_score": round(self.decision_score, 4),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DecisionTelemetry":
        return cls(
            decision_time_ms=d.get("decision_time_ms", 0.0),
            policy_time_ms=d.get("policy_time_ms", 0.0),
            priority_time_ms=d.get("priority_time_ms", 0.0),
            cache_hits=d.get("cache_hits", 0),
            cache_misses=d.get("cache_misses", 0),
            policies_evaluated=d.get("policies_evaluated", 0),
            policies_triggered=d.get("policies_triggered", 0),
            workflow_skipped=d.get("workflow_skipped", False),
            workflow_reordered=d.get("workflow_reordered", False),
            decision_score=d.get("decision_score", 0.0),
        )
