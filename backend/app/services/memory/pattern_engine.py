"""Deterministic Pattern Recognition Engine."""

from __future__ import annotations

import hashlib
from typing import Dict, List

from app.services.memory.memory_models import PatternRecord, WorkflowMemory


def detect_patterns(
    history: List[WorkflowMemory],
) -> List[PatternRecord]:
    """Scans workflow execution history to extract and merge recurring issue patterns.

    Detects:
    - Repeated bugs (by signature)
    - Repeated security findings
    - Modularity hotspots (files modified frequently)
    - Repeated dependency problems
    """
    patterns: Dict[str, PatternRecord] = {}

    # Helper to generate a stable, unique SHA-256 pattern ID
    def _make_pattern_id(sig: str) -> str:
        return hashlib.sha256(sig.encode("utf-8")).hexdigest()[:16]

    for run in history:
        for finding in run.findings:
            title = finding.get("title", "")
            file_path = finding.get("file_path") or finding.get("file") or "unknown_file"
            category = finding.get("category") or "general"
            severity = finding.get("severity") or "medium"
            symbol = finding.get("symbol") or ""

            # Check if this represents a bug, security issue, or dependency problem
            is_bug = "bug" in category.lower() or "error" in title.lower() or "bug" in title.lower()
            is_security = "security" in category.lower() or "vuln" in title.lower() or "cve" in title.lower()
            is_dep = "dependency" in category.lower() or "package" in category.lower()

            pat_cat = "general"
            if is_bug:
                pat_cat = "repeated_bug"
            elif is_security:
                pat_cat = "repeated_security_finding"
            elif is_dep:
                pat_cat = "repeated_dependency_problem"

            # Create a signature for matching
            # Match by normalized description/title substring + file
            norm_title = "".join(c for c in title.lower() if c.isalnum())[:30]
            sig = f"{pat_cat}:{file_path}:{norm_title}"

            if sig in patterns:
                pat = patterns[sig]
                pat.frequency += 1
                pat.confidence = min(0.98, 0.8 + 0.05 * pat.frequency)
                # Elevate severity if critical/high is found
                if severity.lower() in ("critical", "high") and pat.severity.lower() not in ("critical", "high"):
                    pat.severity = severity.lower()
            else:
                pat_id = _make_pattern_id(sig)
                desc = f"Recurring {pat_cat.replace('_', ' ')} in {file_path}: {title}"
                patterns[sig] = PatternRecord(
                    pattern_id=pat_id,
                    category=pat_cat,
                    key_signature=sig,
                    description=desc,
                    frequency=1,
                    severity=severity,
                    confidence=0.8,
                )

    # Detect modularity hotspots from plan modification frequencies
    file_mods: Dict[str, List[str]] = {}  # file_path -> list of titles/intents
    for run in history:
        for step in run.execution_plan.get("steps", []):
            agent = step.get("agent")
            if agent in ("Refactor Agent", "Write Code Agent"):
                for fp in step.get("files", []):
                    file_mods.setdefault(fp, []).append(run.intent)

    for fp, intents in file_mods.items():
        if len(intents) >= 2:
            sig = f"hotspot:{fp}"
            pat_id = _make_pattern_id(sig)
            desc = f"Architecture Hotspot: {fp} modified frequently across {len(intents)} runs"
            patterns[sig] = PatternRecord(
                pattern_id=pat_id,
                category="repeated_hotspot",
                key_signature=sig,
                description=desc,
                frequency=len(intents),
                severity="medium" if len(intents) < 4 else "high",
                confidence=min(0.98, 0.75 + 0.05 * len(intents)),
            )

    return sorted(list(patterns.values()), key=lambda p: p.frequency, reverse=True)
