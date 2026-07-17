"""Collaboration pipeline orchestrator — Phase 8.6."""

from app.services.collaboration.collaboration_models import make_sha256_id
# pyrefly: ignore [invalid-syntax]
from __future__ import annotations

from typing import Any, Dict, Tuple

from app.services.collaboration.collaboration_models import (
    SharedFinding,
    compute_workspace_hash,
)
from app.services.collaboration.consensus_engine import consensus_engine
from app.services.collaboration.conflict_resolver import conflict_resolver
from app.services.collaboration.evidence_manager import evidence_manager
from app.services.collaboration.review_engine import review_engine
from app.services.collaboration.workspace_manager import workspace_manager

SEVERITY_KEYWORDS = {
    "critical": ("critical", "severe", "catastrophic"),
    "high": ("high", "major", "vulnerability", "security"),
    "low": ("low", "minor", "trivial", "informational"),
}


def infer_severity(text: str, default: str = "medium") -> str:
    lower = text.lower()
    for severity, keywords in SEVERITY_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return severity
    return default


def build_shared_finding(raw: Dict[str, Any]) -> SharedFinding:
    step_id = raw.get("step_id", "")
    agent_name = raw.get("agent", "")
    text = raw.get("text", "")
    file_path = raw.get("file_path", "")
    line_range = raw.get("line_range", "")
    symbol = raw.get("symbol", "")
    confidence = float(raw.get("confidence", 0.7))
    category = raw.get("category", agent_name)
    severity = raw.get("severity") or infer_severity(text)
    title = text[:80] if len(text) > 80 else text
    if not title:
        title = "Untitled finding"

    finding_id = make_sha256_id(f"{step_id}:{agent_name}:{title}:{file_path}:{line_range}")
    return SharedFinding(
        finding_id=finding_id,
        step_id=step_id,
        agent_name=agent_name,
        category=category,
        severity=severity,
        title=title,
        description=text,
        file_path=file_path,
        symbol=symbol,
        line_range=line_range,
        confidence=confidence,
        status="pending",
    )


def format_validated_findings_text(workspace) -> str:
    lines = [
        f"[VALIDATED][{f.severity.upper()}] {f.title} ({f.file_path}): {f.description}"
        for f in workspace.findings
        if f.status == "validated"
    ]
    return "\n".join(lines)


def run_collaboration_pipeline(
    workflow_id: str,
    repository_id: str,
    repository_hash: str,
    step_obj: Dict[str, Any],
    context: Any,
    agent_name: str,
) -> Tuple[Dict[str, Any], str]:
    """Run the full collaboration pipeline synchronously (called via asyncio.to_thread)."""
    if agent_name == "Summary Agent":
        return getattr(context, "collaboration_snapshot", {}), getattr(
            context, "collaboration_context", {}
        ).get("validated_findings_text", "")

    step_id = step_obj.get("step_id", "")
    bundle = getattr(context, "shared_context_bundle", {}) or {}
    raw_findings = bundle.get("agent_findings", [])
    step_findings = [f for f in raw_findings if f.get("step_id") == step_id]
    if not step_findings:
        snapshot = getattr(context, "collaboration_snapshot", {})
        validated_text = getattr(context, "collaboration_context", {}).get(
            "validated_findings_text", ""
        )
        return snapshot, validated_text

    # Phase 8.8 — Sort findings by EvidenceRanking (reasoning is canonical evidence source)
    try:
        from app.services.reasoning.reasoning_engine import reasoning_engine as _re
        _r_summary = _re.get_summary(repository_id)
        if _r_summary and _r_summary.evidence_ranking and _r_summary.evidence_ranking.ranked_items:
            _ranked_scores = {
                item.title: item.score
                for item in _r_summary.evidence_ranking.ranked_items
            }
            step_findings = sorted(
                step_findings,
                key=lambda f: -_ranked_scores.get(f.get("file_path", ""), 0.0),
            )
    except Exception:
        pass  # fallback to original order

    if not workspace_manager.validate_manifest(workflow_id, repository_hash):
        workspace_manager.write_manifest(workflow_id, repository_hash)
        workspace = workspace_manager.create_workspace(workflow_id, repository_id)
    else:
        workspace = workspace_manager.load_workspace(workflow_id)
        if not workspace:
            workspace_manager.write_manifest(workflow_id, repository_hash)
            workspace = workspace_manager.create_workspace(workflow_id, repository_id)

    telemetry = workspace_manager.load_telemetry(workflow_id)
    analysis_data = bundle.get("analysis", {})

    new_shared = [build_shared_finding(raw) for raw in step_findings]

    # --- Phase 8.7 Integration ---
    try:
        from app.services.memory import memory_storage
        mem_data = memory_storage.load(repository_id)
        if mem_data:
            memory, patterns, recommendations, mem_metrics, history = mem_data
            
            # 1. Increase confidence for recurring validated findings
            for finding in new_shared:
                for pattern in patterns:
                    if pattern.category in ("repeated_bug", "repeated_security_finding", "repeated_dependency_problem"):
                        parts = pattern.key_signature.split(":")
                        pat_file = parts[1] if len(parts) > 1 else ""
                        if pat_file and finding.file_path == pat_file:
                            finding.confidence = min(0.99, finding.confidence + 0.15)
                            finding.description = f"[Recurring Pattern Match] {finding.description}"
    except Exception:
        pass
    # -----------------------------

    evidence_records = evidence_manager.batch_generate(new_shared, bundle, analysis_data)

    for finding in new_shared:
        workspace_manager.publish_finding(workflow_id, finding)
    for ev in evidence_records:
        workspace_manager.add_evidence(workflow_id, ev)

    workspace = workspace_manager.replay_workspace(workflow_id)
    if not workspace:
        return {}, ""

    resolved_conflicts = conflict_resolver.resolve_all(workspace)

    # --- Phase 8.7 Integration ---
    try:
        from app.services.memory import memory_storage
        mem_data = memory_storage.load(repository_id)
        if mem_data:
            memory, patterns, recommendations, mem_metrics, history = mem_data
            for conflict in resolved_conflicts:
                for pattern in patterns:
                    if pattern.category == "repeated_hotspot":
                        parts = pattern.key_signature.split(":")
                        pat_file = parts[1] if len(parts) > 1 else ""
                        if pat_file and conflict.file_path == pat_file:
                            conflict.resolution_reason = f"[Repeated Hotspot Conflict Detected] {conflict.resolution_reason or ''}"
    except Exception:
        pass
    # -----------------------------

    for conflict in resolved_conflicts:
        workspace_manager.add_conflict(workflow_id, conflict)

    workspace = workspace_manager.replay_workspace(workflow_id)
    if not workspace:
        return {}, ""

    reviews = review_engine.batch_review(
        new_shared,
        workspace.evidence,
        workspace.findings,
        workspace.conflicts,
        reviewer_agent=agent_name,
        reviewer_step_id=step_id,
    )
    for review in reviews:
        workspace_manager.add_review(workflow_id, review)
        status = review_engine.apply_review(
            next(f for f in new_shared if f.finding_id == review.finding_id),
            review,
        )
        workspace_manager.update_finding_status(workflow_id, review.finding_id, status)

    workspace = workspace_manager.replay_workspace(workflow_id)
    if not workspace:
        return {}, ""

    consensus = None
    if consensus_engine.should_regenerate(workspace):
        consensus = consensus_engine.generate_consensus(workspace)
        workspace_manager.save_consensus(workflow_id, consensus)
        validated_ids = [f.finding_id for f in workspace.findings if f.status == "validated"]
        new_hash = compute_workspace_hash(validated_ids)
        workspace_manager.mark_consensus_written(workflow_id, new_hash)
        telemetry.consensus_generation_ms = consensus.generated_duration_ms
    else:
        consensus = workspace_manager.load_consensus(workflow_id)

    workspace = workspace_manager.replay_workspace(workflow_id)
    validated_count = len([f for f in workspace.findings if f.status == "validated"]) if workspace else 0
    pending_conflicts = len([c for c in workspace.conflicts if c.resolution == "pending"]) if workspace else 0

    snapshot = {
        "findings_count": len(workspace.findings) if workspace else 0,
        "validated_count": validated_count,
        "conflicts_count": pending_conflicts,
        "confidence": consensus.overall_confidence if consensus else 0.0,
        "consensus_id": consensus.consensus_id if consensus else None,
    }

    telemetry.workspace_updates += 1
    telemetry.findings_created += len(new_shared)
    telemetry.findings_validated += len([r for r in reviews if r.decision == "approved"])
    telemetry.findings_rejected += len([r for r in reviews if r.decision == "rejected"])
    telemetry.conflicts_detected += len(resolved_conflicts)
    telemetry.conflicts_resolved += len([c for c in resolved_conflicts if c.resolution == "resolved"])
    if reviews:
        telemetry.average_confidence = sum(r.confidence for r in reviews) / len(reviews)
    workspace_manager.save_telemetry(workflow_id, telemetry)

    if workspace:
        workspace_manager.save_workspace(workflow_id, workspace)

    validated_text = format_validated_findings_text(workspace) if workspace else ""
    return snapshot, validated_text
