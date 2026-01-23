# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pydantic response models for tag/category management."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CategoryResponse(BaseModel):
    """Category response with metadata and usage counts."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    sort_order: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    usage_count: int = Field(default=0, description="Number of prompts using this category")


class TagResponse(BaseModel):
    """Tag response with metadata and usage counts."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    color: Optional[str] = None
    parent_tag_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    usage_count: int = Field(default=0, description="Number of prompts using this tag")


class CategoryListResponse(BaseModel):
    """List response for categories."""

    items: List[CategoryResponse]


class TagListResponse(BaseModel):
    """List response for tags."""

    items: List[TagResponse]


class BulkActionResponse(BaseModel):
    """Generic bulk action response."""

    success: bool
    affected: int


class OrphanPromptsResponse(BaseModel):
    """Response for prompts without a category."""

    prompt_ids: List[int]
    count: int


class OrphanPromptItem(BaseModel):
    """Prompt metadata for orphan lists."""

    id: int
    title: str


class OrphanPromptDetailsResponse(BaseModel):
    """Response for orphan prompt details."""

    items: List[OrphanPromptItem]
    count: int


class TagSuggestionItem(BaseModel):
    """Single tag suggestion item."""

    name: str
    score: float


class TagSuggestionResponse(BaseModel):
    """Response for tag suggestions."""

    suggestions: List[TagSuggestionItem]
