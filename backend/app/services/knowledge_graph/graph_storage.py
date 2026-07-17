"""Knowledge Graph storage — serialize, deserialize, validate, and reuse.

Responsibilities
----------------
- Write validated KnowledgeGraph to ``knowledge_graph.json``
- Read and deserialize from disk
- Determine whether a cached graph is still valid (3-version + hash check)
- Remove orphan edges and duplicate edges before saving
- Never persist an invalid graph

This is the ONLY module that reads or writes ``knowledge_graph.json``.
No other component should touch the file directly.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.logger import logger
from app.services.knowledge_graph.graph_models import GraphEdge, GraphNode, KnowledgeGraph
from app.services.knowledge_graph.versions import (
    GRAPH_FILE_NAME,
    GRAPH_GENERATOR_NAME,
    GRAPH_GENERATOR_VERSION,
    GRAPH_SCHEMA_VERSION,
    GRAPH_VERSION,
    SELF_LOOP_ALLOWED,
)


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _dedup_nodes(graph: KnowledgeGraph) -> int:
    """Nodes are stored by id in a dict, so duplicates are structurally impossible.
    This function exists for completeness; it verifies and returns count."""
    return len(graph.nodes)


def _dedup_edges(edges: List[GraphEdge]) -> Tuple[List[GraphEdge], int]:
    """Remove duplicate edges (same source, target, relationship).

    Returns (deduplicated list, number of duplicates removed).
    """
    seen: set = set()
    result: List[GraphEdge] = []
    removed = 0
    for edge in edges:
        key = (edge.source, edge.target, edge.relationship)
        if key in seen:
            removed += 1
        else:
            seen.add(key)
            result.append(edge)
    return result, removed


def _remove_orphan_edges(
    edges: List[GraphEdge], node_ids: set
) -> Tuple[List[GraphEdge], int]:
    """Remove edges whose source or target is not in the node set.

    Returns (clean list, number of orphans removed).
    """
    result: List[GraphEdge] = []
    removed = 0
    for edge in edges:
        if edge.source in node_ids and edge.target in node_ids:
            result.append(edge)
        else:
            removed += 1
    return result, removed


def _remove_self_loops(
    edges: List[GraphEdge],
) -> Tuple[List[GraphEdge], int]:
    """Remove self-loop edges that are not explicitly allowed.

    Returns (clean list, number removed).
    """
    result: List[GraphEdge] = []
    removed = 0
    for edge in edges:
        if edge.source == edge.target and edge.relationship not in SELF_LOOP_ALLOWED:
            removed += 1
        else:
            result.append(edge)
    return result, removed


def validate_and_clean(graph: KnowledgeGraph) -> Dict[str, Any]:
    """Run all validation passes on the graph in-place.

    Passes (order matters):
    1. Self-loop removal
    2. Orphan edge removal
    3. Duplicate edge removal

    Returns a summary dict describing what was cleaned.
    """
    node_ids = set(graph.nodes.keys())

    # Pass 1: self-loops
    clean1, self_loops = _remove_self_loops(graph.edges)
    # Pass 2: orphan edges
    clean2, orphans = _remove_orphan_edges(clean1, node_ids)
    # Pass 3: duplicate edges
    clean3, duplicates = _dedup_edges(clean2)

    graph.edges = clean3
    # Rebuild adjacency after cleaning
    graph.rebuild_adjacency()

    summary = {
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "self_loops_removed": self_loops,
        "orphan_edges_removed": orphans,
        "duplicate_edges_removed": duplicates,
        "is_valid": True,
    }
    if self_loops or orphans or duplicates:
        logger.info(
            f"[GraphStorage] Graph cleaned: "
            f"self_loops={self_loops} orphans={orphans} duplicates={duplicates}"
        )
    return summary


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def _build_metadata(
    graph: KnowledgeGraph,
    build_time_ms: int,
    validation_summary: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "graph_version": GRAPH_VERSION,
        "schema_version": GRAPH_SCHEMA_VERSION,
        "generator_version": GRAPH_GENERATOR_VERSION,
        "generator": GRAPH_GENERATOR_NAME,
        "repository_id": graph.repository_id,
        "repository_hash": graph.repository_hash,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "build_time_ms": build_time_ms,
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "node_types": graph.stats().get("node_types", {}),
        "edge_relationships": graph.stats().get("edge_relationships", {}),
        "validation": validation_summary,
    }


def save(
    graph: KnowledgeGraph,
    intelligence_path: str,
    build_time_ms: int = 0,
) -> str:
    """Validate, clean, then persist *graph* to ``knowledge_graph.json``.

    Parameters
    ----------
    graph:
        The fully-built KnowledgeGraph (will be cleaned in-place before saving).
    intelligence_path:
        Directory where intelligence artifacts live; graph file is written here.
    build_time_ms:
        Build duration to embed in metadata.

    Returns
    -------
    Absolute path string of the written file.
    """
    validation_summary = validate_and_clean(graph)

    metadata = _build_metadata(graph, build_time_ms, validation_summary)

    payload: Dict[str, Any] = {
        "metadata": metadata,
        "nodes": [n.to_dict() for n in graph.nodes.values()],
        "edges": [e.to_dict() for e in graph.edges],
    }

    out_path = Path(intelligence_path) / GRAPH_FILE_NAME
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)

    logger.info(
        f"[GraphStorage] Saved knowledge_graph.json "
        f"({metadata['node_count']} nodes, {metadata['edge_count']} edges) "
        f"to {out_path}"
    )
    return str(out_path)


# ---------------------------------------------------------------------------
# Deserialization
# ---------------------------------------------------------------------------

def load(intelligence_path: str) -> Optional[KnowledgeGraph]:
    """Load and deserialize a knowledge graph from disk.

    Returns ``None`` if the file is missing or corrupted.
    """
    path = Path(intelligence_path) / GRAPH_FILE_NAME
    if not path.is_file():
        return None

    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)

        meta = payload.get("metadata", {})
        repo_id   = meta.get("repository_id", "")
        repo_hash = meta.get("repository_hash", "")

        graph = KnowledgeGraph(
            repository_id=repo_id,
            repository_hash=repo_hash,
            graph_version=meta.get("graph_version", ""),
        )

        for node_dict in payload.get("nodes", []):
            graph.nodes[node_dict["id"]] = GraphNode.from_dict(node_dict)

        for edge_dict in payload.get("edges", []):
            graph.edges.append(GraphEdge.from_dict(edge_dict))

        # Rebuild adjacency after loading all nodes and edges
        graph.rebuild_adjacency()

        logger.info(
            f"[GraphStorage] Loaded knowledge_graph.json: "
            f"{len(graph.nodes)} nodes, {len(graph.edges)} edges"
        )
        return graph

    except Exception as exc:
        logger.error(f"[GraphStorage] Failed to load knowledge_graph.json: {exc}")
        return None


# ---------------------------------------------------------------------------
# Cache validity check
# ---------------------------------------------------------------------------

def is_valid_cache(
    intelligence_path: str,
    repo_hash: Optional[str],
) -> bool:
    """Return True if the persisted graph is still valid.

    Validity requires ALL of:
    1. ``knowledge_graph.json`` exists
    2. ``graph_version`` matches GRAPH_VERSION
    3. ``schema_version`` matches GRAPH_SCHEMA_VERSION
    4. ``generator_version`` matches GRAPH_GENERATOR_VERSION
    5. ``repository_hash`` matches *repo_hash* (when provided)
    """
    path = Path(intelligence_path) / GRAPH_FILE_NAME
    if not path.is_file():
        return False
    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        meta = payload.get("metadata", {})
        if meta.get("graph_version") != GRAPH_VERSION:
            return False
        if meta.get("schema_version") != GRAPH_SCHEMA_VERSION:
            return False
        if meta.get("generator_version") != GRAPH_GENERATOR_VERSION:
            return False
        if repo_hash and meta.get("repository_hash") != repo_hash:
            return False
        return True
    except Exception:
        return False


def read_metadata(intelligence_path: str) -> Dict[str, Any]:
    """Read only the metadata block from ``knowledge_graph.json`` without loading nodes/edges."""
    path = Path(intelligence_path) / GRAPH_FILE_NAME
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as fh:
            payload = json.load(fh)
        return payload.get("metadata", {})
    except Exception:
        return {}
