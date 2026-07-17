"""Planning Engine data models.

Defined as plain dataclasses for framework independence and easy serialization.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class StepDependency:
    """Represents a dependency between two execution steps."""

    source_step_id: str
    target_step_id: str
    dependency_type: str = "sequential"  # sequential | optional

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> StepDependency:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ExecutionStep:
    """Represents a single step in the execution plan."""

    step_id: str
    agent: str  # e.g., Repository Agent, Security Agent
    title: str
    description: str
    execution_group: str  # repository | analysis | refactoring | summary
    input_files: List[str] = field(default_factory=list)
    estimated_duration: int = 15  # seconds
    estimated_token_cost: int = 1000

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ExecutionStep:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class PlanningMetrics:
    """Orchestration metrics computed during plan generation."""

    estimated_duration: int = 0
    estimated_tokens: int = 0
    estimated_cost: float = 0.0
    parallel_groups: List[str] = field(default_factory=list)
    critical_path: List[str] = field(default_factory=list)
    dependency_depth: int = 0
    affected_files: int = 0
    affected_modules: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> PlanningMetrics:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ExecutionPlan:
    """Structured execution plan for satisfying a user goal."""

    plan_id: str
    plan_version: str
    repository_hash: str
    generated_at: str  # ISO timestamp
    planner_version: str
    plan_schema_version: str
    ruleset_version: str
    goal_text: str = ""
    steps: List[ExecutionStep] = field(default_factory=list)
    dependencies: List[StepDependency] = field(default_factory=list)
    intent: str = "General Analysis"
    priority_score: int = 5
    risk_level: str = "low"  # low | medium | high
    complexity_level: str = "low"  # low | medium | high
    rationale: str = ""
    metrics: PlanningMetrics = field(default_factory=PlanningMetrics)
    score: Dict[str, Any] = field(default_factory=dict)  # confidence, completeness, success_prob
    telemetry: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["steps"] = [s.to_dict() for s in self.steps]
        d["dependencies"] = [dep.to_dict() for dep in self.dependencies]
        d["metrics"] = self.metrics.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ExecutionPlan:
        steps = [ExecutionStep.from_dict(s) for s in d.get("steps", [])]
        deps = [StepDependency.from_dict(dep) for dep in d.get("dependencies", [])]
        metrics = PlanningMetrics.from_dict(d.get("metrics", {}))
        
        filtered = {k: v for k, v in d.items() if k in cls.__dataclass_fields__ and k not in ("steps", "dependencies", "metrics")}
        return cls(steps=steps, dependencies=deps, metrics=metrics, **filtered)


@dataclass
class PlanningContext:
    """Rich context package passed to the Planning Engine."""

    repository_id: str
    repository_hash: str
    goal: str
    workflow_type: str
    repository_metadata: Dict[str, Any] = field(default_factory=dict)
    intelligence_summary: Dict[str, Any] = field(default_factory=dict)
    knowledge_graph_stats: Dict[str, Any] = field(default_factory=dict)
    repository_analysis: Dict[str, Any] = field(default_factory=dict)
    repository_memory: Dict[str, Any] = field(default_factory=dict)
