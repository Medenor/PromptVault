# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pydantic request validation models for the prompt sharing API."""

from typing import Literal

from pydantic import BaseModel, Field


class PromptVisibilityUpdateRequest(BaseModel):
    """Request model for un-grandfathering a legacy-public prompt.

    Attributes:
        legacy_public: Must be ``False`` — the one-way un-grandfather
            transition (contracts §4b, FR-018). ``True`` is rejected by the
            route handler with a 400 (there is no re-publish action).
    """

    legacy_public: bool | None = Field(
        default=None,
        description="Set to false to un-grandfather a legacy-public prompt",
    )


class ShareGrantRequest(BaseModel):
    """Request model for granting (or updating) a prompt share.

    Attributes:
        identifier: Username or email of the grantee.
        permission: Access level to grant — 'read' or 'edit'.
    """

    identifier: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Username or email of the user to share with",
        examples=["alice", "alice@example.com"],
    )
    permission: Literal["read", "edit"] = Field(
        ...,
        description="Access level to grant",
        examples=["read", "edit"],
    )
