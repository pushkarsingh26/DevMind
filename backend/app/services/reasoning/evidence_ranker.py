"""Evidence Ranker — weighted, deterministic multi-source ranking.

Five scoring factors with fixed weights sum to 1.0.
Output is sorted by score DESC, then evidence_id ASC to break ties.
No randomness. Same inputs always produce identical output.
"""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List

from app.core.logger import logger
from app.services.reasoning.reasoning_models import (
    EvidenceItem,
    EvidenceRanking,
    ReasoningContext,
    DependencyReasoning,
)

# Factor weights — must sum to 1.0
_WEIGHTS = {
    "analysis_severity":    0.25,
    "graph_connectivity":   0.20,
    "collab_confidence":    0.25,
    "historical_confidence":0.20,
    "hotspot_frequency":    0.10,
}

_SEVERITY_SCORES = {
    "critical": 1.0,
    "high": 0.8,
    "medium": 0.5,
    "low": 0.2,
    "info": 0.1,
}


def _sha256_id(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _normalize(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return min(1.0, value / max_value)


class EvidenceRanker:

    def rank(
        self,
        context: ReasoningContext,
        dependency_reasoning: DependencyReasoning,
    ) -> EvidenceRanking:
        logger.debug(f"[EvidenceRanker] Ranking evidence for {context.repository_id}")

        # --- Collect raw inputs ---
        memory = context.memory_summary
        hotspot_history: Dict[str, int] = memory.get("hotspot_history", {})
        max_hotspot = max(hotspot_history.values(), default=1) or 1

        # Get graph in-degrees for connectivity factor
        in_degree_map: Dict[str, int] = {}
        try:
            from app.services.knowledge_graph.graph_manager import graph_manager
            graph = graph_manager.get_graph(context.repository_id)
            if graph and graph.edges:
                for edge in graph.edges:
                    target = edge.target if hasattr(edge, "target") else edge.get("target", "")
                    if target:
                        in_degree_map[target] = in_degree_map.get(target, 0) + 1
        except Exception:
            pass
        max_in_degree = max(in_degree_map.values(), default=1) or 1

        # Get analysis findings
        analysis_findings: List[Dict[str, Any]] = []
        try:
            from app.services.repository_analysis.analysis_storage import analysis_storage
            intel_path = context.analysis_summary.get("_intel_path", "")
            if intel_path:
                summary = analysis_storage.load_summary(intel_path) or {}
                analysis_findings = summary.get("findings", [])
        except Exception:
            pass

        # Get memory pattern confidence map: file → max pattern confidence
        pattern_conf_map: Dict[str, float] = {}
        try:
            from app.services.memory import memory_storage
            mem_data = memory_storage.load(context.repository_id)
            if mem_data:
                _, patterns, _, _, _ = mem_data
                for pat in patterns:
                    parts = pat.key_signature.split(":")
                    f = parts[1] if len(parts) > 1 else pat.key_signature
                    if f:
                        pattern_conf_map[f] = max(
                            pattern_conf_map.get(f, 0.0), pat.confidence
                        )
        except Exception:
            pass

        # --- Build evidence items ---
        items: List[EvidenceItem] = []
        seen_ids = set()

        # Source 1: Dependency-critical files
        for fname in dependency_reasoning.critical_files:
            eid = _sha256_id(f"dep:{fname}")
            if eid in seen_ids:
                continue
            seen_ids.add(eid)

            node_id = fname  # approximate — name matches
            factors = {
                "analysis_severity": 0.0,
                "graph_connectivity": _normalize(in_degree_map.get(node_id, 0), max_in_degree),
                "collab_confidence": 0.5,
                "historical_confidence": pattern_conf_map.get(fname, 0.5),
                "hotspot_frequency": _normalize(hotspot_history.get(fname, 0), max_hotspot),
            }
            score = sum(_WEIGHTS[k] * v for k, v in factors.items())
            items.append(EvidenceItem(
                evidence_id=eid,
                source="dependency_reasoning",
                title=fname,
                score=round(score, 4),
                confidence=round(factors["graph_connectivity"], 4),
                factors=factors,
            ))

        # Source 2: Analysis findings
        for finding in analysis_findings:
            title = finding.get("title", finding.get("text", ""))[:120]
            fpath = finding.get("file_path", "")
            severity = finding.get("severity", "medium")
            confidence = float(finding.get("confidence", 0.7))
            eid = _sha256_id(f"analysis:{title}:{fpath}")
            if eid in seen_ids:
                continue
            seen_ids.add(eid)

            factors = {
                "analysis_severity": _SEVERITY_SCORES.get(severity, 0.5),
                "graph_connectivity": _normalize(in_degree_map.get(fpath, 0), max_in_degree),
                "collab_confidence": confidence,
                "historical_confidence": pattern_conf_map.get(fpath, 0.5),
                "hotspot_frequency": _normalize(hotspot_history.get(fpath, 0), max_hotspot),
            }
            score = sum(_WEIGHTS[k] * v for k, v in factors.items())
            items.append(EvidenceItem(
                evidence_id=eid,
                source="repository_analysis",
                title=title,
                score=round(score, 4),
                confidence=round(confidence, 4),
                factors=factors,
            ))

        # Source 3: Memory hotspots
        for fname, freq in sorted(hotspot_history.items()):
            eid = _sha256_id(f"hotspot:{fname}")
            if eid in seen_ids:
                continue
            seen_ids.add(eid)

            factors = {
                "analysis_severity": 0.0,
                "graph_connectivity": _normalize(in_degree_map.get(fname, 0), max_in_degree),
                "collab_confidence": 0.5,
                "historical_confidence": pattern_conf_map.get(fname, 0.5),
                "hotspot_frequency": _normalize(freq, max_hotspot),
            }
            score = sum(_WEIGHTS[k] * v for k, v in factors.items())
            items.append(EvidenceItem(
                evidence_id=eid,
                source="memory_hotspot",
                title=fname,
                score=round(score, 4),
                confidence=round(factors["hotspot_frequency"], 4),
                factors=factors,
            ))

        # Sort: score DESC, evidence_id ASC for ties (deterministic)
        items.sort(key=lambda x: (-x.score, x.evidence_id))

        top_confidence = items[0].confidence if items else 0.0

        return EvidenceRanking(
            ranked_items=items,
            total_sources=len(set(i.source for i in items)),
            top_confidence=round(top_confidence, 4),
        )


evidence_ranker = EvidenceRanker()
