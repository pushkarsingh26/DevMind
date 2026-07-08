from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.db.database import Base

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True)
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_job_id = Column(String, ForeignKey("analysis_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String, nullable=False)
    language = Column(String, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    # Relationships
    repository = relationship("Repository", back_populates="chunks")
    job = relationship("AnalysisJobORM", back_populates="chunks")
    embeddings = relationship("Embedding", back_populates="chunk", cascade="all, delete-orphan")

# Import related models at bottom to avoid circular import issues in SQLAlchemy registry
from app.models.repository import Repository
from app.models.job import AnalysisJobORM
from app.models.embedding import Embedding

