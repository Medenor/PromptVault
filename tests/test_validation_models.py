"""Unit tests for Pydantic validation models."""

import pytest
from pydantic import ValidationError
from src.web.models import (
    PromptCreateRequest,
    PromptUpdateRequest,
    ExportRequest,
    ImportRequest,
    BackupCreateRequest,
    BackupCleanupRequest,
    BackupCompressRequest,
    VersionRevertRequest,
    ExportFormat,
    ImportMode,
)


class TestPromptCreateRequest:
    """Test PromptCreateRequest validation."""

    def test_valid_prompt_creation(self):
        """Test creating a prompt with valid data."""
        data = PromptCreateRequest(
            title="Test Prompt",
            prompt="This is a test prompt content",
            category="Testing",
            tags="tag1,tag2,tag3",
        )
        assert data.title == "Test Prompt"
        assert data.prompt == "This is a test prompt content"
        assert data.category == "Testing"
        assert data.tags == "tag1,tag2,tag3"

    def test_title_too_long(self):
        """Test that title exceeding max length is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PromptCreateRequest(
                title="x" * 201,  # Exceeds 200 character limit
                prompt="Test",
            )
        errors = exc_info.value.errors()
        assert any("title" in str(error["loc"]) for error in errors)

    def test_title_empty(self):
        """Test that empty title is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PromptCreateRequest(
                title="",
                prompt="Test",
            )
        errors = exc_info.value.errors()
        assert any("title" in str(error["loc"]) for error in errors)

    def test_title_whitespace_only(self):
        """Test that whitespace-only title is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PromptCreateRequest(
                title="   ",
                prompt="Test",
            )
        errors = exc_info.value.errors()
        assert any("whitespace" in str(error["msg"]).lower() for error in errors)

    def test_prompt_content_too_long(self):
        """Test that prompt exceeding max length is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PromptCreateRequest(
                title="Test",
                prompt="x" * 50001,  # Exceeds 50000 character limit
            )
        errors = exc_info.value.errors()
        assert any("prompt" in str(error["loc"]) for error in errors)

    def test_too_many_tags(self):
        """Test that more than 50 tags are rejected."""
        tags = ",".join([f"tag{i}" for i in range(51)])
        with pytest.raises(ValidationError) as exc_info:
            PromptCreateRequest(
                title="Test",
                prompt="Test prompt",
                tags=tags,
            )
        errors = exc_info.value.errors()
        assert any("50 tags" in str(error["msg"]) for error in errors)

    def test_tag_too_long(self):
        """Test that tag exceeding 50 characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PromptCreateRequest(
                title="Test",
                prompt="Test prompt",
                tags="x" * 51,  # Single tag exceeding 50 chars
            )
        errors = exc_info.value.errors()
        assert any("50 characters" in str(error["msg"]) for error in errors)

    def test_whitespace_stripping(self):
        """Test that whitespace is stripped from title and category."""
        data = PromptCreateRequest(
            title="  Test Title  ",
            prompt="Test prompt",
            category="  Test Category  ",
        )
        assert data.title == "Test Title"
        assert data.category == "Test Category"

    def test_empty_tags_filtered(self):
        """Test that empty tags are filtered out."""
        data = PromptCreateRequest(
            title="Test",
            prompt="Test prompt",
            tags="tag1,,tag2,  ,tag3",
        )
        # Tags should be cleaned
        assert "tag1" in data.tags
        assert "tag2" in data.tags
        assert "tag3" in data.tags


class TestPromptUpdateRequest:
    """Test PromptUpdateRequest validation."""

    def test_valid_prompt_update(self):
        """Test updating a prompt with valid data."""
        data = PromptUpdateRequest(
            title="Updated Title",
            prompt="Updated content",
            category="Updated",
            tags="new,tags",
            commit_message="Updated prompt",
        )
        assert data.commit_message == "Updated prompt"

    def test_commit_message_too_long(self):
        """Test that commit message exceeding max length is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            PromptUpdateRequest(
                title="Test",
                prompt="Test",
                commit_message="x" * 501,  # Exceeds 500 character limit
            )
        errors = exc_info.value.errors()
        assert any("commit_message" in str(error["loc"]) for error in errors)

    def test_default_commit_message(self):
        """Test that default commit message is set."""
        data = PromptUpdateRequest(
            title="Test",
            prompt="Test",
        )
        assert data.commit_message == "Update"


class TestExportRequest:
    """Test ExportRequest validation."""

    def test_valid_export_request(self):
        """Test valid export request."""
        data = ExportRequest(
            format=ExportFormat.CSV,
            filename="test_export",
        )
        assert data.format == ExportFormat.CSV
        assert data.filename == "test_export"

    def test_invalid_format(self):
        """Test that invalid format is rejected."""
        with pytest.raises(ValidationError):
            ExportRequest(
                format="invalid_format",  # type: ignore
                filename="test",
            )

    def test_filename_with_invalid_characters(self):
        """Test that filename with invalid characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ExportRequest(
                format=ExportFormat.JSON,
                filename="../../../etc/passwd",
            )
        errors = exc_info.value.errors()
        assert any("filename" in str(error["loc"]) for error in errors)

    def test_filename_too_long(self):
        """Test that filename exceeding max length is rejected."""
        with pytest.raises(ValidationError):
            ExportRequest(
                format=ExportFormat.CSV,
                filename="x" * 256,  # Exceeds 255 character limit
            )

    def test_filename_with_path_separator(self):
        """Test that filename with path separator is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ExportRequest(
                format=ExportFormat.CSV,
                filename="some/path/file",
            )
        errors = exc_info.value.errors()
        # Check that validation failed (either for path separators or invalid characters)
        assert len(errors) > 0
        assert any("filename" in str(error["loc"]) for error in errors)


class TestImportRequest:
    """Test ImportRequest validation."""

    def test_valid_import_modes(self):
        """Test all valid import modes."""
        for mode in [ImportMode.APPEND, ImportMode.MERGE, ImportMode.REPLACE]:
            data = ImportRequest(mode=mode)
            assert data.mode == mode

    def test_invalid_import_mode(self):
        """Test that invalid import mode is rejected."""
        with pytest.raises(ValidationError):
            ImportRequest(mode="invalid_mode")  # type: ignore


class TestBackupCreateRequest:
    """Test BackupCreateRequest validation."""

    def test_valid_backup_name(self):
        """Test valid backup name."""
        data = BackupCreateRequest(name="my_backup_123")
        assert data.name == "my_backup_123"

    def test_none_backup_name(self):
        """Test that None backup name is allowed."""
        data = BackupCreateRequest(name=None)
        assert data.name is None

    def test_empty_backup_name(self):
        """Test that empty backup name returns None."""
        data = BackupCreateRequest(name="")
        assert data.name is None

    def test_backup_name_with_invalid_characters(self):
        """Test that backup name with invalid characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BackupCreateRequest(name="backup@#$%")
        errors = exc_info.value.errors()
        assert any("letters, numbers, underscores, and hyphens" in str(error["msg"]) for error in errors)

    def test_backup_name_too_long(self):
        """Test that backup name exceeding max length is rejected."""
        with pytest.raises(ValidationError):
            BackupCreateRequest(name="x" * 65)  # Exceeds 64 character limit

    def test_backup_name_with_path_traversal(self):
        """Test that path traversal attempt in backup name is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            BackupCreateRequest(name="../../../etc")
        errors = exc_info.value.errors()
        # Check that validation failed (either for path separators or invalid characters)
        assert len(errors) > 0
        assert any("name" in str(error["loc"]) for error in errors)


class TestBackupCleanupRequest:
    """Test BackupCleanupRequest validation."""

    def test_valid_retention_days(self):
        """Test valid retention days."""
        data = BackupCleanupRequest(retention_days=30)
        assert data.retention_days == 30

    def test_retention_days_minimum(self):
        """Test minimum retention days (1)."""
        data = BackupCleanupRequest(retention_days=1)
        assert data.retention_days == 1

    def test_retention_days_maximum(self):
        """Test maximum retention days (3650)."""
        data = BackupCleanupRequest(retention_days=3650)
        assert data.retention_days == 3650

    def test_retention_days_too_low(self):
        """Test that retention days below minimum is rejected."""
        with pytest.raises(ValidationError):
            BackupCleanupRequest(retention_days=0)

    def test_retention_days_too_high(self):
        """Test that retention days above maximum is rejected."""
        with pytest.raises(ValidationError):
            BackupCleanupRequest(retention_days=3651)


class TestBackupCompressRequest:
    """Test BackupCompressRequest validation."""

    def test_valid_days_threshold(self):
        """Test valid days threshold."""
        data = BackupCompressRequest(days_threshold=7)
        assert data.days_threshold == 7

    def test_days_threshold_minimum(self):
        """Test minimum days threshold (1)."""
        data = BackupCompressRequest(days_threshold=1)
        assert data.days_threshold == 1

    def test_days_threshold_maximum(self):
        """Test maximum days threshold (365)."""
        data = BackupCompressRequest(days_threshold=365)
        assert data.days_threshold == 365

    def test_days_threshold_too_low(self):
        """Test that days threshold below minimum is rejected."""
        with pytest.raises(ValidationError):
            BackupCompressRequest(days_threshold=0)

    def test_days_threshold_too_high(self):
        """Test that days threshold above maximum is rejected."""
        with pytest.raises(ValidationError):
            BackupCompressRequest(days_threshold=366)


class TestVersionRevertRequest:
    """Test VersionRevertRequest validation."""

    def test_valid_commit_message(self):
        """Test valid commit message."""
        data = VersionRevertRequest(commit_message="Revert to previous state")
        assert data.commit_message == "Revert to previous state"

    def test_default_commit_message(self):
        """Test default commit message."""
        data = VersionRevertRequest()
        assert data.commit_message == "Revert to previous version"

    def test_commit_message_too_long(self):
        """Test that commit message exceeding max length is rejected."""
        with pytest.raises(ValidationError):
            VersionRevertRequest(commit_message="x" * 501)

    def test_commit_message_whitespace_stripping(self):
        """Test that whitespace is stripped from commit message."""
        data = VersionRevertRequest(commit_message="  Test message  ")
        assert data.commit_message == "Test message"
