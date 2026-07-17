"""REST API for Multi-Agent Collaboration — Phase 8.6.

All endpoints are read-only (GET). The collaboration pipeline drives all writes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.services.collaboration.collaboration_models import ConsensusResult
from app.services.collaboration.versions import COLLABORATION_VERSION
from app.services.collaboration.workspace_manager import workspace_manager

router = APIRouter(prefix="/api/collaboration", tags=["Multi-Agent Collaboration"])


def _require_workspace(workflow_id: str):
    ws = workspace_manager.load_workspace(workflow_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Collaboration workspace not found.")
    return ws


@router.get("/{workflow_id}/workspace", summary="Shared workspace metadata")
async def get_workspace(workflow_id: str) -> Dict[str, Any]:
    ws = _require_workspace(workflow_id)
    return ws.to_dict()


@router.get("/{workflow_id}/findings", summary="Shared findings with optional status filter")
async def get_findings(
    workflow_id: str,
    status: Optional[str] = Query(None, description="Filter by status: pending/validated/rejected"),
) -> List[Dict[str, Any]]:
    findings = workspace_manager.get_findings(workflow_id)
    if status:
        findings = [f for f in findings if f.status == status]
    return [f.to_dict() for f in findings]


@router.get("/{workflow_id}/reviews", summary="Agent reviews")
async def get_reviews(workflow_id: str) -> List[Dict[str, Any]]:
    ws = _require_workspace(workflow_id)
    return [r.to_dict() for r in ws.reviews]


@router.get("/{workflow_id}/conflicts", summary="Conflict records")
async def get_conflicts(workflow_id: str) -> List[Dict[str, Any]]:
    ws = _require_workspace(workflow_id)
    return [c.to_dict() for c in ws.conflicts]


@router.get("/{workflow_id}/consensus", summary="Consensus result")
async def get_consensus(workflow_id: str) -> Dict[str, Any]:
    consensus = workspace_manager.load_consensus(workflow_id)
    if not consensus:
        raise HTTPException(status_code=404, detail="Consensus not yet generated.")
    return consensus.to_dict()


@router.get("/{workflow_id}/evidence", summary="Evidence records")
async def get_evidence(workflow_id: str) -> List[Dict[str, Any]]:
    ws = _require_workspace(workflow_id)
    return [e.to_dict() for e in ws.evidence]


@router.get("/{workflow_id}/telemetry", summary="Collaboration telemetry")
async def get_telemetry(workflow_id: str) -> Dict[str, Any]:
    telemetry = workspace_manager.load_telemetry(workflow_id)
    return telemetry.to_dict()


@router.get("/{workflow_id}/events", summary="Agent event timeline")
async def get_events(workflow_id: str) -> List[Dict[str, Any]]:
    events = workspace_manager.load_events(workflow_id)
    return [e.to_dict() for e in events]


@router.get("/{workflow_id}/health", summary="Collaboration health summary")
async def get_health(workflow_id: str) -> Dict[str, Any]:
    ws = _require_workspace(workflow_id)
    findings = ws.findings
    duplicate_count = len([c for c in ws.conflicts if c.conflict_type == "duplicate"])
    unresolved = len([c for c in ws.conflicts if c.resolution == "pending"])
    reviewed = len(ws.reviews)
    evidence_coverage = (
        len({e.finding_id for e in ws.evidence}) / len(findings) if findings else 0.0
    )
    return {
        "duplicate_count": duplicate_count,
        "unresolved_conflicts": unresolved,
        "reviewed_findings": reviewed,
        "evidence_coverage": round(evidence_coverage, 3),
        "collaboration_version": COLLABORATION_VERSION,
    }
