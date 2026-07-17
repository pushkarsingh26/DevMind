"""Memory engine model definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RepositoryMemory:
    """Long-term structural knowledge about a repository."""

    repository_id: str
    repository_hash: str
    recurring_files: List[str] = field(default_factory=list)
    frequently_modified_modules: List[str] = field(default_factory=list)
    hotspot_history: Dict[str, int] = field(default_factory=dict)
    dependency_history: List[str] = field(default_factory=list)
    architecture_history: List[str] = field(default_factory=list)
    language_history: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "repository_hash": self.repository_hash,
            "recurring_files": self.recurring_files,
            "frequently_modified_modules": self.frequently_modified_modules,
            "hotspot_history": self.hotspot_history,
            "dependency_history": self.dependency_history,
            "architecture_history": self.architecture_history,
            "language_history": self.language_history,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RepositoryMemory:
        return cls(
            repository_id=data.get("repository_id", ""),
            repository_hash=data.get("repository_hash", ""),
            recurring_files=data.get("recurring_files", []),
            frequently_modified_modules=data.get("frequently_modified_modules", []),
            hotspot_history=data.get("hotspot_history", {}),
            dependency_history=data.get("dependency_history", []),
            architecture_history=data.get("architecture_history", []),
            language_history=data.get("language_history", {}),
        )


@dataclass
class WorkflowMemory:
    """Execution details of a specific workflow."""

    workflow_id: str
    goal: str
    intent: str
    execution_plan: Dict[str, Any] = field(default_factory=dict)
    execution_metrics: Dict[str, Any] = field(default_factory=dict)
    collaboration_summary: Dict[str, Any] = field(default_factory=dict)
    findings: List[Dict[str, Any]] = field(default_factory=list)
    duration: float = 0.0
    provider_usage: List[str] = field(default_factory=list)
    success: bool = True
    completed_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "goal": self.goal,
            "intent": self.intent,
            "execution_plan": self.execution_plan,
            "execution_metrics": self.execution_metrics,
            "collaboration_summary": self.collaboration_summary,
            "findings": self.findings,
            "duration": self.duration,
            "provider_usage": self.provider_usage,
            "success": self.success,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkflowMemory:
        return cls(
            workflow_id=data.get("workflow_id", ""),
            goal=data.get("goal", ""),
            intent=data.get("intent", ""),
            execution_plan=data.get("execution_plan", {}),
            execution_metrics=data.get("execution_metrics", {}),
            collaboration_summary=data.get("collaboration_summary", {}),
            findings=data.get("findings", []),
            duration=data.get("duration", 0.0),
            provider_usage=data.get("provider_usage", []),
            success=data.get("success", True),
            completed_at=data.get("completed_at", ""),
        )


@dataclass
class PatternRecord:
    """Recurring issue pattern detected across execution runs."""

    pattern_id: str
    category: str
    key_signature: str
    description: str
    frequency: int = 1
    severity: str = "medium"
    confidence: float = 0.8

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "category": self.category,
            "key_signature": self.key_signature,
            "description": self.description,
            "frequency": self.frequency,
            "severity": self.severity,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PatternRecord:
        return cls(
            pattern_id=data.get("pattern_id", ""),
            category=data.get("category", ""),
            key_signature=data.get("key_signature", ""),
            description=data.get("description", ""),
            frequency=data.get("frequency", 1),
            severity=data.get("severity", "medium"),
            confidence=data.get("confidence", 0.8),
        )


@dataclass
class Recommendation:
    """Historical recommendation computed deterministically from memory."""

    recommendation_id: str
    type: str
    title: str
    description: str
    confidence: float = 0.8
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "details": self.details,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Recommendation:
        return cls(
            recommendation_id=data.get("recommendation_id", ""),
            type=data.get("type", ""),
            title=data.get("title", ""),
            description=data.get("description", ""),
            confidence=data.get("confidence", 0.8),
            details=data.get("details", {}),
        )


@dataclass
class LearningMetrics:
    """Aggregated workflow execution statistics and trends."""

    workflow_success_rate: float = 1.0
    average_execution_time: float = 0.0
    average_retries: float = 0.0
    provider_reliability: Dict[str, float] = field(default_factory=dict)
    recurring_findings_count: int = 0
    repository_health_trend: List[float] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_success_rate": self.workflow_success_rate,
            "average_execution_time": self.average_execution_time,
            "average_retries": self.average_retries,
            "provider_reliability": self.provider_reliability,
            "recurring_findings_count": self.recurring_findings_count,
            "repository_health_trend": self.repository_health_trend,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LearningMetrics:
        return cls(
            workflow_success_rate=data.get("workflow_success_rate", 1.0),
            average_execution_time=data.get("average_execution_time", 0.0),
            average_retries=data.get("average_retries", 0.0),
            provider_reliability=data.get("provider_reliability", {}),
            recurring_findings_count=data.get("recurring_findings_count", 0),
            repository_health_trend=data.get("repository_health_trend", []),
        )


@dataclass
class MemoryStatistics:
    """High-level summary of cached memory state."""

    repository_id: str
    workflow_count: int
    pattern_count: int
    recommendation_count: int
    last_updated: str
