from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.core.constants import TaskType
from app.services.scanner_service import RepositoryMetadata
from app.services.chunk_service import CodeChunk

class AnalysisJob(BaseModel):
    id: str = Field(..., description="Unique job UUID string")
    task_type: TaskType = Field(..., description="Pipeline objective")
    repo_identifier: str = Field(..., description="Local repo path or folder name")
    start_time: float = Field(..., description="Unix timestamp of when the job registered")
    
    status: str = Field("running", description="Status string: running, completed, failed")
    progress: int = Field(0, description="Percentage complete (0-100)")
    current_stage: str = Field("Initializing", description="Description string of active task stage")
    
    # Improved fields for future AI ingestion
    repository_metadata: Optional[RepositoryMetadata] = Field(None, description="Detailed codebase structure metadata")
    chunks: Optional[List[CodeChunk]] = Field(None, description="Collection of parsed code segments")
    result: Optional[Dict[str, Any]] = Field(None, description="Structured analysis result dictionary")
    
    created_at: float = Field(..., description="Unix timestamp of when the job was created")
    updated_at: float = Field(..., description="Unix timestamp of when the job was last updated")
    error: Optional[str] = Field(None, description="Details of analysis error if status is failed")


# SQLAlchemy persistent database model
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base as DBBase

class AnalysisJobORM(DBBase):
    __tablename__ = "analysis_jobs"

    id = Column(String, primary_key=True)
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=True, index=True)
    task_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    progress = Column(Integer, nullable=False, default=0)
    current_stage = Column(String, nullable=True)
    result = Column(Text, nullable=True)  # Stored as serialized JSON string
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    repository = relationship("Repository", back_populates="jobs")
    chunks = relationship("Chunk", back_populates="job", cascade="all, delete-orphan")

# Import related models at bottom to avoid circular import issues in SQLAlchemy registry
from app.models.repository import Repository
from app.models.chunk import Chunk


