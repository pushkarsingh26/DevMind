"""Deterministic conflict detection and resolution — Phase 8.6."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from app.services.collaboration.collaboration_models import (
    ConflictRecord,
    SharedFinding,
    SharedWorkspace,
    make_sha256_id,
)
from app.services.collaboration.versions import CONFLICT_RULESET_VERSION

SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}

AGENT_PRIORITY: Dict[str, int] = {
    "Review Agent": 4,
    "Repository Agent": 3,
    "Security Agent": 2,
    "Performance Agent": 2,
    "Testing Agent": 2,
    "Documentation Agent": 2,
    "Refactor Agent": 2,
    "Summary Agent": 1,
}

POSITIVE_PATTERNS = ("no issue", "no problem", "looks good", "passes", "clean", "safe")
NEGATIVE_PATTERNS = ("critical", "vulnerability", "bug", "error", "fail", "issue", "risk")


class ConflictResolver:
    """Detects and resolves conflicts between agent findings."""

    def __init__(self):
        self.ruleset_version = CONFLICT_RULESET_VERSION

    def _duplicate_key(self, finding: SharedFinding) -> str:
        return make_sha256_id(f"{finding.title}:{finding.file_path}:{finding.line_range}")

    def _is_positive(self, text: str) -> bool:
        lower = text.lower()
        return any(p in lower for p in POSITIVE_PATTERNS)

    def _is_negative(self, text: str) -> bool:
        lower = text.lower()
        return any(p in lower for p in NEGATIVE_PATTERNS)

    def _agent_priority(self, agent_name: str) -> int:
        return AGENT_PRIORITY.get(agent_name, 2)

    def detect_conflicts(self, findings: List[SharedFinding]) -> List[ConflictRecord]:
        conflicts: List[ConflictRecord] = []
        seen: Dict[str, str] = {}

        for i, fa in enumerate(findings):
            dup_key = self._duplicate_key(fa)
            if dup_key in seen and seen[dup_key] != fa.finding_id:
                fb_id = seen[dup_key]
                conflict_id = make_sha256_id(f"duplicate:{fa.finding_id}:{fb_id}")
                conflicts.append(ConflictRecord(
                    conflict_id=conflict_id,
                    finding_id_a=fa.finding_id,
                    finding_id_b=fb_id,
                    conflict_type="duplicate",
                    resolution="pending",
                    winning_finding_id="",
                    resolution_reason="",
                ))
            else:
                seen[dup_key] = fa.finding_id

            for fb in findings[i + 1:]:
                if fa.finding_id == fb.finding_id:
                    continue

                conflict_type: Optional[str] = None

                if fa.title == fb.title and fa.severity != fb.severity:
                    conflict_type = "severity_mismatch"
                elif (
                    fa.file_path == fb.file_path
                    and fa.symbol == fb.symbol
                    and fa.symbol
                    and self._is_positive(fa.description) != self._is_positive(fb.description)
                    and (self._is_negative(fa.description) or self._is_negative(fb.description))
                ):
                    conflict_type = "contradiction"
                elif (
                    fa.category == fb.category
                    and fa.title != fb.title
                    and self._is_positive(fa.description) != self._is_positive(fb.description)
                ):
                    conflict_type = "recommendation_mismatch"

                if conflict_type:
                    pair = tuple(sorted([fa.finding_id, fb.finding_id]))
                    conflict_id = make_sha256_id(f"{conflict_type}:{pair[0]}:{pair[1]}")
                    if not any(c.conflict_id == conflict_id for c in conflicts):
                        conflicts.append(ConflictRecord(
                            conflict_id=conflict_id,
                            finding_id_a=fa.finding_id,
                            finding_id_b=fb.finding_id,
                            conflict_type=conflict_type,
                            resolution="pending",
                            winning_finding_id="",
                            resolution_reason="",
                        ))

        return conflicts

    def resolve_conflict(
        self,
        conflict: ConflictRecord,
        findings: List[SharedFinding],
    ) -> ConflictRecord:
        if conflict.resolution == "resolved" and conflict.winning_finding_id:
            return conflict

        finding_map = {f.finding_id: f for f in findings}
        fa = finding_map.get(conflict.finding_id_a)
        fb = finding_map.get(conflict.finding_id_b)
        if not fa or not fb:
            return conflict

        winner, reason = self._pick_winner(fa, fb, conflict.conflict_type)
        conflict.resolution = "resolved"
        conflict.winning_finding_id = winner.finding_id
        conflict.resolution_reason = reason
        return conflict

    def _pick_winner(
        self,
        fa: SharedFinding,
        fb: SharedFinding,
        conflict_type: str,
    ) -> Tuple[SharedFinding, str]:
        sev_a = SEVERITY_ORDER.get(fa.severity.lower(), 0)
        sev_b = SEVERITY_ORDER.get(fb.severity.lower(), 0)
        if sev_a != sev_b:
            winner = fa if sev_a > sev_b else fb
            return winner, f"Higher severity ({winner.severity}) wins."

        pri_a = self._agent_priority(fa.agent_name)
        pri_b = self._agent_priority(fb.agent_name)
        if pri_a != pri_b:
            winner = fa if pri_a > pri_b else fb
            return winner, f"Agent priority ({winner.agent_name}) wins."

        winner = fa if fa.step_id >= fb.step_id else fb
        return winner, "Recency tie-break — latest step wins."

    def resolve_all(self, workspace: SharedWorkspace) -> List[ConflictRecord]:
        detected = self.detect_conflicts(workspace.findings)
        existing_ids = {c.conflict_id for c in workspace.conflicts}

        merged = list(workspace.conflicts)
        for conflict in detected:
            if conflict.conflict_id not in existing_ids:
                merged.append(conflict)
                existing_ids.add(conflict.conflict_id)

        resolved = []
        for conflict in merged:
            resolved.append(self.resolve_conflict(conflict, workspace.findings))
        return resolved


conflict_resolver = ConflictResolver()
