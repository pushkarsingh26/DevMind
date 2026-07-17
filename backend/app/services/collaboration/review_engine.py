"""Deterministic finding review and validation — Phase 8.6."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.services.collaboration.collaboration_models import (
    AgentReview,
    ConflictRecord,
    SharedFinding,
    EvidenceRecord,
    make_sha256_id,
)
from app.services.collaboration.versions import REVIEW_RULESET_VERSION

CONFIDENCE_THRESHOLD = 0.6


class ReviewEngine:
    """Validates SharedFinding objects using deterministic rule checks."""

    def __init__(self, confidence_threshold: float = CONFIDENCE_THRESHOLD):
        self.confidence_threshold = confidence_threshold
        self.ruleset_version = REVIEW_RULESET_VERSION

    def _finding_has_evidence(self, finding_id: str, evidence_list: List[EvidenceRecord]) -> bool:
        return any(e.finding_id == finding_id for e in evidence_list)

    def _is_duplicate(self, finding: SharedFinding, existing: List[SharedFinding]) -> bool:
        key = make_sha256_id(f"{finding.title}:{finding.file_path}:{finding.line_range}")
        for other in existing:
            if other.finding_id == finding.finding_id:
                continue
            other_key = make_sha256_id(f"{other.title}:{other.file_path}:{other.line_range}")
            if key == other_key:
                return True
        return False

    def _has_unresolved_conflict(self, finding_id: str, conflicts: List[ConflictRecord]) -> bool:
        for c in conflicts:
            if c.resolution != "pending":
                continue
            if finding_id in (c.finding_id_a, c.finding_id_b):
                return True
        return False

    def _agreement_score(self, finding: SharedFinding, existing: List[SharedFinding]) -> float:
        matches = sum(
            1 for f in existing
            if f.finding_id != finding.finding_id
            and f.title == finding.title
            and f.file_path == finding.file_path
        )
        return min(1.0, matches / 2.0)

    def _reviewer_confidence(
        self,
        finding: SharedFinding,
        evidence_list: List[EvidenceRecord],
        existing: List[SharedFinding],
    ) -> float:
        evidence_quality = 0.0
        for e in evidence_list:
            if e.finding_id == finding.finding_id:
                evidence_quality = max(evidence_quality, e.quality_score)
        agreement = self._agreement_score(finding, existing)
        return 0.4 * finding.confidence + 0.3 * evidence_quality + 0.3 * agreement

    def review_finding(
        self,
        finding: SharedFinding,
        evidence_list: List[EvidenceRecord],
        existing_findings: List[SharedFinding],
        conflicts: List[ConflictRecord],
        reviewer_agent: str = "Review Engine",
        reviewer_step_id: str = "collaboration",
    ) -> AgentReview:
        has_evidence = self._finding_has_evidence(finding.finding_id, evidence_list)
        is_dup = self._is_duplicate(finding, existing_findings)
        unresolved = self._has_unresolved_conflict(finding.finding_id, conflicts)
        reviewer_conf = self._reviewer_confidence(finding, evidence_list, existing_findings)

        if not has_evidence:
            decision = "needs_evidence"
            reason = "Missing supporting evidence record."
        elif finding.confidence < self.confidence_threshold or unresolved or is_dup:
            decision = "rejected"
            if unresolved:
                reason = "Unresolved conflict detected."
            elif is_dup:
                reason = "Duplicate finding detected."
            else:
                reason = f"Confidence {finding.confidence:.2f} below threshold {self.confidence_threshold}."
        else:
            decision = "approved"
            reason = "All validation checks passed."

        review_id = make_sha256_id(
            f"{finding.finding_id}:{reviewer_agent}:{decision}:{reason}"
        )
        return AgentReview(
            review_id=review_id,
            finding_id=finding.finding_id,
            reviewer_agent=reviewer_agent,
            reviewer_step_id=reviewer_step_id,
            decision=decision,
            confidence=reviewer_conf,
            reason=reason,
            reviewed_at=datetime.now(timezone.utc).isoformat(),
        )

    def batch_review(
        self,
        findings: List[SharedFinding],
        evidence_list: List[EvidenceRecord],
        existing_findings: List[SharedFinding],
        conflicts: List[ConflictRecord],
        reviewer_agent: str = "Review Engine",
        reviewer_step_id: str = "collaboration",
    ) -> List[AgentReview]:
        return [
            self.review_finding(f, evidence_list, existing_findings, conflicts, reviewer_agent, reviewer_step_id)
            for f in findings
        ]

    def apply_review(self, finding: SharedFinding, review: AgentReview) -> str:
        if review.decision == "approved":
            return "validated"
        if review.decision == "needs_evidence":
            return "pending"
        return "rejected"


review_engine = ReviewEngine()
