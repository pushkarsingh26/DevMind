import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from app.db.database import Base

def _new_uuid() -> str:
    return str(uuid.uuid4())

class RepositoryMemoryORM(Base):
    """
    Stores historical execution summaries and audits for reuse by future agent workflows.
    """
    __tablename__ = "repository_memories"

    id = Column(String, primary_key=True, default=_new_uuid)
    repository_id = Column(
        String,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    memory_key = Column(String(100), nullable=False, index=True) # e.g. review, security, doc, general
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Relationships
    repository = relationship("Repository", back_populates="memories")

    __table_args__ = (
        Index("idx_repo_mem_key_created", "repository_id", "memory_key", "created_at"),
    )

# Avoid circular imports: import Repository at bottom
from app.models.repository import Repository
