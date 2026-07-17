"""Collaboration workspace persistence — Phase 8.6."""

from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import List, Optional

from app.core.logger import logger
from app.utils import workflow_storage
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
)
from app.services.collaboration.versions import (
    COLLABORATION_VERSION,
    CONFLICT_RULESET_VERSION,
    CONSENSUS_VERSION,
    EVIDENCE_RULESET_VERSION,
    REVIEW_RULESET_VERSION,
    WORKSPACE_SCHEMA_VERSION,
)

COLLAB_DIR = "collaboration"


class WorkspaceManager:
    """Manages modular collaboration persistence under workflow collaboration/."""

    def __init__(self):
        self._lock = threading.RLock()

    def _path(self, filename: str) -> str:
        return f"{COLLAB_DIR}/{filename}"

    def _save_split(self, workflow_id: str, filename: str, data) -> None:
        wdir = workflow_storage.get_workflow_dir(workflow_id)
        rel_path = self._path(filename)
        os.makedirs(os.path.join(wdir, COLLAB_DIR), exist_ok=True)
        workflow_storage.save_json(workflow_id, rel_path, data)

    def _load_split(self, workflow_id: str, filename: str):
        return workflow_storage.load_json(workflow_id, self._path(filename))

    def create_workspace(self, workflow_id: str, repository_id: str) -> SharedWorkspace:
        with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            workspace = SharedWorkspace(
                workflow_id=workflow_id,
                repository_id=repository_id,
                schema_version=WORKSPACE_SCHEMA_VERSION,
                updated_at=now,
                is_dirty=True,
            )
            self.save_workspace(workflow_id, workspace)
            return workspace

    def save_workspace(self, workflow_id: str, workspace: SharedWorkspace) -> None:
        with self._lock:
            workspace.updated_at = datetime.now(timezone.utc).isoformat()
            self._save_split(workflow_id, "workspace.json", workspace.to_dict())
            self._save_split(
                workflow_id,
                "findings.json",
                [f.to_dict() for f in workspace.findings],
            )
            self._save_split(
                workflow_id,
                "reviews.json",
                [r.to_dict() for r in workspace.reviews],
            )
            self._save_split(
                workflow_id,
                "evidence.json",
                [e.to_dict() for e in workspace.evidence],
            )
            self._save_split(
                workflow_id,
                "conflicts.json",
                [c.to_dict() for c in workspace.conflicts],
            )
            self._save_split(
                workflow_id,
                "agent_events.json",
                [e.to_dict() for e in workspace.events],
            )

    def replay_workspace(self, workflow_id: str) -> Optional[SharedWorkspace]:
        meta = self._load_split(workflow_id, "workspace.json")
        if not meta:
            return None

        findings_data = self._load_split(workflow_id, "findings.json") or []
        reviews_data = self._load_split(workflow_id, "reviews.json") or []
        evidence_data = self._load_split(workflow_id, "evidence.json") or []
        conflicts_data = self._load_split(workflow_id, "conflicts.json") or []
        events_data = self._load_split(workflow_id, "agent_events.json") or []
        contributions_data = self._load_split(workflow_id, "contributions.json") or []

        return SharedWorkspace(
            workflow_id=meta.get("workflow_id", workflow_id),
            repository_id=meta.get("repository_id", ""),
            findings=[SharedFinding.from_dict(f) for f in findings_data],
            reviews=[AgentReview.from_dict(r) for r in reviews_data],
            evidence=[EvidenceRecord.from_dict(e) for e in evidence_data],
            conflicts=[ConflictRecord.from_dict(c) for c in conflicts_data],
            contributions=[AgentContribution.from_dict(c) for c in contributions_data],
            events=[AgentEvent.from_dict(e) for e in events_data],
            schema_version=meta.get("schema_version", WORKSPACE_SCHEMA_VERSION),
            updated_at=meta.get("updated_at", ""),
            workspace_hash=meta.get("workspace_hash", ""),
            is_dirty=meta.get("is_dirty", True),
        )

    def load_workspace(self, workflow_id: str) -> Optional[SharedWorkspace]:
        with self._lock:
            return self.replay_workspace(workflow_id)

    def get_findings(self, workflow_id: str) -> List[SharedFinding]:
        with self._lock:
            ws = self.replay_workspace(workflow_id)
            return ws.findings if ws else []

    def publish_finding(self, workflow_id: str, finding: SharedFinding) -> None:
        with self._lock:
            ws = self.replay_workspace(workflow_id)
            if not ws:
                return
            existing_ids = {f.finding_id for f in ws.findings}
            if finding.finding_id not in existing_ids:
                ws.findings.append(finding)
            ws.is_dirty = True
            self.append_event(workflow_id, AgentEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent=finding.agent_name,
                step_id=finding.step_id,
                event="published",
                finding_id=finding.finding_id,
            ), workspace=ws)
            self.save_workspace(workflow_id, ws)

    def update_finding_status(self, workflow_id: str, finding_id: str, status: str) -> None:
        with self._lock:
            ws = self.replay_workspace(workflow_id)
            if not ws:
                return
            for f in ws.findings:
                if f.finding_id == finding_id:
                    f.status = status
                    break
            ws.is_dirty = True
            self.save_workspace(workflow_id, ws)

    def add_review(self, workflow_id: str, review: AgentReview) -> None:
        with self._lock:
            ws = self.replay_workspace(workflow_id)
            if not ws:
                return
            ws.reviews.append(review)
            ws.is_dirty = True
            finding = next((f for f in ws.findings if f.finding_id == review.finding_id), None)
            self.append_event(workflow_id, AgentEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent=review.reviewer_agent,
                step_id=review.reviewer_step_id,
                event="reviewed",
                finding_id=review.finding_id,
            ), workspace=ws)
            self.save_workspace(workflow_id, ws)

    def add_evidence(self, workflow_id: str, evidence: EvidenceRecord) -> None:
        with self._lock:
            ws = self.replay_workspace(workflow_id)
            if not ws:
                return
            existing = {e.evidence_id for e in ws.evidence}
            if evidence.evidence_id not in existing:
                ws.evidence.append(evidence)
            ws.is_dirty = True
            self.save_workspace(workflow_id, ws)

    def add_conflict(self, workflow_id: str, conflict: ConflictRecord) -> None:
        with self._lock:
            ws = self.replay_workspace(workflow_id)
            if not ws:
                return
            existing = {c.conflict_id for c in ws.conflicts}
            if conflict.conflict_id not in existing:
                ws.conflicts.append(conflict)
                self.append_event(workflow_id, AgentEvent(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    agent="Conflict Resolver",
                    step_id="collaboration",
                    event="conflict_detected",
                    finding_id=conflict.finding_id_a,
                ), workspace=ws)
            if conflict.resolution == "resolved" and conflict.winning_finding_id:
                self.append_event(workflow_id, AgentEvent(
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    agent="Conflict Resolver",
                    step_id="collaboration",
                    event="conflict_resolved",
                    finding_id=conflict.winning_finding_id,
                ), workspace=ws)
            ws.is_dirty = True
            self.save_workspace(workflow_id, ws)

    def mark_consensus_written(self, workflow_id: str, new_hash: str) -> None:
        with self._lock:
            ws = self.replay_workspace(workflow_id)
            if not ws:
                return
            ws.workspace_hash = new_hash
            ws.is_dirty = False
            meta = ws.to_dict()
            meta["workspace_hash"] = new_hash
            meta["is_dirty"] = False
            self._save_split(workflow_id, "workspace.json", meta)
            self.append_event(workflow_id, AgentEvent(
                timestamp=datetime.now(timezone.utc).isoformat(),
                agent="Consensus Engine",
                step_id="collaboration",
                event="consensus_generated",
            ), workspace=ws)
            self.save_workspace(workflow_id, ws)

    def needs_consensus(self, workflow_id: str) -> bool:
        with self._lock:
            ws = self.replay_workspace(workflow_id)
            return ws.is_dirty if ws else True

    def save_consensus(self, workflow_id: str, consensus: ConsensusResult) -> None:
        with self._lock:
            self._save_split(workflow_id, "consensus.json", consensus.to_dict())

    def load_consensus(self, workflow_id: str) -> Optional[ConsensusResult]:
        with self._lock:
            data = self._load_split(workflow_id, "consensus.json")
            return ConsensusResult.from_dict(data) if data else None

    def save_telemetry(self, workflow_id: str, telemetry: CollaborationTelemetry) -> None:
        with self._lock:
            self._save_split(workflow_id, "telemetry.json", telemetry.to_dict())

    def load_telemetry(self, workflow_id: str) -> CollaborationTelemetry:
        with self._lock:
            data = self._load_split(workflow_id, "telemetry.json")
            return CollaborationTelemetry.from_dict(data) if data else CollaborationTelemetry()

    def write_manifest(self, workflow_id: str, repository_hash: str) -> None:
        with self._lock:
            manifest = {
                "workflow_id": workflow_id,
                "repository_hash": repository_hash,
                "collaboration_version": COLLABORATION_VERSION,
                "schema_version": WORKSPACE_SCHEMA_VERSION,
                "consensus_version": CONSENSUS_VERSION,
                "review_ruleset_version": REVIEW_RULESET_VERSION,
                "evidence_ruleset_version": EVIDENCE_RULESET_VERSION,
                "conflict_ruleset_version": CONFLICT_RULESET_VERSION,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            self._save_split(workflow_id, "manifest.json", manifest)

    def validate_manifest(self, workflow_id: str, repository_hash: str) -> bool:
        with self._lock:
            manifest = self._load_split(workflow_id, "manifest.json")
            if not manifest:
                return False
            checks = [
                ("collaboration_version", COLLABORATION_VERSION),
                ("schema_version", WORKSPACE_SCHEMA_VERSION),
                ("consensus_version", CONSENSUS_VERSION),
                ("review_ruleset_version", REVIEW_RULESET_VERSION),
                ("evidence_ruleset_version", EVIDENCE_RULESET_VERSION),
                ("conflict_ruleset_version", CONFLICT_RULESET_VERSION),
            ]
            for field, expected in checks:
                if manifest.get(field) != expected:
                    logger.info(
                        f"[WorkspaceManager] Manifest invalid: {field} "
                        f"expected {expected}, got {manifest.get(field)}"
                    )
                    return False
            if manifest.get("repository_hash") != repository_hash:
                return False
            return True

    def append_event(
        self,
        workflow_id: str,
        event: AgentEvent,
        workspace: Optional[SharedWorkspace] = None,
    ) -> None:
        ws = workspace or self.replay_workspace(workflow_id)
        if not ws:
            return
        ws.events.append(event)
        if workspace is None:
            self._save_split(
                workflow_id,
                "agent_events.json",
                [e.to_dict() for e in ws.events],
            )

    def load_events(self, workflow_id: str) -> List[AgentEvent]:
        with self._lock:
            data = self._load_split(workflow_id, "agent_events.json") or []
            return [AgentEvent.from_dict(e) for e in data]


workspace_manager = WorkspaceManager()
