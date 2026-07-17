"""Deterministic Recommendation Engine."""

from __future__ import annotations

import hashlib
from typing import List

from app.services.memory.memory_models import (
    PatternRecord,
    Recommendation,
    RepositoryMemory,
    WorkflowMemory,
)


def generate_recommendations(
    memory: RepositoryMemory,
    history: List[WorkflowMemory],
    patterns: List[PatternRecord],
) -> List[Recommendation]:
    """Computes deterministic recommendations based on historical memory and patterns."""
    recommendations: List[Recommendation] = []

    # Helper to generate unique recommendation IDs
    def _make_rec_id(sig: str) -> str:
        return hashlib.sha256(sig.encode("utf-8")).hexdigest()[:16]

    # 1. Suggested Workflow recommendations
    # Look at successful historical workflow types/intents
    intent_success = {}
    intent_total = {}
    for run in history:
        intent_total[run.intent] = intent_total.get(run.intent, 0) + 1
        if run.success:
            intent_success[run.intent] = intent_success.get(run.intent, 0) + 1

    for intent, total in intent_total.items():
        success_rate = intent_success.get(intent, 0) / total
        if success_rate >= 0.8:
            sig = f"workflow:{intent}"
            recommendations.append(
                Recommendation(
                    recommendation_id=_make_rec_id(sig),
                    type="suggested_workflow",
                    title=f"Leverage '{intent}' workflow",
                    description=(
                        f"This workflow has an established historical success rate of "
                        f"{success_rate * 100:.0f}% on this repository across {total} runs."
                    ),
                    confidence=success_rate,
                    details={"intent": intent, "runs": total, "success_rate": success_rate},
                )
            )

    # 2. Hotspots & Affected Files recommendation
    # Suggest focusing on files that appear repeatedly in patterns or hotspots
    hotspots = [p for p in patterns if p.category == "repeated_hotspot"]
    if hotspots:
        top_hotspots = hotspots[:3]
        hotspot_paths = [h.key_signature.replace("hotspot:", "") for h in top_hotspots]
        sig = f"hotspots:{','.join(hotspot_paths)}"
        recommendations.append(
            Recommendation(
                recommendation_id=_make_rec_id(sig),
                type="likely_affected_files",
                title="Audit Hotspot Files",
                description=(
                    f"Prioritize architectural reviews on frequently modified hotspot files: "
                    f"{', '.join(hotspot_paths)}."
                ),
                confidence=0.85,
                details={"files": hotspot_paths, "frequency": [h.frequency for h in top_hotspots]},
            )
        )

    # 3. Bug Risk / Common Failure Location recommendation
    failed_runs = [run for run in history if not run.success]
    failed_files = {}
    for run in failed_runs:
        for step in run.execution_plan.get("steps", []):
            for fp in step.get("files", []):
                failed_files[fp] = failed_files.get(fp, 0) + 1

    if failed_files:
        top_failed = sorted(failed_files.items(), key=lambda x: x[1], reverse=True)[:3]
        failed_paths = [f[0] for f in top_failed]
        sig = f"failure_risk:{','.join(failed_paths)}"
        recommendations.append(
            Recommendation(
                recommendation_id=_make_rec_id(sig),
                type="common_failure_locations",
                title="High Risk Modification Paths",
                description=(
                    f"Modification of the following files has repeatedly triggered workflow failures "
                    f"in previous runs: {', '.join(failed_paths)}."
                ),
                confidence=0.9,
                details={"files": failed_paths, "failure_counts": [f[1] for f in top_failed]},
            )
        )

    # 4. Dependency Risk recommendation
    dep_issues = [p for p in patterns if p.category == "repeated_dependency_problem"]
    if dep_issues:
        sig = f"dependency_issues:{len(dep_issues)}"
        recommendations.append(
            Recommendation(
                recommendation_id=_make_rec_id(sig),
                type="repeated_dependency_issues",
                title="Resolve Outdated Dependencies",
                description=(
                    f"Identified {len(dep_issues)} recurring dependency problems. "
                    f"Execute a dependency audit workflow to resolve version conflicts."
                ),
                confidence=0.8,
                details={"issues_count": len(dep_issues)},
            )
        )

    return recommendations
