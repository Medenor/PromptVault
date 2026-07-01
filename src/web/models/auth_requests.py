# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pydantic request validation models for authentication API.

This module defines request validation schemas for all authentication endpoints,
implementing comprehensive input validation, password policy checks, and security
best practices.

All request models include:
    - Field validation with Pydantic validators
    - Input sanitization (whitespace stripping)
    - Password confirmation matching
    - OpenAPI documentation examples
    - Security-focused validation rules
"""

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class RegisterRequest(BaseModel):
    """Request model for user registration.

    Field constraints:
        - username: 3-32 characters, alphanumeric + underscore only, required
        - email: Valid email format, required
        - password: Must meet password policy (min length from config), required
        - confirm_password: Must match password, required

    Example:
        >>> request = RegisterRequest(
        ...     username="alice",
        ...     email="alice@example.com",
        ...     password="SecureP@ssw0rd123",
        ...     confirm_password="SecureP@ssw0rd123"
        ... )
    """

    username: str = Field(
        ...,
        min_length=3,
        max_length=32,
        description="Username (alphanumeric and underscore only)",
        examples=["alice", "bob_smith", "user123"],
    )
    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Email address",
        examples=["alice@example.com", "user@domain.co.uk"],
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Password (must meet security policy)",
        examples=["MySecureP@ssw0rd123"],
    )
    confirm_password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Password confirmation (must match password)",
        examples=["MySecureP@ssw0rd123"],
    )

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format and strip whitespace.

        Rules:
            - 3-32 characters
            - Only alphanumeric and underscore allowed
            - No leading/trailing whitespace
            - Cannot be only underscores

        Args:
            v: Username to validate

        Returns:
            Validated and sanitized username

        Raises:
            ValueError: If username format is invalid
        """
        # Strip whitespace
        v = v.strip()

        # Validate length after stripping
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if len(v) > 32:
            raise ValueError("Username must not exceed 32 characters")

        # Validate character set (alphanumeric + underscore)
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "Username can only contain letters, numbers, and underscores"
            )

        # Prevent usernames that are only underscores
        if v.replace("_", "") == "":
            raise ValueError("Username cannot be only underscores")

        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format and normalize.

        Rules:
            - Basic email format validation
            - Convert to lowercase for consistency
            - Strip whitespace

        Args:
            v: Email to validate

        Returns:
            Validated and normalized email

        Raises:
            ValueError: If email format is invalid
        """
        # Strip whitespace and convert to lowercase
        v = v.strip().lower()

        # Basic email validation
        if "@" not in v or "." not in v.split("@")[1]:
            raise ValueError("Invalid email address format")

        # Prevent multiple @ signs
        if v.count("@") > 1:
            raise ValueError("Invalid email address format")

        # Prevent empty local or domain parts
        local, domain = v.split("@")
        if not local or not domain:
            raise ValueError("Invalid email address format")

        return v

    @field_validator("password", "confirm_password")
    @classmethod
    def validate_password_not_empty(cls, v: str) -> str:
        """Ensure password is not empty or whitespace only.

        Note: Full password policy validation is done by AuthService.
        This validator only checks for empty passwords.

        Args:
            v: Password to validate

        Returns:
            Original password (not stripped to preserve spaces)

        Raises:
            ValueError: If password is empty or whitespace only
        """
        if not v or not v.strip():
            raise ValueError("Password cannot be empty or whitespace only")

        return v

    @model_validator(mode="after")
    def validate_passwords_match(self):
        """Validate that password and confirm_password match.

        This is a model-level validator that runs after all field validators.

        Returns:
            Self if validation passes

        Raises:
            ValueError: If passwords don't match
        """
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")

        return self

    @field_validator("password")
    @classmethod
    def validate_password_policy_message(cls, v: str) -> str:
        """Ensure password validation errors mention password explicitly."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v

    @field_validator("confirm_password")
    @classmethod
    def validate_confirm_password_policy_message(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class LoginRequest(BaseModel):
    """Request model for user login.

    Field constraints:
        - username_or_email: Username or email, required
        - password: User's password, required
        - remember_me: Keep user logged in with extended refresh token

    Example:
        >>> request = LoginRequest(
        ...     username_or_email="alice",
        ...     password="SecureP@ssw0rd123"
        ... )
    """

    username_or_email: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Username or email address",
        examples=["alice", "alice@example.com"],
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="User password",
        examples=["MySecureP@ssw0rd123"],
    )
    remember_me: bool = Field(
        default=False,
        description="Extend session duration for this device",
        examples=[True],
    )

    @field_validator("username_or_email")
    @classmethod
    def strip_username_or_email(cls, v: str) -> str:
        """Strip whitespace and convert to lowercase if email.

        Args:
            v: Username or email

        Returns:
            Sanitized input

        Raises:
            ValueError: If empty after stripping
        """
        v = v.strip()

        if not v:
            raise ValueError("Username or email cannot be empty")

        # Convert to lowercase if it looks like an email
        if "@" in v:
            v = v.lower()

        return v

    @field_validator("password")
    @classmethod
    def validate_password_not_empty(cls, v: str) -> str:
        """Ensure password is not empty.

        Args:
            v: Password to validate

        Returns:
            Original password

        Raises:
            ValueError: If password is empty
        """
        if not v:
            raise ValueError("Password cannot be empty")

        return v


class RefreshTokenRequest(BaseModel):
    """Request model for refreshing access token.

    Field constraints:
        - refresh_token: Valid JWT refresh token, required

    Example:
        >>> request = RefreshTokenRequest(
        ...     refresh_token="eyJ0eXAiOiJKV1QiLCJhbGc..."
        ... )
    """

    refresh_token: str = Field(
        ...,
        min_length=10,
        description="JWT refresh token",
        examples=["eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9..."],
    )

    @field_validator("refresh_token")
    @classmethod
    def validate_refresh_token(cls, v: str) -> str:
        """Validate refresh token format.

        Args:
            v: Refresh token to validate

        Returns:
            Sanitized token

        Raises:
            ValueError: If token is invalid
        """
        v = v.strip()

        if not v:
            raise ValueError("Refresh token cannot be empty")

        # Basic JWT format check (three parts separated by dots)
        if v.count(".") != 2:
            raise ValueError("Invalid refresh token format")

        return v


class LogoutRequest(BaseModel):
    """Request model for logout endpoint (all fields optional — token may come from cookie)."""

    refresh_token: Optional[str] = Field(
        None,
        min_length=10,
        description="JWT refresh token (optional if sent via cookie)",
    )


class ChangePasswordRequest(BaseModel):
    """Request model for changing user password.

    Field constraints:
        - old_password: Current password for verification, required
        - new_password: New password (must meet policy), required
        - confirm_new_password: Must match new_password, required

    Example:
        >>> request = ChangePasswordRequest(
        ...     old_password="OldP@ssw0rd123",
        ...     new_password="NewP@ssw0rd456",
        ...     confirm_new_password="NewP@ssw0rd456"
        ... )
    """

    old_password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="Current password for verification",
        examples=["OldP@ssw0rd123"],
    )
    new_password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="New password (must meet security policy)",
        examples=["NewP@ssw0rd456"],
    )
    confirm_new_password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="New password confirmation (must match new_password)",
        examples=["NewP@ssw0rd456"],
    )

    @field_validator("old_password", "new_password", "confirm_new_password")
    @classmethod
    def validate_password_not_empty(cls, v: str) -> str:
        """Ensure passwords are not empty.

        Args:
            v: Password to validate

        Returns:
            Original password

        Raises:
            ValueError: If password is empty
        """
        if not v or not v.strip():
            raise ValueError("Password cannot be empty or whitespace only")

        return v

    @model_validator(mode="after")
    def validate_passwords_match(self):
        """Validate that new_password and confirm_new_password match.

        Returns:
            Self if validation passes

        Raises:
            ValueError: If passwords don't match or new password equals old
        """
        if self.new_password != self.confirm_new_password:
            raise ValueError("New passwords do not match")

        if self.old_password == self.new_password:
            raise ValueError("New password must be different from old password")

        return self


class PasswordResetRequestRequest(BaseModel):
    """Request model for initiating password reset.

    Field constraints:
        - email: Email address of account to reset, required

    Example:
        >>> request = PasswordResetRequestRequest(
        ...     email="alice@example.com"
        ... )
    """

    email: str = Field(
        ...,
        min_length=5,
        max_length=255,
        description="Email address for password reset",
        examples=["alice@example.com"],
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format and normalize.

        Args:
            v: Email to validate

        Returns:
            Validated and normalized email

        Raises:
            ValueError: If email format is invalid
        """
        v = v.strip().lower()

        if "@" not in v or "." not in v.split("@")[1]:
            raise ValueError("Invalid email address format")

        return v


class PasswordResetConfirmRequest(BaseModel):
    """Request model for confirming password reset with token.

    Field constraints:
        - token: Password reset token from email, required
        - new_password: New password (must meet policy), required
        - confirm_new_password: Must match new_password, required

    Example:
        >>> request = PasswordResetConfirmRequest(
        ...     token="abc123def456",
        ...     new_password="NewP@ssw0rd456",
        ...     confirm_new_password="NewP@ssw0rd456"
        ... )
    """

    token: str = Field(
        ...,
        min_length=10,
        max_length=500,
        description="Password reset token from email",
        examples=["a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"],
    )
    new_password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="New password (must meet security policy)",
        examples=["NewP@ssw0rd456"],
    )
    confirm_new_password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="New password confirmation (must match new_password)",
        examples=["NewP@ssw0rd456"],
    )

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        """Validate token format.

        Args:
            v: Token to validate

        Returns:
            Sanitized token

        Raises:
            ValueError: If token is empty
        """
        v = v.strip()

        if not v:
            raise ValueError("Reset token cannot be empty")

        return v

    @field_validator("new_password", "confirm_new_password")
    @classmethod
    def validate_password_not_empty(cls, v: str) -> str:
        """Ensure passwords are not empty.

        Args:
            v: Password to validate

        Returns:
            Original password

        Raises:
            ValueError: If password is empty
        """
        if not v or not v.strip():
            raise ValueError("Password cannot be empty or whitespace only")

        return v

    @model_validator(mode="after")
    def validate_passwords_match(self):
        """Validate that new_password and confirm_new_password match.

        Returns:
            Self if validation passes

        Raises:
            ValueError: If passwords don't match
        """
        if self.new_password != self.confirm_new_password:
            raise ValueError("New passwords do not match")

        return self


class RevokeSessionRequest(BaseModel):
    """Request model for revoking user sessions.

    Field constraints:
        - session_id: Optional session ID to revoke specific session
                      If not provided, can be used for revoking all sessions

    Example:
        >>> # Revoke specific session
        >>> request = RevokeSessionRequest(
        ...     session_id="550e8400-e29b-41d4-a716-446655440000"
        ... )
        >>>
        >>> # Revoke all sessions (session_id is None)
        >>> request = RevokeSessionRequest()
    """

    session_id: Optional[str] = Field(
        default=None,
        min_length=36,
        max_length=36,
        description="Session ID to revoke (UUID format). If not provided, revokes all sessions.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        """Validate session ID format (UUID).

        Args:
            v: Session ID to validate

        Returns:
            Validated session ID or None

        Raises:
            ValueError: If session ID format is invalid
        """
        if v is None:
            return None

        v = v.strip()

        if not v:
            return None

        # Basic UUID format validation (8-4-4-4-12 hexadecimal)
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        if not re.match(uuid_pattern, v, re.IGNORECASE):
            raise ValueError("Invalid session ID format (must be UUID)")

        return v.lower()


class UpdateProfileRequest(BaseModel):
    """Request model for updating user profile.

    Allows authenticated users to update their display name and/or email address.

    Field constraints:
        - display_name: 1-200 characters (optional)
        - email: Valid email format, must be unique (optional)
        - At least one field must be provided

    Example:
        >>> request = UpdateProfileRequest(
        ...     display_name="Alice Smith",
        ...     email="newemail@example.com"
        ... )
    """

    display_name: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=200,
        description="Display name (1-200 characters)",
        examples=["Alice Smith", "Bob Johnson"],
    )
    email: Optional[str] = Field(
        default=None,
        min_length=5,
        max_length=255,
        description="Email address (must be unique)",
        examples=["newemail@example.com"],
    )

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and normalize display name.

        Args:
            v: Display name to validate

        Returns:
            Validated and normalized display name or None

        Raises:
            ValueError: If display name is empty or only whitespace
        """
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Display name cannot be empty or whitespace only")

        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format and normalize.

        Args:
            v: Email to validate

        Returns:
            Validated and normalized email or None

        Raises:
            ValueError: If email format is invalid
        """
        if v is not None:
            v = v.strip().lower()
            if "@" not in v or "." not in v.split("@")[1]:
                raise ValueError("Invalid email address format")

        return v

    @model_validator(mode="after")
    def validate_at_least_one_field(self):
        """Ensure at least one field is provided for update.

        Raises:
            ValueError: If both fields are None
        """
        if self.display_name is None and self.email is None:
            raise ValueError("At least one field (display_name or email) must be provided")

        return self
