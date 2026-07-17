"""Reasoning API router — Phase 8.8.

All GET endpoints read persisted JSON ONLY — zero graph traversal or
reasoning computation is performed at query time.

Only POST /rebuild may trigger a reasoning build.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.logger import logger
from app.services.reasoning import reasoning_engine
from app.services.reasoning import reasoning_storage

router = APIRouter(prefix="/api/reasoning", tags=["reasoning"])


class RebuildRequest(BaseModel):
    goal: str = ""


def _require_data(data: Any, repository_id: str, label: str) -> Dict[str, Any]:
    """Return dict or raise 404 if no data exists yet."""
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No {label} found for repository '{repository_id}'. "
                   f"Run POST /api/reasoning/{repository_id}/rebuild first.",
        )
    return data


# ---------------------------------------------------------------------------
# GET endpoints — disk-only reads
# ---------------------------------------------------------------------------

@router.get("/{repository_id}")
async def get_reasoning_summary(repository_id: str) -> Dict[str, Any]:
    """Full ReasoningSummary for a repository (from disk)."""
    data = reasoning_storage.load_full_dict(repository_id)
    return _require_data(data, repository_id, "reasoning summary")


@router.get("/{repository_id}/context")
async def get_reasoning_context(repository_id: str) -> Dict[str, Any]:
    """ReasoningContext section from the persisted summary."""
    data = reasoning_storage.load_section(repository_id, "reasoning_context")
    return _require_data(data, repository_id, "reasoning context")


@router.get("/{repository_id}/dependencies")
async def get_dependency_reasoning(repository_id: str) -> Dict[str, Any]:
    """DependencyReasoning section from the persisted summary."""
    data = reasoning_storage.load_section(repository_id, "dependency_reasoning")
    return _require_data(data, repository_id, "dependency reasoning")


@router.get("/{repository_id}/impact")
async def get_impact_reasoning(repository_id: str) -> Dict[str, Any]:
    """ImpactReasoning section from the persisted summary."""
    data = reasoning_storage.load_section(repository_id, "impact_reasoning")
    return _require_data(data, repository_id, "impact reasoning")


@router.get("/{repository_id}/evidence")
async def get_evidence_ranking(repository_id: str) -> Dict[str, Any]:
    """EvidenceRanking section from the persisted summary."""
    data = reasoning_storage.load_section(repository_id, "evidence_ranking")
    return _require_data(data, repository_id, "evidence ranking")


@router.get("/{repository_id}/history")
async def get_historical_reasoning(repository_id: str) -> Dict[str, Any]:
    """HistoricalReasoning section from the persisted summary."""
    data = reasoning_storage.load_section(repository_id, "historical_reasoning")
    return _require_data(data, repository_id, "historical reasoning")


@router.get("/{repository_id}/metrics")
async def get_reasoning_metrics(repository_id: str) -> Dict[str, Any]:
    """ReasoningMetrics from the persisted metrics.json file."""
    data = reasoning_storage.load_metrics_dict(repository_id)
    return _require_data(data, repository_id, "reasoning metrics")


@router.get("/{repository_id}/cache")
async def get_cache_status(repository_id: str) -> Dict[str, Any]:
    """Cache manifest (cache.json) for compatibility inspection."""
    data = reasoning_storage.get_cache_manifest(repository_id)
    if data is None:
        return {"status": "no_cache", "repository_id": repository_id}
    return {"status": "cached", "repository_id": repository_id, **data}


# ---------------------------------------------------------------------------
# POST /rebuild — only endpoint allowed to trigger computation
# ---------------------------------------------------------------------------

@router.post("/{repository_id}/rebuild")
async def rebuild_reasoning(repository_id: str, body: RebuildRequest = None) -> Dict[str, Any]:
    """Trigger a full reasoning rebuild in a background thread.

    Accepts optional { "goal": "..." } body. If omitted, uses empty goal
    which maps to 'General Analysis' intent.
    """
    goal = (body.goal if body else "") or ""

    # Fetch repo hash and intel_path from DB
    repo_hash = "unknown"
    intel_path = ""
    try:
        from app.db.session import SessionLocal
        from app.models.repository import Repository
        with SessionLocal() as db:
            repo = db.query(Repository).filter(Repository.id == repository_id).first()
            if repo:
                repo_hash = repo.repository_hash or "unknown"
                intel_path = repo.intelligence_path or ""
    except Exception as exc:
        logger.warning(f"[ReasoningAPI] DB lookup failed for {repository_id}: {exc}")

    # Invalidate existing cache so build proceeds
    reasoning_engine.invalidate(repository_id)

    # Run build in background thread to avoid blocking the event loop
    async def _do_rebuild():
        try:
            await asyncio.to_thread(
                reasoning_engine.build,
                repository_id,
                goal,
                repo_hash,
                intel_path,
            )
            logger.info(f"[ReasoningAPI] Rebuild complete for {repository_id}")
        except Exception as exc:
            logger.error(f"[ReasoningAPI] Rebuild failed for {repository_id}: {exc}")

    asyncio.create_task(_do_rebuild())

    return {
        "status": "rebuilding",
        "repository_id": repository_id,
        "goal": goal,
        "message": "Reasoning rebuild started. Poll GET /api/reasoning/{repository_id} for results.",
    }
