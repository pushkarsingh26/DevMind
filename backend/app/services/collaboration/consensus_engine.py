"""Lazy consensus generation from validated findings — Phase 8.6."""

from __future__ import annotations

import time
from collections import Counter
from datetime import datetime, timezone
from typing import List

from app.services.collaboration.collaboration_models import (
    AgentReview,
    ConsensusResult,
    EvidenceRecord,
    SharedFinding,
    SharedWorkspace,
    compute_workspace_hash,
    make_sha256_id,
)
from app.services.collaboration.versions import CONSENSUS_VERSION


class ConsensusEngine:
    """Generates deterministic ConsensusResult from validated findings."""

    def should_regenerate(self, workspace: SharedWorkspace) -> bool:
        if workspace.is_dirty:
            return True
        validated_ids = [
            f.finding_id for f in workspace.findings if f.status == "validated"
        ]
        new_hash = compute_workspace_hash(validated_ids)
        return new_hash != workspace.workspace_hash

    def calculate_agreement_score(
        self,
        findings: List[SharedFinding],
        reviews: List[AgentReview],
    ) -> float:
        if not findings:
            return 0.0
        review_counts: dict[str, int] = {}
        for r in reviews:
            review_counts[r.finding_id] = review_counts.get(r.finding_id, 0) + 1
        validated = [f for f in findings if f.status == "validated"]
        if not validated:
            return 0.0
        multi_reviewed = sum(1 for f in validated if review_counts.get(f.finding_id, 0) >= 2)
        return multi_reviewed / len(validated)

    def generate_consensus(self, workspace: SharedWorkspace) -> ConsensusResult:
        start = time.time()

        validated = [f for f in workspace.findings if f.status == "validated"]
        validated_ids = sorted(f.finding_id for f in validated)
        workspace_hash = compute_workspace_hash(validated_ids)

        validated_reviews = [
            r for r in workspace.reviews
            if r.finding_id in validated_ids and r.decision == "approved"
        ]
        validated_evidence = [
            e for e in workspace.evidence if e.finding_id in validated_ids
        ]

        source_conf = (
            sum(f.confidence for f in validated) / len(validated) if validated else 0.0
        )
        review_conf = (
            sum(r.confidence for r in validated_reviews) / len(validated_reviews)
            if validated_reviews else 0.0
        )
        evidence_conf = (
            sum(e.quality_score for e in validated_evidence) / len(validated_evidence)
            if validated_evidence else 0.0
        )
        agreement = self.calculate_agreement_score(workspace.findings, workspace.reviews)

        overall = min(
            1.0,
            max(0.0, 0.40 * source_conf + 0.30 * review_conf + 0.20 * evidence_conf + 0.10 * agreement),
        )

        severities = [f.severity.lower() for f in validated]
        recommendation = Counter(severities).most_common(1)[0][0] if severities else "medium"

        supporting = sorted({f.agent_name for f in validated})
        conflicting = sorted({
            f.agent_name for f in workspace.findings
            if f.status == "rejected"
        })

        consensus_id = make_sha256_id(
            f"{workspace.workflow_id}:{':'.join(validated_ids)}"
        )
        duration_ms = int((time.time() - start) * 1000)

        return ConsensusResult(
            consensus_id=consensus_id,
            supporting_agents=supporting,
            conflicting_agents=conflicting,
            validated_findings=validated_ids,
            overall_confidence=overall,
            evidence_count=len(validated_evidence),
            recommendation=recommendation,
            generated_at=datetime.now(timezone.utc).isoformat(),
            consensus_version=CONSENSUS_VERSION,
            generated_from_workspace_hash=workspace_hash,
            generated_duration_ms=max(1, duration_ms),
            validated_findings_count=len(validated),
        )


consensus_engine = ConsensusEngine()
