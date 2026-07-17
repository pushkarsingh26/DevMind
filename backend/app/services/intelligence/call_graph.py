"""Call Graph Foundation for the Repository Intelligence layer.

Phase 8.3 will implement full call graph generation.
This module defines the models, placeholder, and serialization format
so that WorkflowEngine can plug in later without redesigning the
intelligence layer or requiring migration logic.

Public API
----------
CallGraphBuilder   – stub builder; returns a placeholder
serialize()        – produce the dict written to call_graph.json
deserialize()      – reconstruct from a stored dict
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.services.intelligence.models import (
    CallGraphEdge,
    CallGraphNode,
    CallGraphPlaceholder,
)

# ---------------------------------------------------------------------------
# Current graph version
# ---------------------------------------------------------------------------

CALL_GRAPH_VERSION: str = "v0"
"""v0 = placeholder only.  Bump to v1 when full extraction is implemented."""


# ---------------------------------------------------------------------------
# Builder (stub)
# ---------------------------------------------------------------------------

class CallGraphBuilder:
    """Placeholder builder.

    Phase 8.3 will replace this with real call-site analysis.
    The public interface (``build()``, ``serialize()``) must stay stable.
    """

    def build(
        self,
        symbols: List[Dict[str, Any]],
        imports: List[Dict[str, Any]],
    ) -> CallGraphPlaceholder:
        """Return an empty placeholder graph.

        Parameters
        ----------
        symbols:
            List of symbol dicts from the intelligence layer.
        imports:
            List of import dicts from the intelligence layer.
        """
        return CallGraphPlaceholder(
            status="not_built",
            version=CALL_GRAPH_VERSION,
            generated_at=None,
            nodes=[],
            edges=[],
            message=(
                "Call graph will be built in Phase 8.3. "
                "Symbols and imports are available for future analysis."
            ),
        )

    def serialize(self, graph: CallGraphPlaceholder) -> Dict[str, Any]:
        """Convert a ``CallGraphPlaceholder`` to a JSON-serialisable dict."""
        return graph.to_dict()

    def deserialize(self, data: Dict[str, Any]) -> CallGraphPlaceholder:
        """Reconstruct a ``CallGraphPlaceholder`` from a stored dict."""
        return CallGraphPlaceholder(
            status=data.get("status", "not_built"),
            version=data.get("version", CALL_GRAPH_VERSION),
            generated_at=data.get("generated_at"),
            nodes=data.get("nodes", []),
            edges=data.get("edges", []),
            message=data.get("message", ""),
        )


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

_builder = CallGraphBuilder()


def build_placeholder(
    symbols: List[Dict[str, Any]],
    imports: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Build and serialize the call graph placeholder.

    This is the function called by IntelligenceService.
    """
    graph = _builder.build(symbols, imports)
    return _builder.serialize(graph)
