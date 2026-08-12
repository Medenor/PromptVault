# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pydantic response models for the prompt sharing API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class UserSuggestion(BaseModel):
    """A single user typeahead result.

    Attributes:
        id: User's unique identifier (UUID).
        username: User's username (no email — avoids leaking it via search).
    """

    id: str = Field(..., description="User's unique identifier (UUID)")
    username: str = Field(..., description="User's username")


class ShareGranteeInfo(BaseModel):
    """Grantee summary embedded in a share response.

    Attributes:
        id: Grantee's unique identifier (UUID).
        username: Grantee's username.
    """

    id: str = Field(..., description="Grantee's unique identifier (UUID)")
    username: str = Field(..., description="Grantee's username")


class ShareResponse(BaseModel):
    """Response model for a single prompt share grant.

    Attributes:
        prompt_id: The shared prompt's id.
        grantee: The user the prompt was shared with.
        permission: Effective access level ('read' or 'edit').
        granted_by: Username of the granting user, or None if that account
            has since been deleted.
        created_at: Grant creation timestamp.
        updated_at: Timestamp of the last permission-level change.
    """

    prompt_id: int = Field(..., description="The shared prompt's id")
    grantee: ShareGranteeInfo = Field(..., description="The user granted access")
    permission: Literal["read", "edit"] = Field(
        ..., description="Effective access level"
    )
    granted_by: str | None = Field(
        default=None,
        description="Username of the granting user, or None if deleted",
    )
    created_at: datetime = Field(..., description="Grant creation timestamp")
    updated_at: datetime = Field(
        ..., description="Last permission-level change timestamp"
    )


class ShareListResponse(BaseModel):
    """Response model for listing a prompt's grants.

    Attributes:
        prompt_id: The prompt whose grants are listed.
        shares: All active grants on the prompt.
    """

    prompt_id: int = Field(..., description="The prompt whose grants are listed")
    shares: list[ShareResponse] = Field(
        default_factory=list, description="All active grants on the prompt"
    )


class UserSearchResponse(BaseModel):
    """Response model for the user typeahead endpoint.

    Attributes:
        users: Matching active users (usernames only).
    """

    users: list[UserSuggestion] = Field(
        default_factory=list, description="Matching active users"
    )
