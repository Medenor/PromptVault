# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Pydantic response models for admin API.

This module defines response schemas for all admin endpoints,
implementing consistent response structures, proper serialization,
and OpenAPI documentation support.

All response models include:
    - Field descriptions for OpenAPI documentation
    - Example values for API documentation
    - Type hints for all fields
    - Proper datetime serialization
"""

from datetime import datetime
from typing import Optional, Dict

from pydantic import BaseModel, Field, ConfigDict

from src.web.models.auth_responses import UserResponse


class UserDetailResponse(UserResponse):
    """Extended user response model with admin-only fields.

    This model extends the standard UserResponse with additional
    administrative fields that should only be visible to admins.

    Attributes:
        id: User's unique identifier (UUID)
        username: User's username
        email: User's email address
        role: User's role (viewer/editor/admin)
        is_active: Account active status
        email_verified: Email verification status
        created_at: Account creation timestamp
        updated_at: Account last update timestamp
        last_login: Last successful login timestamp (admin-only)
        failed_login_attempts: Failed login counter (admin-only)
        locked_until: Account lockout expiration (admin-only)
        password_changed_at: Last password change timestamp (admin-only)
        session_count: Number of active sessions (admin-only)

    Example:
        >>> user = UserDetailResponse(
        ...     id="550e8400-e29b-41d4-a716-446655440000",
        ...     username="alice",
        ...     email="alice@example.com",
        ...     role="editor",
        ...     is_active=True,
        ...     email_verified=True,
        ...     created_at=datetime.now(),
        ...     updated_at=datetime.now(),
        ...     last_login=datetime.now(),
        ...     failed_login_attempts=0,
        ...     locked_until=None,
        ...     password_changed_at=datetime.now(),
        ...     session_count=2
        ... )
    """

    last_login: Optional[datetime] = Field(
        default=None,
        description="Last successful login timestamp",
        examples=["2025-12-02T10:30:00Z"],
    )
    failed_login_attempts: int = Field(
        default=0,
        description="Number of failed login attempts",
        examples=[0, 1, 5],
    )
    locked_until: Optional[datetime] = Field(
        default=None,
        description="Account lockout expiration timestamp",
        examples=[None, "2025-12-02T11:30:00Z"],
    )
    password_changed_at: Optional[datetime] = Field(
        default=None,
        description="Last password change timestamp",
        examples=["2025-12-02T10:30:00Z"],
    )
    session_count: int = Field(
        default=0,
        description="Number of active sessions",
        examples=[0, 1, 5],
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={datetime: lambda v: v.isoformat()},
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "username": "alice",
                "email": "alice@example.com",
                "role": "editor",
                "is_active": True,
                "email_verified": True,
                "created_at": "2025-12-02T10:30:00Z",
                "updated_at": "2025-12-02T10:30:00Z",
                "last_login": "2025-12-03T08:15:00Z",
                "failed_login_attempts": 0,
                "locked_until": None,
                "password_changed_at": "2025-12-02T10:30:00Z",
                "session_count": 2,
            }
        },
    )


class UserListResponse(BaseModel):
    """Response model for paginated user list.

    Attributes:
        users: List of users for current page
        total: Total number of users matching filters
        page: Current page number
        page_size: Number of items per page
        total_pages: Total number of pages

    Example:
        >>> response = UserListResponse(
        ...     users=[user1, user2],
        ...     total=50,
        ...     page=1,
        ...     page_size=20,
        ...     total_pages=3
        ... )
    """

    users: list[UserDetailResponse] = Field(
        ...,
        description="List of users for current page",
    )
    total: int = Field(
        ...,
        description="Total number of users matching filters",
        examples=[0, 50, 1000],
    )
    page: int = Field(
        ...,
        description="Current page number",
        examples=[1, 2, 10],
    )
    page_size: int = Field(
        ...,
        description="Number of items per page",
        examples=[10, 20, 50],
    )
    total_pages: int = Field(
        ...,
        description="Total number of pages",
        examples=[0, 1, 50],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "users": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "username": "alice",
                        "email": "alice@example.com",
                        "role": "editor",
                        "is_active": True,
                        "email_verified": True,
                        "created_at": "2025-12-02T10:30:00Z",
                        "updated_at": "2025-12-02T10:30:00Z",
                        "last_login": "2025-12-03T08:15:00Z",
                        "failed_login_attempts": 0,
                        "locked_until": None,
                        "password_changed_at": "2025-12-02T10:30:00Z",
                        "session_count": 2,
                    }
                ],
                "total": 50,
                "page": 1,
                "page_size": 20,
                "total_pages": 3,
            }
        }
    )


class AdminStatsResponse(BaseModel):
    """Response model for system statistics.

    Attributes:
        total_users: Total number of users
        active_users: Number of active users
        inactive_users: Number of inactive users
        total_sessions: Total number of sessions
        active_sessions: Number of active (non-expired, non-revoked) sessions
        users_by_role: Count of users by role

    Example:
        >>> response = AdminStatsResponse(
        ...     total_users=100,
        ...     active_users=85,
        ...     inactive_users=15,
        ...     total_sessions=150,
        ...     active_sessions=120,
        ...     users_by_role={"viewer": 60, "editor": 30, "admin": 10}
        ... )
    """

    total_users: int = Field(
        ...,
        description="Total number of users",
        examples=[0, 100, 1000],
    )
    active_users: int = Field(
        ...,
        description="Number of active users",
        examples=[0, 85, 950],
    )
    inactive_users: int = Field(
        ...,
        description="Number of inactive users",
        examples=[0, 15, 50],
    )
    total_sessions: int = Field(
        ...,
        description="Total number of sessions",
        examples=[0, 150, 2000],
    )
    active_sessions: int = Field(
        ...,
        description="Number of active (non-expired, non-revoked) sessions",
        examples=[0, 120, 1800],
    )
    users_by_role: Dict[str, int] = Field(
        ...,
        description="Count of users by role",
        examples=[{"viewer": 60, "editor": 30, "admin": 10}],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "total_users": 100,
                "active_users": 85,
                "inactive_users": 15,
                "total_sessions": 150,
                "active_sessions": 120,
                "users_by_role": {
                    "viewer": 60,
                    "editor": 30,
                    "admin": 10,
                },
            }
        }
    )
