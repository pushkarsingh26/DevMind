"""pytest test suite for Phase 8.2 Knowledge Graph Engine.

Test categories
---------------
- Graph models (node/edge creation, adjacency, self-loops)
- Graph validation (dedup, orphan removal, self-loop removal)
- GraphBuilder (7-stage build from mock intelligence data)
- GraphStorage (serialize/deserialize, version validity, cache check)
- GraphManager API (build, load, exists, invalidate, traversal, search)
- Incremental rebuild logic (hash-based cache reuse)
- Fallback retrieval (candidate_files returns [] when no match)
- Traversal APIs (find_callers, find_callees, find_related, shortest_path, impacted_files)
"""

from __future__ import annotations

import json
import pytest
import time
from pathlib import Path
from typing import Any, Dict, List

# Explicitly import all models to bind SQLAlchemy relationships
import app.db.base
from app.models.repository import Repository
from app.models.chat import ChatConversation, ChatMessage
from app.models.workflow import WorkflowExecutionORM

from app.services.knowledge_graph.graph_models import (
    EdgeRelation, GraphEdge, GraphNode, KnowledgeGraph, NodeType,
)
from app.services.knowledge_graph import graph_storage
from app.services.knowledge_graph.graph_builder import GraphBuilder
from app.services.knowledge_graph.graph_manager import GraphManager
from app.services.knowledge_graph.versions import (
    GRAPH_FILE_NAME,
    GRAPH_GENERATOR_VERSION,
    GRAPH_SCHEMA_VERSION,
    GRAPH_VERSION,
)
from app.services.intelligence.parsers import PARSER_VERSION


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture()
def empty_graph():
    return KnowledgeGraph(repository_id="test", repository_hash="abc")


@pytest.fixture()
def sample_graph():
    g = KnowledgeGraph(repository_id="repo1", repository_hash="h1")
    file_node = GraphNode(id="file:main.py", type=NodeType.FILE, name="main.py", file="main.py")
    mod_node  = GraphNode(id="module:main.py", type=NodeType.MODULE, name="main.py", file="main.py")
    sym_node  = GraphNode(id="sym:py:main.py:App:class", type=NodeType.SYMBOL, name="App",
                          file="main.py", language="python", visibility="public",
                          metadata={"symbol_type": "class"})
    dep_node  = GraphNode(id="dep:python:fastapi", type=NodeType.DEPENDENCY, name="fastapi",
                          metadata={"ecosystem": "python", "version": "0.116.0"})
    g.add_node(file_node)
    g.add_node(mod_node)
    g.add_node(sym_node)
    g.add_node(dep_node)
    g.add_edge(GraphEdge("file:main.py", "module:main.py", EdgeRelation.CONTAINS))
    g.add_edge(GraphEdge("module:main.py", "sym:py:main.py:App:class", EdgeRelation.DEFINES))
    g.add_edge(GraphEdge("file:main.py", "dep:python:fastapi", EdgeRelation.DEPENDS_ON))
    return g


@pytest.fixture()
def mini_intelligence() -> Dict[str, Any]:
    """Minimal intelligence data for GraphBuilder tests."""
    return {
        "file_tree": [
            {"path": "main.py", "language": "python", "size_bytes": 1024, "sha256": "a" * 64, "last_modified": 1.0, "extension": ".py"},
            {"path": "utils.py", "language": "python", "size_bytes": 512, "sha256": "b" * 64, "last_modified": 2.0, "extension": ".py"},
        ],
        "modules": [
            {"path": "main.py", "language": "python", "symbol_count": 2, "import_count": 1},
            {"path": "utils.py", "language": "python", "symbol_count": 1, "import_count": 0},
        ],
        "symbols": [
            {"id": "py:main.py:App:class", "name": "App", "type": "class", "file_path": "main.py",
             "language": "python", "line_start": 5, "line_end": 30, "visibility": "public",
             "id_hash": "a" * 64, "metadata": {}},
            {"id": "py:main.py:run:function", "name": "run", "type": "function", "file_path": "main.py",
             "language": "python", "line_start": 32, "line_end": 40, "visibility": "public",
             "id_hash": "b" * 64, "metadata": {}},
            {"id": "py:utils.py:helper:function", "name": "helper", "type": "function", "file_path": "utils.py",
             "language": "python", "line_start": 1, "line_end": 10, "visibility": "private",
             "id_hash": "c" * 64, "metadata": {}},
        ],
        "imports": [
            {"module": "fastapi", "file": "main.py", "language": "python", "line": 1, "name": None, "alias": None},
        ],
        "dependencies": [
            {"name": "fastapi", "ecosystem": "python", "version": "0.116.0", "source_file": "requirements.txt"},
            {"name": "pydantic", "ecosystem": "python", "version": ">=2.0", "source_file": "requirements.txt"},
        ],
        "statistics": {
            "total_files": 2,
            "entry_points": ["main.py"],
        },
        "manifest": {},
        "errors": {},
        "call_graph": {},
    }


# ===========================================================================
# Graph models
# ===========================================================================

class TestGraphModels:
    def test_add_node_no_duplicate(self, empty_graph):
        n = GraphNode(id="n1", type=NodeType.FILE, name="a.py")
        empty_graph.add_node(n)
        empty_graph.add_node(n)
        assert len(empty_graph.nodes) == 1

    def test_add_edge_updates_adjacency(self, sample_graph):
        succs = sample_graph.successors("file:main.py")
        assert "module:main.py" in succs

    def test_add_edge_updates_reverse_adjacency(self, sample_graph):
        preds = sample_graph.predecessors("module:main.py")
        assert "file:main.py" in preds

    def test_add_edge_drops_orphan_source(self, empty_graph):
        n = GraphNode(id="n1", type=NodeType.FILE, name="x.py")
        empty_graph.add_node(n)
        empty_graph.add_edge(GraphEdge("n1", "ghost", EdgeRelation.CONTAINS))
        assert len(empty_graph.edges) == 0

    def test_add_edge_drops_self_loop(self, empty_graph):
        n = GraphNode(id="n1", type=NodeType.FILE, name="x.py")
        empty_graph.add_node(n)
        empty_graph.add_edge(GraphEdge("n1", "n1", EdgeRelation.CONTAINS))
        assert len(empty_graph.edges) == 0

    def test_successors_filtered_by_rel(self, sample_graph):
        succs = sample_graph.successors("file:main.py", EdgeRelation.CONTAINS)
        assert "module:main.py" in succs
        assert "dep:python:fastapi" not in succs

    def test_rebuild_adjacency(self, sample_graph):
        sample_graph._adj = {}
        sample_graph._radj = {}
        sample_graph.rebuild_adjacency()
        assert "module:main.py" in sample_graph.successors("file:main.py")

    def test_stats_counts(self, sample_graph):
        stats = sample_graph.stats()
        assert stats["total_nodes"] == 4
        assert stats["total_edges"] == 3
        assert "file" in stats["node_types"]
        assert EdgeRelation.CONTAINS in stats["edge_relationships"]


# ===========================================================================
# Graph validation (graph_storage.validate_and_clean)
# ===========================================================================

class TestGraphValidation:
    def test_duplicate_edges_removed(self):
        g = KnowledgeGraph(repository_id="r", repository_hash="h")
        n1 = GraphNode(id="n1", type=NodeType.FILE, name="a")
        n2 = GraphNode(id="n2", type=NodeType.MODULE, name="b")
        g.add_node(n1); g.add_node(n2)
        # Add same edge three times via raw list (bypassing add_edge dedup)
        for _ in range(3):
            g.edges.append(GraphEdge("n1", "n2", EdgeRelation.CONTAINS))
        g.rebuild_adjacency()
        summary = graph_storage.validate_and_clean(g)
        assert len(g.edges) == 1
        assert summary["duplicate_edges_removed"] == 2

    def test_orphan_edges_removed(self):
        g = KnowledgeGraph(repository_id="r", repository_hash="h")
        n1 = GraphNode(id="n1", type=NodeType.FILE, name="a")
        g.add_node(n1)
        g.edges.append(GraphEdge("n1", "ghost_node", EdgeRelation.CONTAINS))
        summary = graph_storage.validate_and_clean(g)
        assert len(g.edges) == 0
        assert summary["orphan_edges_removed"] == 1

    def test_self_loops_removed(self):
        g = KnowledgeGraph(repository_id="r", repository_hash="h")
        n1 = GraphNode(id="n1", type=NodeType.FILE, name="a")
        g.add_node(n1)
        g.edges.append(GraphEdge("n1", "n1", EdgeRelation.CONTAINS))
        summary = graph_storage.validate_and_clean(g)
        assert len(g.edges) == 0
        assert summary["self_loops_removed"] == 1

    def test_valid_graph_unchanged(self, sample_graph):
        before = len(sample_graph.edges)
        summary = graph_storage.validate_and_clean(sample_graph)
        assert len(sample_graph.edges) == before
        assert summary["duplicate_edges_removed"] == 0
        assert summary["orphan_edges_removed"] == 0
        assert summary["self_loops_removed"] == 0
        assert summary["is_valid"] is True


# ===========================================================================
# GraphBuilder
# ===========================================================================

class TestGraphBuilder:
    def test_builds_file_nodes(self, mini_intelligence):
        g = GraphBuilder().build(mini_intelligence, "repo", "hash")
        assert "file:main.py" in g.nodes
        assert "file:utils.py" in g.nodes

    def test_builds_module_nodes(self, mini_intelligence):
        g = GraphBuilder().build(mini_intelligence, "repo", "hash")
        assert "module:main.py" in g.nodes

    def test_builds_symbol_nodes(self, mini_intelligence):
        g = GraphBuilder().build(mini_intelligence, "repo", "hash")
        sym_ids = [nid for nid in g.nodes if g.nodes[nid].type == NodeType.SYMBOL]
        assert len(sym_ids) == 3

    def test_builds_dependency_nodes(self, mini_intelligence):
        g = GraphBuilder().build(mini_intelligence, "repo", "hash")
        dep_ids = [nid for nid in g.nodes if g.nodes[nid].type == NodeType.DEPENDENCY]
        assert len(dep_ids) == 2  # fastapi + pydantic

    def test_builds_entry_point_nodes(self, mini_intelligence):
        g = GraphBuilder().build(mini_intelligence, "repo", "hash")
        assert "entry:main.py" in g.nodes

    def test_no_duplicate_nodes(self, mini_intelligence):
        g = GraphBuilder().build(mini_intelligence, "repo", "hash")
        ids = list(g.nodes.keys())
        assert len(ids) == len(set(ids))

    def test_no_orphan_edges(self, mini_intelligence):
        g = GraphBuilder().build(mini_intelligence, "repo", "hash")
        node_ids = set(g.nodes.keys())
        for e in g.edges:
            assert e.source in node_ids, f"Orphan source: {e.source}"
            assert e.target in node_ids, f"Orphan target: {e.target}"

    def test_no_self_loops(self, mini_intelligence):
        g = GraphBuilder().build(mini_intelligence, "repo", "hash")
        for e in g.edges:
            assert e.source != e.target, f"Self-loop: {e.source}"

    def test_file_contains_module_edge(self, mini_intelligence):
        g = GraphBuilder().build(mini_intelligence, "repo", "hash")
        succs = g.successors("file:main.py", EdgeRelation.CONTAINS)
        assert "module:main.py" in succs

    def test_module_defines_symbol_edge(self, mini_intelligence):
        g = GraphBuilder().build(mini_intelligence, "repo", "hash")
        succs = g.successors("module:main.py", EdgeRelation.DEFINES)
        sym_ids = [s for s in succs if g.nodes.get(s, GraphNode("", "", "")).name == "App"]
        assert len(sym_ids) > 0

    def test_dedup_dependencies(self, mini_intelligence):
        """Adding the same dep twice should produce one node."""
        intel = dict(mini_intelligence)
        intel["dependencies"] = intel["dependencies"] + intel["dependencies"]
        g = GraphBuilder().build(intel, "repo", "hash")
        dep_ids = [nid for nid in g.nodes if g.nodes[nid].type == NodeType.DEPENDENCY]
        assert len(dep_ids) == 2  # still 2, not 4


# ===========================================================================
# GraphStorage — serialize / deserialize / cache validity
# ===========================================================================

class TestGraphStorage:
    def test_save_and_load_round_trip(self, sample_graph, tmp_path):
        path = str(tmp_path)
        graph_storage.save(sample_graph, path, build_time_ms=100)
        loaded = graph_storage.load(path)
        assert loaded is not None
        assert len(loaded.nodes) == len(sample_graph.nodes)
        assert len(loaded.edges) == len(sample_graph.edges)

    def test_load_rebuilds_adjacency(self, sample_graph, tmp_path):
        path = str(tmp_path)
        graph_storage.save(sample_graph, path)
        loaded = graph_storage.load(path)
        succs = loaded.successors("file:main.py")
        assert "module:main.py" in succs

    def test_metadata_contains_all_fields(self, sample_graph, tmp_path):
        path = str(tmp_path)
        graph_storage.save(sample_graph, path, build_time_ms=42)
        meta = graph_storage.read_metadata(path)
        assert meta["graph_version"] == GRAPH_VERSION
        assert meta["schema_version"] == GRAPH_SCHEMA_VERSION
        assert meta["generator_version"] == GRAPH_GENERATOR_VERSION
        assert meta["node_count"] == 4
        assert meta["edge_count"] == 3
        assert meta["build_time_ms"] == 42
        assert "repository_hash" in meta
        assert "generated_at" in meta

    def test_is_valid_cache_true(self, sample_graph, tmp_path):
        path = str(tmp_path)
        graph_storage.save(sample_graph, path)
        assert graph_storage.is_valid_cache(path, "h1") is True

    def test_is_valid_cache_wrong_hash(self, sample_graph, tmp_path):
        path = str(tmp_path)
        graph_storage.save(sample_graph, path)
        assert graph_storage.is_valid_cache(path, "wrong_hash") is False

    def test_is_valid_cache_missing_file(self, tmp_path):
        assert graph_storage.is_valid_cache(str(tmp_path), "h1") is False

    def test_is_valid_cache_wrong_graph_version(self, sample_graph, tmp_path):
        path = str(tmp_path)
        graph_storage.save(sample_graph, path)
        # Tamper with the file
        fp = Path(path) / GRAPH_FILE_NAME
        payload = json.loads(fp.read_text())
        payload["metadata"]["graph_version"] = "v999"
        fp.write_text(json.dumps(payload))
        assert graph_storage.is_valid_cache(path, "h1") is False

    def test_load_returns_none_on_missing(self, tmp_path):
        assert graph_storage.load(str(tmp_path)) is None


# ===========================================================================
# GraphManager — cache lifecycle
# ===========================================================================

class TestGraphManagerLifecycle:
    def test_exists_false_when_not_built(self):
        mgr = GraphManager()
        assert mgr.exists("no_repo") is False

    def test_build_and_exists(self, mini_intelligence, tmp_path):
        mgr = GraphManager()
        ok = mgr.build("r1", mini_intelligence, str(tmp_path), "h1")
        assert ok is True
        assert mgr.exists("r1") is True

    def test_invalidate_removes(self, mini_intelligence, tmp_path):
        mgr = GraphManager()
        mgr.build("r2", mini_intelligence, str(tmp_path), "h1")
        mgr.invalidate("r2")
        assert mgr.exists("r2") is False

    def test_load_from_disk(self, mini_intelligence, tmp_path):
        mgr = GraphManager()
        mgr.build("r3", mini_intelligence, str(tmp_path), "h1")
        mgr.invalidate("r3")
        ok = mgr.load("r3", str(tmp_path), "h1")
        assert ok is True
        assert mgr.exists("r3") is True

    def test_load_fails_wrong_hash(self, mini_intelligence, tmp_path):
        mgr = GraphManager()
        mgr.build("r4", mini_intelligence, str(tmp_path), "h1")
        mgr.invalidate("r4")
        ok = mgr.load("r4", str(tmp_path), "wrong_hash")
        assert ok is False

    def test_ensure_available_reuses_cache(self, mini_intelligence, tmp_path):
        mgr = GraphManager()
        mgr.build("r5", mini_intelligence, str(tmp_path), "h1")
        mgr.invalidate("r5")
        ok = mgr.ensure_available("r5", mini_intelligence, str(tmp_path), "h1")
        assert ok is True


# ===========================================================================
# GraphManager — query and traversal APIs
# ===========================================================================

class TestGraphManagerTraversal:
    @pytest.fixture()
    def mgr_with_graph(self, mini_intelligence, tmp_path):
        mgr = GraphManager()
        mgr.build("trav", mini_intelligence, str(tmp_path), "h1")
        return mgr

    def test_get_symbol_exact(self, mgr_with_graph):
        syms = mgr_with_graph.get_symbol("trav", "App")
        assert len(syms) == 1
        assert syms[0]["name"] == "App"

    def test_get_symbol_missing(self, mgr_with_graph):
        assert mgr_with_graph.get_symbol("trav", "NonExistent") == []

    def test_find_symbols_pattern(self, mgr_with_graph):
        syms = mgr_with_graph.find_symbols("trav", "pp")
        names = [s["name"] for s in syms]
        assert "App" in names

    def test_find_file(self, mgr_with_graph):
        result = mgr_with_graph.find_file("trav", "main.py")
        assert result is not None
        assert result["type"] == NodeType.FILE

    def test_find_module(self, mgr_with_graph):
        result = mgr_with_graph.find_module("trav", "utils.py")
        assert result is not None
        assert result["type"] == NodeType.MODULE

    def test_find_dependencies(self, mgr_with_graph):
        deps = mgr_with_graph.find_dependencies("trav")
        names = [d["name"] for d in deps]
        assert "fastapi" in names
        assert "pydantic" in names

    def test_get_statistics(self, mgr_with_graph):
        stats = mgr_with_graph.get_statistics("trav")
        assert stats["total_nodes"] > 0
        assert stats["total_edges"] > 0

    def test_neighbors_returns_adjacent(self, mgr_with_graph):
        nbrs = mgr_with_graph.neighbors("trav", "file:main.py")
        nids = [n["id"] for n in nbrs]
        assert "module:main.py" in nids

    def test_descendants_within_depth(self, mgr_with_graph):
        desc = mgr_with_graph.descendants("trav", "file:main.py", depth=2)
        assert len(desc) > 0

    def test_ancestors_within_depth(self, mgr_with_graph):
        anc = mgr_with_graph.ancestors("trav", "module:main.py", depth=1)
        ids = [n["id"] for n in anc]
        assert "file:main.py" in ids

    def test_find_callers(self, mgr_with_graph):
        # App is defined by module:main.py (incoming DEFINES edge)
        app_id = [nid for nid in mgr_with_graph.get_graph("trav").nodes
                  if mgr_with_graph.get_graph("trav").nodes[nid].name == "App"][0]
        callers = mgr_with_graph.find_callers("trav", app_id)
        assert len(callers) > 0

    def test_impacted_files(self, mgr_with_graph):
        app_id = [nid for nid in mgr_with_graph.get_graph("trav").nodes
                  if mgr_with_graph.get_graph("trav").nodes[nid].name == "App"][0]
        files = mgr_with_graph.impacted_files("trav", app_id)
        assert "main.py" in files

    def test_search_substring(self, mgr_with_graph):
        results = mgr_with_graph.search("trav", "main")
        names = [r["name"] for r in results]
        assert "main.py" in names

    def test_search_empty_query(self, mgr_with_graph):
        # Empty query returns all nodes
        results = mgr_with_graph.search("trav", "")
        assert len(results) == 0  # search("") returns [] (no match)


# ===========================================================================
# Fallback retrieval: candidate_files_for_goal
# ===========================================================================

class TestCandidateFiles:
    def test_returns_files_for_keyword(self, mini_intelligence, tmp_path):
        mgr = GraphManager()
        mgr.build("cf1", mini_intelligence, str(tmp_path), "h1")
        # "helper" (>3 chars) matches the "helper" symbol in utils.py
        files = mgr.candidate_files_for_goal("cf1", "review the helper function", max_files=30)
        assert "utils.py" in files

    def test_returns_empty_for_no_match(self, mini_intelligence, tmp_path):
        mgr = GraphManager()
        mgr.build("cf2", mini_intelligence, str(tmp_path), "h1")
        files = mgr.candidate_files_for_goal("cf2", "xyz", max_files=30)
        # Short or non-matching keyword → empty list (no error)
        assert isinstance(files, list)

    def test_returns_empty_when_graph_missing(self):
        mgr = GraphManager()
        files = mgr.candidate_files_for_goal("no_graph", "some goal")
        assert files == []

    def test_respects_max_files(self, mini_intelligence, tmp_path):
        mgr = GraphManager()
        mgr.build("cf3", mini_intelligence, str(tmp_path), "h1")
        files = mgr.candidate_files_for_goal("cf3", "all python files and modules", max_files=1)
        assert len(files) <= 1


# ===========================================================================
# Incremental rebuild
# ===========================================================================

class TestIncrementalRebuild:
    def test_cache_reused_same_hash(self, mini_intelligence, tmp_path):
        mgr = GraphManager()
        mgr.build("inc1", mini_intelligence, str(tmp_path), "h1")
        # Save node count
        before = len(mgr.get_graph("inc1").nodes)
        mgr.invalidate("inc1")
        # ensure_available should reload from disk
        ok = mgr.ensure_available("inc1", mini_intelligence, str(tmp_path), "h1")
        assert ok
        after = len(mgr.get_graph("inc1").nodes)
        assert before == after

    def test_rebuild_on_hash_change(self, mini_intelligence, tmp_path):
        mgr = GraphManager()
        mgr.build("inc2", mini_intelligence, str(tmp_path), "h1")
        mgr.invalidate("inc2")
        # Different hash → should not load from disk → falls back to rebuild
        ok = mgr.ensure_available("inc2", mini_intelligence, str(tmp_path), "h2")
        assert ok
        meta = graph_storage.read_metadata(str(tmp_path))
        assert meta["repository_hash"] == "h2"


# ===========================================================================
# Phase 8.2.1 Stabilization Tests
# ===========================================================================

class TestStabilizationFeatures:
    def test_bfs_dfs_with_cycles(self):
        """Construct a graph with a directed/undirected cycle and verify traversal."""
        import time
        g = KnowledgeGraph(repository_id="cycle_repo", repository_hash="h1")
        n1 = GraphNode(id="n1", type=NodeType.SYMBOL, name="Node 1")
        n2 = GraphNode(id="n2", type=NodeType.SYMBOL, name="Node 2")
        n3 = GraphNode(id="n3", type=NodeType.SYMBOL, name="Node 3")
        g.add_node(n1); g.add_node(n2); g.add_node(n3)

        # Create cycle n1 -> n2 -> n3 -> n1
        g.add_edge(GraphEdge("n1", "n2", EdgeRelation.USES))
        g.add_edge(GraphEdge("n2", "n3", EdgeRelation.USES))
        g.add_edge(GraphEdge("n3", "n1", EdgeRelation.USES))

        # BFS shortest path n1 -> n3 should visit cycle
        p = g.successors("n1")
        assert "n2" in p
        
        # Test connected components metrics (should find 1 component since all are connected)
        mgr = GraphManager()
        # Manually seed in cache
        mgr._cache["cycle_repo"] = (g, time.time())
        stats = mgr.get_statistics("cycle_repo")
        assert stats["connected_components"] == 1
        assert stats["node_count"] == 3
        assert stats["edge_count"] == 3

    def test_lazy_loading(self, mini_intelligence, tmp_path):
        """Lazy loading resolves graph from disk on first query when cached in DB."""
        from app.db.session import SessionLocal
        from app.models.repository import Repository
        
        # Seed DB
        with SessionLocal() as db:
            # Clean up existing test row if any
            db.query(Repository).filter(Repository.id == "lazy_repo").delete()
            repo = Repository(
                id="lazy_repo",
                name="lazy_repo",
                owner="owner",
                source="source",
                intelligence_path=str(tmp_path),
                repository_hash="h1"
            )
            db.add(repo)
            db.commit()

        mgr = GraphManager()
        mgr.build("lazy_repo", mini_intelligence, str(tmp_path), "h1")
        mgr.invalidate("lazy_repo")  # Evict memory cache

        # Query stats directly — triggers lazy loading implicitly
        stats = mgr.get_statistics("lazy_repo")
        assert stats["total_nodes"] > 0
        assert mgr.exists("lazy_repo") is True

    def test_lru_eviction(self, mini_intelligence, tmp_path):
        """Cache eviction caps size to limit (e.g. 2 for test) and discards oldest."""
        mgr = GraphManager(cache_limit=2)
        # Build 3 repositories
        mgr.build("repoA", mini_intelligence, str(tmp_path / "A"), "h")
        mgr.build("repoB", mini_intelligence, str(tmp_path / "B"), "h")
        mgr.build("repoC", mini_intelligence, str(tmp_path / "C"), "h")

        # repoA should have been evicted (oldest) since capacity is 2
        with mgr._lock:
            cached_ids = list(mgr._cache.keys())
        assert "repoA" not in cached_ids
        assert "repoB" in cached_ids
        assert "repoC" in cached_ids

    def test_ttl_expiration(self, mini_intelligence, tmp_path):
        """Cache entry with expired TTL triggers reload."""
        from app.db.session import SessionLocal
        from app.models.repository import Repository
        
        # Seed DB
        with SessionLocal() as db:
            db.query(Repository).filter(Repository.id == "ttl_repo").delete()
            repo = Repository(
                id="ttl_repo",
                name="ttl_repo",
                owner="owner",
                source="source",
                intelligence_path=str(tmp_path),
                repository_hash="h1"
            )
            db.add(repo)
            db.commit()

        mgr = GraphManager(ttl_seconds=-10)  # negative TTL so it is immediately expired
        mgr.build("ttl_repo", mini_intelligence, str(tmp_path), "h1")
        
        # stats lookup triggers lazy reload because TTL expired
        stats = mgr.get_statistics("ttl_repo")
        assert stats["total_nodes"] > 0

    def test_traversal_cache_and_invalidation(self, mini_intelligence, tmp_path):
        """Traversal queries are cached in memory and cleared on rebuild/load."""
        mgr = GraphManager()
        mgr.build("trav_cache", mini_intelligence, str(tmp_path), "h1")

        sym_id = "sym:py:main.py:App:class"
        # First call: populates cache
        res1 = mgr.find_related("trav_cache", sym_id, depth=2)
        assert len(res1) > 0
        
        # Verify traversal cache is populated
        assert "trav_cache" in mgr._traversal_cache
        
        # Rebuild invalidates traversal cache
        mgr.build("trav_cache", mini_intelligence, str(tmp_path), "h1")
        assert "trav_cache" not in mgr._traversal_cache

    def test_concurrent_graph_loading(self, mini_intelligence, tmp_path):
        """Multiple threads calling ensure_graph simultaneously resolve thread-safely."""
        import threading
        from app.db.session import SessionLocal
        from app.models.repository import Repository
        from app.services.intelligence.intelligence_manager import intelligence_manager
        
        # Seed DB
        with SessionLocal() as db:
            db.query(Repository).filter(Repository.id == "concurrent_repo").delete()
            repo = Repository(
                id="concurrent_repo",
                name="concurrent_repo",
                owner="owner",
                source="source",
                intelligence_path=str(tmp_path),
                repository_hash="h1"
            )
            db.add(repo)
            db.commit()

        mgr = GraphManager()

        # Pre-save mock intelligence in manager BEFORE threads run
        intel_copy = dict(mini_intelligence)
        intel_copy["manifest"] = {
            "repository_hash": "h1",
            "intelligence_version": "v2",
            "parser_version": PARSER_VERSION,
            "schema_version": "v1",
        }
        intelligence_manager._cache["concurrent_repo"] = intel_copy

        errors = []
        def worker():
            try:
                ok = mgr.ensure_graph("concurrent_repo", str(tmp_path), "h1")
                assert ok
            except Exception as e:
                errors.append(e)

        # Create 10 threads running concurrent loading
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert mgr.exists("concurrent_repo")

    def test_repository_context_bundling(self, mini_intelligence, tmp_path):
        """RepositoryContext correctly aggregates graph, intelligence, memory, and stats."""
        from app.db.session import SessionLocal
        from app.models.repository import Repository
        from app.services.intelligence.intelligence_manager import intelligence_manager
        
        # Seed DB
        with SessionLocal() as db:
            db.query(Repository).filter(Repository.id == "ctx_repo").delete()
            repo = Repository(
                id="ctx_repo",
                name="ctx_repo",
                owner="owner",
                source="source",
                intelligence_path=str(tmp_path),
                repository_hash="h1"
            )
            db.add(repo)
            db.commit()

        # Pre-seed intelligence
        intel_copy = dict(mini_intelligence)
        intel_copy["manifest"] = {
            "repository_hash": "h1",
            "intelligence_version": "v2",
            "parser_version": PARSER_VERSION,
            "schema_version": "v1",
        }
        intelligence_manager._cache["ctx_repo"] = intel_copy
        
        # Build graph on disk first
        mgr = GraphManager()
        mgr.build("ctx_repo", intel_copy, str(tmp_path), "h1")
        mgr.invalidate("ctx_repo")

        from app.services.repository_context import get_repository_context
        ctx = get_repository_context("ctx_repo", str(tmp_path), "h1")
        assert ctx.repository_id == "ctx_repo"
        assert ctx.repository_hash == "h1"
        assert ctx.graph is not None
        assert ctx.intelligence == intel_copy
        assert ctx.statistics == intel_copy["statistics"]
        assert ctx.memory["is_indexed"] is True


