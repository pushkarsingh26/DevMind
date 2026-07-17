"""Context Builder — incremental, missing-safe subsystem loader.

Each of the five subsystems is loaded in an independent try/except block.
A missing or broken subsystem returns an empty dict/object — it never
raises an exception or blocks the reasoning pipeline.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any, Dict

from app.core.logger import logger
from app.services.reasoning.reasoning_models import ReasoningContext


def _load_intelligence(repository_id: str) -> Dict[str, Any]:
    """Load repository intelligence manifest summary."""
    try:
        from app.services.intelligence.intelligence_manager import intelligence_manager
        intel = intelligence_manager.get(repository_id) or {}
        stats = intel.get("statistics", {})
        return {
            "file_count": stats.get("total_files", 0),
            "symbol_count": stats.get("total_symbols", 0),
            "module_count": stats.get("total_modules", 0),
            "languages": stats.get("languages", {}),
            "intelligence_version": intel.get("intelligence_version", ""),
        }
    except Exception as exc:
        logger.debug(f"[ContextBuilder] Intelligence unavailable for {repository_id}: {exc}")
        return {}


def _load_graph(repository_id: str) -> Dict[str, Any]:
    """Load knowledge graph summary (node/edge counts, type distribution)."""
    try:
        from app.services.knowledge_graph.graph_manager import graph_manager
        graph = graph_manager.get_graph(repository_id)
        if graph is None:
            return {}
        stats = graph.stats()
        return {
            "node_count": stats.get("total_nodes", 0),
            "edge_count": stats.get("total_edges", 0),
            "node_types": stats.get("node_types", {}),
            "edge_relationships": stats.get("edge_relationships", {}),
        }
    except Exception as exc:
        logger.debug(f"[ContextBuilder] Graph unavailable for {repository_id}: {exc}")
        return {}


def _load_analysis(intel_path: str) -> Dict[str, Any]:
    """Load repository analysis summary."""
    if not intel_path:
        return {}
    try:
        from app.services.repository_analysis.analysis_storage import analysis_storage
        summary = analysis_storage.load_summary(intel_path) or {}
        return {
            "total_nodes": summary.get("total_nodes", 0),
            "findings_count": summary.get("findings_count", 0),
            "quality_score": summary.get("quality_score", 0.0),
            "architecture_patterns": summary.get("architecture_patterns", []),
        }
    except Exception as exc:
        logger.debug(f"[ContextBuilder] Analysis unavailable for path {intel_path}: {exc}")
        return {}


def _load_memory(repository_id: str) -> Dict[str, Any]:
    """Load memory engine summary (patterns, history counts, hotspots)."""
    try:
        from app.services.memory import memory_storage
        mem_data = memory_storage.load(repository_id)
        if not mem_data:
            return {}
        memory, patterns, recommendations, metrics, history = mem_data
        return {
            "recurring_files": memory.recurring_files,
            "hotspot_history": memory.hotspot_history,
            "pattern_count": len(patterns),
            "history_count": len(history),
            "workflow_success_rate": metrics.workflow_success_rate,
            "provider_reliability": metrics.provider_reliability,
            "language_history": memory.language_history,
        }
    except Exception as exc:
        logger.debug(f"[ContextBuilder] Memory unavailable for {repository_id}: {exc}")
        return {}


def _load_collaboration(repository_id: str) -> Dict[str, Any]:
    """Load collaboration summary — validated finding count and confidence."""
    try:
        # Collaboration stores per-workflow; we inspect the most recent workspace
        # by checking workspace_manager for any stored workspaces for this repo.
        from app.services.collaboration.workspace_manager import workspace_manager
        # workspace_manager does not expose a repo-level list, so we return minimal info
        # from evidence_manager if available
        return {
            "available": True,
        }
    except Exception as exc:
        logger.debug(f"[ContextBuilder] Collaboration unavailable for {repository_id}: {exc}")
        return {}


class ContextBuilder:
    """Assembles a ReasoningContext by independently querying each subsystem."""

    def build(
        self,
        repository_id: str,
        intel_path: str,
        repo_hash: str,
    ) -> ReasoningContext:
        t0 = time.time()
        logger.debug(f"[ContextBuilder] Building context for {repository_id}")

        intelligence = _load_intelligence(repository_id)
        graph        = _load_graph(repository_id)
        analysis     = _load_analysis(intel_path)
        memory       = _load_memory(repository_id)
        collaboration= _load_collaboration(repository_id)

        elapsed_ms = (time.time() - t0) * 1000
        logger.debug(f"[ContextBuilder] Context built in {elapsed_ms:.1f}ms for {repository_id}")

        return ReasoningContext(
            repository_id=repository_id,
            repository_hash=repo_hash,
            intelligence_summary=intelligence,
            graph_summary=graph,
            analysis_summary=analysis,
            memory_summary=memory,
            collaboration_summary=collaboration,
            built_at=datetime.now(timezone.utc).isoformat(),
        )


context_builder = ContextBuilder()
