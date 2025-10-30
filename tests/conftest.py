"""
Shared test fixtures for PromptVault test suite.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
import sys

# Add the parent directory to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.services.prompt_data_service import PromptDataService
from src.services.backup_service import BackupService
from src.services.prompt_filter_service import PromptFilterService
from src.services.prompt_import_export_service import PromptImportExportService
from src.services.prompt_versioning_service import PromptVersioningService
from src.services.version_compression_service import VersionCompressionService
from src.services.version_tagging_service import VersionTaggingService
from src.services.version_export_service import VersionExportService
from fastapi.testclient import TestClient


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for testing with automatic cleanup."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def temp_data_file(temp_data_dir):
    """Create a temporary data file path for testing."""
    temp_file = Path(temp_data_dir) / "test_prompts.json"
    yield str(temp_file)


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
def empty_data_service(temp_data_file):
    """Create an empty PromptDataService instance."""
    service = PromptDataService(temp_data_file)
    return service


@pytest.fixture
def populated_data_service(temp_data_file, sample_prompt_data):
    """Create a PromptDataService with pre-populated test data."""
    service = PromptDataService(temp_data_file)

    # Create multiple test prompts
    prompts = [
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

    for prompt in prompts:
        service.add_new_prompt(prompt)

    service.save_prompts()
    return service


@pytest.fixture
def large_dataset_service(temp_data_file, sample_prompt_data):
    """Create a PromptDataService with a large dataset for performance testing."""
    service = PromptDataService(temp_data_file)

    categories = [
        "Programming",
        "Development",
        "Database",
        "Security",
        "Testing",
        "Documentation",
    ]
    tag_pool = [
        "python",
        "javascript",
        "java",
        "sql",
        "api",
        "web",
        "mobile",
        "cloud",
        "devops",
    ]

    # Create 1000 prompts
    for i in range(1000):
        category = categories[i % len(categories)]
        tags = [tag_pool[j % len(tag_pool)] for j in range(i % 3 + 1)]

        prompt_data = sample_prompt_data(
            title=f"Test Prompt {i}",
            prompt=f"This is test prompt content number {i}. "
            * 10,  # Make it substantial
            note=f"Test note {i}",
            category=category,
            tags=tags,
            favorite=(i % 10 == 0),  # Every 10th prompt is favorite
        )
        service.add_new_prompt(prompt_data)

    service.save_prompts()
    return service


@pytest.fixture
def prompt_with_versions(temp_data_file, sample_prompt_data):
    """Create a prompt with multiple versions."""
    service = PromptDataService(temp_data_file)

    # Create initial prompt
    initial_data = sample_prompt_data(
        title="Versioned Prompt", prompt="Initial content"
    )
    prompt_id = service.add_new_prompt(initial_data)

    # Create multiple updates to build version history
    for i in range(10):
        updated_data = sample_prompt_data(
            title=f"Versioned Prompt v{i+1}",
            prompt=f"Content update {i+1}",
            category="Test",
        )
        service.update_prompt(prompt_id, updated_data, f"Update {i+1}")

    service.save_prompts()
    return service, prompt_id


@pytest.fixture
def test_client():
    """Create a FastAPI test client."""
    from src.web.app import app

    return TestClient(app)


@pytest.fixture
def api_client_context(temp_data_dir, sample_prompt_data):
    """
    Provide a configured FastAPI TestClient with isolated data/backup services.

    Returns a dict with 'client', 'data_service', and 'temp_dir'.
    """
    from src.web import app as web_app

    data_file = Path(temp_data_dir) / "prompts_data.json"
    data_service = PromptDataService(str(data_file))

    # Seed data with two prompts
    data_service.add_new_prompt(
        sample_prompt_data(
            title="API Prompt 1",
            prompt="Content 1",
            category="Testing",
            tags=["api", "test"],
            favorite=True,
        )
    )
    data_service.add_new_prompt(
        sample_prompt_data(
            title="API Prompt 2",
            prompt="Content 2",
            category="Docs",
            tags=["docs"],
            favorite=False,
        )
    )
    data_service.save_prompts()

    backup_service = BackupService(temp_data_dir)
    filter_service = PromptFilterService()
    import_export_service = PromptImportExportService()

    original_services = (
        web_app.data_service,
        web_app.backup_service,
        web_app.filter_service,
        web_app.import_export_service,
    )

    web_app.data_service = data_service
    web_app.backup_service = backup_service
    web_app.filter_service = filter_service
    web_app.import_export_service = import_export_service

    client = TestClient(web_app.app)

    try:
        yield {
            "client": client,
            "data_service": data_service,
            "temp_dir": temp_data_dir,
        }
    finally:
        client.close()
        (
            web_app.data_service,
            web_app.backup_service,
            web_app.filter_service,
            web_app.import_export_service,
        ) = original_services


@pytest.fixture
def backup_service(temp_data_dir):
    """Create a BackupService instance."""
    return BackupService(temp_data_dir)


@pytest.fixture
def filter_service():
    """Create a PromptFilterService instance."""
    return PromptFilterService()


@pytest.fixture
def import_export_service():
    """Create a PromptImportExportService instance."""
    return PromptImportExportService()


@pytest.fixture
def compression_service():
    """Create a VersionCompressionService instance."""
    return VersionCompressionService(compression_threshold_days=30)


@pytest.fixture
def tagging_service():
    """Create a VersionTaggingService instance."""
    return VersionTaggingService()


@pytest.fixture
def export_service():
    """Create a VersionExportService instance."""
    return VersionExportService()


@pytest.fixture
def versioning_service():
    """Create a PromptVersioningService instance."""
    return PromptVersioningService()


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


@pytest.fixture
def malformed_json_samples():
    """Collection of malformed JSON samples for error testing."""
    return {
        "invalid_json": "{this is not valid json}",
        "missing_prompts": '{"next_id": 5}',
        "wrong_type_prompts": '{"next_id": 5, "prompts": "not a dict"}',
        "missing_data_field": '{"next_id": 1, "prompts": {"0": {"versions": []}}}',
        "invalid_prompt_id": '{"next_id": 1, "prompts": {"invalid_id": {"data": {}}}}',
        "null_values": '{"next_id": null, "prompts": null}',
    }
