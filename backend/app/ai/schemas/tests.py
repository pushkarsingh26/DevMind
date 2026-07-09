from pydantic import Field
from typing import List
from app.ai.schemas.base import BaseAISchema

class TestsSchema(BaseAISchema):
    """
    Structured schema representing AI suggestions for unit tests, integration tests,
    existing test coverage status, mock recommendations, and edge cases.
    """
    unit_test_suggestions: List[str] = Field(
        default_factory=list,
        description="Suggestions for unit testing classes, modules, and logical branches."
    )
    integration_test_suggestions: List[str] = Field(
        default_factory=list,
        description="Suggestions for testing route controllers, API requests, or database flows."
    )
    coverage_status: List[str] = Field(
        default_factory=list,
        description="Observations regarding missing test targets and general coverage rates."
    )
    mock_opportunities: List[str] = Field(
        default_factory=list,
        description="Suggestions on which network clients, external tools, or DB adapters should be mocked."
    )
    edge_cases: List[str] = Field(
        default_factory=list,
        description="Parameter constraints, boundary limits, and error handling edge cases to test."
    )
