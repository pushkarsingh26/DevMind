from pydantic import Field
from typing import List
from app.ai.schemas.base import BaseAISchema

class ReviewSchema(BaseAISchema):
    """
    Structured schema representing AI code review findings, strengths, improvements,
    security, performance, maintainability, and actionable recommendations.
    """
    executive_summary: str = Field(
        ...,
        description="General executive summary of the repository architecture and quality."
    )
    strengths: List[str] = Field(
        default_factory=list,
        description="Identified architectural, organizational, or logical strengths."
    )
    improvements: List[str] = Field(
        default_factory=list,
        description="Identified architecture flaws, bad design patterns, or logical concerns."
    )
    security_observations: List[str] = Field(
        default_factory=list,
        description="Observations regarding secrets leak, vulnerability usage, or poor sanitization."
    )
    performance_observations: List[str] = Field(
        default_factory=list,
        description="Observations regarding time/space complexity, resource locks, or high cost operations."
    )
    maintainability_observations: List[str] = Field(
        default_factory=list,
        description="Observations regarding readability, formatting rules, circular coupling, or documentation gaps."
    )
    recommendations: List[str] = Field(
        default_factory=list,
        description="Actionable advice list to improve repository architecture and code quality."
    )
