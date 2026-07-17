"""Repository Analysis Engine.

Performs deterministic, graph-based structural analysis, circular dependency detection,
unused symbol (dead code) discovery, and coupling hotspot rankings.
"""

from __future__ import annotations

import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from app.core.logger import logger
from app.services.knowledge_graph.graph_manager import graph_manager
from app.services.knowledge_graph.graph_models import KnowledgeGraph, NodeType
from app.services.repository_analysis.analysis_models import (
    AnalysisSummary,
    CircularDependency,
    DeadCodeReport,
    HotspotReport,
    ImpactResult,
    ArchitectureIssue,
)
from app.services.repository_analysis.analysis_storage import analysis_storage


class RepositoryAnalysisEngine:
    """Computes high-signal architectural insights and metrics directly from the Knowledge Graph."""

    def _get_graph(self, repo_id: str) -> Optional[KnowledgeGraph]:
        """Lazy-retrieve the Knowledge Graph via the GraphManager."""
        try:
            return graph_manager.get_graph(repo_id)
        except Exception:
            return None

    def ensure_analysis(self, repo_id: str, intelligence_path: str, repo_hash: str) -> bool:
        """Main entry point. Loads from disk if valid, otherwise computes and saves."""
        if analysis_storage.is_valid_cache(intelligence_path, repo_hash):
            logger.info(f"[AnalysisEngine] Cache is valid. Loaded analysis for {repo_id}")
            return True

        start_time = time.time()
        logger.info(f"[AnalysisEngine] Calculating analysis reports for {repo_id}...")

        # 1. Fetch Graph
        graph = self._get_graph(repo_id)
        if not graph:
            logger.warning(f"[AnalysisEngine] Cannot run analysis: Knowledge Graph is missing for {repo_id}")
            return False

        # 2. Run Analysis Routines
        circulars = self.detect_circular_dependencies(repo_id)
        dead_code = self.detect_dead_code(repo_id)
        large_modules = self.detect_large_modules(repo_id)
        hotspots = self.detect_architecture_hotspots(repo_id)

        # 3. Compile Impact mapping
        impacts: Dict[str, Any] = {}
        for nid, node in graph.nodes.items():
            if node.type == NodeType.SYMBOL:
                impacts[nid] = self.impacted_files(repo_id, nid)

        # 4. Compile Dependency paths
        dependencies: Dict[str, Any] = {}
        # Simple sample path tracing
        modules = [nid for nid, node in graph.nodes.items() if node.type == NodeType.MODULE]
        if len(modules) >= 2:
            dependencies["sample_paths"] = []
            for i in range(min(5, len(modules) - 1)):
                path = self.shortest_path(repo_id, modules[i], modules[i + 1])
                if path:
                    dependencies["sample_paths"].append({
                        "source": modules[i],
                        "target": modules[i + 1],
                        "path": path
                    })

        # 5. Build Issues list
        issues: List[ArchitectureIssue] = []
        
        for c in circulars:
            cycle_str = " -> ".join([graph.nodes[n].name for n in c.cycle if n in graph.nodes])
            issues.append(ArchitectureIssue(
                id=f"circ_{hash(cycle_str)}",
                type="circular_dependency",
                severity="high",
                message=f"Circular import path detected: {cycle_str}",
                affected_files=[graph.nodes[n].file for n in c.cycle if n in graph.nodes and graph.nodes[n].file]
            ))

        for lm in large_modules:
            issues.append(ArchitectureIssue(
                id=f"large_{hash(lm['file'])}",
                type="large_module",
                severity=lm["severity"],
                message=f"File contains {lm['symbol_count']} symbols (Complexity Hotspot)",
                affected_files=[lm["file"]]
            ))

        for hs in hotspots.hotspots[:5]:
            issues.append(ArchitectureIssue(
                id=f"hs_{hash(hs['id'])}",
                type="high_coupling",
                severity="medium" if hs["coupling_degree"] > 10 else "low",
                message=f"Component has high coupling degree of {hs['coupling_degree']} (In: {hs['in_degree']}, Out: {hs['out_degree']})",
                affected_files=[hs["file"]] if hs["file"] else []
            ))

        # 6. Build Summary
        health = 100 - (len(circulars) * 15 + len(large_modules) * 5 + len(dead_code.unused_symbols) * 2)
        health_score = max(20, min(100, health))
        
        summary = AnalysisSummary(
            repository_id=repo_id,
            repository_hash=repo_hash,
            health_score=health_score,
            total_nodes=len(graph.nodes),
            total_edges=len(graph.edges),
            issues_count=len(issues),
            build_time_ms=int((time.time() - start_time) * 1000),
            analysis_date=datetime.now(timezone.utc).isoformat(),
        )

        # 7. Save to disk
        analysis_storage.save_analysis(
            intelligence_path=intelligence_path,
            summary=summary,
            impacts=impacts,
            dependencies=dependencies,
            dead_code=dead_code,
            hotspots=hotspots,
            issues=issues,
        )
        return True

    def impacted_files(self, repo_id: str, symbol_id: str) -> List[str]:
        """Returns the list of relative file paths impacted by a symbol change."""
        graph = self._get_graph(repo_id)
        if not graph or symbol_id not in graph.nodes:
            return []

        visited = set()
        q = deque([symbol_id])
        visited.add(symbol_id)

        while q:
            curr = q.popleft()
            # Traverse predecessors: B uses A, so if A changes, B is impacted.
            for pred in graph.predecessors(curr):
                if pred not in visited:
                    visited.add(pred)
                    q.append(pred)

        files = set()
        for nid in visited:
            node = graph.nodes.get(nid)
            if node:
                if node.file:
                    files.add(node.file)
                elif node.type == NodeType.FILE:
                    files.add(node.name)
        return sorted(list(files))

    def impacted_symbols(self, repo_id: str, symbol_id: str) -> List[str]:
        """Returns the list of specific symbol IDs impacted by a symbol change."""
        graph = self._get_graph(repo_id)
        if not graph or symbol_id not in graph.nodes:
            return []

        visited = set()
        q = deque([symbol_id])
        visited.add(symbol_id)

        while q:
            curr = q.popleft()
            for pred in graph.predecessors(curr):
                if pred not in visited:
                    visited.add(pred)
                    q.append(pred)

        symbols = [nid for nid in visited if graph.nodes[nid].type == NodeType.SYMBOL and nid != symbol_id]
        return symbols

    def find_callers(self, repo_id: str, symbol_id: str) -> List[str]:
        """Returns incoming references/callers of a symbol."""
        graph = self._get_graph(repo_id)
        if not graph:
            return []
        return [pred for pred in graph.predecessors(symbol_id, rel="uses")]

    def find_callees(self, repo_id: str, symbol_id: str) -> List[str]:
        """Returns outgoing calls/references made by a symbol."""
        graph = self._get_graph(repo_id)
        if not graph:
            return []
        return [succ for succ in graph.successors(symbol_id, rel="uses")]

    def shortest_path(self, repo_id: str, source: str, target: str) -> List[str]:
        """BFS implementation to find the shortest dependency path between two nodes."""
        graph = self._get_graph(repo_id)
        if not graph or source not in graph.nodes or target not in graph.nodes:
            return []

        visited = {source: None}
        q = deque([source])

        while q:
            curr = q.popleft()
            if curr == target:
                break
            for succ in graph.successors(curr):
                if succ not in visited:
                    visited[succ] = curr
                    q.append(succ)

        if target not in visited:
            return []

        path = []
        curr = target
        while curr is not None:
            path.append(curr)
            curr = visited[curr]
        path.reverse()
        return path

    def dependency_path(self, repo_id: str, source: str, target: str) -> List[str]:
        return self.shortest_path(repo_id, source, target)

    def detect_circular_dependencies(self, repo_id: str) -> List[CircularDependency]:
        """Find cycles among modules using depth-first search."""
        graph = self._get_graph(repo_id)
        if not graph:
            return []

        modules = [nid for nid, node in graph.nodes.items() if node.type == NodeType.MODULE]
        cycles: List[List[str]] = []
        visited: Set[str] = set()

        def dfs(node: str, path: List[str], path_set: Set[str]) -> None:
            visited.add(node)
            path.append(node)
            path_set.add(node)

            for succ in graph.successors(node):
                succ_node = graph.nodes.get(succ)
                if succ_node and succ_node.type == NodeType.MODULE:
                    if succ in path_set:
                        start_idx = path.index(succ)
                        cycle_path = path[start_idx:]
                        min_node = min(cycle_path)
                        min_idx = cycle_path.index(min_node)
                        norm_cycle = cycle_path[min_idx:] + cycle_path[:min_idx]
                        if norm_cycle not in cycles:
                            cycles.append(norm_cycle)
                    elif succ not in visited:
                        dfs(succ, path, path_set)

            path.pop()
            path_set.remove(node)

        for m in modules:
            if m not in visited:
                dfs(m, [], set())

        return [CircularDependency(cycle=c, length=len(c)) for c in cycles]

    def detect_dead_code(self, repo_id: str) -> DeadCodeReport:
        """Finds symbols with zero incoming references that are not entries or public tests."""
        graph = self._get_graph(repo_id)
        if not graph:
            return DeadCodeReport()

        unused_syms = []
        for nid, node in graph.nodes.items():
            if node.type == NodeType.SYMBOL:
                # Check for incoming USES or INHERITS relationships
                incoming_refs = []
                for pred in graph.predecessors(nid):
                    for edge in graph.edges:
                        if edge.source == pred and edge.target == nid:
                            if edge.relationship in ("uses", "inherits", "implements"):
                                incoming_refs.append(pred)
                if not incoming_refs:
                    file_path = node.file or ""
                    if "test" in file_path.lower() or "main" in file_path.lower():
                        continue
                    unused_syms.append(node.to_dict())

        unused_mods = []
        for nid, node in graph.nodes.items():
            if node.type == NodeType.MODULE:
                incoming_imports = []
                for pred in graph.predecessors(nid):
                    for edge in graph.edges:
                        if edge.source == pred and edge.target == nid:
                            if edge.relationship in ("module_imports", "imports"):
                                incoming_imports.append(pred)
                if not incoming_imports:
                    file_path = node.file or ""
                    if "main" in file_path.lower() or "app" in file_path.lower():
                        continue
                    unused_mods.append(node.file or nid)

        return DeadCodeReport(
            unused_symbols=unused_syms[:30],
            unused_modules=unused_mods[:20],
            summary_count=len(unused_syms) + len(unused_mods),
        )

    def detect_unused_symbols(self, repo_id: str) -> List[Dict[str, Any]]:
        return self.detect_dead_code(repo_id).unused_symbols

    def detect_unused_modules(self, repo_id: str) -> List[str]:
        return self.detect_dead_code(repo_id).unused_modules

    def detect_large_modules(self, repo_id: str) -> List[Dict[str, Any]]:
        """Finds modules with high complexity (> 15 symbol declarations)."""
        graph = self._get_graph(repo_id)
        if not graph:
            return []

        counts: Dict[str, int] = {}
        for nid, node in graph.nodes.items():
            if node.type == NodeType.SYMBOL and node.file:
                counts[node.file] = counts.get(node.file, 0) + 1

        large = []
        for nid, node in graph.nodes.items():
            if node.type == NodeType.FILE:
                sym_cnt = counts.get(node.file, 0)
                size_kb = node.metadata.get("size_bytes", 0) / 1024
                if sym_cnt > 15 or size_kb > 50:
                    large.append({
                        "file": node.file,
                        "symbol_count": sym_cnt,
                        "size_kb": round(size_kb, 2),
                        "severity": "high" if sym_cnt > 30 else "medium",
                    })
        return sorted(large, key=lambda x: x["symbol_count"], reverse=True)

    def detect_architecture_hotspots(self, repo_id: str) -> HotspotReport:
        """Finds files/symbols with the highest degree centralities (coupling degree)."""
        graph = self._get_graph(repo_id)
        if not graph:
            return HotspotReport()

        hotspots = []
        for nid, node in graph.nodes.items():
            if node.type in (NodeType.FILE, NodeType.MODULE, NodeType.SYMBOL):
                in_deg = len(graph.predecessors(nid))
                out_deg = len(graph.successors(nid))
                total = in_deg + out_deg
                if total > 1:
                    hotspots.append({
                        "id": nid,
                        "name": node.name,
                        "type": node.type,
                        "file": node.file,
                        "coupling_degree": total,
                        "in_degree": in_deg,
                        "out_degree": out_deg,
                    })

        hotspots.sort(key=lambda x: x["coupling_degree"], reverse=True)
        max_deg = hotspots[0]["coupling_degree"] if hotspots else 0
        return HotspotReport(hotspots=hotspots[:20], max_coupling_degree=max_deg)

    def repository_summary(self, repo_id: str) -> Dict[str, Any]:
        """Provides an aggregated summary count dictionary."""
        graph = self._get_graph(repo_id)
        if not graph:
            return {}
        summary_obj = analysis_storage.load_summary(repo_id) or {}
        return summary_obj


repository_analysis_engine = RepositoryAnalysisEngine()
