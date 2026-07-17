"""Execution Engine data models.

Defined as plain dataclasses for framework independence and easy serialization.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ExecutionCheckpoint:
    """Represents a saved state at the completion of a workflow execution step."""

    step_id: str
    status: str  # pending | running | completed | failed
    completed_at: str  # ISO timestamp
    telemetry: Dict[str, Any] = field(default_factory=dict)  # tokens, cost, duration_sec
    outputs: Dict[str, Any] = field(default_factory=dict)  # context updates, variables

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ExecutionCheckpoint:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ExecutionState:
    """Represents the execution state of a running workflow."""

    workflow_id: str
    repository_id: str
    current_step_id: Optional[str]
    current_tier_index: int
    status: str  # queued | running | paused | completed | failed
    start_time: str  # ISO timestamp
    last_updated_at: str  # ISO timestamp
    last_completed_step: Optional[str] = None
    failed_step: Optional[str] = None
    resume_from_step: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ExecutionState:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ExecutionBudget:
    """Tracks token and cost limits vs usage for execution runs."""

    max_tokens: int = 1000000
    max_cost_usd: float = 5.0
    used_tokens: int = 0
    used_cost_usd: float = 0.0
    remaining_tokens: int = 1000000
    remaining_cost: float = 5.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ExecutionBudget:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ExecutionMetrics:
    """Live metrics gathered during execution."""

    total_duration_sec: int = 0
    remaining_duration_sec_eta: int = 0
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    retry_count: int = 0
    active_provider: str = "google"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ExecutionMetrics:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ExecutionEvent:
    """Tracks step lifecycle events for rendering timelines and replays."""

    timestamp: str  # ISO timestamp
    step_id: str
    event: str  # started | completed | failed | retry | failover
    provider: str
    duration_ms: int
    retry: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ExecutionEvent:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
