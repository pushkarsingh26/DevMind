"""Knowledge Graph package.

Public surface
--------------
    graph_manager   ← singleton GraphManager (use this everywhere)
    graph_builder   ← singleton GraphBuilder (used by graph_manager internally)
    graph_storage   ← module (functions, used by graph_manager internally)

External callers should interact ONLY with ``graph_manager``.
"""

from app.services.knowledge_graph.graph_manager import graph_manager
from app.services.knowledge_graph.graph_builder import graph_builder
from app.services.knowledge_graph import graph_storage

__all__ = ["graph_manager", "graph_builder", "graph_storage"]
