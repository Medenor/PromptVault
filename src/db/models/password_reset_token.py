# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""PasswordResetToken model for secure password reset flow.

This model tracks password reset tokens sent via email. Tokens are:
- Single-use (marked as used after password reset)
- Time-limited (default 1 hour expiration)
- Securely hashed before storage
"""

import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from src.db.base import Base


class PasswordResetToken(Base):
    """Password reset token model.

    Tracks password reset tokens for secure password recovery flow.
    Tokens are single-use and time-limited for security.

    Attributes:
        id: UUID primary key
        user_id: Foreign key to users table
        token: Secure random token (hashed)
        is_used: Token usage status (single-use)
        created_at: Token creation timestamp
        expires_at: Token expiration timestamp
        used_at: Token usage timestamp
        ip_address: IP address that requested the reset
        user: Relationship to User model
    """

    __tablename__ = "password_reset_tokens"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign key to users
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Token data
    token = Column(String(255), unique=True, nullable=False, index=True)
    is_used = Column(Boolean, default=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    used_at = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    ip_address = Column(String(45), nullable=True)

    # Relationships
    user = relationship("User", back_populates="password_reset_tokens")

    # Composite indexes
    __table_args__ = (
        Index("ix_password_reset_tokens_user_used", "user_id", "is_used"),
        Index("ix_password_reset_tokens_expires", "expires_at"),
    )

    def __repr__(self):
        return f"<PasswordResetToken(id={self.id}, user_id={self.user_id}, is_used={self.is_used})>"
