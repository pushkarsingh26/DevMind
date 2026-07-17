"""Version constants for the Knowledge Graph layer.

Versioning strategy
-------------------
Three independent version strings govern graph cache validity.

GRAPH_VERSION
    Bumped when the overall graph build pipeline changes (new build stages,
    new output sections, new node/edge types added).

GRAPH_SCHEMA_VERSION
    Bumped when the JSON schema of nodes, edges, or metadata changes in a
    breaking way (field renamed/removed, type changed).

GRAPH_GENERATOR_VERSION
    Bumped when the generator logic changes in a way that produces
    structurally different results for the same input (new relationship
    discovery, changed confidence scoring, edge deduplication rules).

A cached knowledge graph is ONLY valid when ALL THREE version strings AND
the repository_hash match the current constants.

Separation from intelligence versions
--------------------------------------
The graph versions are intentionally independent from the intelligence layer
versions (INTELLIGENCE_VERSION, PARSER_VERSION, etc.).  This allows:

- Intelligence rebuild without graph rebuild when only parsing changes.
- Graph rebuild without intelligence rebuild when only graph logic changes.
- Surgical cache invalidation at each layer independently.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Version constants
# ---------------------------------------------------------------------------

GRAPH_VERSION: str = "v1"
"""Bumped when graph build pipeline structure changes."""

GRAPH_SCHEMA_VERSION: str = "v1"
"""Bumped when node/edge/metadata JSON schema changes."""

GRAPH_GENERATOR_VERSION: str = "0.1.0"
"""Bumped when graph generator logic changes output for the same input."""

# ---------------------------------------------------------------------------
# Generator metadata
# ---------------------------------------------------------------------------

GRAPH_GENERATOR_NAME: str = "devmind-knowledge-graph"

# ---------------------------------------------------------------------------
# Output file name
# ---------------------------------------------------------------------------

GRAPH_FILE_NAME: str = "knowledge_graph.json"

# ---------------------------------------------------------------------------
# Node type constants (duplicated here for validation without circular import)
# ---------------------------------------------------------------------------

VALID_NODE_TYPES: frozenset = frozenset({
    "file", "module", "symbol", "dependency", "entry_point",
})

# ---------------------------------------------------------------------------
# Edge relationship constants (for validation)
# ---------------------------------------------------------------------------

VALID_EDGE_RELATIONS: frozenset = frozenset({
    "contains", "defines", "imports", "depends_on",
    "inherits", "implements", "uses", "module_imports", "entry_to",
})

# ---------------------------------------------------------------------------
# Self-loop policy: relationships where source == target is allowed
# ---------------------------------------------------------------------------

SELF_LOOP_ALLOWED: frozenset = frozenset()  # none allowed by default
