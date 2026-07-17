"""Multi-Agent Collaboration data models — Phase 8.6."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


def make_sha256_id(content: str) -> str:
    """Deterministic ID from canonical content (16-char hex prefix)."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def compute_workspace_hash(validated_finding_ids: List[str]) -> str:
    """SHA-256 of sorted validated finding IDs."""
    canonical = ":".join(sorted(validated_finding_ids))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass
class SharedFinding:
    finding_id: str
    step_id: str
    agent_name: str
    category: str
    severity: str  # critical/high/medium/low
    title: str
    description: str
    file_path: str
    symbol: str
    line_range: str
    confidence: float
    status: str = "pending"  # pending/validated/rejected

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> SharedFinding:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class EvidenceRecord:
    evidence_id: str
    finding_id: str
    file_path: str
    symbol: str
    graph_node_id: str
    chunk_id: str
    workflow_step_id: str
    source_agent: str
    quality_score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> EvidenceRecord:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class AgentContribution:
    agent_name: str
    step_id: str
    findings_count: int
    evidence_count: int
    published_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AgentContribution:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class AgentEvent:
    timestamp: str
    agent: str
    step_id: str
    event: str  # published/reviewed/conflict_detected/conflict_resolved/consensus_generated
    finding_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AgentEvent:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class AgentReview:
    review_id: str
    finding_id: str
    reviewer_agent: str
    reviewer_step_id: str
    decision: str  # approved/rejected/needs_evidence
    confidence: float
    reason: str
    reviewed_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> AgentReview:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ConflictRecord:
    conflict_id: str
    finding_id_a: str
    finding_id_b: str
    conflict_type: str  # duplicate/contradiction/severity_mismatch/recommendation_mismatch
    resolution: str  # pending/resolved
    winning_finding_id: str
    resolution_reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ConflictRecord:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class ConsensusResult:
    consensus_id: str
    supporting_agents: List[str]
    conflicting_agents: List[str]
    validated_findings: List[str]
    overall_confidence: float
    evidence_count: int
    recommendation: str
    generated_at: str
    consensus_version: str
    generated_from_workspace_hash: str
    generated_duration_ms: int
    validated_findings_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ConsensusResult:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class SharedWorkspace:
    workflow_id: str
    repository_id: str
    findings: List[SharedFinding] = field(default_factory=list)
    reviews: List[AgentReview] = field(default_factory=list)
    conflicts: List[ConflictRecord] = field(default_factory=list)
    evidence: List[EvidenceRecord] = field(default_factory=list)
    contributions: List[AgentContribution] = field(default_factory=list)
    events: List[AgentEvent] = field(default_factory=list)
    schema_version: str = "v1"
    updated_at: str = ""
    workspace_hash: str = ""
    is_dirty: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "repository_id": self.repository_id,
            "schema_version": self.schema_version,
            "updated_at": self.updated_at,
            "workspace_hash": self.workspace_hash,
            "is_dirty": self.is_dirty,
            "findings_count": len(self.findings),
            "reviews_count": len(self.reviews),
            "conflicts_count": len(self.conflicts),
            "evidence_count": len(self.evidence),
            "contributions_count": len(self.contributions),
            "events_count": len(self.events),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> SharedWorkspace:
        return cls(
            workflow_id=d.get("workflow_id", ""),
            repository_id=d.get("repository_id", ""),
            findings=[SharedFinding.from_dict(f) for f in d.get("findings", [])],
            reviews=[AgentReview.from_dict(r) for r in d.get("reviews", [])],
            conflicts=[ConflictRecord.from_dict(c) for c in d.get("conflicts", [])],
            evidence=[EvidenceRecord.from_dict(e) for e in d.get("evidence", [])],
            contributions=[AgentContribution.from_dict(c) for c in d.get("contributions", [])],
            events=[AgentEvent.from_dict(e) for e in d.get("events", [])],
            schema_version=d.get("schema_version", "v1"),
            updated_at=d.get("updated_at", ""),
            workspace_hash=d.get("workspace_hash", ""),
            is_dirty=d.get("is_dirty", True),
        )


@dataclass
class CollaborationTelemetry:
    workspace_updates: int = 0
    findings_created: int = 0
    findings_validated: int = 0
    findings_rejected: int = 0
    duplicates_removed: int = 0
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    average_confidence: float = 0.0
    average_review_time_ms: float = 0.0
    consensus_generation_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> CollaborationTelemetry:
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
