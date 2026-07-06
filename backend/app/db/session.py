from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.db.database import engine


SessionLocal = sessionmaker(
    bind=engine,

    # Don't automatically flush pending changes
    autoflush=False,

    # Explicit commits only
    autocommit=False,

    # Prevent objects from expiring after commit
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency.

    Creates one database session per request.

    Usage:

        @router.get("/")
        def endpoint(db: Session = Depends(get_db)):
            ...

    The session is automatically closed after the request.
    """

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()