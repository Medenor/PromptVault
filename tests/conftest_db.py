# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Database-aware test fixtures for PromptVault test suite.

This module provides pytest fixtures for testing with the database backend,
including in-memory SQLite for fast, isolated tests.
"""

import shutil
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest

# Add the parent directory to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.db.base import Base
from src.db.models import (
    Category,
    Prompt,
    PromptVersion,
    Tag,
    User,
)
from src.db.repositories import (
    CategoryRepository,
    PromptRepository,
    TagRepository,
    VersionRepository,
)
from src.services.backup_service_db import BackupService
from src.services.prompt_data_service_db import PromptDataService


@pytest.fixture(scope="function")
def test_db_engine():
    """Create in-memory SQLite engine for tests.

    Each test gets a fresh database that is automatically cleaned up.
    """
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_db_engine) -> Generator[Session]:
    """Create a test database session.

    Uses in-memory SQLite for fast, isolated tests.
    Session is automatically rolled back and closed after each test.
    """
    SessionLocal = sessionmaker(bind=test_db_engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.rollback()
        session.close()


# NOTE: This module is not wired in as a pytest plugin (only tests/conftest.py
# is auto-loaded); tests/conftest.py defines its own equivalent fixtures,
# including the cross-dialect FTS matrix (`postgres_db`, `db_dialect_matrix`).
# See tests/conftest.py for the fixtures actually used by the test suite.


@pytest.fixture
def test_user(test_db_session) -> User:
    """Create a test user."""
    user = User(
        id="test-user-id",
        username="test_user",
        display_name="Test User",
        email="test@example.com",
        role="user",
    )
    test_db_session.add(user)
    test_db_session.flush()
    return user


@pytest.fixture
def test_category(test_db_session) -> Category:
    """Create a test category."""
    category = Category(name="Test Category")
    test_db_session.add(category)
    test_db_session.flush()
    return category


@pytest.fixture
def test_tags(test_db_session) -> list[Tag]:
    """Create test tags."""
    tags = [
        Tag(name="test"),
        Tag(name="sample"),
        Tag(name="python"),
    ]
    test_db_session.add_all(tags)
    test_db_session.flush()
    return tags


@pytest.fixture
def test_prompt(test_db_session, test_user, test_category, test_tags) -> Prompt:
    """Create a test prompt with relationships."""
    prompt = Prompt(
        title="Test Prompt",
        prompt="This is a test prompt content",
        category_id=test_category.id,
        note="Test note",
        favorite=False,
        user_id=test_user.id,
    )
    prompt.tags.extend(test_tags[:2])  # Add first two tags
    test_db_session.add(prompt)
    test_db_session.flush()
    return prompt


@pytest.fixture
def test_prompt_with_versions(
    test_db_session, test_prompt, test_user
) -> tuple[Prompt, list[PromptVersion]]:
    """Create a prompt with multiple versions."""
    versions = []

    # Create 3 versions
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


@pytest.fixture
def prompt_repo(test_db_session) -> PromptRepository:
    """Create a PromptRepository instance."""
    return PromptRepository(test_db_session)


@pytest.fixture
def version_repo(test_db_session) -> VersionRepository:
    """Create a VersionRepository instance."""
    return VersionRepository(test_db_session)


@pytest.fixture
def category_repo(test_db_session) -> CategoryRepository:
    """Create a CategoryRepository instance."""
    return CategoryRepository(test_db_session)


@pytest.fixture
def tag_repo(test_db_session) -> TagRepository:
    """Create a TagRepository instance."""
    return TagRepository(test_db_session)


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for testing with automatic cleanup."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_prompt_data():
    """Factory fixture for generating sample prompt data."""

    def _create_prompt(
        title="Test Prompt",
        prompt="This is a test prompt content",
        note="Test note",
        category="Test Category",
        tags=None,
        favorite=False,
    ):
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
def db_data_service(temp_data_dir, monkeypatch):
    """Create a PromptDataService with in-memory database.

    This fixture patches the database configuration to use an in-memory
    SQLite database for testing.
    """
    from src.db import config as db_config_module

    # Create in-memory database URL
    test_db_url = "sqlite:///:memory:"

    # Patch the database settings
    monkeypatch.setenv("DATABASE_URL", test_db_url)

    # Reload the config to pick up the new DATABASE_URL
    from importlib import reload

    reload(db_config_module)

    # Create engine and tables
    from src.db.base import Base
    from src.db.session import engine

    Base.metadata.create_all(bind=engine)

    # Create service
    service = PromptDataService()

    yield service

    # Cleanup
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def populated_db_service(db_data_service, sample_prompt_data):
    """Create a database-backed service with pre-populated test data."""
    service = db_data_service

    # Create multiple test prompts
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
        service.add_new_prompt(prompt)

    return service


@pytest.fixture
def db_backup_service(temp_data_dir):
    """Create a database-aware BackupService instance."""
    return BackupService(temp_data_dir)


# Sample data fixtures (compatible with both JSON and DB backends)


@pytest.fixture
def sample_version_data():
    """Factory fixture for generating sample version data."""

    def _create_version(
        version_id="test-version-id",
        timestamp="2024-01-01T12:00:00Z",
        author="test_user",
        message="Test commit",
        data=None,
        parents=None,
    ):
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
def sample_csv_content():
    """Sample CSV content for import testing."""
    return """title,prompt,note,category,tags,favorite
Test Prompt 1,Test content 1,Test note 1,Category1,"tag1, tag2",Yes
Test Prompt 2,Test content 2,Test note 2,Category2,"tag3, tag4",No
"""


@pytest.fixture
def sample_markdown_content():
    """Sample Markdown content for import testing."""
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
