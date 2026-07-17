"""Dependency Reasoner — deterministic graph traversal.

Consumes a ReasoningContext and the cached KnowledgeGraph to produce
DependencyReasoning. All output lists are sorted before return.
An empty or missing graph always produces empty-but-valid output.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Set, Tuple

from app.core.logger import logger
from app.services.reasoning.reasoning_models import (
    DependencyReasoning,
    ReasoningChain,
    ReasoningContext,
)

_MAX_CHAIN_DEPTH = 5
_MAX_CRITICAL_FILES = 20


def _build_in_degree(nodes: Dict, edges: List) -> Dict[str, int]:
    """Compute in-degree for every node from the edge list."""
    in_degree: Dict[str, int] = {nid: 0 for nid in nodes}
    for edge in edges:
        target = edge.target if hasattr(edge, "target") else edge.get("target", "")
        if target in in_degree:
            in_degree[target] += 1
    return in_degree


def _bfs_forward(graph, start_id: str, max_depth: int) -> List[str]:
    """BFS outward from start_id. Returns visited node IDs (excl. start)."""
    visited: Set[str] = set()
    queue: deque = deque([(start_id, 0)])
    result: List[str] = []
    while queue:
        nid, depth = queue.popleft()
        if depth > max_depth or nid in visited:
            continue
        visited.add(nid)
        if nid != start_id:
            result.append(nid)
        for successor in graph.successors(nid):
            if successor not in visited:
                queue.append((successor, depth + 1))
    return result


def _bfs_reverse(graph, start_ids: List[str], max_depth: int) -> List[str]:
    """Reverse BFS from a set of start nodes. Returns all upstream dependents."""
    visited: Set[str] = set(start_ids)
    queue: deque = deque([(sid, 0) for sid in start_ids])
    result: List[str] = []
    while queue:
        nid, depth = queue.popleft()
        if depth > max_depth:
            continue
        for pred in graph.predecessors(nid):
            if pred not in visited:
                visited.add(pred)
                result.append(pred)
                queue.append((pred, depth + 1))
    return result


class DependencyReasoner:

    def reason(self, context: ReasoningContext) -> DependencyReasoning:
        logger.debug(f"[DependencyReasoner] Running for {context.repository_id}")
        try:
            from app.services.knowledge_graph.graph_manager import graph_manager
            graph = graph_manager.get_graph(context.repository_id)
        except Exception:
            graph = None

        if graph is None or not graph.nodes:
            return DependencyReasoning()

        in_degree = _build_in_degree(graph.nodes, graph.edges)

        # 1. Critical files — file nodes with highest in-degree
        file_nodes = [
            (nid, node) for nid, node in graph.nodes.items()
            if node.type == "file"
        ]
        critical_sorted = sorted(
            file_nodes,
            key=lambda x: (-in_degree.get(x[0], 0), x[0]),
        )[:_MAX_CRITICAL_FILES]
        critical_files = sorted([node.name or nid for nid, node in critical_sorted])

        # 2. Dependency chains — BFS from each critical file
        chains: List[ReasoningChain] = []
        for nid, node in critical_sorted:
            steps_raw = _bfs_forward(graph, nid, _MAX_CHAIN_DEPTH)
            # Resolve node IDs to human-readable names
            steps = sorted([
                graph.nodes[s].name or s
                for s in steps_raw
                if s in graph.nodes
            ])
            chain = ReasoningChain(
                chain_id=f"chain:{nid}",
                source=node.name or nid,
                steps=steps,
                depth=min(len(steps), _MAX_CHAIN_DEPTH),
                confidence=min(1.0, in_degree.get(nid, 0) / max(len(graph.nodes), 1) * 10),
                reasoning_type="dependency",
            )
            chains.append(chain)

        # Sort chains by chain_id
        chains = sorted(chains, key=lambda c: c.chain_id)

        # 3. Affected symbols — symbol nodes reachable from critical files
        affected_symbol_ids: Set[str] = set()
        for nid, _ in critical_sorted:
            for sid in _bfs_forward(graph, nid, _MAX_CHAIN_DEPTH):
                if sid in graph.nodes and graph.nodes[sid].type == "symbol":
                    affected_symbol_ids.add(sid)
        affected_symbols = sorted([
            graph.nodes[s].name or s
            for s in affected_symbol_ids
            if s in graph.nodes
        ])

        # 4. Architecture influence — per-module: how many modules depend on it
        module_influence: Dict[str, int] = {}
        for nid, node in graph.nodes.items():
            if node.type == "module":
                dependents = _bfs_reverse(graph, [nid], _MAX_CHAIN_DEPTH)
                module_influence[node.name or nid] = len(dependents)
        # Sort by name for determinism
        architecture_influence = {k: module_influence[k] for k in sorted(module_influence)}

        # 5. Transitive impact — reverse BFS from critical file node IDs
        critical_ids = [nid for nid, _ in critical_sorted]
        transitive_raw = _bfs_reverse(graph, critical_ids, _MAX_CHAIN_DEPTH)
        transitive_impact = sorted([
            graph.nodes[t].name or t
            for t in transitive_raw
            if t in graph.nodes
        ])

        # 6. Repository boundaries — files with external depends_on edges
        boundary_files: Set[str] = set()
        for edge in graph.edges:
            source = edge.source if hasattr(edge, "source") else edge.get("source", "")
            target = edge.target if hasattr(edge, "target") else edge.get("target", "")
            rel = edge.relationship if hasattr(edge, "relationship") else edge.get("relationship", "")
            if rel == "depends_on" and target in graph.nodes:
                target_node = graph.nodes[target]
                if target_node.type == "dependency":
                    if source in graph.nodes:
                        boundary_files.add(graph.nodes[source].name or source)
        repository_boundaries = sorted(boundary_files)

        return DependencyReasoning(
            critical_files=critical_files,
            dependency_chains=chains,
            affected_symbols=affected_symbols,
            architecture_influence=architecture_influence,
            transitive_impact=transitive_impact,
            repository_boundaries=repository_boundaries,
        )


dependency_reasoner = DependencyReasoner()
