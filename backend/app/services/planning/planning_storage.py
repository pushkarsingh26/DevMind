"""Planning Cache Storage.

Handles serialization and lookup of plans under backend/data/repositories/{repository_id}/plans/.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.logger import logger
from app.services.planning.planning_models import ExecutionPlan
from app.services.planning.versions import PLAN_VERSION, PLANNER_VERSION, PLAN_SCHEMA_VERSION, RULESET_VERSION


class PlanningStorage:
    """Manages the persistence of generated planning execution plans."""

    def _get_plans_dir(self, repository_id: str) -> Path:
        """Returns the plans directory for a given repository."""
        # e.g., backend/data/repositories/{repository_id}/plans/
        plans_dir = Path("backend/data/repositories") / repository_id / "plans"
        plans_dir.mkdir(parents=True, exist_ok=True)
        return plans_dir

    def save_plan(self, repository_id: str, plan: ExecutionPlan) -> None:
        """Saves a plan file, graph file, and metrics file to disk."""
        plans_dir = self._get_plans_dir(repository_id)
        plan_file = plans_dir / f"{plan.plan_id}.json"
        graph_file = plans_dir / f"{plan.plan_id}_graph.json"
        metrics_file = plans_dir / f"{plan.plan_id}_metrics.json"
        
        plan_dict = plan.to_dict()
        graph_dict = {
            "steps": plan_dict.get("steps", []),
            "dependencies": plan_dict.get("dependencies", []),
            "intent": plan_dict.get("intent", ""),
        }
        metrics_dict = {
            "metrics": plan_dict.get("metrics", {}),
            "score": plan_dict.get("score", {}),
            "telemetry": plan_dict.get("telemetry", {}),
        }
        
        try:
            with plan_file.open("w", encoding="utf-8") as f:
                json.dump(plan_dict, f, indent=2, ensure_ascii=False)
            with graph_file.open("w", encoding="utf-8") as f:
                json.dump(graph_dict, f, indent=2, ensure_ascii=False)
            with metrics_file.open("w", encoding="utf-8") as f:
                json.dump(metrics_dict, f, indent=2, ensure_ascii=False)
            logger.info(f"[PlanningStorage] Plan, graph, and metrics saved for ID {plan.plan_id}")
        except Exception as e:
            logger.error(f"[PlanningStorage] Failed to save plan: {e}")

    def load_plan(self, repository_id: str, plan_id: str) -> Optional[ExecutionPlan]:
        """Loads a plan file from disk."""
        plans_dir = self._get_plans_dir(repository_id)
        plan_file = plans_dir / f"{plan_id}.json"
        
        if not plan_file.is_file():
            return None
            
        try:
            with plan_file.open("r", encoding="utf-8") as f:
                d = json.load(f)
            return ExecutionPlan.from_dict(d)
        except Exception as e:
            logger.error(f"[PlanningStorage] Failed to load plan {plan_id}: {e}")
            return None

    def validate_cache(
        self,
        repository_id: str,
        goal: str,
        repo_hash: str,
    ) -> Optional[ExecutionPlan]:
        """Looks for a valid cached plan matching repo hash, goal, and versions.
        
        Returns the plan if valid, otherwise None.
        """
        plans_dir = self._get_plans_dir(repository_id)
        if not plans_dir.is_dir():
            return None
            
        normalized_goal = goal.strip().lower()
        
        try:
            for pfile in plans_dir.glob("*.json"):
                # Skip graph and metrics files when looking for full plans
                if pfile.name.endswith("_graph.json") or pfile.name.endswith("_metrics.json"):
                    continue
                    
                with pfile.open("r", encoding="utf-8") as f:
                    d = json.load(f)
                
                # Check version matches
                if d.get("plan_version") != PLAN_VERSION:
                    continue
                if d.get("planner_version") != PLANNER_VERSION:
                    continue
                if d.get("plan_schema_version") != PLAN_SCHEMA_VERSION:
                    continue
                if d.get("ruleset_version") != RULESET_VERSION:
                    continue
                    
                # Check target hash matches
                if d.get("repository_hash") != repo_hash:
                    continue
                    
                # Check goal matches
                if d.get("goal_text", "").strip().lower() == normalized_goal:
                    logger.info(f"[PlanningStorage] Found valid cached plan: {d.get('plan_id')}")
                    return ExecutionPlan.from_dict(d)
                    
            return None
        except Exception as e:
            logger.error(f"[PlanningStorage] Error scanning planning cache: {e}")
            return None

    def clear_cache(self, repository_id: str) -> None:
        """Removes all cached plans for a repository."""
        plans_dir = self._get_plans_dir(repository_id)
        if not plans_dir.is_dir():
            return
            
        try:
            for pfile in plans_dir.glob("*.json"):
                pfile.unlink()
            logger.info(f"[PlanningStorage] Cleared all cached plans for repository {repository_id}")
        except Exception as e:
            logger.error(f"[PlanningStorage] Failed to clear planning cache: {e}")


planning_storage = PlanningStorage()
