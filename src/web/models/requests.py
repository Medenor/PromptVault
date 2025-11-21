"""Pydantic request validation models for PromptVault API.

This module defines request validation schemas for all API endpoints,
implementing the constraints specified in the Phase 0 specification.
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any, Dict, List, Optional, Literal
import re
from .enums import ExportFormat, ImportMode


class PromptCreateRequest(BaseModel):
    """Request model for creating a new prompt.

    Field constraints:
    - title: 1-200 characters, required, whitespace trimmed
    - prompt: 1-50,000 characters, required
    - category: 0-100 characters, optional, whitespace trimmed
    - tags: comma-separated string parsed to list, max 50 tags, each tag max 50 chars
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Prompt title",
    )
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Prompt content",
    )
    category: Optional[str] = Field(
        default="",
        max_length=100,
        description="Category name",
    )
    tags: Optional[str] = Field(
        default="",
        description="Comma-separated tags",
    )

    @field_validator("title", "category")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading and trailing whitespace from text fields."""
        if v:
            return v.strip()
        return v

    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v: str) -> str:
        """Ensure title is not empty after stripping whitespace."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()

    @field_validator("tags")
    @classmethod
    def validate_and_parse_tags(cls, v: str) -> str:
        """Validate tag format and count.

        Tags are validated but kept as string for compatibility.
        The API layer will parse them using _parse_tags_field().

        Validation rules:
        - Maximum 50 tags
        - Each tag maximum 50 characters
        - No empty tags after trimming
        """
        if not v:
            return ""

        # Parse tags
        tag_list = [tag.strip() for tag in v.split(",")]
        # Filter out empty tags
        tag_list = [tag for tag in tag_list if tag]

        # Validate tag count
        if len(tag_list) > 50:
            raise ValueError("Maximum 50 tags allowed")

        # Validate each tag length
        for tag in tag_list:
            if len(tag) > 50:
                raise ValueError(f"Tag '{tag}' exceeds maximum length of 50 characters")

        # Return as comma-separated string
        return ",".join(tag_list)


class PromptUpdateRequest(BaseModel):
    """Request model for updating an existing prompt.

    Includes all fields from PromptCreateRequest plus commit_message.
    """

    title: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Prompt title",
    )
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Prompt content",
    )
    category: Optional[str] = Field(
        default="",
        max_length=100,
        description="Category name",
    )
    tags: Optional[str] = Field(
        default="",
        description="Comma-separated tags",
    )
    commit_message: str = Field(
        default="Update",
        min_length=1,
        max_length=500,
        description="Version control commit message",
    )

    @field_validator("title", "category", "commit_message")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading and trailing whitespace from text fields."""
        if v:
            return v.strip()
        return v

    @field_validator("title")
    @classmethod
    def validate_title_not_empty(cls, v: str) -> str:
        """Ensure title is not empty after stripping whitespace."""
        if not v or not v.strip():
            raise ValueError("Title cannot be empty or whitespace only")
        return v.strip()

    @field_validator("tags")
    @classmethod
    def validate_and_parse_tags(cls, v: str) -> str:
        """Validate tag format and count."""
        if not v:
            return ""

        tag_list = [tag.strip() for tag in v.split(",")]
        tag_list = [tag for tag in tag_list if tag]

        if len(tag_list) > 50:
            raise ValueError("Maximum 50 tags allowed")

        for tag in tag_list:
            if len(tag) > 50:
                raise ValueError(f"Tag '{tag}' exceeds maximum length of 50 characters")

        return ",".join(tag_list)


class ExportRequest(BaseModel):
    """Request model for exporting prompts.

    Field constraints:
    - format: Must be one of: csv, markdown, json
    - filename: 1-255 characters, alphanumeric + underscore/hyphen only
    - include_favorites: boolean
    - include_metadata: boolean
    """

    format: ExportFormat = Field(
        ...,
        description="Export format",
    )
    filename: str = Field(
        default="promptvault_export",
        min_length=1,
        max_length=255,
        description="Export filename (without extension)",
    )
    include_favorites: bool = Field(
        default=False,
        description="Export only favorite prompts",
    )
    include_metadata: bool = Field(
        default=True,
        description="Include metadata in export",
    )

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate filename is safe and contains no path separators.

        Allowed characters: A-Z, a-z, 0-9, underscore, hyphen
        Disallowed: path separators, special characters
        """
        if not v:
            raise ValueError("Filename cannot be empty")

        # Remove any file extensions if provided
        v = v.split(".")[0]

        # Validate against safe character set
        if not re.match(r"^[A-Za-z0-9_-]+$", v):
            raise ValueError(
                "Filename can only contain letters, numbers, underscores, and hyphens"
            )

        # Additional check for path traversal attempts
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Filename cannot contain path separators")

        return v


class ImportRequest(BaseModel):
    """Request model for import operation metadata.

    Note: File upload is handled separately via FastAPI UploadFile.
    This model validates the form parameters.
    """

    mode: ImportMode = Field(
        default=ImportMode.APPEND,
        description="Import mode",
    )
    validate_data: bool = Field(
        default=True,
        description="Validate imported data",
    )


class BackupCreateRequest(BaseModel):
    """Request model for creating a manual backup.

    Field constraints:
    - name: Optional, 1-64 characters, alphanumeric + underscore/hyphen only
    """

    name: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Custom backup name",
    )

    @field_validator("name")
    @classmethod
    def validate_backup_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate backup name contains only safe characters.

        Allowed: A-Z, a-z, 0-9, underscore, hyphen
        This prevents path traversal and ensures filesystem compatibility.
        """
        if v is None or v == "":
            return None

        v = v.strip()
        if not v:
            return None

        # Validate character set
        if not re.match(r"^[A-Za-z0-9_-]+$", v):
            raise ValueError(
                "Backup name can only contain letters, numbers, underscores, and hyphens"
            )

        # Check for path traversal attempts
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("Backup name cannot contain path separators")

        return v


class BackupCleanupRequest(BaseModel):
    """Request model for backup cleanup operation.

    Field constraints:
    - retention_days: 1-3650 (1 day to 10 years)
    """

    retention_days: int = Field(
        default=30,
        ge=1,
        le=3650,
        description="Number of days to retain backups",
    )


class BackupCompressRequest(BaseModel):
    """Request model for backup compression operation.

    Field constraints:
    - days_threshold: 1-365 (1 day to 1 year)
    """

    days_threshold: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Compress backups older than this many days",
    )


class VersionRevertRequest(BaseModel):
    """Request model for reverting to a previous version.

    Field constraints:
    - commit_message: 1-500 characters
    """

    commit_message: str = Field(
        default="Revert to previous version",
        min_length=1,
        max_length=500,
        description="Commit message for the revert operation",
    )

    @field_validator("commit_message")
    @classmethod
    def strip_whitespace(cls, v: str) -> str:
        """Strip leading and trailing whitespace."""
        if v:
            return v.strip()
        return v


class FrontendLogEntry(BaseModel):
    """Telemetry payload sent from the frontend error reporter."""

    component: str = Field(..., min_length=1, max_length=100)
    action: str = Field(..., min_length=1, max_length=100)
    message: str = Field(..., min_length=1, max_length=500)
    severity: Literal["error", "warning", "info"] = "error"
    stack: Optional[str] = Field(default=None, max_length=2000)
    url: Optional[str] = Field(default=None, max_length=500)
    context: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("component", "action", "message", "stack", "url")
    @classmethod
    def strip_strings(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        return v.strip()
