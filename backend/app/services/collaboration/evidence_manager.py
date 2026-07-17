"""Deterministic evidence generation and quality scoring — Phase 8.6."""

from __future__ import annotations

from typing import Any, Dict, List

from app.services.collaboration.collaboration_models import (
    EvidenceRecord,
    SharedFinding,
    make_sha256_id,
)
from app.services.collaboration.versions import EVIDENCE_RULESET_VERSION


class EvidenceManager:
    """Generates EvidenceRecord objects from agent outputs and context."""

    def __init__(self):
        self.ruleset_version = EVIDENCE_RULESET_VERSION

    def calculate_quality(
        self,
        evidence: EvidenceRecord,
        context_bundle: Dict[str, Any],
        analysis_data: Dict[str, Any],
        agreement_count: int = 1,
    ) -> float:
        score = 0.0
        if evidence.graph_node_id:
            score += 0.30
        impacted = analysis_data.get("impacted_files", [])
        if evidence.file_path and evidence.file_path in impacted:
            score += 0.25
        if evidence.symbol:
            score += 0.20
        if evidence.chunk_id:
            score += 0.15
        if agreement_count >= 2:
            score += 0.10
        return min(1.0, score)

    def _find_graph_node(self, symbol: str, context_bundle: Dict[str, Any]) -> str:
        symbols = context_bundle.get("symbols", [])
        if symbol and symbol in symbols:
            return make_sha256_id(f"symbol:{symbol}")
        return ""

    def _find_chunk_id(self, file_path: str, context_bundle: Dict[str, Any]) -> str:
        chunks = context_bundle.get("relevant_chunks", [])
        for idx, item in enumerate(chunks):
            chunk = item[0] if isinstance(item, (list, tuple)) else item
            path = getattr(chunk, "path", None) or (chunk.get("path") if isinstance(chunk, dict) else "")
            if path == file_path:
                return make_sha256_id(f"chunk:{file_path}:{idx}")
        return ""

    def generate_evidence(
        self,
        finding: SharedFinding,
        context_bundle: Dict[str, Any],
        analysis_data: Dict[str, Any],
        agreement_count: int = 1,
    ) -> EvidenceRecord:
        graph_node_id = self._find_graph_node(finding.symbol, context_bundle)
        chunk_id = self._find_chunk_id(finding.file_path, context_bundle)

        evidence_id = make_sha256_id(
            f"{finding.finding_id}:{finding.file_path}:{finding.symbol}:{chunk_id}"
        )
        record = EvidenceRecord(
            evidence_id=evidence_id,
            finding_id=finding.finding_id,
            file_path=finding.file_path,
            symbol=finding.symbol,
            graph_node_id=graph_node_id,
            chunk_id=chunk_id,
            workflow_step_id=finding.step_id,
            source_agent=finding.agent_name,
            quality_score=0.0,
        )
        record.quality_score = self.calculate_quality(
            record, context_bundle, analysis_data, agreement_count
        )
        return record

    def batch_generate(
        self,
        findings: List[SharedFinding],
        context_bundle: Dict[str, Any],
        analysis_data: Dict[str, Any],
    ) -> List[EvidenceRecord]:
        title_counts: Dict[str, int] = {}
        for f in findings:
            key = f"{f.title}:{f.file_path}"
            title_counts[key] = title_counts.get(key, 0) + 1

        return [
            self.generate_evidence(
                f,
                context_bundle,
                analysis_data,
                agreement_count=title_counts.get(f"{f.title}:{f.file_path}", 1),
            )
            for f in findings
        ]


evidence_manager = EvidenceManager()
