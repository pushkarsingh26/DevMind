"""Knowledge Graph data models.

Plain Python dataclasses — no Pydantic dependency — so the knowledge graph
layer remains independent from the web framework.

All version constants are imported from ``versions.py`` rather than defined
here, keeping this file focused on data structures only.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from app.services.knowledge_graph.versions import (
    GRAPH_VERSION,
    VALID_NODE_TYPES,
    VALID_EDGE_RELATIONS,
    SELF_LOOP_ALLOWED,
)

# ---------------------------------------------------------------------------
# Node types  (string constants — remain JSON-serializable without conversion)
# ---------------------------------------------------------------------------

class NodeType:
    FILE        = "file"
    MODULE      = "module"
    SYMBOL      = "symbol"
    DEPENDENCY  = "dependency"
    ENTRY_POINT = "entry_point"

    ALL = VALID_NODE_TYPES


# ---------------------------------------------------------------------------
# Edge relationships
# ---------------------------------------------------------------------------

class EdgeRelation:
    CONTAINS       = "contains"       # file → symbol
    DEFINES        = "defines"        # module → symbol
    IMPORTS        = "imports"        # file/symbol → dependency or module
    DEPENDS_ON     = "depends_on"     # file → external dependency
    INHERITS       = "inherits"       # symbol → symbol
    IMPLEMENTS     = "implements"     # symbol → symbol
    USES           = "uses"           # symbol → symbol (generic)
    MODULE_IMPORTS = "module_imports" # module → module
    ENTRY_TO       = "entry_to"       # entry_point → module

    ALL = VALID_EDGE_RELATIONS


# ---------------------------------------------------------------------------
# GraphNode
# ---------------------------------------------------------------------------

@dataclass
class GraphNode:
    """A node in the knowledge graph."""

    id: str                         # deterministic unique ID
    type: str                       # NodeType constant
    name: str
    file: Optional[str] = None      # relative file path
    language: Optional[str] = None
    line: int = 0
    visibility: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GraphNode":
        return cls(
            id=d["id"],
            type=d["type"],
            name=d["name"],
            file=d.get("file"),
            language=d.get("language"),
            line=d.get("line", 0),
            visibility=d.get("visibility", "unknown"),
            metadata=d.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# GraphEdge
# ---------------------------------------------------------------------------

@dataclass
class GraphEdge:
    """A directed edge in the knowledge graph."""

    source: str                     # source node ID
    target: str                     # target node ID
    relationship: str               # EdgeRelation constant
    confidence: float = 1.0         # 0.0–1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "GraphEdge":
        return cls(
            source=d["source"],
            target=d["target"],
            relationship=d["relationship"],
            confidence=d.get("confidence", 1.0),
            metadata=d.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# KnowledgeGraph  (in-memory structure)
# ---------------------------------------------------------------------------

@dataclass
class KnowledgeGraph:
    """Complete in-memory knowledge graph for a repository.

    Internal structure
    ------------------
    nodes   : Dict[node_id, GraphNode]
    edges   : List[GraphEdge]
    _adj    : Dict[node_id, Dict[relationship, List[node_id]]]  outgoing
    _radj   : Dict[node_id, Dict[relationship, List[node_id]]]  incoming
    """

    repository_id: str
    repository_hash: str
    graph_version: str = GRAPH_VERSION

    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    edges: List[GraphEdge] = field(default_factory=list)

    # Adjacency indices — built by add_edge(), NOT persisted to JSON
    _adj:  Dict[str, Dict[str, List[str]]] = field(default_factory=dict, repr=False)
    _radj: Dict[str, Dict[str, List[str]]] = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------------
    # Mutation helpers
    # ------------------------------------------------------------------

    def add_node(self, node: GraphNode) -> None:
        """Add a node; silently skip exact duplicate IDs."""
        if node.id not in self.nodes:
            self.nodes[node.id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        """Add a directed edge and update adjacency indexes.

        Guards:
        - Source and target must already be in ``nodes``
        - Self-loops are dropped unless the relationship is in SELF_LOOP_ALLOWED
        """
        if edge.source not in self.nodes or edge.target not in self.nodes:
            return
        if edge.source == edge.target and edge.relationship not in SELF_LOOP_ALLOWED:
            return

        self.edges.append(edge)

        # Forward adjacency
        self._adj.setdefault(edge.source, {}).setdefault(edge.relationship, [])
        if edge.target not in self._adj[edge.source][edge.relationship]:
            self._adj[edge.source][edge.relationship].append(edge.target)

        # Reverse adjacency
        self._radj.setdefault(edge.target, {}).setdefault(edge.relationship, [])
        if edge.source not in self._radj[edge.target][edge.relationship]:
            self._radj[edge.target][edge.relationship].append(edge.source)

    # ------------------------------------------------------------------
    # Rebuild adjacency from edge list (used after deserialization)
    # ------------------------------------------------------------------

    def rebuild_adjacency(self) -> None:
        """Re-derive ``_adj`` and ``_radj`` from ``self.edges``.

        Call this after deserializing a KnowledgeGraph from JSON.
        """
        self._adj = {}
        self._radj = {}
        for edge in self.edges:
            if edge.source not in self.nodes or edge.target not in self.nodes:
                continue
            self._adj.setdefault(edge.source, {}).setdefault(edge.relationship, [])
            if edge.target not in self._adj[edge.source][edge.relationship]:
                self._adj[edge.source][edge.relationship].append(edge.target)
            self._radj.setdefault(edge.target, {}).setdefault(edge.relationship, [])
            if edge.source not in self._radj[edge.target][edge.relationship]:
                self._radj[edge.target][edge.relationship].append(edge.source)

    # ------------------------------------------------------------------
    # Adjacency accessors
    # ------------------------------------------------------------------

    def successors(self, node_id: str, rel: Optional[str] = None) -> List[str]:
        """Return outgoing neighbor IDs, optionally filtered by relationship."""
        adj = self._adj.get(node_id, {})
        if rel is not None:
            return list(adj.get(rel, []))
        return [nid for ids in adj.values() for nid in ids]

    def predecessors(self, node_id: str, rel: Optional[str] = None) -> List[str]:
        """Return incoming neighbor IDs, optionally filtered by relationship."""
        radj = self._radj.get(node_id, {})
        if rel is not None:
            return list(radj.get(rel, []))
        return [nid for ids in radj.values() for nid in ids]

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        type_counts: Dict[str, int] = {}
        for n in self.nodes.values():
            type_counts[n.type] = type_counts.get(n.type, 0) + 1

        rel_counts: Dict[str, int] = {}
        for e in self.edges:
            rel_counts[e.relationship] = rel_counts.get(e.relationship, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": type_counts,
            "edge_relationships": rel_counts,
        }
