"""REST API for Repository Analysis Engine.

All endpoints are prefix-registered under /api/analysis.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.logger import logger
from app.db.session import SessionLocal
from app.models.repository import Repository
from app.services.repository_analysis.analysis_engine import repository_analysis_engine
from app.services.repository_analysis.analysis_storage import analysis_storage

router = APIRouter(prefix="/api/analysis", tags=["Repository Analysis"])


def _get_and_ensure_analysis(repo_id: str) -> str:
    """Helper to verify repository in DB and ensure analysis reports exist on disk."""
    with SessionLocal() as db:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            raise HTTPException(
                status_code=404,
                detail=f"Repository '{repo_id}' not found in database.",
            )
        intel_path = repo.intelligence_path
        repo_hash = repo.repository_hash
        
    if not intel_path:
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{repo_id}' has not been indexed yet. Build intelligence first.",
        )
        
    # Ensure analysis exists (loads cache if valid, otherwise runs calculations)
    ok = repository_analysis_engine.ensure_analysis(repo_id, intel_path, repo_hash)
    if not ok:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate repository analysis for '{repo_id}'.",
        )
    return intel_path


@router.get("/{repository_id}/summary", summary="Get global repository analysis summary")
async def get_summary(repository_id: str) -> Dict[str, Any]:
    intel_path = _get_and_ensure_analysis(repository_id)
    summary = analysis_storage.load_summary(intel_path)
    if not summary:
        raise HTTPException(status_code=404, detail="Summary analysis report not found.")
    return summary


@router.get("/{repository_id}/impact", summary="Get change impact analysis for a symbol")
async def get_impact(
    repository_id: str,
    symbol_id: str = Query(..., description="The symbol node ID to run impact mapping for"),
) -> Dict[str, Any]:
    intel_path = _get_and_ensure_analysis(repository_id)
    impact_data = analysis_storage.load_impact(intel_path)
    if not impact_data:
        raise HTTPException(status_code=404, detail="Impact analysis report not found.")
        
    impacts = impact_data.get("impacts", {})
    symbol_impact = impacts.get(symbol_id, [])
    
    # Calculate impacted symbols list
    impacted_symbols = repository_analysis_engine.impacted_symbols(repository_id, symbol_id)
    
    return {
        "symbol_id": symbol_id,
        "impacted_files": symbol_impact,
        "impacted_symbols": impacted_symbols,
        "files_count": len(symbol_impact),
        "symbols_count": len(impacted_symbols),
    }


@router.get("/{repository_id}/dependencies", summary="Get dependency chain path analysis")
async def get_dependencies(
    repository_id: str,
    source: str = Query(..., description="The source node ID (e.g. module:pkg/file_0.py)"),
    target: str = Query(..., description="The target node ID (e.g. module:pkg/file_1.py)"),
) -> Dict[str, Any]:
    _get_and_ensure_analysis(repository_id)
    path = repository_analysis_engine.shortest_path(repository_id, source, target)
    return {
        "source": source,
        "target": target,
        "path": path,
        "length": len(path),
    }


@router.get("/{repository_id}/dead-code", summary="Get dead code and unused symbols")
async def get_dead_code(repository_id: str) -> Dict[str, Any]:
    intel_path = _get_and_ensure_analysis(repository_id)
    dead_code = analysis_storage.load_dead_code(intel_path)
    if not dead_code:
        raise HTTPException(status_code=404, detail="Dead code report not found.")
    return dead_code


@router.get("/{repository_id}/hotspots", summary="Get complexity and coupling hotspots")
async def get_hotspots(repository_id: str) -> Dict[str, Any]:
    intel_path = _get_and_ensure_analysis(repository_id)
    hotspots = analysis_storage.load_hotspots(intel_path)
    if not hotspots:
        raise HTTPException(status_code=404, detail="Hotspots report not found.")
    return hotspots


@router.get("/{repository_id}/architecture", summary="Get identified architecture issues")
async def get_architecture(repository_id: str) -> Dict[str, Any]:
    intel_path = _get_and_ensure_analysis(repository_id)
    architecture = analysis_storage.load_architecture(intel_path)
    if not architecture:
        raise HTTPException(status_code=404, detail="Architecture issues report not found.")
    return architecture
