"""
Phase 8.6 — Multi-Agent Collaboration Engine Tests
Covers: deterministic IDs, serialization, workspace persistence, locking,
        duplicate detection, review validation, evidence generation,
        conflict resolution, lazy consensus, agent timeline, manifest validation, telemetry.
"""
import hashlib
import json
import os
import shutil
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest

from app.services.collaboration.collaboration_models import (
    AgentContribution,
    AgentEvent,
    AgentReview,
    CollaborationTelemetry,
    ConflictRecord,
    ConsensusResult,
    EvidenceRecord,
    SharedFinding,
    SharedWorkspace,
    compute_workspace_hash,
    make_sha256_id,
)
from app.services.collaboration.consensus_engine import consensus_engine
from app.services.collaboration.conflict_resolver import conflict_resolver
from app.services.collaboration.evidence_manager import evidence_manager
from app.services.collaboration.review_engine import review_engine, CONFIDENCE_THRESHOLD
from app.services.collaboration.workspace_manager import workspace_manager
from app.services.collaboration.versions import (
    COLLABORATION_VERSION,
    CONFLICT_RULESET_VERSION,
    CONSENSUS_VERSION,
    EVIDENCE_RULESET_VERSION,
    REVIEW_RULESET_VERSION,
    WORKSPACE_SCHEMA_VERSION,
)
from app.utils import workflow_storage


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_workflow():
    wf_id = f"test_collab_{make_sha256_id(str(time.time()))}"
    yield wf_id
    wdir = workflow_storage.get_workflow_dir(wf_id)
    if os.path.exists(wdir):
        shutil.rmtree(wdir, ignore_errors=True)


def _make_finding(
    step_id="step_1",
    agent="Security Agent",
    title="SQL injection risk",
    file_path="app/db.py",
    severity="high",
    confidence=0.85,
    status="pending",
    line_range="10-20",
    description=None,
) -> SharedFinding:
    fid = make_sha256_id(f"{step_id}:{agent}:{title}:{file_path}:{line_range}")
    return SharedFinding(
        finding_id=fid,
        step_id=step_id,
        agent_name=agent,
        category=agent,
        severity=severity,
        title=title,
        description=description or f"Description of {title}",
        file_path=file_path,
        symbol="query_db",
        line_range=line_range,
        confidence=confidence,
        status=status,
    )


def _make_evidence(finding: SharedFinding, quality: float = 0.7) -> EvidenceRecord:
    eid = make_sha256_id(f"{finding.finding_id}:{finding.file_path}:{finding.symbol}:chunk1")
    return EvidenceRecord(
        evidence_id=eid,
        finding_id=finding.finding_id,
        file_path=finding.file_path,
        symbol=finding.symbol,
        graph_node_id=make_sha256_id("symbol:query_db"),
        chunk_id=make_sha256_id("chunk:app/db.py:0"),
        workflow_step_id=finding.step_id,
        source_agent=finding.agent_name,
        quality_score=quality,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 1. Deterministic IDs
# ─────────────────────────────────────────────────────────────────────────────

def test_sha256_id_reproducible():
    content = "step_1:Security Agent:SQL injection:app/db.py:10-20"
    id1 = make_sha256_id(content)
    id2 = make_sha256_id(content)
    assert id1 == id2
    assert len(id1) == 16


def test_sha256_id_collision_free():
    ids = {make_sha256_id(f"content_{i}") for i in range(100)}
    assert len(ids) == 100


def test_finding_id_format():
    f = _make_finding()
    expected = make_sha256_id("step_1:Security Agent:SQL injection risk:app/db.py:10-20")
    assert f.finding_id == expected


# ─────────────────────────────────────────────────────────────────────────────
# 2. Serialization (9 dataclasses)
# ─────────────────────────────────────────────────────────────────────────────

def test_shared_finding_roundtrip():
    f = _make_finding()
    restored = SharedFinding.from_dict(f.to_dict())
    assert restored.finding_id == f.finding_id
    assert restored.severity == f.severity


def test_evidence_record_roundtrip():
    f = _make_finding()
    e = _make_evidence(f)
    restored = EvidenceRecord.from_dict(e.to_dict())
    assert restored.evidence_id == e.evidence_id


def test_agent_contribution_roundtrip():
    c = AgentContribution("Security Agent", "step_1", 3, 2, "2026-01-01T00:00:00Z")
    restored = AgentContribution.from_dict(c.to_dict())
    assert restored.agent_name == "Security Agent"


def test_agent_event_roundtrip():
    ev = AgentEvent("2026-01-01T00:00:00Z", "Security Agent", "step_1", "published", "abc123")
    restored = AgentEvent.from_dict(ev.to_dict())
    assert restored.event == "published"


def test_agent_review_roundtrip():
    r = AgentReview("rev1", "find1", "Review Agent", "step_2", "approved", 0.9, "OK", "2026-01-01T00:00:00Z")
    restored = AgentReview.from_dict(r.to_dict())
    assert restored.decision == "approved"


def test_conflict_record_roundtrip():
    c = ConflictRecord("c1", "f1", "f2", "duplicate", "resolved", "f1", "Higher severity")
    restored = ConflictRecord.from_dict(c.to_dict())
    assert restored.conflict_type == "duplicate"


def test_consensus_result_roundtrip():
    c = ConsensusResult(
        consensus_id="cons1", supporting_agents=["A"], conflicting_agents=[],
        validated_findings=["f1"], overall_confidence=0.8, evidence_count=1,
        recommendation="high", generated_at="2026-01-01T00:00:00Z",
        consensus_version=CONSENSUS_VERSION, generated_from_workspace_hash="hash1",
        generated_duration_ms=5, validated_findings_count=1,
    )
    restored = ConsensusResult.from_dict(c.to_dict())
    assert restored.consensus_id == "cons1"


def test_shared_workspace_roundtrip():
    ws = SharedWorkspace("wf1", "repo1", findings=[_make_finding()])
    restored = SharedWorkspace.from_dict({
        "workflow_id": "wf1", "repository_id": "repo1",
        "findings": [f.to_dict() for f in ws.findings],
    })
    assert len(restored.findings) == 1


def test_collaboration_telemetry_roundtrip():
    t = CollaborationTelemetry(workspace_updates=5, findings_created=10)
    restored = CollaborationTelemetry.from_dict(t.to_dict())
    assert restored.workspace_updates == 5


# ─────────────────────────────────────────────────────────────────────────────
# 3. Workspace persistence
# ─────────────────────────────────────────────────────────────────────────────

def test_create_workspace(tmp_workflow):
    ws = workspace_manager.create_workspace(tmp_workflow, "repo_test")
    assert ws.workflow_id == tmp_workflow
    assert ws.is_dirty is True


def test_save_and_load_workspace(tmp_workflow):
    ws = workspace_manager.create_workspace(tmp_workflow, "repo_test")
    f = _make_finding()
    ws.findings.append(f)
    workspace_manager.save_workspace(tmp_workflow, ws)
    loaded = workspace_manager.load_workspace(tmp_workflow)
    assert loaded is not None
    assert len(loaded.findings) == 1


def test_replay_workspace(tmp_workflow):
    ws = workspace_manager.create_workspace(tmp_workflow, "repo_test")
    f = _make_finding()
    workspace_manager.publish_finding(tmp_workflow, f)
    replayed = workspace_manager.replay_workspace(tmp_workflow)
    assert replayed is not None
    assert len(replayed.findings) == 1


def test_get_findings(tmp_workflow):
    ws = workspace_manager.create_workspace(tmp_workflow, "repo_test")
    workspace_manager.publish_finding(tmp_workflow, _make_finding())
    findings = workspace_manager.get_findings(tmp_workflow)
    assert len(findings) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 4. Workspace lock
# ─────────────────────────────────────────────────────────────────────────────

def test_concurrent_publish_no_corruption(tmp_workflow):
    workspace_manager.create_workspace(tmp_workflow, "repo_test")

    def publish(i):
        f = _make_finding(title=f"Finding {i}", file_path=f"app/file_{i}.py")
        workspace_manager.publish_finding(tmp_workflow, f)

    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(publish, range(10)))

    findings = workspace_manager.get_findings(tmp_workflow)
    assert len(findings) == 10


def test_concurrent_save_no_corruption(tmp_workflow):
    workspace_manager.create_workspace(tmp_workflow, "repo_test")
    errors = []

    def save_loop():
        try:
            for i in range(5):
                ws = workspace_manager.load_workspace(tmp_workflow)
                if ws:
                    workspace_manager.save_workspace(tmp_workflow, ws)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=save_loop) for _ in range(3)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(errors) == 0


# ─────────────────────────────────────────────────────────────────────────────
# 5. Duplicate detection
# ─────────────────────────────────────────────────────────────────────────────

def test_duplicate_same_title_file():
    f1 = _make_finding(title="Duplicate issue", file_path="app/main.py")
    f2 = _make_finding(title="Duplicate issue", file_path="app/main.py", agent="Review Agent")
    conflicts = conflict_resolver.detect_conflicts([f1, f2])
    assert any(c.conflict_type == "duplicate" for c in conflicts)


def test_duplicate_same_sha256():
    f1 = _make_finding()
    f2 = _make_finding(agent="Review Agent")
    key1 = conflict_resolver._duplicate_key(f1)
    key2 = conflict_resolver._duplicate_key(f2)
    assert key1 == key2


def test_duplicate_cross_agent():
    f1 = _make_finding(agent="Security Agent")
    f2 = _make_finding(agent="Review Agent")
    conflicts = conflict_resolver.detect_conflicts([f1, f2])
    assert len([c for c in conflicts if c.conflict_type == "duplicate"]) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 6. Review validation
# ─────────────────────────────────────────────────────────────────────────────

def test_review_validated_path():
    f = _make_finding(confidence=0.9)
    ev = _make_evidence(f, quality=0.8)
    review = review_engine.review_finding(f, [ev], [f], [])
    assert review.decision == "approved"
    assert review_engine.apply_review(f, review) == "validated"


def test_review_pending_missing_evidence():
    f = _make_finding()
    review = review_engine.review_finding(f, [], [f], [])
    assert review.decision == "needs_evidence"
    assert review_engine.apply_review(f, review) == "pending"


def test_review_rejected_low_confidence():
    f = _make_finding(confidence=0.3)
    ev = _make_evidence(f)
    review = review_engine.review_finding(f, [ev], [f], [])
    assert review.decision == "rejected"


def test_review_rejected_unresolved_conflict():
    f = _make_finding()
    ev = _make_evidence(f)
    conflict = ConflictRecord("c1", f.finding_id, "other", "duplicate", "pending", "", "")
    review = review_engine.review_finding(f, [ev], [f], [conflict])
    assert review.decision == "rejected"


def test_review_confidence_threshold():
    f = _make_finding(confidence=CONFIDENCE_THRESHOLD)
    ev = _make_evidence(f, quality=0.5)
    review = review_engine.review_finding(f, [ev], [f], [])
    assert review.decision == "approved"


# ─────────────────────────────────────────────────────────────────────────────
# 7. Evidence generation
# ─────────────────────────────────────────────────────────────────────────────

def test_evidence_quality_scoring():
    f = _make_finding()
    bundle = {"symbols": ["query_db"], "relevant_chunks": []}
    analysis = {"impacted_files": ["app/db.py"]}
    ev = evidence_manager.generate_evidence(f, bundle, analysis)
    assert ev.quality_score >= 0.45


def test_evidence_graph_reference_bonus():
    f = _make_finding()
    bundle = {"symbols": ["query_db"]}
    ev = evidence_manager.generate_evidence(f, bundle, {})
    assert ev.graph_node_id != ""
    assert ev.quality_score >= 0.30


def test_evidence_multi_agent_agreement():
    f1 = _make_finding(title="Shared issue", agent="Security Agent")
    f2 = _make_finding(title="Shared issue", agent="Review Agent")
    records = evidence_manager.batch_generate([f1, f2], {}, {})
    assert any(r.quality_score >= 0.10 for r in records)


def test_evidence_batch_generate():
    findings = [_make_finding(title=f"Issue {i}", file_path=f"app/f{i}.py") for i in range(3)]
    records = evidence_manager.batch_generate(findings, {}, {})
    assert len(records) == 3


# ─────────────────────────────────────────────────────────────────────────────
# 8. Conflict resolution
# ─────────────────────────────────────────────────────────────────────────────

def test_conflict_severity_priority():
    f_high = _make_finding(severity="high", agent="Testing Agent")
    f_low = _make_finding(severity="low", agent="Testing Agent", title="Different title")
    conflict = ConflictRecord("c1", f_high.finding_id, f_low.finding_id, "severity_mismatch", "pending", "", "")
    resolved = conflict_resolver.resolve_conflict(conflict, [f_high, f_low])
    assert resolved.winning_finding_id == f_high.finding_id


def test_conflict_reviewer_priority():
    f_review = _make_finding(agent="Review Agent", severity="medium", title="Issue A")
    f_test = _make_finding(agent="Testing Agent", severity="medium", title="Issue B", file_path="app/other.py")
    conflict = ConflictRecord("c2", f_review.finding_id, f_test.finding_id, "recommendation_mismatch", "pending", "", "")
    resolved = conflict_resolver.resolve_conflict(conflict, [f_review, f_test])
    assert resolved.winning_finding_id == f_review.finding_id


def test_conflict_recency_tiebreak():
    f_old = _make_finding(step_id="step_1", severity="medium", title="Issue X")
    f_new = _make_finding(step_id="step_9", severity="medium", title="Issue Y", file_path="app/new.py")
    conflict = ConflictRecord("c3", f_old.finding_id, f_new.finding_id, "recommendation_mismatch", "pending", "", "")
    resolved = conflict_resolver.resolve_conflict(conflict, [f_old, f_new])
    assert resolved.winning_finding_id == f_new.finding_id


def test_conflict_contradiction_detection():
    f_pos = _make_finding(title="No issue found", description="Code looks good, no issue detected")
    f_neg = _make_finding(title="Critical bug", description="Critical vulnerability found in auth", severity="critical")
    conflicts = conflict_resolver.detect_conflicts([f_pos, f_neg])
    assert any(c.conflict_type == "contradiction" for c in conflicts)


# ─────────────────────────────────────────────────────────────────────────────
# 9. Lazy consensus
# ─────────────────────────────────────────────────────────────────────────────

def test_consensus_skipped_when_not_dirty(tmp_workflow):
    ws = SharedWorkspace(
        workflow_id=tmp_workflow, repository_id="repo1",
        findings=[_make_finding(status="validated")],
        is_dirty=False,
        workspace_hash=compute_workspace_hash([_make_finding(status="validated").finding_id]),
    )
    assert consensus_engine.should_regenerate(ws) is False


def test_consensus_regenerated_when_dirty():
    f = _make_finding(status="validated")
    ws = SharedWorkspace(
        workflow_id="wf1", repository_id="repo1",
        findings=[f], is_dirty=True, workspace_hash="",
    )
    assert consensus_engine.should_regenerate(ws) is True


def test_consensus_generated_duration_nonzero():
    f = _make_finding(status="validated")
    ev = _make_evidence(f)
    review = AgentReview("r1", f.finding_id, "Review Agent", "s1", "approved", 0.9, "OK", "2026-01-01T00:00:00Z")
    ws = SharedWorkspace(
        workflow_id="wf1", repository_id="repo1",
        findings=[f], evidence=[ev], reviews=[review],
    )
    result = consensus_engine.generate_consensus(ws)
    assert result.generated_duration_ms > 0


# ─────────────────────────────────────────────────────────────────────────────
# 10. Consensus metadata
# ─────────────────────────────────────────────────────────────────────────────

def test_consensus_workspace_hash_matches():
    f = _make_finding(status="validated")
    ws = SharedWorkspace(workflow_id="wf1", repository_id="repo1", findings=[f])
    result = consensus_engine.generate_consensus(ws)
    expected_hash = compute_workspace_hash([f.finding_id])
    assert result.generated_from_workspace_hash == expected_hash


def test_consensus_validated_count():
    findings = [_make_finding(status="validated", title=f"Issue {i}", file_path=f"app/f{i}.py") for i in range(3)]
    ws = SharedWorkspace(workflow_id="wf1", repository_id="repo1", findings=findings)
    result = consensus_engine.generate_consensus(ws)
    assert result.validated_findings_count == 3


def test_consensus_only_validated_findings():
    f_val = _make_finding(status="validated")
    f_rej = _make_finding(status="rejected", title="Rejected issue", file_path="app/rej.py")
    ws = SharedWorkspace(workflow_id="wf1", repository_id="repo1", findings=[f_val, f_rej])
    result = consensus_engine.generate_consensus(ws)
    assert f_rej.finding_id not in result.validated_findings


# ─────────────────────────────────────────────────────────────────────────────
# 11. Agent timeline
# ─────────────────────────────────────────────────────────────────────────────

def test_events_appended_on_publish(tmp_workflow):
    workspace_manager.create_workspace(tmp_workflow, "repo_test")
    f = _make_finding()
    workspace_manager.publish_finding(tmp_workflow, f)
    events = workspace_manager.load_events(tmp_workflow)
    assert any(e.event == "published" for e in events)


def test_events_ordering_preserved(tmp_workflow):
    workspace_manager.create_workspace(tmp_workflow, "repo_test")
    for i in range(3):
        f = _make_finding(title=f"Issue {i}", file_path=f"app/f{i}.py")
        workspace_manager.publish_finding(tmp_workflow, f)
        time.sleep(0.01)
    events = workspace_manager.load_events(tmp_workflow)
    timestamps = [e.timestamp for e in events]
    assert timestamps == sorted(timestamps)


def test_events_load_roundtrip(tmp_workflow):
    workspace_manager.create_workspace(tmp_workflow, "repo_test")
    ev = AgentEvent(datetime.now(timezone.utc).isoformat(), "Agent", "s1", "published", "f1")
    workspace_manager.append_event(tmp_workflow, ev)
    loaded = workspace_manager.load_events(tmp_workflow)
    assert len(loaded) >= 1
    assert loaded[-1].event == "published"


# ─────────────────────────────────────────────────────────────────────────────
# 12. Manifest validation
# ─────────────────────────────────────────────────────────────────────────────

def test_manifest_valid(tmp_workflow):
    workspace_manager.write_manifest(tmp_workflow, "hash_abc")
    assert workspace_manager.validate_manifest(tmp_workflow, "hash_abc") is True


def test_manifest_rejects_collaboration_version(tmp_workflow):
    workspace_manager.write_manifest(tmp_workflow, "hash_abc")
    manifest = workflow_storage.load_json(tmp_workflow, "collaboration/manifest.json")
    manifest["collaboration_version"] = "v99"
    workflow_storage.save_json(tmp_workflow, "collaboration/manifest.json", manifest)
    assert workspace_manager.validate_manifest(tmp_workflow, "hash_abc") is False


def test_manifest_rejects_schema_version(tmp_workflow):
    workspace_manager.write_manifest(tmp_workflow, "hash_abc")
    manifest = workflow_storage.load_json(tmp_workflow, "collaboration/manifest.json")
    manifest["schema_version"] = "v99"
    workflow_storage.save_json(tmp_workflow, "collaboration/manifest.json", manifest)
    assert workspace_manager.validate_manifest(tmp_workflow, "hash_abc") is False


def test_manifest_rejects_consensus_version(tmp_workflow):
    workspace_manager.write_manifest(tmp_workflow, "hash_abc")
    manifest = workflow_storage.load_json(tmp_workflow, "collaboration/manifest.json")
    manifest["consensus_version"] = "v99"
    workflow_storage.save_json(tmp_workflow, "collaboration/manifest.json", manifest)
    assert workspace_manager.validate_manifest(tmp_workflow, "hash_abc") is False


def test_manifest_rejects_ruleset_versions(tmp_workflow):
    workspace_manager.write_manifest(tmp_workflow, "hash_abc")
    for field in ["review_ruleset_version", "evidence_ruleset_version", "conflict_ruleset_version"]:
        workspace_manager.write_manifest(tmp_workflow, "hash_abc")
        manifest = workflow_storage.load_json(tmp_workflow, "collaboration/manifest.json")
        manifest[field] = "v99"
        workflow_storage.save_json(tmp_workflow, "collaboration/manifest.json", manifest)
        assert workspace_manager.validate_manifest(tmp_workflow, "hash_abc") is False


# ─────────────────────────────────────────────────────────────────────────────
# 13. Telemetry
# ─────────────────────────────────────────────────────────────────────────────

def test_telemetry_counter_increments(tmp_workflow):
    t = CollaborationTelemetry(findings_created=5, workspace_updates=2)
    workspace_manager.save_telemetry(tmp_workflow, t)
    loaded = workspace_manager.load_telemetry(tmp_workflow)
    assert loaded.findings_created == 5
    assert loaded.workspace_updates == 2


def test_telemetry_serialization(tmp_workflow):
    t = CollaborationTelemetry(
        findings_validated=3, conflicts_detected=1, consensus_generation_ms=42,
    )
    workspace_manager.save_telemetry(tmp_workflow, t)
    loaded = workspace_manager.load_telemetry(tmp_workflow)
    assert loaded.consensus_generation_ms == 42
