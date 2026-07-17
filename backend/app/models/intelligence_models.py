from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Literal

from pydantic import BaseModel, Field


class SymbolItem(BaseModel):
    """Represents a code symbol extracted from a source file."""

    name: str = Field(..., description="Symbol name (e.g., class, function, variable).")
    type: Literal["class", "function", "method", "variable", "enum", "interface", "type_alias"] = Field(
        ..., description="Kind of symbol."
    )
    file: str = Field(..., description="Path to the file relative to the repository root.")
    line: int = Field(..., ge=1, description="Line number where the symbol is defined.")
    parent: Optional[str] = Field(
        None, description="Name of the containing class/module if applicable."
    )

    class Config:
        orm_mode = True


class RepoStatistics(BaseModel):
    """High‑level statistics of a repository used for quick overview panels."""

    languages: List[str] = Field(..., description="Programming languages detected.")
    total_files: int = Field(..., ge=0, description="Total number of files in the repository.")
    source_files: int = Field(..., ge=0, description="Files that contain source code (excluding docs, binaries, etc.).")
    classes: int = Field(..., ge=0, description="Number of class definitions.")
    functions: int = Field(..., ge=0, description="Number of function definitions.")
    imports: int = Field(..., ge=0, description="Total import statements across the codebase.")
    dependencies: int = Field(..., ge=0, description="Number of external package dependencies detected.")
    largest_files: List[str] = Field(
        [], description="Paths of the top‑N largest source files (ordered descending)."
    )
    entry_points: List[str] = Field(
        [], description="Files that contain entry‑point constructs (e.g., `if __name__ == \"__main__\"`)."
    )

    class Config:
        orm_mode = True


class RepoManifest(BaseModel):
    """Metadata describing a generated intelligence bundle for a repository."""

    repository_id: str = Field(..., description="Unique identifier of the repository (same as DB primary key).")
    repository_hash: str = Field(
        ..., description="Hash (e.g., SHA‑256) of the repository contents at generation time."
    )
    generated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of generation in UTC.")
    intelligence_version: str = Field(
        "v1", description="Version identifier of the intelligence schema, useful for migrations."
    )
    languages: List[str] = Field(..., description="Languages included in this intelligence bundle.")
    build_time_ms: int = Field(..., ge=0, description="Time taken to generate all intelligence files, in milliseconds.")

    class Config:
        orm_mode = True
