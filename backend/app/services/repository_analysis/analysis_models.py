"""Dataclass models for the Repository Analysis Engine.

These are plain Python dataclasses (no Pydantic dependency) to keep the analysis
layer independent of the web framework.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class ImpactResult:
    """Represents the estimated impact of changing a symbol or file."""

    target_id: str
    impacted_files: List[str] = field(default_factory=list)
    impacted_symbols: List[str] = field(default_factory=list)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ImpactResult:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class DependencyChain:
    """Represents a path of dependencies between two nodes."""

    source: str
    target: str
    path: List[str] = field(default_factory=list)  # list of node IDs forming the path
    relationship_types: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DependencyChain:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class CircularDependency:
    """Represents a cycle of imports/dependencies in the codebase."""

    cycle: List[str] = field(default_factory=list)  # list of module/file IDs in cycle order
    length: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> CircularDependency:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class DeadCodeReport:
    """Lists detected unused code elements."""

    unused_symbols: List[Dict[str, Any]] = field(default_factory=list)  # symbols with no incoming links
    unused_modules: List[str] = field(default_factory=list)  # un-imported modules/files
    summary_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> DeadCodeReport:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class HotspotReport:
    """Represents architectural complexity and coupling hotspots."""

    hotspots: List[Dict[str, Any]] = field(default_factory=list)  # nodes ranked by centrality
    max_coupling_degree: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> HotspotReport:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ArchitectureIssue:
    """Represents an identified structural architecture anomaly."""

    id: str
    type: str  # circular_dependency | dead_code | large_module | high_coupling
    severity: str  # high | medium | low
    message: str
    affected_files: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ArchitectureIssue:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class AnalysisSummary:
    """Aggregated structural statistics of the repository."""

    repository_id: str
    repository_hash: str
    health_score: int = 100
    total_nodes: int = 0
    total_edges: int = 0
    issues_count: int = 0
    build_time_ms: int = 0
    analysis_date: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AnalysisSummary:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
