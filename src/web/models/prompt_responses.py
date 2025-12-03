# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pydantic response models for prompt-related API endpoints.

This module defines response schemas for prompt operations,
ensuring consistent and type-safe API responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime


class PromptResponse(BaseModel):
    """Response model for a single prompt.

    Attributes:
        id: Prompt ID
        title: Prompt title
        prompt: Prompt content
        category: Category name (empty string if no category)
        tags: List of tag names
        note: Optional note/description
        favorite: Favorite status
        user_id: Owner's user ID
        created_at: Creation timestamp
        updated_at: Last update timestamp
    """

    id: int = Field(..., description="Prompt ID")
    title: str = Field(..., description="Prompt title")
    prompt: str = Field(..., description="Prompt content")
    category: str = Field(..., description="Category name")
    tags: List[str] = Field(..., description="List of tags")
    note: str = Field(..., description="Optional note")
    favorite: bool = Field(..., description="Favorite status")
    user_id: str = Field(..., description="Owner's user ID")
    created_at: Optional[str] = Field(None, description="Creation timestamp (ISO format)")
    updated_at: Optional[str] = Field(None, description="Update timestamp (ISO format)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": 1,
                "title": "Marketing Email Template",
                "prompt": "Write a marketing email about...",
                "category": "Marketing",
                "tags": ["email", "marketing", "template"],
                "note": "Use for customer outreach",
                "favorite": True,
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2024-01-01T12:00:00Z",
                "updated_at": "2024-01-02T10:30:00Z",
            }
        }
    }


class PromptListResponse(BaseModel):
    """Response model for listing prompts.

    Attributes:
        prompts: Dictionary of prompts keyed by ID (as string)
    """

    prompts: Dict[str, PromptResponse] = Field(
        ..., description="Dictionary of prompts keyed by ID"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "prompts": {
                    "1": {
                        "id": 1,
                        "title": "Marketing Email",
                        "prompt": "Write a marketing email...",
                        "category": "Marketing",
                        "tags": ["email"],
                        "note": "",
                        "favorite": False,
                        "user_id": "550e8400-e29b-41d4-a716-446655440000",
                        "created_at": "2024-01-01T12:00:00Z",
                        "updated_at": None,
                    }
                }
            }
        }
    }


class PromptCreateResponse(BaseModel):
    """Response model for prompt creation.

    Attributes:
        success: Whether the operation succeeded
        prompt_id: ID of the created prompt
    """

    success: bool = Field(..., description="Operation success status")
    prompt_id: int = Field(..., description="Created prompt ID")

    model_config = {
        "json_schema_extra": {
            "example": {"success": True, "prompt_id": 42}
        }
    }


class PromptUpdateResponse(BaseModel):
    """Response model for prompt update.

    Attributes:
        success: Whether the operation succeeded
    """

    success: bool = Field(..., description="Operation success status")

    model_config = {
        "json_schema_extra": {
            "example": {"success": True}
        }
    }


class PromptDeleteResponse(BaseModel):
    """Response model for prompt deletion.

    Attributes:
        success: Whether the operation succeeded
    """

    success: bool = Field(..., description="Operation success status")

    model_config = {
        "json_schema_extra": {
            "example": {"success": True}
        }
    }


class PromptFavoriteResponse(BaseModel):
    """Response model for toggling favorite status.

    Attributes:
        success: Whether the operation succeeded
        favorite: New favorite status
    """

    success: bool = Field(..., description="Operation success status")
    favorite: bool = Field(..., description="New favorite status")

    model_config = {
        "json_schema_extra": {
            "example": {"success": True, "favorite": True}
        }
    }


class BulkDeleteResponse(BaseModel):
    """Response model for bulk delete operation.

    Attributes:
        success: Whether the operation succeeded
        deleted_count: Number of prompts successfully deleted
        failed_count: Number of prompts that failed to delete
        failed_ids: List of IDs that failed to delete
    """

    success: bool = Field(..., description="Operation success status")
    deleted_count: int = Field(..., description="Number of prompts deleted")
    failed_count: int = Field(..., description="Number of failed deletions")
    failed_ids: List[int] = Field(..., description="List of failed prompt IDs")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "deleted_count": 5,
                "failed_count": 0,
                "failed_ids": [],
            }
        }
    }
