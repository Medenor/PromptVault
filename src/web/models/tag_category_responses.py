# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pydantic response models for tag/category management."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryResponse(BaseModel):
    """Category response with metadata and usage counts."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    color: str | None = None
    sort_order: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    usage_count: int = Field(
        default=0, description="Number of prompts using this category"
    )


class TagResponse(BaseModel):
    """Tag response with metadata and usage counts."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    color: str | None = None
    parent_tag_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    usage_count: int = Field(default=0, description="Number of prompts using this tag")


class CategoryListResponse(BaseModel):
    """List response for categories."""

    items: list[CategoryResponse]


class TagListResponse(BaseModel):
    """List response for tags."""

    items: list[TagResponse]


class BulkActionResponse(BaseModel):
    """Generic bulk action response."""

    success: bool
    affected: int


class OrphanPromptsResponse(BaseModel):
    """Response for prompts without a category."""

    prompt_ids: list[int]
    count: int


class OrphanPromptItem(BaseModel):
    """Prompt metadata for orphan lists."""

    id: int
    title: str


class OrphanPromptDetailsResponse(BaseModel):
    """Response for orphan prompt details."""

    items: list[OrphanPromptItem]
    count: int


class TagSuggestionItem(BaseModel):
    """Single tag suggestion item."""

    name: str
    score: float


class TagSuggestionResponse(BaseModel):
    """Response for tag suggestions."""

    suggestions: list[TagSuggestionItem]
