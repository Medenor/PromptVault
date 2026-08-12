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

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CreateUserRequest(BaseModel):
    """Request model for creating a new user by admin.

    Field constraints:
        - username: 3-32 characters, alphanumeric + underscore only, unique
        - email: Valid email format, unique
        - password: Min 12 chars, must contain uppercase, lowercase, digit, special char
        - confirm_password: Must match password
        - role: User role (viewer, editor, admin) - optional, defaults to viewer
        - email_verified: Whether to mark email as verified - optional, defaults to False

    Example:
        >>> request = CreateUserRequest(
        ...     username="john_doe",
        ...     email="john@example.com",
        ...     password="SecureP@ssw0rd123",
        ...     confirm_password="SecureP@ssw0rd123",
        ...     role="editor",
        ...     email_verified=False
        ... )
    """

    username: str = Field(
        ...,
        min_length=3,
        max_length=32,
        description="Username (3-32 chars, alphanumeric + underscore)",
        examples=["john_doe", "user123"],
    )
    email: str = Field(
        ...,
        description="Email address",
        examples=["john@example.com"],
    )
    password: str = Field(
        ...,
        min_length=12,
        max_length=128,
        description="Password (min 12 chars, must contain uppercase, lowercase, digit, special char)",
        examples=["SecureP@ssw0rd123"],
    )
    confirm_password: str = Field(
        ...,
        min_length=12,
        max_length=128,
        description="Password confirmation (must match password)",
        examples=["SecureP@ssw0rd123"],
    )
    role: Literal["viewer", "editor", "admin"] = Field(
        default="viewer",
        description="User role (defaults to viewer)",
        examples=["viewer", "editor", "admin"],
    )
    email_verified: bool = Field(
        default=False,
        description="Whether to mark email as verified",
        examples=[True, False],
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format.

        Args:
            v: Username to validate

        Returns:
            Validated username

        Raises:
            ValueError: If username format is invalid
        """
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "Username must contain only letters, numbers, and underscores"
            )
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format.

        Args:
            v: Email to validate

        Returns:
            Validated email

        Raises:
            ValueError: If email format is invalid
        """
        email_regex = r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
        if not re.match(email_regex, v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password policy.

        Args:
            v: Password to validate

        Returns:
            Validated password

        Raises:
            ValueError: If password doesn't meet policy requirements
        """
        errors = []

        if len(v) < 12:
            errors.append("Password must be at least 12 characters")
        if not re.search(r"[A-Z]", v):
            errors.append("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            errors.append("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            errors.append("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", v):
            errors.append("Password must contain at least one special character")

        if errors:
            raise ValueError(" | ".join(errors))

        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password(cls, v: str, info) -> str:
        """Validate that confirm_password matches password.

        Args:
            v: Confirmation password
            info: Validation info with other field values

        Returns:
            Validated confirmation password

        Raises:
            ValueError: If passwords don't match
        """
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        """Validate role value.

        Args:
            v: Role to validate

        Returns:
            Validated role

        Raises:
            ValueError: If role is invalid
        """
        valid_roles = {"viewer", "editor", "admin"}
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}")
        return v


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

    role: Literal["viewer", "editor", "admin"] | None = Field(
        default=None,
        description="User role (viewer, editor, admin)",
        examples=["viewer", "editor", "admin"],
    )
    is_active: bool | None = Field(
        default=None,
        description="Account active status",
        examples=[True, False],
    )
    email_verified: bool | None = Field(
        default=None,
        description="Email verification status",
        examples=[True, False],
    )

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str | None) -> str | None:
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
    role: Literal["viewer", "editor", "admin"] | None = Field(
        default=None,
        description="Filter by role",
        examples=["viewer", "editor", "admin"],
    )
    is_active: bool | None = Field(
        default=None,
        description="Filter by active status",
        examples=[True, False],
    )
    search: str | None = Field(
        default=None,
        max_length=255,
        description="Search by username or email (case-insensitive)",
        examples=["john", "user@example.com"],
    )

    @field_validator("search")
    @classmethod
    def validate_search(cls, v: str | None) -> str | None:
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
    def validate_role(cls, v: str | None) -> str | None:
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
