from pydantic import Field
from typing import List
from app.ai.schemas.base import BaseAISchema

class BugsSchema(BaseAISchema):
    """
    Structured schema representing AI analysis for logical bugs, risk areas,
    error-prone patterns, null validations, async concerns, resources, security,
    and performance issues.
    """
    logical_issues: List[str] = Field(
        default_factory=list,
        description="Identified flaws in execution logic or implementation designs."
    )
    risk_areas: List[str] = Field(
        default_factory=list,
        description="Complex or brittle codebase layers showing regression risks."
    )
    error_prone_patterns: List[str] = Field(
        default_factory=list,
        description="Bare except handlers, silent passes, code smells, or logical defects."
    )
    null_handling_concerns: List[str] = Field(
        default_factory=list,
        description="Dereferencing properties without null validation checks."
    )
    async_concerns: List[str] = Field(
        default_factory=list,
        description="Missing awaits, sync operations inside async, or concurrency issues."
    )
    resource_management_observations: List[str] = Field(
        default_factory=list,
        description="Unclosed file streams, database connections, or socket leaks."
    )
    security_observations: List[str] = Field(
        default_factory=list,
        description="Vulnerabilities, weak cryptos, dependency risks, or lack of sanitize checks."
    )
    performance_concerns: List[str] = Field(
        default_factory=list,
        description="High memory allocations, slow loops, or N+1 query patterns."
    )
