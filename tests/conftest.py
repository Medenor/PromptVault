# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Comprehensive test fixtures for PromptVault test suite.

This module provides pytest fixtures for testing with database backend,
using in-memory SQLite for fast, isolated tests. All JSON-based fixtures
have been removed as the application now uses SQLite/PostgreSQL.

Fixture Categories:
    - Database Fixtures: Engine, session, and connection management
    - Model Fixtures: Pre-configured database models (User, Category, Tag, Prompt)
    - Repository Fixtures: Repository instances with test session
    - Service Fixtures: Service layer with test database
    - Data Factory Fixtures: Helper functions to generate test data
    - API Test Client: FastAPI TestClient with database backend
"""

import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Generator, Callable, Dict, Any, List
from datetime import datetime, timedelta, timezone

# Ensure AUTH_ENABLED=true before any src.* imports so that auth routes
# (including /api/admin/*) are mounted when the app module is loaded.
os.environ.setdefault("AUTH_ENABLED", "true")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import database components
from src.db.base import Base
from src.db.models import (
    User,
    Category,
    Tag,
    Prompt,
    PromptVersion,
    PromptBranch,
    Backup,
    BackupSchedule,
    BackupStorageProvider,
    AuditLogEntry,
    EncryptionKeyConfig,
    prompt_tags,
)
from src.db.repositories import (
    PromptRepository,
    VersionRepository,
    CategoryRepository,
    TagRepository,
)

# Import services
from src.services.prompt_data_service_db import PromptDataService
from src.services.backup_service_db import BackupService
from src.services.backup_encryption_service import BackupEncryptionService
from src.services.backup_cloud_service import BackupCloudService
from src.services.backup_scheduler_service import BackupSchedulerService
from src.services.backup_audit_service import BackupAuditService
from src.services.prompt_filter_service import PromptFilterService
from src.services.prompt_import_export_service import PromptImportExportService
from src.services.prompt_versioning_service import PromptVersioningService

# ============================================================================
# ENVIRONMENT SETUP FOR TESTS
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up environment variables for all tests.

    This fixture runs once per test session and ensures that rate limiting
    is disabled for tests to prevent 429 responses during test execution.
    """
    # Disable rate limiting during tests
    os.environ["DISABLE_RATE_LIMITING"] = "true"
    yield


# ============================================================================
# DATABASE RESET FIXTURE (for backward compatibility)
# ============================================================================


@pytest.fixture(autouse=True, scope="function")
def reset_database(request):
    """
    Autouse fixture that drops and recreates the test database before each test.

    This ensures test isolation for tests using the shared test database
    (e.g., API endpoint tests). Tests using in-memory SQLite via test_db_engine
    fixture are automatically skipped.

    This fixture provides backward compatibility with existing test files that
    rely on database resets between tests (e.g., test_api_endpoints.py).
    """
    # Skip database reset if test uses test_db_engine (in-memory DB)
    # Check if test_db_engine is in the test's fixture dependencies
    if "test_db_engine" in request.fixturenames:
        yield
        return

    # Also skip for tests that use api_client_context (which uses test_db_engine internally)
    if "api_client_context" in request.fixturenames:
        yield
        return

    # Only reset for tests using the persistent database
    from src.db.session import drop_all_tables, create_all_tables
    from src.db.models import (
        User,
        Category,
        Tag,
        Prompt,
        PromptVersion,
        PromptBranch,
        Backup,
        BackupSchedule,
        BackupStorageProvider,
        AuditLogEntry,
        EncryptionKeyConfig,
        prompt_tags,
    )

    try:
        drop_all_tables()
        create_all_tables()
    except Exception as e:
        # Silently skip if database operations fail
        pass

    yield

    # Optionally clean up after test
    try:
        drop_all_tables()
    except Exception:
        pass


# ============================================================================
# DATABASE FIXTURES
# ============================================================================


@pytest.fixture(scope="function")
def test_db_engine(request):
    """Create in-memory SQLite engine for tests.

    Each test gets a fresh database that is automatically cleaned up.
    Uses function scope to ensure complete isolation between tests.

    For tests using FastAPI TestClient (multi-threaded), uses a shared
    cache connection to allow the same in-memory database to be accessed
    across threads within one test. Each test gets a unique database name to ensure isolation.

    Yields:
        Engine: SQLAlchemy engine with all tables created
    """
    # Use file::memory:?cache=shared with unique db name for multi-threaded access
    # This allows the in-memory DB to be shared across threads within one test
    # but isolated between different tests
    import uuid

    # Ensure all models are imported before creating tables
    from src.db.models import (
        User,
        Category,
        Tag,
        Prompt,
        PromptVersion,
        PromptBranch,
        Backup,
        BackupSchedule,
        BackupStorageProvider,
        AuditLogEntry,
        EncryptionKeyConfig,
        prompt_tags,
    )

    db_name = f"test_db_{uuid.uuid4().hex}"

    engine = create_engine(
        f"sqlite:///file:{db_name}?mode=memory&cache=shared&uri=true",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session, None, None]:
    """Create test database session with automatic rollback.

    Uses in-memory SQLite for fast, isolated tests.
    Session is automatically rolled back and closed after each test,
    ensuring no state leaks between tests.

    Yields:
        Session: SQLAlchemy session object
    """
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


# ============================================================================
# MODEL FIXTURES
# ============================================================================


@pytest.fixture
def test_user(test_db_session: Session) -> User:
    """Create a test user.

    Returns:
        User: Test user with username 'test_user'
    """
    user = User(
        id="test-user-id",
        username="test_user",
        display_name="Test User",
        email="test@example.com",
        password_hash="hashed_password_placeholder",  # Required field
        role="user",
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture
def test_category(test_db_session: Session) -> Category:
    """Create a test category.

    Returns:
        Category: Test category named 'Test Category'
    """
    category = Category(name="Test Category", description="Category for testing")
    test_db_session.add(category)
    test_db_session.flush()
    return category


@pytest.fixture
def test_tags(test_db_session: Session) -> List[Tag]:
    """Create multiple test tags.

    Returns:
        List[Tag]: List of three tags: 'test', 'sample', 'python'
    """
    tags = [
        Tag(name="test"),
        Tag(name="sample"),
        Tag(name="python"),
    ]
    test_db_session.add_all(tags)
    test_db_session.flush()
    return tags


@pytest.fixture
def test_prompt(
    test_db_session: Session,
    test_user: User,
    test_category: Category,
    test_tags: List[Tag],
) -> Prompt:
    """Create a test prompt with relationships.

    Args:
        test_db_session: Database session
        test_user: Test user fixture
        test_category: Test category fixture
        test_tags: Test tags fixture

    Returns:
        Prompt: Test prompt with category and tags
    """
    prompt = Prompt(
        title="Test Prompt",
        prompt="This is a test prompt content",
        category_id=test_category.id,
        note="Test note",
        favorite=False,
        user_id=test_user.id,
    )
    # Add first two tags to the prompt
    prompt.tags.extend(test_tags[:2])
    test_db_session.add(prompt)
    test_db_session.flush()
    return prompt


@pytest.fixture
def test_prompt_with_versions(
    test_db_session: Session, test_prompt: Prompt, test_user: User
) -> tuple[Prompt, List[PromptVersion]]:
    """Create a prompt with multiple versions for version control testing.

    Args:
        test_db_session: Database session
        test_prompt: Test prompt fixture
        test_user: Test user fixture

    Returns:
        tuple: (Prompt, List of 3 PromptVersion objects)
    """
    versions = []

    # Create 3 versions with linear history
    for i in range(3):
        version = PromptVersion(
            prompt_id=test_prompt.id,
            version_id=f"version-{i}",
            version_number=i + 1,
            title=f"Test Prompt v{i+1}",
            prompt=f"Content v{i+1}",
            note=f"Note v{i+1}",
            tags=["test", "sample"],
            favorite=False,
            author=test_user.username,
            message=f"Version {i+1}",
            parent_version_id=versions[-1].version_id if versions else None,
        )
        test_db_session.add(version)
        test_db_session.flush()
        versions.append(version)

    return test_prompt, versions


# ============================================================================
# REPOSITORY FIXTURES
# ============================================================================


@pytest.fixture
def prompt_repo(test_db_session: Session) -> PromptRepository:
    """Create a PromptRepository instance.

    Args:
        test_db_session: Database session

    Returns:
        PromptRepository: Repository for prompt operations
    """
    return PromptRepository(test_db_session)


@pytest.fixture
def version_repo(test_db_session: Session) -> VersionRepository:
    """Create a VersionRepository instance.

    Args:
        test_db_session: Database session

    Returns:
        VersionRepository: Repository for version control operations
    """
    return VersionRepository(test_db_session)


@pytest.fixture
def category_repo(test_db_session: Session) -> CategoryRepository:
    """Create a CategoryRepository instance.

    Args:
        test_db_session: Database session

    Returns:
        CategoryRepository: Repository for category operations
    """
    return CategoryRepository(test_db_session)


@pytest.fixture
def backup_repo(test_db_session: Session) -> "BackupRepository":
    """Create a BackupRepository instance.

    Args:
        test_db_session: Database session

    Returns:
        BackupRepository: Repository for backup metadata operations
    """
    from src.db.repositories.backup_repository import BackupRepository

    return BackupRepository(test_db_session)


@pytest.fixture
def tag_repo(test_db_session: Session) -> TagRepository:
    """Create a TagRepository instance.

    Args:
        test_db_session: Database session

    Returns:
        TagRepository: Repository for tag operations
    """
    return TagRepository(test_db_session)


# ============================================================================
# SERVICE FIXTURES
# ============================================================================


@pytest.fixture
def db_data_service(test_db_engine, monkeypatch) -> PromptDataService:
    """Create PromptDataService with in-memory database.

    This fixture patches the database SessionLocal to use the test engine,
    ensuring all service operations use the in-memory test database.

    Args:
        test_db_engine: Test database engine
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        PromptDataService: Data service instance
    """
    # Patch the SessionLocal to use test engine
    from src.db import session as session_module
    from contextlib import contextmanager

    # Store original SessionLocal
    original_session_local = session_module.SessionLocal

    # Create test session factory
    TestSessionLocal = sessionmaker(bind=test_db_engine)

    # Patch SessionLocal
    monkeypatch.setattr(session_module, "SessionLocal", TestSessionLocal)

    # Create a new get_db_session that uses the test SessionLocal
    @contextmanager
    def mock_get_db_session():
        """Mock context manager that uses test database."""
        session = TestSessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Patch get_db_session
    monkeypatch.setattr(session_module, "get_db_session", mock_get_db_session)
    # PromptDataService imports get_db_session directly
    # (`from src.db.session import get_db_session`), so patching the
    # attribute on src.db.session alone doesn't affect its already-bound
    # module-level reference — patch it explicitly too.
    monkeypatch.setattr(
        "src.services.prompt_data_service_db.get_db_session", mock_get_db_session
    )

    service = PromptDataService()
    return service


@pytest.fixture
def db_backup_service(temp_data_dir: str, test_db_engine, monkeypatch) -> BackupService:
    """Create database-aware BackupService instance with proper DB isolation.

    Each test gets a fresh database session for backup metadata to prevent
    UNIQUE constraint failures from backup IDs persisting across tests.

    Args:
        temp_data_dir: Temporary directory for backups
        test_db_engine: Test database engine
        monkeypatch: Pytest monkeypatch fixture

    Returns:
        BackupService: Backup service instance
    """
    # Create a test database file in temp directory
    import os

    test_db_path = os.path.join(temp_data_dir, "test.db")
    test_db_url = f"sqlite:///{test_db_path}"

    # Patch DATABASE_URL to use test database
    from src.db import config as config_module

    monkeypatch.setattr(config_module.db_settings, "DATABASE_URL", test_db_url)

    # Create the test database file
    from sqlalchemy import create_engine
    from src.db.base import Base

    engine = create_engine(test_db_url)
    Base.metadata.create_all(engine)
    engine.dispose()

    # Patch get_db_session to use test engine with isolation
    from src.db import session as session_module
    from sqlalchemy.orm import sessionmaker
    from contextlib import contextmanager

    # Use the shared test_db_engine to ensure proper isolation
    TestSessionLocal = sessionmaker(bind=test_db_engine)

    @contextmanager
    def mock_get_db_session():
        """Mock context manager that uses test database with proper isolation."""
        session = TestSessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(session_module, "get_db_session", mock_get_db_session)
    # BackupService and BackupAuditService import get_db_session directly
    # (`from src.db.session import get_db_session`), binding their own
    # module-level name at import time. Patching the attribute on
    # src.db.session alone does not affect those already-bound references,
    # so they must be patched individually or they silently fall through to
    # the real, unpatched engine (and the real on-disk database).
    monkeypatch.setattr(
        "src.services.backup_service_db.get_db_session", mock_get_db_session
    )
    monkeypatch.setattr(
        "src.services.backup_audit_service.get_db_session", mock_get_db_session
    )
    monkeypatch.setattr(
        "src.services.backup_metadata_store.get_db_session", mock_get_db_session
    )
    monkeypatch.setattr(
        "src.services.backup_creation_service.get_db_session", mock_get_db_session
    )
    monkeypatch.setattr(
        "src.services.backup_restore_service.get_db_session", mock_get_db_session
    )
    monkeypatch.setattr(
        "src.services.backup_diff_service.get_db_session", mock_get_db_session
    )

    return BackupService(temp_data_dir)


@pytest.fixture
def patched_db_session(test_db_engine, monkeypatch):
    """Patch get_db_session to use in-memory test engine.

    Returns the TestSessionLocal factory for direct session creation.
    """
    from src.db import session as session_module
    from contextlib import contextmanager

    TestSessionLocal = sessionmaker(bind=test_db_engine)

    @contextmanager
    def mock_get_db_session():
        session = TestSessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr(session_module, "get_db_session", mock_get_db_session)
    monkeypatch.setattr(
        "src.services.backup_encryption_service.get_db_session", mock_get_db_session
    )
    monkeypatch.setattr(
        "src.services.backup_cloud_service.get_db_session", mock_get_db_session
    )
    monkeypatch.setattr(
        "src.services.backup_scheduler_service.get_db_session", mock_get_db_session
    )
    monkeypatch.setattr(
        "src.services.backup_audit_service.get_db_session", mock_get_db_session
    )
    monkeypatch.setattr(
        "src.services.backup_service_db.get_db_session", mock_get_db_session
    )
    monkeypatch.setattr(
        "src.services.backup_metadata_store.get_db_session", mock_get_db_session
    )
    monkeypatch.setattr(
        "src.services.backup_creation_service.get_db_session", mock_get_db_session
    )
    monkeypatch.setattr(
        "src.services.backup_restore_service.get_db_session", mock_get_db_session
    )
    monkeypatch.setattr(
        "src.services.backup_diff_service.get_db_session", mock_get_db_session
    )
    return TestSessionLocal


@pytest.fixture
def encryption_service(patched_db_session):
    """Create BackupEncryptionService with patched DB session."""
    return BackupEncryptionService()


@pytest.fixture
def cloud_service(patched_db_session, monkeypatch):
    """Create BackupCloudService with patched DB session and env var."""
    monkeypatch.setenv(
        "PROMPTVAULT_CLOUD_CREDS_PASSPHRASE", "test-cloud-passphrase-secret"
    )
    return BackupCloudService()


@pytest.fixture
def scheduler_service(patched_db_session, db_backup_service):
    """Create BackupSchedulerService with patched DB and backup service."""
    BackupSchedulerService._class_scheduler = None
    svc = BackupSchedulerService(backup_service=db_backup_service)
    yield svc
    if (
        BackupSchedulerService._class_scheduler
        and BackupSchedulerService._class_scheduler.running
    ):
        BackupSchedulerService._class_scheduler.shutdown(wait=False)
    BackupSchedulerService._class_scheduler = None


@pytest.fixture
def audit_service(patched_db_session):
    """Create BackupAuditService with patched DB session."""
    return BackupAuditService()


@pytest.fixture
def filter_service() -> PromptFilterService:
    """Create PromptFilterService instance.

    Returns:
        PromptFilterService: Filter service for prompt filtering
    """
    return PromptFilterService()


@pytest.fixture
def import_export_service() -> PromptImportExportService:
    """Create PromptImportExportService instance.

    Returns:
        PromptImportExportService: Service for import/export operations
    """
    return PromptImportExportService()


@pytest.fixture
def versioning_service() -> PromptVersioningService:
    """Create PromptVersioningService instance.

    Returns:
        PromptVersioningService: Service for version control
    """
    return PromptVersioningService()


# ============================================================================
# DATA FACTORY FIXTURES
# ============================================================================


@pytest.fixture
def sample_prompt_data() -> Callable[..., Dict[str, Any]]:
    """Factory fixture for generating sample prompt data dictionaries.

    This is useful for creating prompt data in the format expected by
    service layer methods like add_new_prompt().

    Returns:
        Callable: Function that returns prompt data dict

    Example:
        >>> prompt_data = sample_prompt_data(title="My Prompt")
        >>> service.add_new_prompt(prompt_data)
    """

    def _create_prompt(
        title: str = "Test Prompt",
        prompt: str = "This is a test prompt content",
        note: str = "Test note",
        category: str = "Test Category",
        tags: List[str] = None,
        favorite: bool = False,
    ) -> Dict[str, Any]:
        if tags is None:
            tags = ["test", "sample"]

        return {
            "title": title,
            "prompt": prompt,
            "note": note,
            "category": category,
            "tags": tags,
            "favorite": favorite,
        }

    return _create_prompt


@pytest.fixture
def sample_version_data() -> Callable[..., Dict[str, Any]]:
    """Factory fixture for generating sample version data dictionaries.

    Returns:
        Callable: Function that returns version data dict
    """

    def _create_version(
        version_id: str = "test-version-id",
        timestamp: str = "2024-01-01T12:00:00Z",
        author: str = "test_user",
        message: str = "Test commit",
        data: Dict[str, Any] = None,
        parents: List[str] = None,
    ) -> Dict[str, Any]:
        if data is None:
            data = {
                "title": "Test",
                "prompt": "Test content",
                "category": "Test",
                "tags": [],
                "favorite": False,
            }
        if parents is None:
            parents = []

        return {
            "version_id": version_id,
            "timestamp": timestamp,
            "author": author,
            "message": message,
            "data": data,
            "parents": parents,
        }

    return _create_version


@pytest.fixture
def sample_csv_content() -> str:
    """Sample CSV content for import testing.

    Returns:
        str: CSV-formatted prompt data
    """
    return """title,prompt,note,category,tags,favorite
Test Prompt 1,Test content 1,Test note 1,Category1,"tag1, tag2",Yes
Test Prompt 2,Test content 2,Test note 2,Category2,"tag3, tag4",No
"""


@pytest.fixture
def sample_markdown_content() -> str:
    """Sample Markdown content for import testing.

    Returns:
        str: Markdown-formatted prompt data
    """
    return """# Test Prompt 1

**Category:** Category1
**Tags:** tag1, tag2
**Favorite:** Yes

## Prompt
Test content 1

## Note
Test note 1

---

# Test Prompt 2

**Category:** Category2
**Tags:** tag3, tag4
**Favorite:** No

## Prompt
Test content 2

## Note
Test note 2

---
"""


# ============================================================================
# POPULATED DATA FIXTURES
# ============================================================================


@pytest.fixture
def populated_db_service(
    db_data_service: PromptDataService,
    sample_prompt_data: Callable[..., Dict[str, Any]],
) -> PromptDataService:
    """Create a database-backed service with pre-populated test data.

    Creates 5 prompts with various categories, tags, and favorite status
    for comprehensive testing of search, filter, and listing functionality.

    Args:
        db_data_service: Empty data service
        sample_prompt_data: Factory for creating prompt data

    Returns:
        PromptDataService: Service with 5 test prompts
    """
    prompts_data = [
        sample_prompt_data(
            title="Python Best Practices",
            prompt="Write clean, readable Python code following PEP 8",
            category="Programming",
            tags=["python", "coding", "best-practices"],
        ),
        sample_prompt_data(
            title="Code Review Checklist",
            prompt="Review code for bugs, performance, and maintainability",
            category="Development",
            tags=["review", "quality"],
            favorite=True,
        ),
        sample_prompt_data(
            title="Database Design",
            prompt="Design normalized database schema",
            category="Database",
            tags=["database", "sql"],
        ),
        sample_prompt_data(
            title="API Documentation",
            prompt="Document REST API endpoints",
            category="Documentation",
            tags=["api", "docs"],
        ),
        sample_prompt_data(
            title="Security Audit",
            prompt="Perform security audit of codebase",
            category="Security",
            tags=["security", "audit"],
            favorite=True,
        ),
    ]

    for prompt in prompts_data:
        db_data_service.add_new_prompt(prompt)

    return db_data_service


# ============================================================================
# API TEST CLIENT FIXTURES
# ============================================================================


@pytest.fixture
def temp_data_dir() -> Generator[str, None, None]:
    """Create a temporary directory for testing with automatic cleanup.

    Yields:
        str: Path to temporary directory
    """
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def api_client(
    test_db_engine, temp_data_dir: str, monkeypatch
) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with database backend.

    This fixture configures the FastAPI app to use an in-memory test database
    and provides a TestClient for making API requests in tests.

    Args:
        test_db_engine: Test database engine
        temp_data_dir: Temporary directory for file operations
        monkeypatch: Pytest monkeypatch fixture

    Yields:
        TestClient: FastAPI test client
    """
    # Ensure DISABLE_RATE_LIMITING is set (redundant but safe)
    os.environ["DISABLE_RATE_LIMITING"] = "true"

    # Import here to avoid circular imports
    from src.web import app as web_app
    from src.db import session as session_module
    from src.db import config as config_module
    from src.web.middleware import rate_limit

    # Reinitialize the limiter with rate limiting disabled
    rate_limit.limiter = rate_limit.create_limiter()
    web_app.app.state.limiter = rate_limit.limiter

    # Store original session factory
    original_session_local = session_module.SessionLocal

    # Create test session factory
    TestSessionLocal = sessionmaker(bind=test_db_engine)

    # Patch the session factory
    session_module.SessionLocal = TestSessionLocal

    # Backup restore reads DATABASE_URL directly (bypassing SessionLocal) to
    # open the raw sqlite file, so it must also point at a throwaway path —
    # otherwise a restore-path test would overwrite the developer's real DB.
    from sqlalchemy import create_engine as _create_engine
    from src.db.base import Base as _Base

    test_db_path = os.path.join(temp_data_dir, "api_client_test.db")
    monkeypatch.setattr(
        config_module.db_settings, "DATABASE_URL", f"sqlite:///{test_db_path}"
    )
    _file_engine = _create_engine(f"sqlite:///{test_db_path}")
    _Base.metadata.create_all(_file_engine)
    _file_engine.dispose()

    # Configure services with test data directory
    web_app.configure_services(data_dir=temp_data_dir)

    # Create test client
    client = TestClient(web_app.app)

    try:
        yield client
    finally:
        client.close()
        # Restore original session factory
        session_module.SessionLocal = original_session_local


@pytest.fixture
def api_client_context(
    test_db_engine,
    temp_data_dir: str,
    sample_prompt_data: Callable[..., Dict[str, Any]],
    monkeypatch,
) -> Generator[Dict[str, Any], None, None]:
    """FastAPI TestClient with database backend and data service access (backward compatibility).

    This fixture provides the same interface as the old api_client_context fixture
    for backward compatibility with existing test files (e.g., test_api_endpoints.py).

    Args:
        test_db_engine: Test database engine
        temp_data_dir: Temporary directory for file operations
        sample_prompt_data: Factory for creating prompt data
        monkeypatch: Pytest monkeypatch fixture

    Yields:
        dict: Dictionary with 'client', 'data_service', and 'temp_dir' keys
    """
    # Import here to avoid circular imports
    from src.web import app as web_app
    from src.db import session as session_module
    from src.db import config as config_module
    from contextlib import contextmanager

    # Backup restore reads DATABASE_URL directly (bypassing SessionLocal) to
    # open the raw sqlite file, so it must also point at a throwaway path —
    # otherwise a restore-path test would overwrite the developer's real DB.
    from sqlalchemy import create_engine as _create_engine
    from src.db.base import Base as _Base

    test_db_path = os.path.join(temp_data_dir, "api_client_context_test.db")
    monkeypatch.setattr(
        config_module.db_settings, "DATABASE_URL", f"sqlite:///{test_db_path}"
    )
    _file_engine = _create_engine(f"sqlite:///{test_db_path}")
    _Base.metadata.create_all(_file_engine)
    _file_engine.dispose()

    # Store original session factory and services
    original_session_local = session_module.SessionLocal
    original_services = (
        web_app.data_service,
        web_app.backup_service,
        web_app.filter_service,
        web_app.import_export_service,
        web_app.versioning_service,
    )

    # Generate test JWT keys
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend

    # Generate test private key
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Generate test public key
    public_key = private_key.public_key()
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Write test keys to temp directory
    private_key_path = os.path.join(temp_data_dir, "test_private_key.pem")
    public_key_path = os.path.join(temp_data_dir, "test_public_key.pem")

    with open(private_key_path, "wb") as f:
        f.write(private_pem)
    with open(public_key_path, "wb") as f:
        f.write(public_pem)

    # Patch auth_settings directly
    from src.config import auth_config
    from src.config.auth_config import AuthConfig

    # Store original auth_settings
    original_auth_settings = auth_config.auth_settings

    # Create test config with test key paths
    test_config = AuthConfig(
        jwt_private_key_path=private_key_path,
        jwt_public_key_path=public_key_path,
    )

    # Patch the module-level variable
    auth_config.auth_settings = test_config

    # Create test session factory
    TestSessionLocal = sessionmaker(bind=test_db_engine)

    # Patch the session factory
    session_module.SessionLocal = TestSessionLocal

    # Create a new get_db_session that uses the test SessionLocal
    @contextmanager
    def mock_get_db_session():
        """Mock context manager that uses test database."""
        session = TestSessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Patch get_db_session
    session_module.get_db_session = mock_get_db_session

    # Force reload of auth config before configuring services
    from src.config import auth_config
    import importlib

    importlib.reload(auth_config)

    # Configure services with test data directory
    web_app.configure_services(data_dir=temp_data_dir)

    # Get reference to data service
    data_service = web_app.data_service

    # Create test user for authenticated API tests
    from src.services.auth.password_service import PasswordService
    from src.config.auth_config import auth_settings
    from src.db.models.user import User
    from src.db.models.user_session import UserSession

    password_service = PasswordService(auth_settings)
    password_hash = password_service.hash_password("ApiUserP@ssw0rd123")

    # Create a session to add the user
    test_session = TestSessionLocal()
    try:
        test_user = User(
            id="api-test-user-id",
            username="apiuser",
            email="api@example.com",
            password_hash=password_hash,
            role="editor",
            is_active=True,
            email_verified=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        test_session.add(test_user)
        test_session.flush()

        # Create an active session for the user
        user_session = UserSession(
            user_id=test_user.id,
            family_id="api-test-family",
            refresh_token_jti="api-test-jti",
            ip_address="127.0.0.1",
            device_info="Test Agent",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            is_revoked=False,
        )
        test_session.add(user_session)
        test_session.commit()
    finally:
        test_session.close()

    # Seed data with two prompts owned by the test user (matching old fixture behavior)
    data_service.add_new_prompt(
        sample_prompt_data(
            title="API Prompt 1",
            prompt="Content 1",
            category="Testing",
            tags=["api", "test"],
            favorite=True,
        ),
        user_id="api-test-user-id",  # Set the owner
    )
    data_service.add_new_prompt(
        sample_prompt_data(
            title="API Prompt 2",
            prompt="Content 2",
            category="Docs",
            tags=["docs"],
            favorite=False,
        ),
        user_id="api-test-user-id",  # Set the owner
    )

    # Create test client
    client = TestClient(web_app.app)

    try:
        yield {
            "client": client,
            "data_service": data_service,
            "temp_dir": temp_data_dir,
        }
    finally:
        client.close()
        # Restore original session factory and services
        session_module.SessionLocal = original_session_local
        (
            web_app.data_service,
            web_app.backup_service,
            web_app.filter_service,
            web_app.import_export_service,
            web_app.versioning_service,
        ) = original_services

        # Restore original auth_settings
        auth_config.auth_settings = original_auth_settings

        # Force reload of auth config again
        importlib.reload(auth_config)


@pytest.fixture
def api_client_with_data(
    api_client: TestClient,
    sample_prompt_data: Callable[..., Dict[str, Any]],
    test_db_session: Session,
    test_user: User,
    test_category: Category,
    test_tags: List[Tag],
) -> Dict[str, Any]:
    """FastAPI TestClient with pre-populated test data.

    Creates a test client and populates it with sample prompts for
    API endpoint testing.

    Args:
        api_client: FastAPI test client
        sample_prompt_data: Factory for creating prompt data
        test_db_session: Database session for seeding data
        test_user: Test user
        test_category: Test category
        test_tags: Test tags

    Returns:
        dict: Dictionary with 'client' and 'prompts' keys
    """
    # Create sample prompts directly in the database
    prompts = []

    prompt_data_list = [
        {
            "title": "API Prompt 1",
            "prompt": "Content 1",
            "category_id": test_category.id,
            "note": "Note 1",
            "favorite": True,
            "user_id": test_user.id,
        },
        {
            "title": "API Prompt 2",
            "prompt": "Content 2",
            "category_id": test_category.id,
            "note": "Note 2",
            "favorite": False,
            "user_id": test_user.id,
        },
    ]

    for prompt_data in prompt_data_list:
        prompt = Prompt(**prompt_data)
        prompt.tags.extend(test_tags[:2])
        test_db_session.add(prompt)
        prompts.append(prompt)

    test_db_session.commit()

    return {
        "client": api_client,
        "prompts": prompts,
    }
