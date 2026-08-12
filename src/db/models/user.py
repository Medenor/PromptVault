# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""User model for PromptVault.

This model represents user accounts in the system with full authentication
and authorization support, including JWT-based authentication and RBAC.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.db.base import Base

if TYPE_CHECKING:
    from src.db.models.password_reset_token import PasswordResetToken
    from src.db.models.prompt import Prompt
    from src.db.models.prompt_share import PromptShare
    from src.db.models.user_session import UserSession


class User(Base):
    """User account model with authentication support.

    Attributes:
        id: UUID primary key (PostgreSQL UUID, String(36) for SQLite)
        username: Unique username (max 100 chars)
        display_name: Optional display name (max 200 chars)
        email: Unique email address (max 255 chars, required)
        password_hash: Argon2id password hash (max 255 chars)
        role: User role - 'viewer', 'editor', or 'admin' (default 'viewer')
        email_verified: Email verification status
        is_active: Account active status (for suspension/soft delete)
        last_login: Timestamp of last successful login
        failed_login_attempts: Counter for failed login attempts
        locked_until: Account lockout expiration timestamp
        password_changed_at: Timestamp of last password change
        created_at: Timestamp when user was created
        updated_at: Timestamp when user was last updated
        prompts: Relationship to user's prompts
    """

    __tablename__ = "users"

    # Use UUID for PostgreSQL, String for SQLite compatibility
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    display_name: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(50), default="viewer")

    # Authentication and security fields
    email_verified: Mapped[bool | None] = mapped_column(default=False)
    is_active: Mapped[bool | None] = mapped_column(default=True)
    last_login: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_login_attempts: Mapped[int | None] = mapped_column(default=0)
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Timestamps
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    prompts: Mapped[list["Prompt"]] = relationship("Prompt", back_populates="user")
    sessions: Mapped[list["UserSession"]] = relationship(
        "UserSession", back_populates="user", cascade="all, delete-orphan"
    )
    password_reset_tokens: Mapped[list["PasswordResetToken"]] = relationship(
        "PasswordResetToken", back_populates="user", cascade="all, delete-orphan"
    )
    received_shares: Mapped[list["PromptShare"]] = relationship(
        "PromptShare",
        foreign_keys="PromptShare.grantee_user_id",
        back_populates="grantee",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"
