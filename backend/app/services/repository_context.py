"""Unified Repository Context.

Bundles repository intelligence, knowledge graph, repository memory,
and statistics into a single structure to simplify data flows in workflow stages.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.core.logger import logger
from app.services.intelligence.intelligence_manager import intelligence_manager
from app.services.knowledge_graph.graph_manager import graph_manager
from app.services.knowledge_graph.graph_models import KnowledgeGraph


@dataclass
class RepositoryContext:
    """Unified container for all repository-specific structural data."""

    repository_id: str
    repository_hash: str
    intelligence: Dict[str, Any]
    graph: Optional[KnowledgeGraph]
    statistics: Dict[str, Any]
    memory: Dict[str, Any]


def get_repository_context(
    repository_id: str,
    intelligence_path: str,
    repo_hash: str,
) -> RepositoryContext:
    """Factory to retrieve and assemble the unified RepositoryContext.

    Guarantees:
    - Loads or rebuilds the knowledge graph via ensure_graph.
    - Resolves intelligence data from intelligence_manager.
    - Integrates repository memory (can be populated by other vector store components).
    """
    logger.info(f"[RepositoryContext] Assembling context for repository: {repository_id}")

    # Ensure graph is cached/loaded
    graph_manager.ensure_graph(
        repo_id=repository_id,
        intelligence_path=intelligence_path,
        repo_hash=repo_hash,
    )

    # Get cached graph
    graph = graph_manager.get_graph(repository_id)

    # Fetch intelligence
    intel = intelligence_manager.get(repository_id) or {}
    stats = intel.get("statistics", {})

    # Repository memory (e.g. active workspace context or FAISS vector store stats if needed)
    memory: Dict[str, Any] = {
        "is_indexed": True,
        "intel_loaded": bool(intel),
        "graph_loaded": graph is not None,
    }

    return RepositoryContext(
        repository_id=repository_id,
        repository_hash=repo_hash,
        intelligence=intel,
        graph=graph,
        statistics=stats,
        memory=memory,
    )
