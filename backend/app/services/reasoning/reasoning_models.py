"""Reasoning Engine data models.

All dataclasses implement to_dict() / from_dict() for JSON persistence.
All list fields are SORTED in to_dict() before serialization to guarantee
deterministic output regardless of insertion or iteration order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# EvidenceItem
# ---------------------------------------------------------------------------

@dataclass
class EvidenceItem:
    """A single ranked evidence record."""

    evidence_id: str
    source: str
    title: str
    score: float = 0.0
    confidence: float = 0.8
    factors: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source": self.source,
            "title": self.title,
            "score": round(self.score, 4),
            "confidence": round(self.confidence, 4),
            "factors": {k: round(v, 4) for k, v in sorted(self.factors.items())},
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EvidenceItem":
        return cls(
            evidence_id=d.get("evidence_id", ""),
            source=d.get("source", ""),
            title=d.get("title", ""),
            score=d.get("score", 0.0),
            confidence=d.get("confidence", 0.8),
            factors=d.get("factors", {}),
        )


# ---------------------------------------------------------------------------
# ReasoningChain
# ---------------------------------------------------------------------------

@dataclass
class ReasoningChain:
    """A single dependency or reasoning chain traversal result."""

    chain_id: str
    source: str
    steps: List[str] = field(default_factory=list)
    depth: int = 0
    confidence: float = 1.0
    reasoning_type: str = "dependency"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "source": self.source,
            "steps": sorted(self.steps),          # deterministic
            "depth": self.depth,
            "confidence": round(self.confidence, 4),
            "reasoning_type": self.reasoning_type,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ReasoningChain":
        return cls(
            chain_id=d.get("chain_id", ""),
            source=d.get("source", ""),
            steps=d.get("steps", []),
            depth=d.get("depth", 0),
            confidence=d.get("confidence", 1.0),
            reasoning_type=d.get("reasoning_type", "dependency"),
        )


# ---------------------------------------------------------------------------
# DependencyReasoning
# ---------------------------------------------------------------------------

@dataclass
class DependencyReasoning:
    """Results of dependency graph traversal."""

    critical_files: List[str] = field(default_factory=list)
    dependency_chains: List[ReasoningChain] = field(default_factory=list)
    affected_symbols: List[str] = field(default_factory=list)
    architecture_influence: Dict[str, int] = field(default_factory=dict)
    transitive_impact: List[str] = field(default_factory=list)
    repository_boundaries: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "critical_files": sorted(self.critical_files),
            "dependency_chains": sorted(
                [c.to_dict() for c in self.dependency_chains],
                key=lambda x: x["chain_id"],
            ),
            "affected_symbols": sorted(self.affected_symbols),
            "architecture_influence": {
                k: v for k, v in sorted(self.architecture_influence.items())
            },
            "transitive_impact": sorted(self.transitive_impact),
            "repository_boundaries": sorted(self.repository_boundaries),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "DependencyReasoning":
        return cls(
            critical_files=d.get("critical_files", []),
            dependency_chains=[
                ReasoningChain.from_dict(c) for c in d.get("dependency_chains", [])
            ],
            affected_symbols=d.get("affected_symbols", []),
            architecture_influence=d.get("architecture_influence", {}),
            transitive_impact=d.get("transitive_impact", []),
            repository_boundaries=d.get("repository_boundaries", []),
        )


# ---------------------------------------------------------------------------
# ImpactReasoning
# ---------------------------------------------------------------------------

@dataclass
class ImpactReasoning:
    """Deterministic impact analysis results."""

    direct_impact: List[str] = field(default_factory=list)
    indirect_impact: List[str] = field(default_factory=list)
    repository_wide_impact: bool = False
    breaking_change_probability: float = 0.0
    refactor_impact_score: float = 0.0
    test_impact: List[str] = field(default_factory=list)
    documentation_impact: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "direct_impact": sorted(self.direct_impact),
            "indirect_impact": sorted(self.indirect_impact),
            "repository_wide_impact": self.repository_wide_impact,
            "breaking_change_probability": round(self.breaking_change_probability, 4),
            "refactor_impact_score": round(self.refactor_impact_score, 4),
            "test_impact": sorted(self.test_impact),
            "documentation_impact": sorted(self.documentation_impact),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ImpactReasoning":
        return cls(
            direct_impact=d.get("direct_impact", []),
            indirect_impact=d.get("indirect_impact", []),
            repository_wide_impact=d.get("repository_wide_impact", False),
            breaking_change_probability=d.get("breaking_change_probability", 0.0),
            refactor_impact_score=d.get("refactor_impact_score", 0.0),
            test_impact=d.get("test_impact", []),
            documentation_impact=d.get("documentation_impact", []),
        )


# ---------------------------------------------------------------------------
# EvidenceRanking
# ---------------------------------------------------------------------------

@dataclass
class EvidenceRanking:
    """Ranked evidence list from all sources."""

    ranked_items: List[EvidenceItem] = field(default_factory=list)
    total_sources: int = 0
    top_confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        # Sort by score DESC, then evidence_id ASC for deterministic tie-breaking
        sorted_items = sorted(
            self.ranked_items,
            key=lambda x: (-x.score, x.evidence_id),
        )
        return {
            "ranked_items": [item.to_dict() for item in sorted_items],
            "total_sources": self.total_sources,
            "top_confidence": round(self.top_confidence, 4),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "EvidenceRanking":
        return cls(
            ranked_items=[EvidenceItem.from_dict(i) for i in d.get("ranked_items", [])],
            total_sources=d.get("total_sources", 0),
            top_confidence=d.get("top_confidence", 0.0),
        )


# ---------------------------------------------------------------------------
# HistoricalReasoning
# ---------------------------------------------------------------------------

@dataclass
class HistoricalReasoning:
    """Historical workflow analysis from Memory Engine."""

    similar_workflows: List[str] = field(default_factory=list)
    historical_failures: List[str] = field(default_factory=list)
    historical_fixes: List[str] = field(default_factory=list)
    common_risks: List[str] = field(default_factory=list)
    success_probability: float = 0.8
    provider_history: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "similar_workflows": sorted(self.similar_workflows),
            "historical_failures": sorted(self.historical_failures),
            "historical_fixes": sorted(self.historical_fixes),
            "common_risks": sorted(self.common_risks),
            "success_probability": round(self.success_probability, 4),
            "provider_history": {
                k: round(v, 4) for k, v in sorted(self.provider_history.items())
            },
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "HistoricalReasoning":
        return cls(
            similar_workflows=d.get("similar_workflows", []),
            historical_failures=d.get("historical_failures", []),
            historical_fixes=d.get("historical_fixes", []),
            common_risks=d.get("common_risks", []),
            success_probability=d.get("success_probability", 0.8),
            provider_history=d.get("provider_history", {}),
        )


# ---------------------------------------------------------------------------
# ReasoningContext
# ---------------------------------------------------------------------------

@dataclass
class ReasoningContext:
    """Flat context summary assembled from all subsystems."""

    repository_id: str
    repository_hash: str
    intelligence_summary: Dict[str, Any] = field(default_factory=dict)
    graph_summary: Dict[str, Any] = field(default_factory=dict)
    analysis_summary: Dict[str, Any] = field(default_factory=dict)
    memory_summary: Dict[str, Any] = field(default_factory=dict)
    collaboration_summary: Dict[str, Any] = field(default_factory=dict)
    built_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "repository_hash": self.repository_hash,
            "intelligence_summary": self.intelligence_summary,
            "graph_summary": self.graph_summary,
            "analysis_summary": self.analysis_summary,
            "memory_summary": self.memory_summary,
            "collaboration_summary": self.collaboration_summary,
            "built_at": self.built_at,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ReasoningContext":
        return cls(
            repository_id=d.get("repository_id", ""),
            repository_hash=d.get("repository_hash", ""),
            intelligence_summary=d.get("intelligence_summary", {}),
            graph_summary=d.get("graph_summary", {}),
            analysis_summary=d.get("analysis_summary", {}),
            memory_summary=d.get("memory_summary", {}),
            collaboration_summary=d.get("collaboration_summary", {}),
            built_at=d.get("built_at", ""),
        )


# ---------------------------------------------------------------------------
# ReasoningMetrics
# ---------------------------------------------------------------------------

@dataclass
class ReasoningMetrics:
    """Per-stage timing telemetry for one reasoning build."""

    reasoning_build_ms: float = 0.0
    context_build_ms: float = 0.0
    dependency_reasoning_ms: float = 0.0
    impact_reasoning_ms: float = 0.0
    evidence_ranking_ms: float = 0.0
    historical_reasoning_ms: float = 0.0
    serialization_ms: float = 0.0
    cache_hit: bool = False
    cache_miss: bool = True
    reasoning_score: float = 0.0
    reasoning_confidence: float = 0.0
    critical_path_count: int = 0
    affected_files: int = 0
    affected_symbols: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reasoning_build_ms": round(self.reasoning_build_ms, 2),
            "context_build_ms": round(self.context_build_ms, 2),
            "dependency_reasoning_ms": round(self.dependency_reasoning_ms, 2),
            "impact_reasoning_ms": round(self.impact_reasoning_ms, 2),
            "evidence_ranking_ms": round(self.evidence_ranking_ms, 2),
            "historical_reasoning_ms": round(self.historical_reasoning_ms, 2),
            "serialization_ms": round(self.serialization_ms, 2),
            "cache_hit": self.cache_hit,
            "cache_miss": self.cache_miss,
            "reasoning_score": round(self.reasoning_score, 4),
            "reasoning_confidence": round(self.reasoning_confidence, 4),
            "critical_path_count": self.critical_path_count,
            "affected_files": self.affected_files,
            "affected_symbols": self.affected_symbols,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ReasoningMetrics":
        return cls(
            reasoning_build_ms=d.get("reasoning_build_ms", 0.0),
            context_build_ms=d.get("context_build_ms", 0.0),
            dependency_reasoning_ms=d.get("dependency_reasoning_ms", 0.0),
            impact_reasoning_ms=d.get("impact_reasoning_ms", 0.0),
            evidence_ranking_ms=d.get("evidence_ranking_ms", 0.0),
            historical_reasoning_ms=d.get("historical_reasoning_ms", 0.0),
            serialization_ms=d.get("serialization_ms", 0.0),
            cache_hit=d.get("cache_hit", False),
            cache_miss=d.get("cache_miss", True),
            reasoning_score=d.get("reasoning_score", 0.0),
            reasoning_confidence=d.get("reasoning_confidence", 0.0),
            critical_path_count=d.get("critical_path_count", 0),
            affected_files=d.get("affected_files", 0),
            affected_symbols=d.get("affected_symbols", 0),
        )


# ---------------------------------------------------------------------------
# ReasoningSummary
# ---------------------------------------------------------------------------

@dataclass
class ReasoningSummary:
    """Unified output of the Reasoning Engine pipeline."""

    repository_id: str
    repository_hash: str
    reasoning_score: float = 0.0
    confidence: float = 0.0
    critical_paths: List[str] = field(default_factory=list)
    affected_modules: List[str] = field(default_factory=list)
    risk_indicators: List[str] = field(default_factory=list)
    reasoning_context: Optional[ReasoningContext] = None
    dependency_reasoning: Optional[DependencyReasoning] = None
    impact_reasoning: Optional[ImpactReasoning] = None
    evidence_ranking: Optional[EvidenceRanking] = None
    historical_reasoning: Optional[HistoricalReasoning] = None
    generated_at: str = ""
    build_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "repository_id": self.repository_id,
            "repository_hash": self.repository_hash,
            "reasoning_score": round(self.reasoning_score, 4),
            "confidence": round(self.confidence, 4),
            "critical_paths": sorted(self.critical_paths),
            "affected_modules": sorted(self.affected_modules),
            "risk_indicators": sorted(self.risk_indicators),
            "reasoning_context": self.reasoning_context.to_dict() if self.reasoning_context else {},
            "dependency_reasoning": self.dependency_reasoning.to_dict() if self.dependency_reasoning else {},
            "impact_reasoning": self.impact_reasoning.to_dict() if self.impact_reasoning else {},
            "evidence_ranking": self.evidence_ranking.to_dict() if self.evidence_ranking else {},
            "historical_reasoning": self.historical_reasoning.to_dict() if self.historical_reasoning else {},
            "generated_at": self.generated_at,
            "build_time_ms": round(self.build_time_ms, 2),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ReasoningSummary":
        dep = d.get("dependency_reasoning")
        imp = d.get("impact_reasoning")
        evi = d.get("evidence_ranking")
        his = d.get("historical_reasoning")
        ctx = d.get("reasoning_context")
        return cls(
            repository_id=d.get("repository_id", ""),
            repository_hash=d.get("repository_hash", ""),
            reasoning_score=d.get("reasoning_score", 0.0),
            confidence=d.get("confidence", 0.0),
            critical_paths=d.get("critical_paths", []),
            affected_modules=d.get("affected_modules", []),
            risk_indicators=d.get("risk_indicators", []),
            reasoning_context=ReasoningContext.from_dict(ctx) if ctx else None,
            dependency_reasoning=DependencyReasoning.from_dict(dep) if dep else None,
            impact_reasoning=ImpactReasoning.from_dict(imp) if imp else None,
            evidence_ranking=EvidenceRanking.from_dict(evi) if evi else None,
            historical_reasoning=HistoricalReasoning.from_dict(his) if his else None,
            generated_at=d.get("generated_at", ""),
            build_time_ms=d.get("build_time_ms", 0.0),
        )
