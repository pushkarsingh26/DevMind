"""Impact Reasoner — deterministic impact analysis.

Consumes ReasoningContext + DependencyReasoning to produce ImpactReasoning.
All arithmetic is deterministic and bounded to [0.0, 1.0].
All output lists are sorted before return.
"""

from __future__ import annotations

from typing import Any, Dict, List, Set

from app.core.logger import logger
from app.services.reasoning.reasoning_models import (
    DependencyReasoning,
    ImpactReasoning,
    ReasoningContext,
)

_DOC_EXTENSIONS = (".md", ".rst", ".txt", ".adoc")
_TEST_PREFIXES = ("test_", "tests/", "test/", "__tests__/", "spec/")


def _is_test_file(path: str) -> bool:
    lower = path.lower().replace("\\", "/")
    return any(lower.startswith(p) or f"/{p}" in lower for p in _TEST_PREFIXES) or \
           any(part.startswith("test_") for part in lower.split("/"))


def _is_doc_file(path: str) -> bool:
    return path.lower().endswith(_DOC_EXTENSIONS)


class ImpactReasoner:

    def reason(
        self,
        context: ReasoningContext,
        dependency_reasoning: DependencyReasoning,
    ) -> ImpactReasoning:
        logger.debug(f"[ImpactReasoner] Running for {context.repository_id}")

        total_files = context.intelligence_summary.get("file_count", 1) or 1
        critical_files = dependency_reasoning.critical_files
        transitive = dependency_reasoning.transitive_impact
        hotspot_history: Dict[str, int] = context.memory_summary.get("hotspot_history", {})

        # 1. Direct impact — the critical files themselves
        direct_impact = sorted(critical_files)

        # 2. Indirect impact — transitive minus direct
        direct_set = set(direct_impact)
        indirect_impact = sorted([f for f in transitive if f not in direct_set])

        # 3. Repository-wide impact
        repository_wide_impact = (len(indirect_impact) / total_files) >= 0.20

        # 4. Breaking change probability
        # = (critical_count / total_files) * avg_in_degree_of_critical, clamped [0,1]
        try:
            from app.services.knowledge_graph.graph_manager import graph_manager
            graph = graph_manager.get_graph(context.repository_id)
        except Exception:
            graph = None

        if graph and graph.nodes and critical_files:
            in_degrees = []
            for edge in graph.edges:
                target = edge.target if hasattr(edge, "target") else edge.get("target", "")
                if target in graph.nodes:
                    node = graph.nodes[target]
                    name = node.name or target
                    if name in direct_set:
                        in_degrees.append(1)
            avg_in_degree = (sum(in_degrees) / max(len(in_degrees), 1)) if in_degrees else 1.0
            breaking_change_probability = min(
                1.0,
                (len(critical_files) / total_files) * avg_in_degree
            )
        else:
            breaking_change_probability = min(1.0, len(critical_files) / max(total_files, 1))

        # 5. Refactor impact score
        # = Σ(hotspot_frequency[f]) / max(total_files, 1), clamped [0,1]
        hotspot_sum = sum(hotspot_history.get(f, 0) for f in critical_files)
        refactor_impact_score = min(1.0, hotspot_sum / max(total_files, 1))

        # 6. Test impact — test files reachable from affected set
        all_affected = set(direct_impact) | set(indirect_impact)
        test_impact = sorted([f for f in all_affected if _is_test_file(f)])

        # 7. Documentation impact — doc files adjacent to affected modules
        documentation_impact = sorted([f for f in all_affected if _is_doc_file(f)])

        return ImpactReasoning(
            direct_impact=direct_impact,
            indirect_impact=indirect_impact,
            repository_wide_impact=repository_wide_impact,
            breaking_change_probability=round(breaking_change_probability, 4),
            refactor_impact_score=round(refactor_impact_score, 4),
            test_impact=test_impact,
            documentation_impact=documentation_impact,
        )


impact_reasoner = ImpactReasoner()
