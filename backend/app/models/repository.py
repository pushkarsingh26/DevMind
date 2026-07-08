from sqlalchemy import Column, String, DateTime, Integer, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    owner = Column(String, nullable=False)
    source = Column(String, nullable=False)
    framework = Column(String, nullable=True)
    language = Column(String, nullable=True)
    repository_hash = Column(String, nullable=True, index=True)
    status = Column(String, nullable=False, default="INDEXING")  # INDEXING, READY, FAILED, DELETED
    
    default_branch = Column(String, nullable=True)
    readme_present = Column(Boolean, nullable=True)
    license = Column(String, nullable=True)
    docker_support = Column(Boolean, nullable=True)
    github_actions = Column(Boolean, nullable=True)
    cicd = Column(Boolean, nullable=True)
    tests_present = Column(Boolean, nullable=True)

    total_files = Column(Integer, nullable=True)
    directories = Column(Integer, nullable=True)
    extensions = Column(JSON, nullable=True)
    largest_files = Column(JSON, nullable=True)
    dependencies = Column(JSON, nullable=True)
    package_managers = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)



    # Relationships
    jobs = relationship("AnalysisJobORM", back_populates="repository", cascade="all, delete-orphan")
    chunks = relationship("Chunk", back_populates="repository", cascade="all, delete-orphan")
    embeddings = relationship("Embedding", back_populates="repository", cascade="all, delete-orphan")

# Import related models at bottom to avoid circular import issues in SQLAlchemy registry
from app.models.job import AnalysisJobORM
from app.models.chunk import Chunk
from app.models.embedding import Embedding

