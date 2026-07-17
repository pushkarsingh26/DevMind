"""REST API for Memory & Learning Engine.

All endpoints are registered under the /api/memory prefix.
"""

from __future__ import annotations

from typing import Any, Dict, List
from fastapi import APIRouter, HTTPException

from app.core.logger import logger
from app.db.session import SessionLocal
from app.models.repository import Repository
from app.services.memory import memory_storage, learning_engine

router = APIRouter(prefix="/api/memory", tags=["Memory & Learning Engine"])


@router.get("/{repository_id}", summary="Get long-term repository memory")
async def get_repository_memory(repository_id: str) -> Dict[str, Any]:
    with SessionLocal() as db:
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found.")

    loaded = memory_storage.load(repository_id)
    if not loaded:
        raise HTTPException(
            status_code=404, detail=f"No memory found for repository {repository_id}"
        )

    memory, _, _, _, _ = loaded
    return memory.to_dict()


@router.get("/{repository_id}/patterns", summary="Get recognized historical patterns")
async def get_memory_patterns(repository_id: str) -> List[Dict[str, Any]]:
    loaded = memory_storage.load(repository_id)
    if not loaded:
        return []
    _, patterns, _, _, _ = loaded
    return [p.to_dict() for p in patterns]


@router.get("/{repository_id}/recommendations", summary="Get recommendations from memory")
async def get_memory_recommendations(repository_id: str) -> List[Dict[str, Any]]:
    loaded = memory_storage.load(repository_id)
    if not loaded:
        return []
    _, _, recommendations, _, _ = loaded
    return [r.to_dict() for r in recommendations]


@router.get("/{repository_id}/history", summary="Get workflow execution memories")
async def get_memory_history(repository_id: str) -> List[Dict[str, Any]]:
    loaded = memory_storage.load(repository_id)
    if not loaded:
        return []
    _, _, _, _, history = loaded
    return [h.to_dict() for h in history]


@router.get("/{repository_id}/metrics", summary="Get compiled learning metrics")
async def get_memory_metrics(repository_id: str) -> Dict[str, Any]:
    loaded = memory_storage.load(repository_id)
    if not loaded:
        from app.services.memory.memory_models import LearningMetrics
        return LearningMetrics().to_dict()
    _, _, _, metrics, _ = loaded
    return metrics.to_dict()


@router.post("/{repository_id}/rebuild", summary="Force rebuild patterns and recommendations")
async def rebuild_memory(repository_id: str) -> Dict[str, Any]:
    with SessionLocal() as db:
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found.")
        repo_hash = repo.repository_hash or "unknown_hash"

    ok = learning_engine.rebuild(repository_id, repo_hash)
    if not ok:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to rebuild memory for {repository_id}. History might be empty.",
        )
    return {"status": "success", "message": f"Memory rebuilt for {repository_id}"}
