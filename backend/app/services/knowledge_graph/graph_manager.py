"""Repository Knowledge Graph Manager.

Architecture rule
-----------------
    WorkflowEngine
           │
           ▼
    GraphManager        ← ONLY authorised traversal entry point
           │
           ▼
    IntelligenceManager
           │
           ▼
    PromptBuilder → LLM

All graph traversal lives here.  No other component traverses the graph
structure directly.  ``GraphStorage`` is the only component that reads
or writes ``knowledge_graph.json``.

Thread-Safe Lazy Loading & Cache Eviction (LRU + TTL)
-----------------------------------------------------
- Graph instances are loaded from disk lazily upon first query.
- Memory cache stores graph and its load timestamp: ``(graph, load_timestamp)``.
- Cache capacity is capped at 16 (Least Recently Used eviction).
- TTL (Time-To-Live) is set to 30 minutes (1800 seconds).

Traversal Cache
---------------
- Traversal results (related, impacted_files, shortest_path, dependency_path)
  are cached in memory per repository.
- Traversal cache is invalidated automatically if the graph changes.
"""

from __future__ import annotations

import re
import time
import threading
from collections import deque, OrderedDict
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.logger import logger
from app.services.knowledge_graph import graph_storage
from app.services.knowledge_graph.graph_builder import graph_builder, _file_id, _module_id, _symbol_id
from app.services.knowledge_graph.graph_models import EdgeRelation, GraphNode, KnowledgeGraph, NodeType


class GraphManager:
    """Thread-safe, in-memory cache and traversal API for knowledge graphs."""

    def __init__(self, cache_limit: int = 16, ttl_seconds: int = 1800):
        self._lock = threading.Lock()
        self.cache_limit = cache_limit
        self.ttl_seconds = ttl_seconds

        # In-memory graph cache: repo_id -> (graph, load_timestamp)
        self._cache: OrderedDict[str, Tuple[KnowledgeGraph, float]] = OrderedDict()

        # Traversal cache: repo_id -> {(func_name, args_tuple): (result, timestamp)}
        self._traversal_cache: Dict[str, Dict[Tuple[str, Tuple[Any, ...]], Tuple[Any, float]]] = {}

        # Cache metrics
        self.metrics_lock = threading.Lock()
        self.metrics: Dict[str, int] = {
            "cache_hits": 0,
            "cache_misses": 0,
            "build_count": 0,
            "rebuild_count": 0,
            "traversal_time_ms": 0,
        }

    # ------------------------------------------------------------------
    # Cache management helper methods
    # ------------------------------------------------------------------

    def _get_or_load(self, repo_id: str) -> Optional[KnowledgeGraph]:
        """Get graph from cache, checking TTL and lazily loading if missing."""
        now = time.time()
        with self._lock:
            if repo_id in self._cache:
                graph, load_time = self._cache[repo_id]
                if now - load_time <= self.ttl_seconds:
                    # Move to end to mark as recently used
                    self._cache.move_to_end(repo_id)
                    with self.metrics_lock:
                        self.metrics["cache_hits"] += 1
                    return graph
                else:
                    # Expired
                    logger.info(f"[GraphManager] TTL expired for repository {repo_id}")
                    self._cache.pop(repo_id)
                    self._traversal_cache.pop(repo_id, None)

            # Cache miss
            with self.metrics_lock:
                self.metrics["cache_misses"] += 1

        # Attempt to load from disk (outside lock to prevent deadlocks)
        # Note: In-progress builds/loads from other threads will be handled via disk verification
        # Fetch repository info to check for paths. We assume default intelligence paths
        from app.db.session import SessionLocal
        from app.models.repository import Repository
        intel_path = None
        repo_hash = None
        try:
            with SessionLocal() as db:
                repo_row = db.query(Repository).filter(Repository.id == repo_id).first()
                if repo_row:
                    intel_path = repo_row.intelligence_path
                    repo_hash = repo_row.repository_hash
        except Exception as err:
            logger.debug(f"[GraphManager] Failed to fetch repository info from DB: {err}")

        if intel_path and graph_storage.is_valid_cache(intel_path, repo_hash):
            graph = graph_storage.load(intel_path)
            if graph:
                with self._lock:
                    self._cache[repo_id] = (graph, time.time())
                    self._cache.move_to_end(repo_id)
                    # Enforce capacity
                    if len(self._cache) > self.cache_limit:
                        evicted_id, _ = self._cache.popitem(last=False)
                        self._traversal_cache.pop(evicted_id, None)
                        logger.info(f"[GraphManager] Evicted {evicted_id} due to cache capacity limit")
                return graph

        return None

    def _clear_traversal_cache(self, repo_id: str) -> None:
        """Clear the traversal query cache for a repository."""
        self._traversal_cache.pop(repo_id, None)

    def _get_traversal_cache(self, repo_id: str, key: Tuple[str, Tuple[Any, ...]]) -> Optional[Any]:
        """Fetch a traversal result from cache if present."""
        if repo_id not in self._traversal_cache:
            return None
        cache = self._traversal_cache[repo_id]
        if key in cache:
            val, load_time = cache[key]
            if time.time() - load_time <= self.ttl_seconds:
                return val
            else:
                cache.pop(key, None)
        return None

    def _set_traversal_cache(self, repo_id: str, key: Tuple[str, Tuple[Any, ...]], val: Any) -> None:
        """Store a traversal result in the cache."""
        self._traversal_cache.setdefault(repo_id, {})[key] = (val, time.time())

    # ------------------------------------------------------------------
    # Unified Public Entrypoint
    # ------------------------------------------------------------------

    def ensure_graph(
        self,
        repo_id: str,
        intelligence_path: str,
        repo_hash: str,
    ) -> bool:
        """Single public entry point for loading/rebuilding graphs.

        Decision Logic:
        - If graph is already loaded and valid (hash/versions match), reuse it.
        - If graph exists on disk and is valid, load it.
        - Otherwise, build the graph from intelligence metadata.
        """
        # 1. Check in-memory cache
        with self._lock:
            if repo_id in self._cache:
                graph, load_time = self._cache[repo_id]
                if graph.repository_hash == repo_hash and time.time() - load_time <= self.ttl_seconds:
                    return True

        # 2. Check disk cache
        if graph_storage.is_valid_cache(intelligence_path, repo_hash):
            ok = self.load(repo_id, intelligence_path, repo_hash)
            if ok:
                return True

        # 3. Rebuild graph from intelligence data
        from app.services.intelligence.intelligence_manager import intelligence_manager
        intel_data = intelligence_manager.get(repo_id, repo_hash=repo_hash)
        if not intel_data:
            # Try without hash if strict hash validation isn't pre-seeded
            intel_data = intelligence_manager.get(repo_id)
        if not intel_data:
            logger.warning(f"[GraphManager] Cannot rebuild graph: no intelligence data found for {repo_id}")
            return False

        with self.metrics_lock:
            self.metrics["rebuild_count"] += 1

        return self.build(repo_id, intel_data, intelligence_path, repo_hash)

    def ensure_available(
        self,
        repo_id: str,
        intelligence_data: Dict[str, Any],
        intelligence_path: str,
        repo_hash: str,
    ) -> bool:
        """Backward compatibility wrapper around ensure_graph."""
        import copy
        from app.services.intelligence.intelligence_manager import intelligence_manager
        from app.services.intelligence.versions import INTELLIGENCE_VERSION, SCHEMA_VERSION
        from app.services.intelligence.parsers import PARSER_VERSION
        
        intel_copy = copy.deepcopy(intelligence_data)
        intel_copy.setdefault("manifest", {})
        intel_copy["manifest"].update({
            "repository_hash": repo_hash,
            "intelligence_version": INTELLIGENCE_VERSION,
            "parser_version": PARSER_VERSION,
            "schema_version": SCHEMA_VERSION,
        })
        intelligence_manager._cache[repo_id] = intel_copy
        return self.ensure_graph(repo_id, intelligence_path, repo_hash)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def build(
        self,
        repo_id: str,
        intelligence_data: Dict[str, Any],
        intelligence_path: str,
        repo_hash: str,
    ) -> bool:
        """Build, validate, persist, and cache the knowledge graph.

        Returns True on success.
        """
        try:
            start = int(time.time() * 1000)
            graph = graph_builder.build(intelligence_data, repo_id, repo_hash)
            build_time_ms = int(time.time() * 1000) - start
            graph_storage.save(graph, intelligence_path, build_time_ms)
            
            with self._lock:
                self._cache[repo_id] = (graph, time.time())
                self._cache.move_to_end(repo_id)
                self._clear_traversal_cache(repo_id)
                if len(self._cache) > self.cache_limit:
                    evicted_id, _ = self._cache.popitem(last=False)
                    self._traversal_cache.pop(evicted_id, None)
                    logger.info(f"[GraphManager] Evicted {evicted_id} due to cache capacity limit")
            
            with self.metrics_lock:
                self.metrics["build_count"] += 1
            
            logger.info(f"[GraphManager] Graph built and cached for {repo_id}")
            return True
        except Exception as exc:
            logger.error(f"[GraphManager] Build failed for {repo_id}: {exc}")
            return False

    def load(
        self,
        repo_id: str,
        intelligence_path: str,
        repo_hash: Optional[str] = None,
    ) -> bool:
        """Load graph from disk into cache.

        Validates version + hash before accepting the cached file.
        Returns True if graph is now available.
        """
        if not graph_storage.is_valid_cache(intelligence_path, repo_hash):
            return False

        graph = graph_storage.load(intelligence_path)
        if graph is None:
            return False

        with self._lock:
            self._cache[repo_id] = (graph, time.time())
            self._cache.move_to_end(repo_id)
            self._clear_traversal_cache(repo_id)
            if len(self._cache) > self.cache_limit:
                evicted_id, _ = self._cache.popitem(last=False)
                self._traversal_cache.pop(evicted_id, None)
                logger.info(f"[GraphManager] Evicted {evicted_id} due to cache capacity limit")
        return True

    def invalidate(self, repo_id: str) -> None:
        """Evict graph for *repo_id* from in-memory cache."""
        with self._lock:
            self._cache.pop(repo_id, None)
            self._clear_traversal_cache(repo_id)
        logger.debug(f"[GraphManager] Cache evicted for {repo_id}")

    def get_graph(self, repo_id: str) -> Optional[KnowledgeGraph]:
        """Get the cached graph. Lazily loads from disk if not present."""
        return self._get_or_load(repo_id)

    def exists(self, repo_id: str) -> bool:
        """Check if graph is loaded or can be loaded."""
        return self._get_or_load(repo_id) is not None

    # ------------------------------------------------------------------
    # Query helpers (return lists or dicts — no raw graph exposure)
    # ------------------------------------------------------------------

    def get_symbol(self, repo_id: str, name: str) -> List[Dict[str, Any]]:
        """Return all symbol nodes matching *name* exactly."""
        graph = self._get_or_load(repo_id)
        if not graph:
            return []
        return [
            n.to_dict() for n in graph.nodes.values()
            if n.type == NodeType.SYMBOL and n.name == name
        ]

    def find_symbols(self, repo_id: str, pattern: str) -> List[Dict[str, Any]]:
        """Return symbol nodes whose name matches *pattern* (regex)."""
        graph = self._get_or_load(repo_id)
        if not graph:
            return []
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error:
            return []
        return [
            n.to_dict() for n in graph.nodes.values()
            if n.type == NodeType.SYMBOL and rx.search(n.name)
        ]

    def find_file(self, repo_id: str, path: str) -> Optional[Dict[str, Any]]:
        """Return the file node matching *path* (substring or exact)."""
        graph = self._get_or_load(repo_id)
        if not graph:
            return None
        node = graph.nodes.get(_file_id(path))
        if node:
            return node.to_dict()
        # Substring fallback
        for n in graph.nodes.values():
            if n.type == NodeType.FILE and path in (n.file or ""):
                return n.to_dict()
        return None

    def find_module(self, repo_id: str, path: str) -> Optional[Dict[str, Any]]:
        """Return the module node matching *path*."""
        graph = self._get_or_load(repo_id)
        if not graph:
            return None
        node = graph.nodes.get(_module_id(path))
        if node:
            return node.to_dict()
        for n in graph.nodes.values():
            if n.type == NodeType.MODULE and path in (n.file or ""):
                return n.to_dict()
        return None

    def find_dependencies(self, repo_id: str) -> List[Dict[str, Any]]:
        """Return all dependency nodes."""
        graph = self._get_or_load(repo_id)
        if not graph:
            return []
        return [n.to_dict() for n in graph.nodes.values() if n.type == NodeType.DEPENDENCY]

    def find_imports(self, repo_id: str, file_path: str) -> List[Dict[str, Any]]:
        """Return all nodes that *file_path*'s module imports."""
        graph = self._get_or_load(repo_id)
        if not graph:
            return []
        mod_id = _module_id(file_path)
        targets = graph.successors(mod_id, EdgeRelation.MODULE_IMPORTS)
        targets += graph.successors(_file_id(file_path), EdgeRelation.DEPENDS_ON)
        return [graph.nodes[t].to_dict() for t in targets if t in graph.nodes]

    def get_statistics(self, repo_id: str) -> Dict[str, Any]:
        """Return graph statistics & advanced metrics.

        Metrics tracked:
        - node_count
        - edge_count
        - average_degree
        - connected_components
        - isolated_nodes
        - build_time_ms
        - traversal_time_ms
        - cache_hits
        - cache_misses
        """
        graph = self._get_or_load(repo_id)
        if not graph:
            return {}

        base_stats = graph.stats()
        node_count = len(graph.nodes)
        edge_count = len(graph.edges)

        # 1. Average degree
        avg_degree = (edge_count * 2) / node_count if node_count > 0 else 0.0

        # 2. Connected Components & Isolated Nodes (DFS/BFS traversal over all nodes)
        visited: Set[str] = set()
        components_count = 0
        isolated_nodes = 0

        for node_id in graph.nodes:
            # Build degree for isolated node check
            deg = len(graph.successors(node_id)) + len(graph.predecessors(node_id))
            if deg == 0:
                isolated_nodes += 1

            if node_id not in visited:
                components_count += 1
                # BFS to cover component
                q = deque([node_id])
                visited.add(node_id)
                while q:
                    curr = q.popleft()
                    neighbors = graph.successors(curr) + graph.predecessors(curr)
                    for nbr in neighbors:
                        if nbr not in visited:
                            visited.add(nbr)
                            q.append(nbr)

        # Get build time from metadata on disk
        build_time = 0
        from app.db.session import SessionLocal
        from app.models.repository import Repository
        try:
            with SessionLocal() as db:
                repo_row = db.query(Repository).filter(Repository.id == repo_id).first()
                if repo_row and repo_row.intelligence_path:
                    meta = graph_storage.read_metadata(repo_row.intelligence_path)
                    build_time = meta.get("build_time_ms", 0)
        except Exception:
            pass

        with self.metrics_lock:
            hits = self.metrics["cache_hits"]
            misses = self.metrics["cache_misses"]
            trav_time = self.metrics["traversal_time_ms"]

        return {
            "total_nodes": node_count,
            "total_edges": edge_count,
            "node_types": base_stats.get("node_types", {}),
            "edge_relationships": base_stats.get("edge_relationships", {}),
            "node_count": node_count,
            "edge_count": edge_count,
            "average_degree": avg_degree,
            "connected_components": components_count,
            "isolated_nodes": isolated_nodes,
            "build_time_ms": build_time,
            "traversal_time_ms": trav_time,
            "cache_hits": hits,
            "cache_misses": misses,
        }

    # ------------------------------------------------------------------
    # Traversal APIs (wrapped with traversal cache and timing metrics)
    # ------------------------------------------------------------------

    def neighbors(self, repo_id: str, node_id: str) -> List[Dict[str, Any]]:
        """Return all directly adjacent nodes (both incoming and outgoing)."""
        graph = self._get_or_load(repo_id)
        if not graph:
            return []
        succ = graph.successors(node_id)
        pred = graph.predecessors(node_id)
        ids = set(succ) | set(pred)
        return [graph.nodes[i].to_dict() for i in ids if i in graph.nodes]

    def descendants(
        self, repo_id: str, node_id: str, depth: int = 3
    ) -> List[Dict[str, Any]]:
        """BFS forward from *node_id* up to *depth* hops."""
        graph = self._get_or_load(repo_id)
        if not graph:
            return []
        return self._bfs(graph, node_id, depth, forward=True)

    def ancestors(
        self, repo_id: str, node_id: str, depth: int = 3
    ) -> List[Dict[str, Any]]:
        """BFS backward from *node_id* up to *depth* hops."""
        graph = self._get_or_load(repo_id)
        if not graph:
            return []
        return self._bfs(graph, node_id, depth, forward=False)

    def find_callers(self, repo_id: str, symbol_id: str) -> List[Dict[str, Any]]:
        """Return all nodes that reference *symbol_id* (incoming edges)."""
        graph = self._get_or_load(repo_id)
        if not graph:
            return []
        preds = (
            graph.predecessors(symbol_id, EdgeRelation.USES)
            + graph.predecessors(symbol_id, EdgeRelation.CONTAINS)
            + graph.predecessors(symbol_id, EdgeRelation.DEFINES)
        )
        return [graph.nodes[p].to_dict() for p in set(preds) if p in graph.nodes]

    def find_callees(self, repo_id: str, symbol_id: str) -> List[Dict[str, Any]]:
        """Return all nodes that *symbol_id* references (outgoing edges)."""
        graph = self._get_or_load(repo_id)
        if not graph:
            return []
        succs = (
            graph.successors(symbol_id, EdgeRelation.USES)
            + graph.successors(symbol_id, EdgeRelation.IMPORTS)
            + graph.successors(symbol_id, EdgeRelation.INHERITS)
        )
        return [graph.nodes[s].to_dict() for s in set(succs) if s in graph.nodes]

    def find_related(
        self, repo_id: str, symbol_id: str, depth: int = 2
    ) -> List[Dict[str, Any]]:
        """Return all nodes within *depth* hops of *symbol_id* in any direction."""
        cache_key = ("find_related", (symbol_id, depth))
        cached = self._get_traversal_cache(repo_id, cache_key)
        if cached is not None:
            return cached

        t0 = time.perf_counter()
        graph = self._get_or_load(repo_id)
        if not graph:
            return []

        visited: Set[str] = set()
        queue = deque([(symbol_id, 0)])
        result: List[Dict[str, Any]] = []
        while queue:
            nid, d = queue.popleft()
            if nid in visited or d > depth:
                continue
            visited.add(nid)
            if nid != symbol_id and nid in graph.nodes:
                result.append(graph.nodes[nid].to_dict())
            if d < depth:
                for neighbor in (
                    graph.successors(nid) + graph.predecessors(nid)
                ):
                    if neighbor not in visited:
                        queue.append((neighbor, d + 1))

        self._set_traversal_cache(repo_id, cache_key, result)
        dt = int((time.perf_counter() - t0) * 1000)
        with self.metrics_lock:
            self.metrics["traversal_time_ms"] += dt

        return result

    def dependency_path(
        self, repo_id: str, a: str, b: str
    ) -> List[str]:
        """BFS shortest path of node IDs from *a* to *b* via DEPENDS_ON / MODULE_IMPORTS."""
        cache_key = ("dependency_path", (a, b))
        cached = self._get_traversal_cache(repo_id, cache_key)
        if cached is not None:
            return cached

        t0 = time.perf_counter()
        graph = self._get_or_load(repo_id)
        if not graph:
            return []
        res = self._bfs_path(
            graph, a, b,
            rel_filter={EdgeRelation.DEPENDS_ON, EdgeRelation.MODULE_IMPORTS, EdgeRelation.IMPORTS},
        )

        self._set_traversal_cache(repo_id, cache_key, res)
        dt = int((time.perf_counter() - t0) * 1000)
        with self.metrics_lock:
            self.metrics["traversal_time_ms"] += dt

        return res

    def module_dependencies(
        self, repo_id: str, module_path: str
    ) -> List[Dict[str, Any]]:
        """Return all modules/deps that *module_path* transitively depends on."""
        graph = self._get_or_load(repo_id)
        if not graph:
            return []
        mod_id = _module_id(module_path)
        all_ids: Set[str] = set()
        queue = deque([mod_id])
        visited: Set[str] = set()
        while queue:
            cur = queue.popleft()
            if cur in visited:
                continue
            visited.add(cur)
            for rel in (EdgeRelation.MODULE_IMPORTS, EdgeRelation.DEPENDS_ON, EdgeRelation.IMPORTS):
                for nid in graph.successors(cur, rel):
                    if nid not in visited:
                        all_ids.add(nid)
                        queue.append(nid)
        return [graph.nodes[i].to_dict() for i in all_ids if i in graph.nodes]

    def impacted_files(self, repo_id: str, symbol_id: str) -> List[str]:
        """Return file paths that would be impacted if *symbol_id* changed."""
        cache_key = ("impacted_files", (symbol_id,))
        cached = self._get_traversal_cache(repo_id, cache_key)
        if cached is not None:
            return cached

        t0 = time.perf_counter()
        graph = self._get_or_load(repo_id)
        if not graph:
            return []

        impacted: Set[str] = set()

        # Files that contain the symbol directly
        for pred in graph.predecessors(symbol_id, EdgeRelation.CONTAINS):
            node = graph.nodes.get(pred)
            if node and node.type == NodeType.FILE and node.file:
                impacted.add(node.file)

        # Modules that define the symbol → then modules that import those modules
        for pred in graph.predecessors(symbol_id, EdgeRelation.DEFINES):
            node = graph.nodes.get(pred)
            if not node or node.type != NodeType.MODULE:
                continue
            if node.file:
                impacted.add(node.file)
            # Modules that import this module
            for importer in graph.predecessors(pred, EdgeRelation.MODULE_IMPORTS):
                imp_node = graph.nodes.get(importer)
                if imp_node and imp_node.file:
                    impacted.add(imp_node.file)

        res = sorted(impacted)
        self._set_traversal_cache(repo_id, cache_key, res)
        dt = int((time.perf_counter() - t0) * 1000)
        with self.metrics_lock:
            self.metrics["traversal_time_ms"] += dt

        return res

    def shortest_path(self, repo_id: str, a: str, b: str) -> List[str]:
        """BFS shortest path of node IDs between *a* and *b* (any relationship)."""
        cache_key = ("shortest_path", (a, b))
        cached = self._get_traversal_cache(repo_id, cache_key)
        if cached is not None:
            return cached

        t0 = time.perf_counter()
        graph = self._get_or_load(repo_id)
        if not graph:
            return []
        res = self._bfs_path(graph, a, b, rel_filter=None)

        self._set_traversal_cache(repo_id, cache_key, res)
        dt = int((time.perf_counter() - t0) * 1000)
        with self.metrics_lock:
            self.metrics["traversal_time_ms"] += dt

        return res

    def search(self, repo_id: str, query: str) -> List[Dict[str, Any]]:
        """Case-insensitive substring search across all node names."""
        graph = self._get_or_load(repo_id)
        if not graph or not query:
            return []
        q = query.lower()
        return [
            n.to_dict() for n in graph.nodes.values()
            if q in n.name.lower()
        ]

    def candidate_files_for_goal(
        self, repo_id: str, goal: str, max_files: int = 30
    ) -> List[str]:
        """Extract high-signal files from the graph for a given goal string."""
        graph = self._get_or_load(repo_id)
        if not graph:
            return []

        keywords = [w.lower() for w in goal.split() if len(w) > 3]
        if not keywords:
            return []

        candidate_files: Set[str] = set()

        for kw in keywords:
            for node in graph.nodes.values():
                if node.type == NodeType.SYMBOL and kw in node.name.lower():
                    if node.file:
                        candidate_files.add(node.file)
                    # Cascade: impacted files
                    for fp in self.impacted_files(repo_id, node.id):
                        candidate_files.add(fp)
                elif node.type in (NodeType.FILE, NodeType.MODULE) and kw in (node.file or "").lower():
                    if node.file:
                        candidate_files.add(node.file)

        return sorted(candidate_files)[:max_files]

    def build_graph_context(
        self,
        repo_id: str,
        goal: str,
        max_symbols: int = 20,
        max_modules: int = 15,
        max_deps: int = 10,
    ) -> str:
        """Build a structured graph context block for injection into prompts.

        Returns an empty string when the graph is unavailable so callers never
        need to guard against None.

        Limits
        ------
        - max 20 symbols (sorted by relevance to *goal*)
        - max 15 modules
        - max 10 dependencies
        """
        try:
            if not self.exists(repo_id):
                return ""

            goal_words = [w.lower() for w in goal.split() if len(w) > 3]

            def _relevance(name: str) -> int:
                n = name.lower()
                return sum(1 for w in goal_words if w in n)

            # Symbols
            all_syms = self.search(repo_id, "")  # all nodes
            symbols = [
                s for s in all_syms if s.get("type") == "symbol"
            ]
            symbols.sort(key=lambda s: _relevance(s.get("name", "")), reverse=True)
            symbols = symbols[:max_symbols]

            # Modules
            modules = [
                s for s in all_syms if s.get("type") == "module"
            ][:max_modules]

            # Dependencies
            deps = self.find_dependencies(repo_id)[:max_deps]

            # Graph stats
            stats = self.get_statistics(repo_id)

            lines: List[str] = []
            lines.append("## Repository Knowledge Graph Context")
            lines.append(f"Nodes: {stats.get('total_nodes', 0)} | "
                         f"Edges: {stats.get('total_edges', 0)}")
            lines.append("")

            if symbols:
                lines.append("### Relevant Symbols")
                for s in symbols:
                    sym_type = s.get("metadata", {}).get("symbol_type") or s.get("type", "")
                    file_path = s.get("file") or ""
                    vis = s.get("visibility", "")
                    lines.append(
                        f"  - `{s['name']}` ({sym_type}, {vis}) ← {file_path}"
                    )
                lines.append("")

            if modules:
                lines.append("### Related Modules")
                for m in modules:
                    lines.append(f"  - {m.get('file', m.get('name', ''))}")
                lines.append("")

            if deps:
                lines.append("### Key Dependencies")
                for d in deps:
                    eco = d.get("metadata", {}).get("ecosystem", "")
                    ver = d.get("metadata", {}).get("version", "")
                    name = d.get("name", "")
                    suffix = f" ({eco}" + (f" {ver}" if ver else "") + ")" if eco else ""
                    lines.append(f"  - {name}{suffix}")
                lines.append("")

            return "\n".join(lines)

        except Exception as exc:
            logger.debug(f"[GraphManager] Graph context skipped: {exc}")
            return ""

    # ------------------------------------------------------------------
    # Private BFS helpers
    # ------------------------------------------------------------------

    def _bfs(
        self,
        graph: KnowledgeGraph,
        start: str,
        depth: int,
        forward: bool,
    ) -> List[Dict[str, Any]]:
        visited: Set[str] = {start}
        queue = deque([(start, 0)])
        result: List[Dict[str, Any]] = []
        while queue:
            nid, d = queue.popleft()
            if d >= depth:
                continue
            neighbours = graph.successors(nid) if forward else graph.predecessors(nid)
            for nb in neighbours:
                if nb not in visited:
                    visited.add(nb)
                    if nb in graph.nodes:
                        result.append(graph.nodes[nb].to_dict())
                    queue.append((nb, d + 1))
        return result

    def _bfs_path(
        self,
        graph: KnowledgeGraph,
        start: str,
        goal: str,
        rel_filter: Optional[Set[str]],
    ) -> List[str]:
        """BFS to find shortest path from *start* to *goal*."""
        if start not in graph.nodes or goal not in graph.nodes:
            return []
        if start == goal:
            return [start]

        visited: Set[str] = {start}
        queue: deque = deque([[start]])

        while queue:
            path = queue.popleft()
            cur = path[-1]

            adj = graph._adj.get(cur, {})
            for rel, targets in adj.items():
                if rel_filter is not None and rel not in rel_filter:
                    continue
                for nid in targets:
                    if nid in visited:
                        continue
                    new_path = path + [nid]
                    if nid == goal:
                        return new_path
                    visited.add(nid)
                    queue.append(new_path)

        return []  # no path found


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

graph_manager = GraphManager()
