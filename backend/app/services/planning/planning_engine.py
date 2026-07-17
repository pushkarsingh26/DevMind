"""Planning Engine implementation.
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.logger import logger
from app.db.session import SessionLocal
from app.models.repository import Repository
from app.services.knowledge_graph.graph_manager import graph_manager
from app.services.repository_analysis.analysis_engine import repository_analysis_engine
from app.services.repository_analysis.analysis_storage import analysis_storage
from app.services.planning.planning_models import (
    ExecutionPlan,
    ExecutionStep,
    StepDependency,
    PlanningMetrics,
)
from app.services.planning.planning_rules import PLANNING_RULES
from app.services.planning.versions import PLAN_VERSION, PLANNER_VERSION, PLAN_SCHEMA_VERSION, RULESET_VERSION


class PlanningEngine:
    """Deterministic, rule-based planner that constructs optimized execution graphs."""

    def parse_goal(self, goal: str) -> str:
        """Parses and normalizes user goal text."""
        return goal.strip()

    def detect_intent(self, goal: str) -> str:
        """Detects workflow category/intent based on goal keyword matching."""
        goal_lower = goal.lower()
        
        if any(w in goal_lower for w in ("dependency", "import", "package", "library", "cycle")):
            return "Dependency Analysis"
        if any(w in goal_lower for w in ("security", "vulnerability", "cve", "owasp")):
            return "Security Audit"
        if any(w in goal_lower for w in ("document", "docs", "readme", "guide", "comment")):
            return "Documentation"
        if any(w in goal_lower for w in ("refactor", "coupling", "simplify", "clean code", "restructure")):
            return "Refactoring"
        if any(w in goal_lower for w in ("performance", "latency", "optimize", "speed", "slow", "bottleneck")):
            return "Performance"
        if any(w in goal_lower for w in ("test", "coverage", "pytest", "unit test", "integration test")):
            return "Testing"
        if any(w in goal_lower for w in ("bug", "fix", "issue", "error", "fail", "crash", "defect")):
            return "Bug Fix"
        if any(w in goal_lower for w in ("architecture", "design pattern", "structure", "subsystem", "audit")):
            return "Architecture Review"
        if any(w in goal_lower for w in ("implement", "add feature", "new feature", "create feature", "build endpoint")):
            return "Feature Implementation"
            
        return "General Analysis"

    def score_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Deterministically scores plan completeness, confidence, and success probability."""
        if not plan.steps:
            return {"confidence": 0.0, "completeness": 0.0, "estimated_success_probability": 0.0}

        # 1. Completeness score based on agent coverage
        has_repo = any(s.agent == "Repository Agent" for s in plan.steps)
        has_summary = any(s.agent == "Summary Agent" for s in plan.steps)
        
        completeness = 0.4
        if has_repo:
            completeness += 0.3
        if has_summary:
            completeness += 0.3

        # 2. Confidence based on intent mapping and rules presence
        confidence = 0.9 if plan.intent != "General Analysis" else 0.7

        # 3. Success probability based on risk levels
        risk_deductions = {"low": 0.0, "medium": 0.1, "high": 0.2}
        complexity_deductions = {"low": 0.0, "medium": 0.05, "high": 0.15}
        
        success_prob = 1.0 - risk_deductions.get(plan.risk_level, 0.0) - complexity_deductions.get(plan.complexity_level, 0.0)
        success_prob = max(0.4, min(1.0, success_prob))

        return {
            "confidence": round(confidence, 2),
            "completeness": round(completeness, 2),
            "estimated_success_probability": round(success_prob, 2),
        }

    def topological_sort(self, steps: List[ExecutionStep], dependencies: List[StepDependency]) -> List[List[str]]:
        """Performs a Kahn's BFS topological sort. Returns tiers of parallelizable step IDs."""
        adj: Dict[str, List[str]] = {}
        in_degree: Dict[str, int] = {}
        
        for s in steps:
            adj[s.step_id] = []
            in_degree[s.step_id] = 0
            
        for dep in dependencies:
            src = dep.source_step_id
            tgt = dep.target_step_id
            if src in adj and tgt in adj:
                adj[src].append(tgt)
                in_degree[tgt] += 1

        # Kahn's algorithm level-by-level
        q = deque([sid for sid, deg in in_degree.items() if deg == 0])
        levels = []
        
        while q:
            level_size = len(q)
            current_level = []
            for _ in range(level_size):
                curr = q.popleft()
                current_level.append(curr)
                for neighbor in adj[curr]:
                     in_degree[neighbor] -= 1
                     if in_degree[neighbor] == 0:
                         q.append(neighbor)
            levels.append(current_level)
            
        visited_count = sum(len(lvl) for lvl in levels)
        if visited_count != len(steps):
            raise ValueError("Cyclic dependencies detected in execution steps.")
            
        return levels

    def generate_plan(self, repository_id: str, goal: str) -> ExecutionPlan:
        """Main planning logic. Builds an ExecutionPlan based on intent rules."""
        start_time = time.time()
        
        # 1. Fetch Repository Details
        with SessionLocal() as db:
            repo = db.query(Repository).filter(Repository.id == repository_id).first()
            repo_hash = repo.repository_hash if repo else "unknown_hash"
            intel_path = repo.intelligence_path if repo else None

        # 2. Parse Goal and Match Intent Rule (profiled)
        t_intent_start = time.time()
        parsed_goal = self.parse_goal(goal)
        intent = self.detect_intent(parsed_goal)
        intent_detection_ms = (time.time() - t_intent_start) * 1000

        # 3. Build Steps and Dependencies (profiled)
        t_rule_start = time.time()
        rule = PLANNING_RULES.get(intent, PLANNING_RULES["General Analysis"])

        steps: List[ExecutionStep] = []
        for step_dict in rule["steps"]:
            steps.append(ExecutionStep(
                step_id=step_dict["step_id"],
                agent=step_dict["agent"],
                title=step_dict["title"],
                description=step_dict["description"],
                execution_group=step_dict["execution_group"],
                estimated_duration=step_dict["estimated_duration"],
                estimated_token_cost=step_dict["estimated_token_cost"],
            ))

        dependencies: List[StepDependency] = []
        for dep_dict in rule["dependencies"]:
            dependencies.append(StepDependency(
                source_step_id=dep_dict["source_step_id"],
                target_step_id=dep_dict["target_step_id"],
            ))
        rule_resolution_ms = (time.time() - t_rule_start) * 1000

        # 4. Validate topological sorting and get parallel tiers (profiled)
        t_topo_start = time.time()
        try:
            tiers = self.topological_sort(steps, dependencies)
        except ValueError as err:
            logger.warning(f"[PlanningEngine] Topological sort failed, resetting dependencies: {err}")
            dependencies = []
            tiers = [[s.step_id] for s in steps]
        topological_sort_ms = (time.time() - t_topo_start) * 1000

        # 5. Extract statistics from Repository Analysis if available
        affected_files = 0
        affected_mods = 0
        if intel_path:
            sum_data = analysis_storage.load_summary(intel_path) or {}
            affected_mods = sum_data.get("total_nodes", 0)
            
            # Simple keyword-based file impact estimation
            keywords = [w.lower() for w in parsed_goal.split() if len(w) > 3]
            if keywords:
                impacted_set = set()
                try:
                    from app.services.knowledge_graph import graph_manager
                    if graph_manager.exists(repository_id):
                        for kw in keywords[:3]:
                            for node in graph_manager.search(repository_id, kw):
                                if node.get("type") == "symbol":
                                    impacted_set.update(repository_analysis_engine.impacted_files(repository_id, node["id"]))
                except Exception:
                    pass
                affected_files = len(impacted_set)

        # 5.5 Phase 8.7: Apply historical memory to adjust risk, priority, and durations
        memory_adjusted = False
        memory_risk = rule.get("risk", "medium")
        memory_priority = rule.get("priority", 5)
        try:
            from app.services.memory import memory_storage
            mem_data = memory_storage.load(repository_id)
            if mem_data:
                memory, patterns, recommendations, mem_metrics, history = mem_data
                
                # If goal text intersects with recurring files, increase duration and risk
                has_hotspot_conflict = False
                for rf in memory.recurring_files:
                    if rf in parsed_goal:
                        has_hotspot_conflict = True
                        break
                        
                if has_hotspot_conflict:
                    for s in steps:
                        s.estimated_duration = int(s.estimated_duration * 1.3)
                    memory_risk = "high"
                    memory_priority = min(10, memory_priority + 2)
                    memory_adjusted = True

                # Adjust risk based on previous workflow outcomes for this intent
                intent_runs = [h for h in history if h.intent == intent]
                intent_failures = [h for h in intent_runs if not h.success]
                if intent_failures:
                    memory_risk = "high"
                    memory_priority = min(10, memory_priority + 2)
                    memory_adjusted = True
                elif intent_runs and all(h.success for h in intent_runs):
                    if memory_risk == "high":
                        memory_risk = "medium"
                    elif memory_risk == "medium":
                        memory_risk = "low"
                    memory_adjusted = True
        except Exception as exc:
            logger.warning(f"[PlanningEngine] Memory-based plan adjustments failed: {exc}")

        # 5.6 Phase 8.8: Apply Reasoning Summary to improve plan quality
        reasoning_adjusted = False
        reasoning_success_probability = None
        reasoning_score = None
        try:
            from app.services.reasoning.reasoning_engine import reasoning_engine
            r_summary = reasoning_engine.get_summary(repository_id)
            if r_summary:
                # Breaking change probability → force high risk
                if r_summary.impact_reasoning and r_summary.impact_reasoning.breaking_change_probability > 0.7:
                    memory_risk = "high"
                    reasoning_adjusted = True

                # Scale affected_files from reasoning critical_files
                if r_summary.dependency_reasoning and r_summary.dependency_reasoning.critical_files:
                    affected_files = max(affected_files, len(r_summary.dependency_reasoning.critical_files))

                # Historical success probability
                if r_summary.historical_reasoning:
                    reasoning_success_probability = r_summary.historical_reasoning.success_probability
                    # If historical success < 50%, elevate risk
                    if reasoning_success_probability < 0.5:
                        if memory_risk == "low":
                            memory_risk = "medium"
                        elif memory_risk == "medium":
                            memory_risk = "high"

                reasoning_score = r_summary.reasoning_score
                reasoning_adjusted = True
        except Exception as exc:
            logger.warning(f"[PlanningEngine] Reasoning-based plan adjustments failed: {exc}")

        # 5.7 Phase 8.9: Apply Decision Engine outcomes
        decision_adjusted = False
        decision_score = None
        decision_priority_level = None
        decision_policies_triggered = []
        try:
            from app.services.decision.decision_engine import decision_engine
            d_summary = decision_engine.get_summary(repository_id)
            if d_summary:
                decision_score = d_summary.decision_score
                decision_priority_level = d_summary.priority_level
                decision_policies_triggered = d_summary.policies_triggered

                # Classify risk based on priority level
                if decision_priority_level in ("high", "critical"):
                    memory_risk = "high"
                
                # Classify priority score
                # Combine memory priority and decision score (average)
                memory_priority = round((memory_priority + decision_score) / 2.0, 4)
                decision_adjusted = True
        except Exception as exc:
            logger.warning(f"[PlanningEngine] Decision-based plan adjustments failed: {exc}")

        # 6. Calculate Planning Metrics
        total_duration = sum(s.estimated_duration for s in steps)
        total_tokens = sum(s.estimated_token_cost for s in steps)
        estimated_cost = round(total_tokens * 0.000002, 4)  # $0.002 per 1M tokens
        
        # Critical path (longest dependency chain in terms of duration)
        # For simplicity, calculate critical path as the sequence of steps in topological levels
        critical_path = [sid for lvl in tiers for sid in lvl]

        metrics = PlanningMetrics(
            estimated_duration=total_duration,
            estimated_tokens=total_tokens,
            estimated_cost=estimated_cost,
            parallel_groups=[",".join(lvl) for lvl in tiers],
            critical_path=critical_path,
            dependency_depth=len(tiers),
            affected_files=max(1, affected_files),
            affected_modules=affected_mods,
        )

        plan_generation_ms = (time.time() - start_time) * 1000

        # 7. Create Execution Plan
        plan = ExecutionPlan(
            plan_id=f"plan_{uuid.uuid4().hex[:12]}",
            plan_version=PLAN_VERSION,
            repository_hash=repo_hash,
            generated_at=datetime.now(timezone.utc).isoformat(),
            planner_version=PLANNER_VERSION,
            plan_schema_version=PLAN_SCHEMA_VERSION,
            ruleset_version=RULESET_VERSION,
            goal_text=parsed_goal,
            steps=steps,
            dependencies=dependencies,
            intent=intent,
            priority_score=memory_priority,
            risk_level=memory_risk,
            complexity_level=rule["complexity"],
            rationale=f"Executing rule-based plan for goal intent: {intent}.",
            metrics=metrics,
            telemetry={
                "planning_time_ms": round(plan_generation_ms, 2),
                "intent_detection_ms": round(intent_detection_ms, 2),
                "rule_resolution_ms": round(rule_resolution_ms, 2),
                "topological_sort_ms": round(topological_sort_ms, 2),
                "cache_hit": False,
                "cache_miss": True,
                "plan_generation_ms": round(plan_generation_ms, 2),
                "memory_adjusted": memory_adjusted,
                "reasoning_adjusted": reasoning_adjusted,
                "reasoning_score": reasoning_score,
                "reasoning_success_probability": reasoning_success_probability,
                "decision_adjusted": decision_adjusted,
                "decision_score": decision_score,
                "decision_policies_triggered": decision_policies_triggered,
            }
        )
        
        # Save goal text inside plan metadata for caching checks
        plan.rationale = f"Goal: {parsed_goal}. Rationale: {plan.rationale}"
        # Store scored properties
        plan.score = self.score_plan(plan)

        return plan


planning_engine = PlanningEngine()
