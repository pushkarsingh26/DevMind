"""pytest test suite for Phase 8.3 Repository Analysis Engine.
"""

from __future__ import annotations

import tempfile
import time
from pathlib import Path
import pytest

from app.services.knowledge_graph.graph_models import (
    GraphEdge,
    GraphNode,
    KnowledgeGraph,
    NodeType,
)
from app.services.knowledge_graph.graph_manager import graph_manager
from app.services.repository_analysis.analysis_models import (
    AnalysisSummary,
    CircularDependency,
    DeadCodeReport,
    HotspotReport,
)
from app.services.repository_analysis.analysis_engine import repository_analysis_engine
from app.services.repository_analysis.analysis_storage import analysis_storage


@pytest.fixture()
def sample_graph():
    """Create a mock graph with cycles, dead code, and hotspots.
    
    Graph Topology:
    - Files: file_A, file_B, file_C (cycle A -> B -> C -> A)
    - Symbols: sym_X (in file_A), sym_Y (in file_B), sym_Z (in file_C)
    - sym_X -[uses]-> sym_Y -[uses]-> sym_Z
    - Orphan/Dead Symbol: sym_orphan (no incoming edges, in file_C)
    """
    graph = KnowledgeGraph(repository_id="test_repo", repository_hash="hash123")
    
    # 1. Add nodes
    # File nodes (modules)
    graph.add_node(GraphNode(id="module:file_A", name="file_A", type=NodeType.MODULE, file="file_A"))
    graph.add_node(GraphNode(id="module:file_B", name="file_B", type=NodeType.MODULE, file="file_B"))
    graph.add_node(GraphNode(id="module:file_C", name="file_C", type=NodeType.MODULE, file="file_C"))
    
    # Symbol nodes
    graph.add_node(GraphNode(id="symbol:sym_X", name="sym_X", type=NodeType.SYMBOL, file="file_A"))
    graph.add_node(GraphNode(id="symbol:sym_Y", name="sym_Y", type=NodeType.SYMBOL, file="file_B"))
    graph.add_node(GraphNode(id="symbol:sym_Z", name="sym_Z", type=NodeType.SYMBOL, file="file_C"))
    graph.add_node(GraphNode(id="symbol:sym_orphan", name="sym_orphan", type=NodeType.SYMBOL, file="file_C"))
    
    # 2. Add edges
    # Cycle among modules (A -> B -> C -> A)
    graph.add_edge(GraphEdge(source="module:file_A", target="module:file_B", relationship="imports"))
    graph.add_edge(GraphEdge(source="module:file_B", target="module:file_C", relationship="imports"))
    graph.add_edge(GraphEdge(source="module:file_C", target="module:file_A", relationship="imports"))
    
    # Dependencies among symbols
    graph.add_edge(GraphEdge(source="symbol:sym_X", target="symbol:sym_Y", relationship="uses"))
    graph.add_edge(GraphEdge(source="symbol:sym_Y", target="symbol:sym_Z", relationship="uses"))
    
    # defines edges (File defines symbol)
    graph.add_edge(GraphEdge(source="module:file_A", target="symbol:sym_X", relationship="defines"))
    graph.add_edge(GraphEdge(source="module:file_B", target="symbol:sym_Y", relationship="defines"))
    graph.add_edge(GraphEdge(source="module:file_C", target="symbol:sym_Z", relationship="defines"))
    graph.add_edge(GraphEdge(source="module:file_C", target="symbol:sym_orphan", relationship="defines"))
    
    return graph


def test_circular_dependency_detection(sample_graph):
    # Bind the graph to graph_manager cache for testing
    graph_manager._cache["test_repo"] = (sample_graph, time.time())
    
    circulars = repository_analysis_engine.detect_circular_dependencies("test_repo")
    assert len(circulars) >= 1
    cycle_files = circulars[0].cycle
    assert "module:file_A" in cycle_files
    assert "module:file_B" in cycle_files
    assert "module:file_C" in cycle_files


def test_dead_code_detection(sample_graph):
    graph_manager._cache["test_repo"] = (sample_graph, time.time())
    
    dead_report = repository_analysis_engine.detect_dead_code("test_repo")
    unused_names = [s["name"] for s in dead_report.unused_symbols]
    
    # sym_orphan has no incoming references/uses, so it should be identified
    assert "sym_orphan" in unused_names
    # sym_X also has no incoming references, so it counts as dead code
    assert "sym_X" in unused_names
    # sym_Y is used by sym_X, so it is NOT dead
    assert "sym_Y" not in unused_names


def test_coupling_hotspots(sample_graph):
    graph_manager._cache["test_repo"] = (sample_graph, time.time())
    
    hotspots = repository_analysis_engine.detect_architecture_hotspots("test_repo")
    assert len(hotspots.hotspots) > 0
    # module:file_B has out-degree 1 (imports file_C) and in-degree 1 (imported by file_A) + symbol defines
    # So it should be ranked
    assert any(h["name"] == "file_B" for h in hotspots.hotspots)


def test_impact_analysis(sample_graph):
    graph_manager._cache["test_repo"] = (sample_graph, time.time())
    
    # If sym_Z is modified, who is impacted?
    # sym_Y uses sym_Z, sym_X uses sym_Y. So both are impacted!
    impacted_symbols = repository_analysis_engine.impacted_symbols("test_repo", "symbol:sym_Z")
    assert "symbol:sym_Y" in impacted_symbols
    assert "symbol:sym_X" in impacted_symbols
    
    impacted_files = repository_analysis_engine.impacted_files("test_repo", "symbol:sym_Z")
    assert "file_A" in impacted_files
    assert "file_B" in impacted_files


def test_shortest_path(sample_graph):
    graph_manager._cache["test_repo"] = (sample_graph, time.time())
    
    # shortest path from module:file_A to module:file_C: file_A -> file_B -> file_C
    path = repository_analysis_engine.shortest_path("test_repo", "module:file_A", "module:file_C")
    assert path == ["module:file_A", "module:file_B", "module:file_C"]


def test_analysis_storage_cache():
    with tempfile.TemporaryDirectory() as tmpdir:
        intel_path = Path(tmpdir) / "intelligence"
        intel_path.mkdir()
        
        # Check invalid cache initially
        assert not analysis_storage.is_valid_cache(str(intel_path), "hash123")
        
        summary = AnalysisSummary(
            repository_id="test_repo",
            repository_hash="hash123",
            health_score=95,
            total_nodes=10,
            total_edges=20,
            issues_count=1,
            build_time_ms=150,
            analysis_date="2026-07-17T12:00:00Z"
        )
        
        dead_code = DeadCodeReport(unused_symbols=[], unused_modules=[], summary_count=0)
        hotspots = HotspotReport(hotspots=[], max_coupling_degree=0)
        
        # Save analysis
        analysis_storage.save_analysis(
            intelligence_path=str(intel_path),
            summary=summary,
            impacts={},
            dependencies={},
            dead_code=dead_code,
            hotspots=hotspots,
            issues=[]
        )
        
        # Cache should now be valid for the same hash
        assert analysis_storage.is_valid_cache(str(intel_path), "hash123")
        
        # Cache should be invalid for a different hash
        assert not analysis_storage.is_valid_cache(str(intel_path), "different_hash")
