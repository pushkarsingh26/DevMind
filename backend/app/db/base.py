"""
SQLAlchemy Metadata Registry

This module imports every SQLAlchemy model so that:

1. SQLAlchemy knows about all tables.
2. Alembic can automatically detect schema changes.
3. Future migrations work without manual registration.

Every new model MUST be imported here.

Example:

from app.models.repository import Repository
from app.models.analysis_job import AnalysisJob
"""

from app.db.database import Base

# ============================================================
# MODEL IMPORTS
# ============================================================
from app.models.repository import Repository
from app.models.job import AnalysisJobORM
from app.models.chunk import Chunk
from app.models.embedding import Embedding

__all__ = ["Base", "Repository", "AnalysisJobORM", "Chunk", "Embedding"]