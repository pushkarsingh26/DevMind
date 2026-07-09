from pydantic import Field
from typing import List
from app.ai.schemas.base import BaseAISchema

class ExplainSchema(BaseAISchema):
    """
    Structured schema representing AI analysis explaining the repository high-level
    architecture, entry points, component structures, modules, and execution/data flows.
    """
    high_level_architecture: List[str] = Field(
        default_factory=list,
        description="High-level description of application patterns (MVC, microservices, etc.)."
    )
    entry_points: List[str] = Field(
        default_factory=list,
        description="List of core code files acting as entry points (e.g. main.py, index.js)."
    )
    component_relationships: List[str] = Field(
        default_factory=list,
        description="Detailed description of component relationships, dependencies, and imports."
    )
    important_modules: List[str] = Field(
        default_factory=list,
        description="Highlight modules containing key logical execution paths."
    )
    execution_flow: List[str] = Field(
        default_factory=list,
        description="Step-by-step description of run execution when triggering the entry points."
    )
    data_flow: str = Field(
        ...,
        description="Summary of how variables, requests, and datasets propagate through codebase layers."
    )
