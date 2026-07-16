from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.database import Base

class Embedding(Base):
    __tablename__ = "embeddings"

    id = Column(String, primary_key=True)
    repository_id = Column(String, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_id = Column(String, ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False, index=True)
    embedding_model = Column(String, nullable=False)
    embedding_dimension = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Relationships
    repository = relationship("Repository", back_populates="embeddings")
    chunk = relationship("Chunk", back_populates="embeddings")

# Import related models at bottom to avoid circular import issues in SQLAlchemy registry
from app.models.repository import Repository
from app.models.chunk import Chunk

