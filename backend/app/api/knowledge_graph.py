"""REST API for the Knowledge Graph.

All endpoints are under /api/graph/.

Endpoints
---------
GET  /api/graph/{repo_id}/status          — graph build status + metadata
POST /api/graph/{repo_id}/build           — trigger (re)build
GET  /api/graph/{repo_id}/stats           — graph statistics
GET  /api/graph/{repo_id}/symbol/{name}   — find symbols by exact name
GET  /api/graph/{repo_id}/search          — search all nodes by substring
GET  /api/graph/{repo_id}/file            — file node lookup
GET  /api/graph/{repo_id}/module          — module node lookup
GET  /api/graph/{repo_id}/dependencies    — all dependency nodes
GET  /api/graph/{repo_id}/imports         — imports for a file
GET  /api/graph/{repo_id}/neighbors/{node_id}
GET  /api/graph/{repo_id}/descendants/{node_id}
GET  /api/graph/{repo_id}/ancestors/{node_id}
GET  /api/graph/{repo_id}/callers/{node_id}
GET  /api/graph/{repo_id}/callees/{node_id}
GET  /api/graph/{repo_id}/related/{node_id}
GET  /api/graph/{repo_id}/impacted/{node_id}
GET  /api/graph/{repo_id}/path            — shortest path between two nodes
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel

from app.core.logger import logger
from app.services.knowledge_graph import graph_manager, graph_storage
from app.services.intelligence.intelligence_manager import intelligence_manager

router = APIRouter(prefix="/api/graph", tags=["Knowledge Graph"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_graph(repo_id: str) -> None:
    if not graph_manager.exists(repo_id):
        raise HTTPException(
            status_code=404,
            detail=f"Knowledge graph not found for repository '{repo_id}'. "
                   "Call POST /api/graph/{repo_id}/build first.",
        )


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------

@router.get("/{repo_id}/status", summary="Graph build status and metadata")
async def graph_status(repo_id: str) -> Dict[str, Any]:
    """Return whether the graph is cached and its metadata if available."""
    cached = graph_manager.exists(repo_id)
    stats = graph_manager.get_statistics(repo_id) if cached else {}
    return {
        "repository_id": repo_id,
        "cached": cached,
        "statistics": stats,
    }


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

class BuildResponse(BaseModel):
    status: str
    message: str
    node_count: Optional[int] = None
    edge_count: Optional[int] = None


def _do_build(repo_id: str, intelligence_path: str, repo_hash: str) -> None:
    """Background build task."""
    try:
        intel = intelligence_manager.get(repo_id)
        if not intel:
            logger.error(f"[GraphAPI] No intelligence data available for {repo_id}")
            return
        graph_manager.build(
            repo_id=repo_id,
            intelligence_data=intel,
            intelligence_path=intelligence_path,
            repo_hash=repo_hash,
        )
    except Exception as exc:
        logger.error(f"[GraphAPI] Background build failed for {repo_id}: {exc}")


@router.post("/{repo_id}/build", summary="Build or rebuild the knowledge graph")
async def build_graph(
    repo_id: str,
    background_tasks: BackgroundTasks,
    intelligence_path: str = Query(..., description="Path to intelligence artifacts directory"),
    repo_hash: str = Query("", description="Repository content hash for cache validation"),
    force: bool = Query(False, description="Force rebuild even if cached"),
) -> BuildResponse:
    """Trigger an asynchronous knowledge-graph build."""
    if not force and graph_manager.exists(repo_id):
        stats = graph_manager.get_statistics(repo_id)
        return BuildResponse(
            status="cached",
            message="Graph already cached. Use force=true to rebuild.",
            node_count=stats.get("total_nodes"),
            edge_count=stats.get("total_edges"),
        )

    background_tasks.add_task(_do_build, repo_id, intelligence_path, repo_hash)
    return BuildResponse(status="building", message="Graph build started in background.")


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

@router.get("/{repo_id}/stats", summary="Graph statistics")
async def graph_stats(repo_id: str) -> Dict[str, Any]:
    _require_graph(repo_id)
    return graph_manager.get_statistics(repo_id)


@router.get("/{repo_id}/statistics", summary="Graph statistics detailed endpoint")
async def graph_statistics(repo_id: str) -> Dict[str, Any]:
    _require_graph(repo_id)
    return graph_manager.get_statistics(repo_id)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/{repo_id}/health", summary="Graph health check")
async def graph_health(repo_id: str) -> Dict[str, Any]:
    _require_graph(repo_id)
    stats = graph_manager.get_statistics(repo_id)
    graph = graph_manager.get_graph(repo_id)
    orphan_count = 0
    self_loop_count = 0
    if graph:
        node_ids = set(graph.nodes.keys())
        for e in graph.edges:
            if e.source not in node_ids or e.target not in node_ids:
                orphan_count += 1
            if e.source == e.target:
                self_loop_count += 1
                
    health_status = "healthy"
    details = []
    if orphan_count > 0:
        health_status = "degraded"
        details.append(f"{orphan_count} orphan edges detected")
    if self_loop_count > 0:
        health_status = "degraded"
        details.append(f"{self_loop_count} self loops detected")
        
    return {
        "repository_id": repo_id,
        "status": health_status,
        "details": details,
        "node_count": stats.get("node_count", 0),
        "edge_count": stats.get("edge_count", 0),
        "isolated_nodes": stats.get("isolated_nodes", 0),
        "connected_components": stats.get("connected_components", 0),
    }


# ---------------------------------------------------------------------------
# Symbol queries
# ---------------------------------------------------------------------------

@router.get("/{repo_id}/symbol/{name}", summary="Find symbols by name")
async def get_symbol(repo_id: str, name: str) -> List[Dict[str, Any]]:
    _require_graph(repo_id)
    return graph_manager.get_symbol(repo_id, name)


@router.get("/{repo_id}/symbols", summary="Find symbols matching a regex pattern")
async def find_symbols(
    repo_id: str,
    pattern: str = Query(..., description="Regex pattern to match symbol names"),
) -> List[Dict[str, Any]]:
    _require_graph(repo_id)
    return graph_manager.find_symbols(repo_id, pattern)


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

@router.get("/{repo_id}/search", summary="Search all nodes by substring")
async def search_graph(
    repo_id: str,
    q: str = Query(..., description="Substring to search in node names"),
) -> List[Dict[str, Any]]:
    _require_graph(repo_id)
    return graph_manager.search(repo_id, q)


# ---------------------------------------------------------------------------
# File / Module / Dependency
# ---------------------------------------------------------------------------

@router.get("/{repo_id}/file", summary="File node lookup")
async def find_file(
    repo_id: str,
    path: str = Query(..., description="File path (partial or exact)"),
) -> Dict[str, Any]:
    _require_graph(repo_id)
    result = graph_manager.find_file(repo_id, path)
    if result is None:
        raise HTTPException(status_code=404, detail=f"File '{path}' not found in graph.")
    return result


@router.get("/{repo_id}/module", summary="Module node lookup")
async def find_module(
    repo_id: str,
    path: str = Query(..., description="Module path (partial or exact)"),
) -> Dict[str, Any]:
    _require_graph(repo_id)
    result = graph_manager.find_module(repo_id, path)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Module '{path}' not found in graph.")
    return result


@router.get("/{repo_id}/dependencies", summary="All dependency nodes")
async def find_dependencies(repo_id: str) -> List[Dict[str, Any]]:
    _require_graph(repo_id)
    return graph_manager.find_dependencies(repo_id)


@router.get("/{repo_id}/imports", summary="Imports for a source file")
async def find_imports(
    repo_id: str,
    file_path: str = Query(..., description="Source file path"),
) -> List[Dict[str, Any]]:
    _require_graph(repo_id)
    return graph_manager.find_imports(repo_id, file_path)


# ---------------------------------------------------------------------------
# Traversal
# ---------------------------------------------------------------------------

@router.get("/{repo_id}/neighbors/{node_id}", summary="Direct neighbors of a node")
async def neighbors(repo_id: str, node_id: str) -> List[Dict[str, Any]]:
    _require_graph(repo_id)
    return graph_manager.neighbors(repo_id, node_id)


@router.get("/{repo_id}/descendants/{node_id}", summary="BFS descendants")
async def descendants(
    repo_id: str,
    node_id: str,
    depth: int = Query(3, ge=1, le=6),
) -> List[Dict[str, Any]]:
    _require_graph(repo_id)
    return graph_manager.descendants(repo_id, node_id, depth)


@router.get("/{repo_id}/ancestors/{node_id}", summary="BFS ancestors")
async def ancestors(
    repo_id: str,
    node_id: str,
    depth: int = Query(3, ge=1, le=6),
) -> List[Dict[str, Any]]:
    _require_graph(repo_id)
    return graph_manager.ancestors(repo_id, node_id, depth)


@router.get("/{repo_id}/callers/{node_id}", summary="Find callers of a symbol")
async def find_callers(repo_id: str, node_id: str) -> List[Dict[str, Any]]:
    _require_graph(repo_id)
    return graph_manager.find_callers(repo_id, node_id)


@router.get("/{repo_id}/callees/{node_id}", summary="Find callees of a symbol")
async def find_callees(repo_id: str, node_id: str) -> List[Dict[str, Any]]:
    _require_graph(repo_id)
    return graph_manager.find_callees(repo_id, node_id)


@router.get("/{repo_id}/related/{node_id}", summary="Find related nodes within depth")
async def find_related(
    repo_id: str,
    node_id: str,
    depth: int = Query(2, ge=1, le=5),
) -> List[Dict[str, Any]]:
    _require_graph(repo_id)
    return graph_manager.find_related(repo_id, node_id, depth)


@router.get("/{repo_id}/impacted/{node_id}", summary="Files impacted by a symbol change")
async def impacted_files(repo_id: str, node_id: str) -> List[str]:
    _require_graph(repo_id)
    return graph_manager.impacted_files(repo_id, node_id)


@router.get("/{repo_id}/module-deps", summary="Transitive module dependencies")
async def module_dependencies(
    repo_id: str,
    module_path: str = Query(..., description="Module file path"),
) -> List[Dict[str, Any]]:
    _require_graph(repo_id)
    return graph_manager.module_dependencies(repo_id, module_path)


@router.get("/{repo_id}/path", summary="Shortest path between two nodes")
async def shortest_path(
    repo_id: str,
    a: str = Query(..., description="Source node ID"),
    b: str = Query(..., description="Target node ID"),
) -> List[str]:
    _require_graph(repo_id)
    return graph_manager.shortest_path(repo_id, a, b)
