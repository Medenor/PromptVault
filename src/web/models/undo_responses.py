# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pydantic response models for undo operations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UndoOperationResponse(BaseModel):
    """Response model for a single undo operation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: str
    entity_type: str = Field(description="Type of entity: 'tag' or 'category'")
    operation: str = Field(description="Operation type: 'create', 'update', 'delete'")
    payload: dict[str, Any] = Field(
        description="JSON data needed to undo the operation"
    )
    created_at: datetime
    expires_at: datetime


class UndoHistoryResponse(BaseModel):
    """Response model for undo operation history."""

    operations: list[UndoOperationResponse] = Field(
        description="List of undo operations"
    )
    count: int = Field(description="Total number of operations")


class UndoResultResponse(BaseModel):
    """Response model for undo operation execution result."""

    success: bool = Field(description="Whether the undo was successful")
    entity_type: str = Field(description="Type of entity that was affected")
    operation: str = Field(description="Operation that was undone")
    entity_id: int | None = Field(None, description="ID of the entity affected by undo")
    message: str | None = Field(
        None, description="Optional message about the undo result"
    )
