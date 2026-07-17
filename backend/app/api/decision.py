"""Decision API Router — Phase 8.9.

All GET endpoints read persisted JSON ONLY — zero graph traversal or
recomputation is performed at query time.

Only POST /evaluate may trigger policy/decision evaluation.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.logger import logger
from app.services.decision import decision_engine, decision_storage

router = APIRouter(prefix="/api/decision", tags=["decision"])


class EvaluateRequest(BaseModel):
    goal: str = ""


def _require_data(data: Any, repository_id: str, label: str) -> Any:
    if data is None:
        raise HTTPException(
            status_code=404,
            detail=f"No {label} found for repository '{repository_id}'. "
                   f"Run POST /api/decision/{repository_id}/evaluate first.",
        )
    return data


# ---------------------------------------------------------------------------
# GET endpoints — disk-only reads
# ---------------------------------------------------------------------------

@router.get("/{repository_id}")
async def get_decision_summary(repository_id: str) -> Dict[str, Any]:
    """Returns stored DecisionSummary dict."""
    data = decision_storage.load_raw_file(repository_id, "decision.json")
    return _require_data(data, repository_id, "decision summary")


@router.get("/{repository_id}/history")
async def get_decision_history(repository_id: str) -> List[Dict[str, Any]]:
    """Returns historical list from history.json."""
    data = decision_storage.load_raw_file(repository_id, "history.json")
    return _require_data(data, repository_id, "decision history")


@router.get("/{repository_id}/metrics")
async def get_decision_metrics(repository_id: str) -> Dict[str, Any]:
    """Returns metrics from metrics.json."""
    data = decision_storage.load_raw_file(repository_id, "metrics.json")
    return _require_data(data, repository_id, "decision metrics")


@router.get("/{repository_id}/telemetry")
async def get_decision_telemetry(repository_id: str) -> Dict[str, Any]:
    """Returns telemetry from telemetry.json."""
    data = decision_storage.load_raw_file(repository_id, "telemetry.json")
    return _require_data(data, repository_id, "decision telemetry")


@router.get("/{repository_id}/cache")
async def get_cache_status(repository_id: str) -> Dict[str, Any]:
    """Cache manifest (cache.json) for compatibility inspection."""
    data = decision_storage.load_raw_file(repository_id, "cache.json")
    if data is None:
        return {"status": "no_cache", "repository_id": repository_id}
    return {"status": "cached", "repository_id": repository_id, **data}


# ---------------------------------------------------------------------------
# POST /evaluate — only endpoint allowed to trigger evaluation
# ---------------------------------------------------------------------------

@router.post("/{repository_id}/evaluate")
async def evaluate_decision(repository_id: str, body: EvaluateRequest = None) -> Dict[str, Any]:
    """Trigger decision evaluation in a background thread."""
    goal = (body.goal if body else "") or ""

    # Fetch repo details from database
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
        logger.warning(f"[DecisionAPI] Database lookup failed for {repository_id}: {exc}")

    # Invalidate existing cache before rebuild
    decision_engine.invalidate(repository_id)

    async def _do_evaluate():
        try:
            await asyncio.to_thread(
                decision_engine.build,
                repository_id,
                goal,
                repo_hash,
                intel_path,
            )
            logger.info(f"[DecisionAPI] Evaluation complete for {repository_id}")
        except Exception as exc:
            logger.error(f"[DecisionAPI] Evaluation failed for {repository_id}: {exc}")

    asyncio.create_task(_do_evaluate())

    return {
        "status": "evaluating",
        "repository_id": repository_id,
        "goal": goal,
        "message": "Decision evaluation started in the background.",
    }
