# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""UserSession model for JWT refresh token tracking.

This model implements token family tracking for JWT refresh token rotation.
Each refresh token belongs to a family, and token reuse detection revokes
the entire family to prevent token theft.
"""

from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from src.db.base import Base


class UserSession(Base):
    """User session model for refresh token tracking.

    Implements JWT refresh token rotation with family tracking.
    Token reuse detection revokes the entire token family.

    Attributes:
        id: UUID primary key
        user_id: Foreign key to users table
        family_id: Token family identifier (unique per session chain)
        refresh_token_jti: Current refresh token JTI (JWT ID)
        device_info: User agent / device information
        ip_address: IPv4 or IPv6 address
        is_revoked: Session revocation status
        created_at: Session creation timestamp
        last_used_at: Last token refresh timestamp
        expires_at: Session expiration timestamp
        user: Relationship to User model
    """

    __tablename__ = "user_sessions"

    # Primary key
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # Foreign key to users
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Token family tracking
    family_id = Column(String(36), unique=True, nullable=False, index=True)
    refresh_token_jti = Column(String(36), unique=True, nullable=False, index=True)

    # Session metadata
    device_info = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)

    # Session status
    is_revoked = Column(Boolean, default=False, index=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="sessions")

    # Composite indexes for efficient queries
    __table_args__ = (
        Index("ix_user_sessions_user_active", "user_id", "is_revoked"),
        Index("ix_user_sessions_expires", "expires_at"),
    )

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, family_id={self.family_id}, is_revoked={self.is_revoked})>"
