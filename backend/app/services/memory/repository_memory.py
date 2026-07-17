"""Repository Memory Management."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List, Set

from app.services.memory.memory_models import RepositoryMemory, WorkflowMemory


def update_repository_memory(
    memory: RepositoryMemory,
    workflow: WorkflowMemory,
) -> None:
    """Updates RepositoryMemory statistics based on a completed workflow.

    Accumulates hotspot history, frequently modified files/modules,
    dependency history, architecture observations, and languages.
    """
    # 1. Accumulate hotspots from findings
    finding_files: List[str] = []
    for finding in workflow.findings:
        f_path = finding.get("file_path") or finding.get("file")
        if f_path:
            finding_files.append(str(f_path))

    # Accumulate hotspots from plan steps if files are listed
    for step in workflow.execution_plan.get("steps", []):
        for fp in step.get("files", []):
            finding_files.append(str(fp))

    # Update hotspot count
    for fp in finding_files:
        memory.hotspot_history[fp] = memory.hotspot_history.get(fp, 0) + 1

    # 2. Recalculate recurring files (files with >= 3 occurrences in hotspots/findings)
    recurring: Set[str] = set(memory.recurring_files)
    for fp, count in memory.hotspot_history.items():
        if count >= 3:
            recurring.add(fp)
    memory.recurring_files = sorted(list(recurring))

    # 3. Frequently modified modules (modules occurring multiple times in completed steps)
    modified_modules: List[str] = []
    for step in workflow.execution_plan.get("steps", []):
        agent = step.get("agent")
        if agent in ("Refactor Agent", "Write Code Agent", "Execution Agent"):
            for fp in step.get("files", []):
                modified_modules.append(str(fp))

    # Count frequencies of modified modules
    module_counter = Counter(memory.frequently_modified_modules + modified_modules)
    # Keep top 15 frequently modified modules
    memory.frequently_modified_modules = [m for m, _ in module_counter.most_common(15)]

    # 4. Dependency History (extract from plan metadata or findings)
    deps: Set[str] = set(memory.dependency_history)
    for finding in workflow.findings:
        dep_name = finding.get("metadata", {}).get("dependency_name")
        if dep_name:
            deps.add(str(dep_name))
    memory.dependency_history = sorted(list(deps))

    # 5. Architecture History (store list of workflow intents executed)
    arch_intents = set(memory.architecture_history)
    arch_intents.add(workflow.intent)
    memory.architecture_history = sorted(list(arch_intents))

    # 6. Language History (aggregate languages of unique files)
    unique_finding_files = set(finding_files)
    for fp in unique_finding_files:
        ext = fp.split(".")[-1].lower() if "." in fp else ""
        if ext in ("py", "python"):
            memory.language_history["python"] = memory.language_history.get("python", 0) + 1
        elif ext in ("ts", "tsx"):
            memory.language_history["typescript"] = memory.language_history.get("typescript", 0) + 1
        elif ext in ("js", "jsx"):
            memory.language_history["javascript"] = memory.language_history.get("javascript", 0) + 1
        elif ext in ("go",):
            memory.language_history["go"] = memory.language_history.get("go", 0) + 1
        elif ext in ("rs", "rust"):
            memory.language_history["rust"] = memory.language_history.get("rust", 0) + 1
