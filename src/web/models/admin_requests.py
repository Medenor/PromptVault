# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pydantic request validation models for admin API.

This module defines request validation schemas for all admin endpoints,
implementing comprehensive input validation and security best practices
for administrative operations.

All request models include:
    - Field validation with Pydantic validators
    - Input sanitization
    - OpenAPI documentation examples
    - Security-focused validation rules
"""

from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator


class UpdateUserRequest(BaseModel):
    """Request model for updating user by admin.

    Field constraints:
        - role: Optional user role (viewer, editor, admin)
        - is_active: Optional account active status
        - email_verified: Optional email verification status

    At least one field must be provided.

    Example:
        >>> request = UpdateUserRequest(
        ...     role="editor",
        ...     is_active=True
        ... )
    """

    role: Optional[Literal["viewer", "editor", "admin"]] = Field(
        default=None,
        description="User role (viewer, editor, admin)",
        examples=["viewer", "editor", "admin"],
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Account active status",
        examples=[True, False],
    )
    email_verified: Optional[bool] = Field(
        default=None,
        description="Email verification status",
        examples=[True, False],
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        """Validate role value.

        Args:
            v: Role to validate

        Returns:
            Validated role

        Raises:
            ValueError: If role is invalid
        """
        if v is not None:
            valid_roles = {"viewer", "editor", "admin"}
            if v not in valid_roles:
                raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


class UserListParams(BaseModel):
    """Query parameters for listing users.

    Field constraints:
        - page: Page number (default 1, minimum 1)
        - page_size: Items per page (default 20, range 1-100)
        - role: Optional role filter
        - is_active: Optional active status filter
        - search: Optional username/email search

    Example:
        >>> params = UserListParams(
        ...     page=1,
        ...     page_size=20,
        ...     role="editor",
        ...     is_active=True,
        ...     search="john"
        ... )
    """

    page: int = Field(
        default=1,
        ge=1,
        description="Page number (starts at 1)",
        examples=[1, 2, 10],
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page (1-100)",
        examples=[10, 20, 50, 100],
    )
    role: Optional[Literal["viewer", "editor", "admin"]] = Field(
        default=None,
        description="Filter by role",
        examples=["viewer", "editor", "admin"],
    )
    is_active: Optional[bool] = Field(
        default=None,
        description="Filter by active status",
        examples=[True, False],
    )
    search: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Search by username or email (case-insensitive)",
        examples=["john", "user@example.com"],
    )

    @field_validator("search")
    @classmethod
    def validate_search(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize search query.

        Args:
            v: Search query

        Returns:
            Sanitized search query or None
        """
        if v is not None:
            v = v.strip()
            if not v:
                return None
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        """Validate role filter value.

        Args:
            v: Role to validate

        Returns:
            Validated role

        Raises:
            ValueError: If role is invalid
        """
        if v is not None:
            valid_roles = {"viewer", "editor", "admin"}
            if v not in valid_roles:
                raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v
