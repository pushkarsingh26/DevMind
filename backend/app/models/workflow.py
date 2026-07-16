import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Float,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    Index,
    Integer,
)
from sqlalchemy.orm import relationship
from app.db.database import Base

def _new_uuid() -> str:
    return str(uuid.uuid4())

class WorkflowExecutionORM(Base):
    """
    Represents one autonomous agent workflow execution.
    """
    __tablename__ = "workflow_executions"

    id = Column(String, primary_key=True, default=_new_uuid)
    repository_id = Column(
        String,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    goal = Column(Text, nullable=False)
    workflow_type = Column(String(100), nullable=False)
    status = Column(String(64), nullable=False, default="running")  # running, completed, failed, pending_approval
    duration = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    
    # Store complex structures as serialized JSON strings for SQLite & PostgreSQL compatibility
    agents_used = Column(Text, nullable=True)     # JSON string of list[str]
    steps = Column(Text, nullable=True)           # JSON string of list[dict]
    report = Column(Text, nullable=True)          # JSON string of dict (ExecutionReport)
    diff = Column(Text, nullable=True)            # Code change diff
    affected_files = Column(Text, nullable=True)  # JSON string of list[str]
    approval_status = Column(String(32), nullable=True)  # pending, approved, rejected
    approval_reason = Column(Text, nullable=True)

    # Rich workflow states columns
    progress = Column(Integer, nullable=True, default=0)
    current_step = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    telemetry = Column(Text, nullable=True)

    # File paths for decoupled storage
    report_path = Column(String(512), nullable=True)
    logs_path = Column(String(512), nullable=True)
    graph_path = Column(String(512), nullable=True)
    diff_path = Column(String(512), nullable=True)
    telemetry_path = Column(String(512), nullable=True)

    # Relationships
    repository = relationship("Repository", back_populates="workflow_executions")

    __table_args__ = (
        Index("idx_workflow_repo_created", "repository_id", "created_at"),
    )

# Avoid circular imports: import Repository at bottom
from app.models.repository import Repository
