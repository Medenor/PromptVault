# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pydantic request models for tag/category management."""

from typing import List, Optional
import re

from pydantic import BaseModel, Field, field_validator, model_validator


_COLOR_TOKEN_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
_COLOR_HEX_PATTERN = re.compile(r"^#(?:[0-9a-fA-F]{3}){1,2}$")
_NAME_PATTERN = re.compile(r"^[A-Za-z0-9 _-]+$")


def _normalize_name(value: str) -> str:
    return value.strip()


def _validate_color(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    if _COLOR_HEX_PATTERN.match(value) or _COLOR_TOKEN_PATTERN.match(value):
        return value
    raise ValueError("Invalid color format")


def _validate_name(value: str) -> str:
    if not _NAME_PATTERN.match(value):
        raise ValueError("Invalid name format")
    return value


class CategoryCreateRequest(BaseModel):
    """Request model for creating a category."""

    name: str = Field(..., min_length=1, max_length=100, description="Category name")
    description: Optional[str] = Field(default=None, max_length=500, description="Category description")
    color: Optional[str] = Field(default=None, description="Color token or hex")
    sort_order: Optional[int] = Field(default=None, description="Custom sort order")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = _normalize_name(value)
        if not normalized:
            raise ValueError("Category name cannot be empty")
        return _validate_name(normalized)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: Optional[str]) -> Optional[str]:
        return _validate_color(value)


class CategoryUpdateRequest(BaseModel):
    """Request model for updating a category."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    color: Optional[str] = Field(default=None)
    sort_order: Optional[int] = Field(default=None)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = _normalize_name(value)
        if not normalized:
            raise ValueError("Category name cannot be empty")
        return _validate_name(normalized)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: Optional[str]) -> Optional[str]:
        return _validate_color(value)

    @model_validator(mode="after")
    def ensure_at_least_one_field(self):
        if (
            self.name is None
            and self.description is None
            and self.color is None
            and self.sort_order is None
        ):
            raise ValueError("At least one field must be provided")
        return self


class TagCreateRequest(BaseModel):
    """Request model for creating a tag."""

    name: str = Field(..., min_length=1, max_length=50, description="Tag name")
    description: Optional[str] = Field(default=None, max_length=500, description="Tag description")
    color: Optional[str] = Field(default=None, description="Color token or hex")
    parent_tag_id: Optional[int] = Field(default=None, description="Parent tag ID")

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = _normalize_name(value)
        if not normalized:
            raise ValueError("Tag name cannot be empty")
        return _validate_name(normalized)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: Optional[str]) -> Optional[str]:
        return _validate_color(value)


class TagUpdateRequest(BaseModel):
    """Request model for updating a tag."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    color: Optional[str] = Field(default=None)
    parent_tag_id: Optional[int] = Field(default=None)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        normalized = _normalize_name(value)
        if not normalized:
            raise ValueError("Tag name cannot be empty")
        return _validate_name(normalized)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: Optional[str]) -> Optional[str]:
        return _validate_color(value)

    @model_validator(mode="after")
    def ensure_at_least_one_field(self):
        if self.name is None and self.description is None and self.color is None:
            raise ValueError("At least one field must be provided")
        return self


class MergeRequest(BaseModel):
    """Request model for merge operations."""

    target_id: int = Field(..., description="Target entity ID")
    source_ids: List[int] = Field(..., min_length=1, description="Source entity IDs")
    confirm: bool = Field(default=False, description="Confirmation flag")

    @model_validator(mode="after")
    def validate_merge_ids(self):
        if self.target_id in self.source_ids:
            raise ValueError("Target ID must not be included in source IDs")
        return self


class BulkDeleteRequest(BaseModel):
    """Request model for bulk delete operations."""

    ids: List[int] = Field(..., min_length=1, description="Entity IDs to delete")
    force: bool = Field(default=False, description="Force delete even if in use")
    confirm: bool = Field(default=False, description="Confirmation flag")


class CategoryFindReplaceRequest(BaseModel):
    """Request model for category find-and-replace operations."""

    find: str = Field(..., min_length=1, max_length=100, description="Find category name")
    replace: str = Field(..., min_length=1, max_length=100, description="Replace category name")
    confirm: bool = Field(default=False, description="Confirmation flag")

    @field_validator("find", "replace")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = _normalize_name(value)
        if not normalized:
            raise ValueError("Name cannot be empty")
        return _validate_name(normalized)

    @model_validator(mode="after")
    def ensure_distinct(self):
        if self.find.lower() == self.replace.lower():
            raise ValueError("Find and replace values must be different")
        return self


class TagFindReplaceRequest(BaseModel):
    """Request model for tag find-and-replace operations."""

    find: str = Field(..., min_length=1, max_length=50, description="Find tag name")
    replace: str = Field(..., min_length=1, max_length=50, description="Replace tag name")
    confirm: bool = Field(default=False, description="Confirmation flag")

    @field_validator("find", "replace")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = _normalize_name(value)
        if not normalized:
            raise ValueError("Name cannot be empty")
        return _validate_name(normalized)

    @model_validator(mode="after")
    def ensure_distinct(self):
        if self.find.lower() == self.replace.lower():
            raise ValueError("Find and replace values must be different")
        return self


class ReorderRequest(BaseModel):
    """Request model for reorder operations."""

    ordered_ids: List[int] = Field(..., min_length=1, description="Ordered entity IDs")

    @model_validator(mode="after")
    def validate_unique(self):
        if len(set(self.ordered_ids)) != len(self.ordered_ids):
            raise ValueError("Ordered IDs must be unique")
        return self


class BulkTagUpdateRequest(BaseModel):
    """Request model for bulk tag updates on prompts."""

    prompt_ids: List[int] = Field(..., min_length=1, description="Prompt IDs to update")
    add: List[str] = Field(default_factory=list, description="Tags to add")
    remove: List[str] = Field(default_factory=list, description="Tags to remove")
    confirm: bool = Field(default=False, description="Confirmation flag")

    @field_validator("add", "remove")
    @classmethod
    def normalize_tags(cls, value: List[str]) -> List[str]:
        normalized = [tag.strip() for tag in value if tag and tag.strip()]
        if len(normalized) > 50:
            raise ValueError("Maximum 50 tags allowed")
        for tag in normalized:
            if len(tag) > 50:
                raise ValueError(f"Tag '{tag}' exceeds maximum length of 50 characters")
        return normalized

    @model_validator(mode="after")
    def ensure_changes(self):
        if not self.add and not self.remove:
            raise ValueError("At least one tag to add or remove must be provided")
        return self


class TagSuggestRequest(BaseModel):
    """Request model for tag suggestion."""

    prompt_id: Optional[int] = Field(default=None, description="Prompt ID to analyze")
    content: Optional[str] = Field(default=None, min_length=1, description="Prompt content")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum suggestions")

    @model_validator(mode="after")
    def validate_input(self):
        if self.prompt_id is None and not self.content:
            raise ValueError("Either prompt_id or content must be provided")
        return self


class CategoryImportItem(BaseModel):
    """Single category import item."""

    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    color: Optional[str] = Field(default=None)
    sort_order: Optional[int] = Field(default=None)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = _normalize_name(value)
        if not normalized:
            raise ValueError("Category name cannot be empty")
        return _validate_name(normalized)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: Optional[str]) -> Optional[str]:
        return _validate_color(value)


class TagImportItem(BaseModel):
    """Single tag import item."""

    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = Field(default=None, max_length=500)
    color: Optional[str] = Field(default=None)
    parent_tag_id: Optional[int] = Field(default=None)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = _normalize_name(value)
        if not normalized:
            raise ValueError("Tag name cannot be empty")
        return _validate_name(normalized)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: Optional[str]) -> Optional[str]:
        return _validate_color(value)


class CategoryImportRequest(BaseModel):
    """Request model for importing categories."""

    items: List[CategoryImportItem] = Field(..., min_length=1)


class TagImportRequest(BaseModel):
    """Request model for importing tags."""

    items: List[TagImportItem] = Field(..., min_length=1)


class CategoryAssignOrphansRequest(BaseModel):
    """Request model for assigning orphan prompts to a category."""

    prompt_ids: List[int] = Field(..., min_length=1, description="Prompt IDs to update")
    category: str = Field(..., min_length=1, max_length=100, description="Category name to assign")
    confirm: bool = Field(default=False, description="Confirmation flag")

    @field_validator("category")
    @classmethod
    def normalize_category(cls, value: str) -> str:
        normalized = _normalize_name(value)
        if not normalized:
            raise ValueError("Category name cannot be empty")
        return _validate_name(normalized)
