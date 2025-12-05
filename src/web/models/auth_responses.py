# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pydantic response models for authentication API.

This module defines response schemas for all authentication endpoints,
implementing consistent response structures, proper serialization, and
OpenAPI documentation support.

All response models include:
    - Field descriptions for OpenAPI documentation
    - Example values for API documentation
    - Type hints for all fields
    - Proper datetime serialization
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, ConfigDict, field_serializer


class UserResponse(BaseModel):
    """Response model for user information.

    This model matches the User database model and is used in
    authentication responses to provide user details.

    Attributes:
        id: User's unique identifier (UUID)
        username: User's username
        email: User's email address
        role: User's role (viewer/editor/admin)
        is_active: Account active status
        email_verified: Email verification status
        created_at: Account creation timestamp
        updated_at: Account last update timestamp

    Example:
        >>> user = UserResponse(
        ...     id="550e8400-e29b-41d4-a716-446655440000",
        ...     username="alice",
        ...     email="alice@example.com",
        ...     role="viewer",
        ...     is_active=True,
        ...     email_verified=False,
        ...     created_at=datetime.now(),
        ...     updated_at=datetime.now()
        ... )
    """

    id: str = Field(
        ...,
        description="User's unique identifier (UUID)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    username: str = Field(
        ...,
        description="User's username",
        examples=["alice", "bob_smith"],
    )
    email: str = Field(
        ...,
        description="User's email address",
        examples=["alice@example.com"],
    )
    role: str = Field(
        ...,
        description="User's role (viewer, editor, admin)",
        examples=["viewer", "editor", "admin"],
    )
    is_active: bool = Field(
        ...,
        description="Account active status",
        examples=[True],
    )
    email_verified: bool = Field(
        ...,
        description="Email verification status",
        examples=[False, True],
    )
    created_at: datetime = Field(
        ...,
        description="Account creation timestamp",
        examples=["2025-12-02T10:30:00Z"],
    )
    updated_at: datetime = Field(
        ...,
        description="Account last update timestamp",
        examples=["2025-12-02T10:30:00Z"],
    )
    last_login: Optional[datetime] = Field(
        None,
        description="Last login timestamp",
        examples=["2025-12-02T10:30:00Z", None],
    )

    model_config = ConfigDict(
        from_attributes=True,  # Allow creation from ORM models
    )

    @field_serializer("created_at", "updated_at", "last_login", when_used="json")
    def _serialize_datetime(self, value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None


class TokenResponse(BaseModel):
    """Response model for authentication token pairs.

    This model is returned by login, register, and refresh token endpoints.

    Attributes:
        access_token: JWT access token for API authentication
        refresh_token: JWT refresh token for obtaining new access tokens
        token_type: Token type (always "Bearer")
        expires_in: Access token expiration time in seconds
        user: User information

    Example:
        >>> response = TokenResponse(
        ...     access_token="eyJ0eXAiOiJKV1QiLCJhbGc...",
        ...     refresh_token="eyJ0eXAiOiJKV1QiLCJhbGc...",
        ...     token_type="Bearer",
        ...     expires_in=900,
        ...     user=user_response
        ... )
    """

    access_token: str = Field(
        ...,
        description="JWT access token for API authentication",
        examples=["eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJleHAiOjE3MDEzNDU2MDAsImlhdCI6MTcwMTM0NDcwMCwidXNlcm5hbWUiOiJhbGljZSIsImVtYWlsIjoiYWxpY2VAZXhhbXBsZS5jb20iLCJyb2xlIjoidmlld2VyIn0..."],
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token for obtaining new access tokens",
        examples=["eyJ0eXAiOiJKV1QiLCJhbGciOiJFUzI1NiJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJleHAiOjE3MDE5NDk1MDAsImlhdCI6MTcwMTM0NDcwMCwiZmFtaWx5X2lkIjoiNzUwZTg0MDAtZTI5Yi00MWQ0LWE3MTYtNDQ2NjU1NDQwMDAwIiwianRpIjoiODUwZTg0MDAtZTI5Yi00MWQ0LWE3MTYtNDQ2NjU1NDQwMDAwIn0..."],
    )
    token_type: str = Field(
        default="Bearer",
        description="Token type (always 'Bearer')",
        examples=["Bearer"],
    )
    expires_in: int = Field(
        ...,
        description="Access token expiration time in seconds",
        examples=[900],  # 15 minutes
    )
    user: UserResponse = Field(
        ...,
        description="User information",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                "token_type": "Bearer",
                "expires_in": 900,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "username": "alice",
                    "email": "alice@example.com",
                    "role": "viewer",
                    "is_active": True,
                    "email_verified": False,
                    "created_at": "2025-12-02T10:30:00Z",
                    "updated_at": "2025-12-02T10:30:00Z",
                }
            }
        }
    )


class SessionResponse(BaseModel):
    """Response model for user session information.

    Attributes:
        id: Session unique identifier (UUID)
        family_id: Token family identifier (for rotation tracking)
        created_at: Session creation timestamp
        last_used_at: Last token refresh timestamp
        expires_at: Session expiration timestamp
        ip_address: Client IP address
        user_agent: Client user agent string
        is_revoked: Session revocation status

    Example:
        >>> session = SessionResponse(
        ...     id="650e8400-e29b-41d4-a716-446655440000",
        ...     family_id="750e8400-e29b-41d4-a716-446655440000",
        ...     created_at=datetime.now(),
        ...     last_used_at=datetime.now(),
        ...     expires_at=datetime.now(),
        ...     ip_address="192.168.1.1",
        ...     user_agent="Mozilla/5.0...",
        ...     is_revoked=False
        ... )
    """

    id: str = Field(
        ...,
        description="Session unique identifier (UUID)",
        examples=["650e8400-e29b-41d4-a716-446655440000"],
    )
    family_id: str = Field(
        ...,
        description="Token family identifier (for rotation tracking)",
        examples=["750e8400-e29b-41d4-a716-446655440000"],
    )
    created_at: datetime = Field(
        ...,
        description="Session creation timestamp",
        examples=["2025-12-02T10:30:00Z"],
    )
    last_used_at: Optional[datetime] = Field(
        default=None,
        description="Last token refresh timestamp",
        examples=["2025-12-02T11:45:00Z"],
    )
    expires_at: datetime = Field(
        ...,
        description="Session expiration timestamp",
        examples=["2025-12-09T10:30:00Z"],
    )
    ip_address: Optional[str] = Field(
        default=None,
        description="Client IP address",
        examples=["192.168.1.1", "2001:0db8:85a3:0000:0000:8a2e:0370:7334"],
    )
    user_agent: Optional[str] = Field(
        default=None,
        description="Client user agent string",
        examples=["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"],
    )
    is_revoked: bool = Field(
        ...,
        description="Session revocation status",
        examples=[False, True],
    )
    is_current: bool = Field(
        ...,
        description="Whether this is the current session",
        examples=[True, False],
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat()},
    )


class MessageResponse(BaseModel):
    """Generic response model for success/info messages.

    Attributes:
        message: Human-readable message
        detail: Optional additional details

    Example:
        >>> response = MessageResponse(
        ...     message="Password changed successfully",
        ...     detail="All sessions remain active"
        ... )
    """

    message: str = Field(
        ...,
        description="Human-readable message",
        examples=["Operation completed successfully", "Password changed successfully"],
    )
    detail: Optional[str] = Field(
        default=None,
        description="Optional additional details",
        examples=["All sessions remain active", "Check your email for reset link"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Operation completed successfully",
                "detail": "Additional information about the operation"
            }
        }
    )


class PasswordResetRequestResponse(BaseModel):
    """Response model for password reset request.

    Attributes:
        message: Success message
        email: Masked email address (e.g., u***@example.com)

    Security Note:
        Email is partially masked to prevent user enumeration attacks
        while still providing feedback to legitimate users.

    Example:
        >>> response = PasswordResetRequestResponse(
        ...     message="Password reset email sent",
        ...     email="a***@example.com"
        ... )
    """

    message: str = Field(
        ...,
        description="Success message",
        examples=["Password reset email sent"],
    )
    email: str = Field(
        ...,
        description="Masked email address (e.g., u***@example.com)",
        examples=["a***@example.com", "u***@domain.co.uk"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Password reset email sent",
                "email": "a***@example.com"
            }
        }
    )


class PasswordStrengthResponse(BaseModel):
    """Response model for password strength analysis.

    Attributes:
        level: Strength rating (weak/medium/strong/very_strong)
        entropy: Password entropy in bits
        feedback: List of improvement suggestions

    Example:
        >>> response = PasswordStrengthResponse(
        ...     level="strong",
        ...     entropy=68.4,
        ...     feedback=[]
        ... )
    """

    level: Literal["weak", "medium", "strong", "very_strong"] = Field(
        ...,
        description="Strength rating based on entropy",
        examples=["weak", "medium", "strong", "very_strong"],
    )
    entropy: float = Field(
        ...,
        description="Password entropy in bits (higher is better)",
        examples=[42.5, 68.4, 85.2],
    )
    feedback: list[str] = Field(
        default_factory=list,
        description="List of improvement suggestions (empty if strong)",
        examples=[
            [],
            ["Consider using a longer password (12+ characters)", "Add special characters for increased strength"]
        ],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "level": "strong",
                "entropy": 68.4,
                "feedback": []
            }
        }
    )


class SessionListResponse(BaseModel):
    """Response model for list of user sessions.

    Attributes:
        sessions: List of active user sessions
        total: Total number of sessions

    Example:
        >>> response = SessionListResponse(
        ...     sessions=[session1, session2],
        ...     total=2
        ... )
    """

    sessions: list[SessionResponse] = Field(
        ...,
        description="List of active user sessions",
    )
    total: int = Field(
        ...,
        description="Total number of sessions",
        examples=[0, 1, 5],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sessions": [
                    {
                        "id": "650e8400-e29b-41d4-a716-446655440000",
                        "family_id": "750e8400-e29b-41d4-a716-446655440000",
                        "created_at": "2025-12-02T10:30:00Z",
                        "last_used_at": "2025-12-02T11:45:00Z",
                        "expires_at": "2025-12-09T10:30:00Z",
                        "ip_address": "192.168.1.1",
                        "user_agent": "Mozilla/5.0...",
                        "is_revoked": False
                    }
                ],
                "total": 1
            }
        }
    )


class RevokeSessionResponse(BaseModel):
    """Response model for session revocation.

    Attributes:
        message: Success message
        revoked_count: Number of sessions revoked

    Example:
        >>> response = RevokeSessionResponse(
        ...     message="Session revoked successfully",
        ...     revoked_count=1
        ... )
    """

    message: str = Field(
        ...,
        description="Success message",
        examples=["Session revoked successfully", "All sessions revoked"],
    )
    revoked_count: int = Field(
        ...,
        description="Number of sessions revoked",
        examples=[0, 1, 5],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Session revoked successfully",
                "revoked_count": 1
            }
        }
    )
