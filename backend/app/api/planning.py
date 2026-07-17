"""REST API for Intelligent Planning Engine.

All endpoints are registered under the /api/planning prefix.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query

from app.core.logger import logger
from app.db.session import SessionLocal
from app.models.repository import Repository
from app.services.planning.planning_engine import planning_engine
from app.services.planning.planning_storage import planning_storage

router = APIRouter(prefix="/api/planning", tags=["Intelligent Planning"])


class GeneratePlanPayload(BaseModel):
    repository_id: str
    goal: str


@router.get("/{repository_id}/preview", summary="Preview execution plan for a repository and goal")
async def preview_plan(
    repository_id: str,
    goal: str = Query(..., description="The user's workflow goal"),
) -> Dict[str, Any]:
    with SessionLocal() as db:
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found.")
            
    try:
        plan = planning_engine.generate_plan(repository_id, goal)
        return plan.to_dict()
    except Exception as e:
        logger.error(f"[PlanningAPI] Plan generation preview failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", summary="Generate and save an execution plan")
async def generate_plan(payload: GeneratePlanPayload) -> Dict[str, Any]:
    with SessionLocal() as db:
        repo = db.query(Repository).filter(Repository.id == payload.repository_id).first()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found.")
            
    try:
        # Check cache
        plan = planning_storage.validate_cache(payload.repository_id, payload.goal, repo.repository_hash)
        if plan:
            plan.telemetry["cache_hit"] = True
            plan.telemetry["cache_miss"] = False
            return plan.to_dict()
            
        plan = planning_engine.generate_plan(payload.repository_id, payload.goal)
        planning_storage.save_plan(payload.repository_id, plan)
        return plan.to_dict()
    except Exception as e:
        logger.error(f"[PlanningAPI] Plan generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/validate", summary="Validate execution plan structure")
async def validate_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    # Check completeness of step structures
    steps = payload.get("steps", [])
    if not steps:
        return {"valid": False, "errors": ["No steps defined in the plan."]}
        
    errors = []
    step_ids = set()
    for idx, step in enumerate(steps):
        sid = step.get("step_id")
        if not sid:
            errors.append(f"Step at index {idx} has no step_id.")
        else:
            step_ids.add(sid)
            
        if not step.get("agent"):
            errors.append(f"Step '{sid or idx}' has no agent specified.")
            
        if not step.get("title"):
            errors.append(f"Step '{sid or idx}' has no title.")
            
    # Verify dependencies are correct
    deps = payload.get("dependencies", [])
    for idx, dep in enumerate(deps):
        src = dep.get("source_step_id")
        tgt = dep.get("target_step_id")
        if not src or src not in step_ids:
            errors.append(f"Dependency at index {idx} has invalid source_step_id: {src}")
        if not tgt or tgt not in step_ids:
            errors.append(f"Dependency at index {idx} has invalid target_step_id: {tgt}")
            
    # Validate no circular dependencies
    if not errors:
        try:
            from app.services.planning.planning_models import ExecutionStep, StepDependency
            step_objs = []
            for s in steps:
                step_objs.append(ExecutionStep(
                    step_id=s["step_id"],
                    agent=s["agent"],
                    title=s["title"],
                    description=s.get("description", ""),
                    execution_group=s.get("execution_group", "analysis"),
                ))
            dep_objs = []
            for dep in deps:
                dep_objs.append(StepDependency(
                    source_step_id=dep["source_step_id"],
                    target_step_id=dep["target_step_id"],
                ))
            planning_engine.topological_sort(step_objs, dep_objs)
        except Exception as e:
            errors.append(f"Dependency Cycle detected: {str(e)}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


@router.delete("/cache/{repository_id}", summary="Delete planning cache for a repository")
async def delete_cache(repository_id: str) -> Dict[str, Any]:
    try:
        planning_storage.clear_cache(repository_id)
        return {"status": "success", "message": f"Planning cache cleared for repository {repository_id}"}
    except Exception as e:
        logger.error(f"[PlanningAPI] Clear planning cache failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
