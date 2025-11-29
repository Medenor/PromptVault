"""Database session management for PromptVault.

This module provides SQLAlchemy engine and session factory configuration.
It handles both PostgreSQL and SQLite databases with appropriate connection
pooling and session lifecycle management.

Usage:
    # Context manager approach (recommended for service layer)
    from src.db.session import get_db_session

    with get_db_session() as session:
        # Perform database operations
        prompt = session.query(Prompt).first()
        # Auto-commits on success, auto-rolls back on exception

    # FastAPI dependency injection approach
    from src.db.session import get_db

    @app.get("/prompts")
    def list_prompts(db: Session = Depends(get_db)):
        return db.query(Prompt).all()
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator
import logging

from src.db.config import db_settings

logger = logging.getLogger(__name__)


# Create SQLAlchemy engine with appropriate configuration
engine_kwargs = db_settings.get_engine_kwargs()

engine = create_engine(
    db_settings.DATABASE_URL,
    **engine_kwargs
)

# Log database connection info
logger.info(f"Database engine created: {db_settings.database_type}")
if db_settings.DB_ECHO:
    logger.info("SQL query logging is ENABLED")


# SQLite-specific configuration
if db_settings.is_sqlite:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Enable foreign key constraints for SQLite.

        SQLite doesn't enforce foreign key constraints by default.
        This event handler enables them for each new connection.
        """
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
        logger.debug("SQLite PRAGMA foreign_keys enabled")


# Create session factory
# autocommit=False: Transactions must be explicitly committed
# autoflush=False: Changes aren't automatically flushed to DB
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """Context manager for database sessions with automatic transaction management.

    This is the recommended approach for service layer code. It automatically
    handles commit/rollback and session cleanup.

    Yields:
        Session: SQLAlchemy session object

    Example:
        with get_db_session() as session:
            prompt = Prompt(title="Example", prompt="Test")
            session.add(prompt)
            # Auto-commits on success
        # Session automatically closed

    Raises:
        Exception: Any database exception (session will auto-rollback)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
        logger.debug("Database session committed successfully")
    except Exception as e:
        session.rollback()
        logger.error(f"Database session rolled back due to error: {e}")
        raise
    finally:
        session.close()
        logger.debug("Database session closed")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions.

    This function is designed to be used with FastAPI's Depends() injection.
    Unlike get_db_session(), this does NOT auto-commit. The caller is
    responsible for committing transactions.

    Yields:
        Session: SQLAlchemy session object

    Example:
        @router.post("/prompts")
        def create_prompt(
            prompt_data: PromptCreateRequest,
            db: Session = Depends(get_db)
        ):
            prompt = Prompt(**prompt_data.dict())
            db.add(prompt)
            db.commit()
            return prompt

    Note:
        The session is automatically closed after the request completes,
        but you must manually call db.commit() or db.rollback().
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
        logger.debug("FastAPI database dependency session closed")


def create_all_tables():
    """Create all database tables based on SQLAlchemy models.

    This is a utility function for development and testing. In production,
    use Alembic migrations instead.

    Warning:
        This does NOT drop existing tables. Use with caution.
    """
    from src.db.base import Base
    Base.metadata.create_all(bind=engine)
    logger.info("All database tables created")


def drop_all_tables():
    """Drop all database tables.

    WARNING: This permanently deletes all data. Use only in development/testing.

    Raises:
        RuntimeError: If attempted in production environment
    """
    if not db_settings.is_sqlite or "test" not in db_settings.DATABASE_URL.lower():
        raise RuntimeError(
            "drop_all_tables() can only be used with test databases. "
            "Use Alembic migrations for production schema changes."
        )

    from src.db.base import Base
    Base.metadata.drop_all(bind=engine)
    logger.warning("All database tables dropped")
