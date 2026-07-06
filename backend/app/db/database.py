from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Every model should inherit from this class.

    Example:

        class Repository(Base):
            __tablename__ = "repositories"
            ...
    """
    pass


engine = create_engine(
    settings.DATABASE_URL,

    # Verify connections before using them
    pool_pre_ping=True,

    # Development pool settings
    pool_size=5,
    max_overflow=10,

    # Recycle idle connections every 30 minutes
    pool_recycle=1800,

    # Log SQL queries only when DEBUG=True
    echo=settings.DEBUG,

    # SQLAlchemy 2.x future behavior
    future=True,
)