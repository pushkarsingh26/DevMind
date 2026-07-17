"""Knowledge Graph builder.

Builds the repository knowledge graph in 7 ordered stages:

Stage 1  — File nodes      (from file_tree)
Stage 2  — Module nodes    (from modules)
Stage 3  — Symbol nodes    (from symbols)
Stage 4  — Dependency nodes (from dependencies)
Stage 5  — Entry-point nodes (from statistics.entry_points)
Stage 6  — Relationships   (edges — only after ALL nodes exist)
Stage 7  — Validation      (via graph_storage.validate_and_clean)

Consumes only IntelligenceManager.  Does NOT read JSON files directly.

Design rule
-----------
Edges are never created before all nodes exist.  This guarantees that the
``add_edge`` guard in KnowledgeGraph (which silently drops edges whose
endpoints are missing) never discards a legitimate edge.
"""

from __future__ import annotations

import time
from pathlib import PurePosixPath
from typing import Any, Dict, List, Optional, Set

from app.core.logger import logger
from app.services.knowledge_graph.graph_models import (
    EdgeRelation,
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    NodeType,
)
from app.services.knowledge_graph.graph_storage import validate_and_clean

# ---------------------------------------------------------------------------
# ID helpers — deterministic, human-readable
# ---------------------------------------------------------------------------

def _file_id(path: str) -> str:
    return f"file:{path}"


def _module_id(path: str) -> str:
    return f"module:{path}"


def _symbol_id(symbol_dict: Dict[str, Any]) -> str:
    """Reuse the intelligence symbol id if present, otherwise derive one."""
    if "id" in symbol_dict:
        return f"sym:{symbol_dict['id']}"
    lang = symbol_dict.get("language", "?")
    path = symbol_dict.get("file_path") or symbol_dict.get("file") or symbol_dict.get("module") or "?"
    name = symbol_dict.get("name", "?")
    typ  = symbol_dict.get("type", "?")
    return f"sym:{lang}:{path}:{name}:{typ}"


def _dep_id(name: str, ecosystem: str) -> str:
    return f"dep:{ecosystem}:{name}"


def _entry_id(path: str) -> str:
    return f"entry:{path}"


# ---------------------------------------------------------------------------
# GraphBuilder
# ---------------------------------------------------------------------------

class GraphBuilder:
    """Builds a KnowledgeGraph from IntelligenceManager data.

    Usage::

        graph = GraphBuilder().build(
            intelligence_data=intelligence_manager.get(repo_id),
            repo_id="my_repo",
            repo_hash="abc123",
        )
    """

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def build(
        self,
        intelligence_data: Dict[str, Any],
        repo_id: str,
        repo_hash: str,
    ) -> KnowledgeGraph:
        """Run all 7 build stages and return the graph.

        Parameters
        ----------
        intelligence_data:
            Full dict returned by ``intelligence_manager.get(repo_id)``.
            Keys: file_tree, modules, symbols, imports, dependencies,
                  statistics, manifest, errors, call_graph.
        repo_id:
            Repository identifier (stored on graph for cache validation).
        repo_hash:
            Repository content hash (stored on graph for cache validation).
        """
        start_ms = int(time.time() * 1000)
        graph = KnowledgeGraph(repository_id=repo_id, repository_hash=repo_hash)

        file_tree    = intelligence_data.get("file_tree", [])
        modules      = intelligence_data.get("modules", [])
        symbols      = intelligence_data.get("symbols", [])
        imports      = intelligence_data.get("imports", [])
        dependencies = intelligence_data.get("dependencies", [])
        statistics   = intelligence_data.get("statistics", {})

        logger.info(f"[GraphBuilder] Starting 7-stage build for {repo_id}")

        # Stages 1–5: nodes
        self._stage1_file_nodes(graph, file_tree)
        self._stage2_module_nodes(graph, modules)
        self._stage3_symbol_nodes(graph, symbols)
        self._stage4_dependency_nodes(graph, dependencies)
        self._stage5_entry_point_nodes(graph, statistics)

        # Stage 6: relationships (edges) — all nodes exist now
        self._stage6_relationships(graph, file_tree, modules, symbols, imports, dependencies, statistics)

        # Stage 7: validation
        summary = validate_and_clean(graph)

        elapsed = int(time.time() * 1000) - start_ms
        logger.info(
            f"[GraphBuilder] Build complete for {repo_id} in {elapsed}ms — "
            f"{len(graph.nodes)} nodes, {len(graph.edges)} edges | "
            f"cleaned: {summary}"
        )
        return graph

    # ------------------------------------------------------------------
    # Stage 1 — File nodes
    # ------------------------------------------------------------------

    def _stage1_file_nodes(
        self, graph: KnowledgeGraph, file_tree: List[Dict[str, Any]]
    ) -> None:
        for f in file_tree:
            path = f.get("path", "")
            if not path:
                continue
            node = GraphNode(
                id=_file_id(path),
                type=NodeType.FILE,
                name=PurePosixPath(path).name,
                file=path,
                language=f.get("language"),
                metadata={
                    "size_bytes": f.get("size_bytes", 0),
                    "sha256": f.get("sha256", ""),
                    "last_modified": f.get("last_modified", 0),
                    "extension": f.get("extension", ""),
                },
            )
            graph.add_node(node)

    # ------------------------------------------------------------------
    # Stage 2 — Module nodes
    # ------------------------------------------------------------------

    def _stage2_module_nodes(
        self, graph: KnowledgeGraph, modules: List[Dict[str, Any]]
    ) -> None:
        for m in modules:
            path = m.get("path", "")
            if not path:
                continue
            node = GraphNode(
                id=_module_id(path),
                type=NodeType.MODULE,
                name=PurePosixPath(path).name,
                file=path,
                language=m.get("language"),
                metadata={
                    "symbol_count": m.get("symbol_count", 0),
                    "import_count": m.get("import_count", 0),
                },
            )
            graph.add_node(node)

    # ------------------------------------------------------------------
    # Stage 3 — Symbol nodes
    # ------------------------------------------------------------------

    def _stage3_symbol_nodes(
        self, graph: KnowledgeGraph, symbols: List[Dict[str, Any]]
    ) -> None:
        for s in symbols:
            node = GraphNode(
                id=_symbol_id(s),
                type=NodeType.SYMBOL,
                name=s.get("name", ""),
                file=s.get("file_path") or s.get("file") or s.get("module"),
                language=s.get("language"),
                line=s.get("line_start", 0),
                visibility=s.get("visibility", "unknown"),
                metadata={
                    "symbol_type": s.get("type", ""),
                    "line_end": s.get("line_end", s.get("line_start", 0)),
                    "id_hash": s.get("id_hash", ""),
                    "original_id": s.get("id", ""),
                },
            )
            graph.add_node(node)

    # ------------------------------------------------------------------
    # Stage 4 — Dependency nodes
    # ------------------------------------------------------------------

    def _stage4_dependency_nodes(
        self, graph: KnowledgeGraph, dependencies: List[Dict[str, Any]]
    ) -> None:
        seen: Set[str] = set()
        for d in dependencies:
            name = d.get("name", "")
            ecosystem = d.get("ecosystem", "unknown")
            if not name:
                continue
            dep_id = _dep_id(name, ecosystem)
            if dep_id in seen:
                continue
            seen.add(dep_id)
            node = GraphNode(
                id=dep_id,
                type=NodeType.DEPENDENCY,
                name=name,
                language=ecosystem,
                metadata={
                    "version": d.get("version", ""),
                    "ecosystem": ecosystem,
                    "source_file": d.get("source_file", ""),
                },
            )
            graph.add_node(node)

    # ------------------------------------------------------------------
    # Stage 5 — Entry-point nodes
    # ------------------------------------------------------------------

    def _stage5_entry_point_nodes(
        self, graph: KnowledgeGraph, statistics: Dict[str, Any]
    ) -> None:
        entry_points: List[str] = statistics.get("entry_points", [])
        for path in entry_points:
            if not path:
                continue
            node = GraphNode(
                id=_entry_id(path),
                type=NodeType.ENTRY_POINT,
                name=PurePosixPath(path).name,
                file=path,
                metadata={"source": "statistics.entry_points"},
            )
            graph.add_node(node)

    # ------------------------------------------------------------------
    # Stage 6 — Relationships (edges)
    # ------------------------------------------------------------------

    def _stage6_relationships(
        self,
        graph: KnowledgeGraph,
        file_tree: List[Dict[str, Any]],
        modules: List[Dict[str, Any]],
        symbols: List[Dict[str, Any]],
        imports: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]],
        statistics: Dict[str, Any],
    ) -> None:
        self._add_file_contains_module(graph, modules)
        self._add_module_defines_symbol(graph, symbols)
        self._add_file_contains_symbol(graph, symbols)
        self._add_file_depends_on_dep(graph, dependencies)
        self._add_module_imports_module(graph, imports, modules)
        self._add_entry_to_module(graph, statistics)
        self._add_symbol_inherits(graph, symbols)

    def _add_file_contains_module(
        self, graph: KnowledgeGraph, modules: List[Dict[str, Any]]
    ) -> None:
        for m in modules:
            path = m.get("path", "")
            if not path:
                continue
            graph.add_edge(GraphEdge(
                source=_file_id(path),
                target=_module_id(path),
                relationship=EdgeRelation.CONTAINS,
                confidence=1.0,
            ))

    def _add_module_defines_symbol(
        self, graph: KnowledgeGraph, symbols: List[Dict[str, Any]]
    ) -> None:
        for s in symbols:
            file_path = s.get("file_path") or s.get("file") or s.get("module") or ""
            if not file_path:
                continue
            graph.add_edge(GraphEdge(
                source=_module_id(file_path),
                target=_symbol_id(s),
                relationship=EdgeRelation.DEFINES,
                confidence=1.0,
            ))

    def _add_file_contains_symbol(
        self, graph: KnowledgeGraph, symbols: List[Dict[str, Any]]
    ) -> None:
        for s in symbols:
            file_path = s.get("file_path") or s.get("file") or s.get("module") or ""
            if not file_path:
                continue
            graph.add_edge(GraphEdge(
                source=_file_id(file_path),
                target=_symbol_id(s),
                relationship=EdgeRelation.CONTAINS,
                confidence=1.0,
            ))

    def _add_file_depends_on_dep(
        self, graph: KnowledgeGraph, dependencies: List[Dict[str, Any]]
    ) -> None:
        seen: Set[tuple] = set()
        for d in dependencies:
            name = d.get("name", "")
            ecosystem = d.get("ecosystem", "unknown")
            source_file = d.get("source_file", "")
            if not name or not source_file:
                continue
            key = (source_file, name, ecosystem)
            if key in seen:
                continue
            seen.add(key)
            graph.add_edge(GraphEdge(
                source=_file_id(source_file),
                target=_dep_id(name, ecosystem),
                relationship=EdgeRelation.DEPENDS_ON,
                confidence=1.0,
                metadata={"version": d.get("version", "")},
            ))

    def _add_module_imports_module(
        self,
        graph: KnowledgeGraph,
        imports: List[Dict[str, Any]],
        modules: List[Dict[str, Any]],
    ) -> None:
        """Add module → module edges for local imports."""
        # Build a set of known module paths for fast lookup
        module_paths: Set[str] = {m.get("path", "") for m in modules if m.get("path")}

        seen: Set[tuple] = set()
        for imp in imports:
            source_file = imp.get("file", "")
            module_raw  = imp.get("module", "")
            if not source_file or not module_raw:
                continue

            # Only wire local imports (relative paths starting with . or matching known modules)
            target_path: Optional[str] = None
            if module_raw.startswith("."):
                # Resolve relative import against source file directory
                parent = "/".join(source_file.split("/")[:-1])
                candidate = (parent + "/" + module_raw.lstrip("./")).rstrip("/")
                # Try common extensions
                for ext in ("", ".py", ".ts", ".js", ".tsx", ".jsx", ".go", ".rs"):
                    full = candidate + ext
                    if full in module_paths:
                        target_path = full
                        break
            else:
                # Non-relative: check if it matches a known module path basename
                for mp in module_paths:
                    if mp.endswith("/" + module_raw) or mp == module_raw:
                        target_path = mp
                        break

            if target_path:
                key = (source_file, target_path)
                if key not in seen:
                    seen.add(key)
                    graph.add_edge(GraphEdge(
                        source=_module_id(source_file),
                        target=_module_id(target_path),
                        relationship=EdgeRelation.MODULE_IMPORTS,
                        confidence=0.85,
                    ))

    def _add_entry_to_module(
        self, graph: KnowledgeGraph, statistics: Dict[str, Any]
    ) -> None:
        for path in statistics.get("entry_points", []):
            if not path:
                continue
            graph.add_edge(GraphEdge(
                source=_entry_id(path),
                target=_module_id(path),
                relationship=EdgeRelation.ENTRY_TO,
                confidence=1.0,
            ))

    def _add_symbol_inherits(
        self, graph: KnowledgeGraph, symbols: List[Dict[str, Any]]
    ) -> None:
        """Build a name→symbol-id lookup, then add INHERITS edges where
        a class has known base classes that are also in the graph."""
        name_to_ids: Dict[str, List[str]] = {}
        for s in symbols:
            name = s.get("name", "")
            if name:
                name_to_ids.setdefault(name, []).append(_symbol_id(s))

        for s in symbols:
            bases: List[str] = s.get("metadata", {}).get("bases", [])
            src_id = _symbol_id(s)
            for base in bases:
                for target_id in name_to_ids.get(base, []):
                    if src_id != target_id:
                        graph.add_edge(GraphEdge(
                            source=src_id,
                            target=target_id,
                            relationship=EdgeRelation.INHERITS,
                            confidence=0.90,
                        ))


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

graph_builder = GraphBuilder()
