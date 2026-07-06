# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""PasswordResetTokenRepository for secure password reset flow."""

from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.sql import func

from src.db.models.password_reset_token import PasswordResetToken
from src.db.repositories.base import BaseRepository


class PasswordResetTokenRepository(BaseRepository[PasswordResetToken]):
    """Repository for PasswordResetToken model.

    Provides methods for password reset token management including
    validation, expiration checking, and cleanup operations.
    """

    def __init__(self, session: Session):
        """Initialize PasswordResetTokenRepository.

        Args:
            session: Database session
        """
        super().__init__(PasswordResetToken, session)

    def create_token(
        self,
        user_id: str,
        token: str,
        expires_at: datetime,
        ip_address: Optional[str] = None,
    ) -> PasswordResetToken:
        """Create a new password reset token.

        Args:
            user_id: User's UUID
            token: Hashed reset token
            expires_at: Token expiration timestamp
            ip_address: Optional IP address that requested reset

        Returns:
            Created PasswordResetToken instance
        """
        return self.create(
            user_id=user_id, token=token, expires_at=expires_at, ip_address=ip_address
        )

    def get_by_token(self, token: str) -> Optional[PasswordResetToken]:
        """Find token by token string.

        Args:
            token: The hashed reset token to search for

        Returns:
            PasswordResetToken instance or None if not found
        """
        return (
            self.session.query(PasswordResetToken)
            .filter(PasswordResetToken.token == token)
            .first()
        )

    def get_valid_token(self, token: str) -> Optional[PasswordResetToken]:
        """Get token if valid (unused and not expired).

        Args:
            token: The hashed reset token to search for

        Returns:
            PasswordResetToken instance if valid, None otherwise
        """
        now = datetime.now(timezone.utc)
        return (
            self.session.query(PasswordResetToken)
            .filter(
                and_(
                    PasswordResetToken.token == token,
                    PasswordResetToken.is_used == False,
                    PasswordResetToken.expires_at > now,
                )
            )
            .first()
        )

    def mark_token_used(self, token_id: str) -> bool:
        """Mark token as used and set used_at timestamp.

        Args:
            token_id: The token's UUID

        Returns:
            True if token was marked as used, False if not found
        """
        token = self.get_by_id(token_id)
        if token:
            token.is_used = True
            token.used_at = datetime.now(timezone.utc)
            self.session.flush()
            return True
        return False

    def get_user_tokens(
        self, user_id: str, unused_only: bool = False
    ) -> List[PasswordResetToken]:
        """Get all tokens for a user.

        Args:
            user_id: User's UUID
            unused_only: If True, return only unused tokens

        Returns:
            List of PasswordResetToken instances
        """
        query = self.session.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user_id
        )

        if unused_only:
            query = query.filter(PasswordResetToken.is_used == False)

        return query.order_by(PasswordResetToken.created_at.desc()).all()

    def invalidate_user_tokens(self, user_id: str) -> int:
        """Mark all user's tokens as used (when password changes).

        Args:
            user_id: User's UUID

        Returns:
            Number of tokens invalidated
        """
        count = (
            self.session.query(PasswordResetToken)
            .filter(
                and_(
                    PasswordResetToken.user_id == user_id,
                    PasswordResetToken.is_used == False,
                )
            )
            .update(
                {"is_used": True, "used_at": datetime.now(timezone.utc)},
                synchronize_session=False,
            )
        )
        self.session.flush()
        return count

    def cleanup_expired_tokens(self) -> int:
        """Delete expired tokens.

        Returns:
            Number of tokens deleted
        """
        now = datetime.now(timezone.utc)
        count = (
            self.session.query(PasswordResetToken)
            .filter(PasswordResetToken.expires_at < now)
            .delete(synchronize_session=False)
        )
        self.session.flush()
        return count

    def get_expired_tokens(self, limit: int = 100) -> List[PasswordResetToken]:
        """Get expired tokens for cleanup.

        Args:
            limit: Maximum number of expired tokens to return

        Returns:
            List of expired PasswordResetToken instances
        """
        now = datetime.now(timezone.utc)
        return (
            self.session.query(PasswordResetToken)
            .filter(PasswordResetToken.expires_at < now)
            .limit(limit)
            .all()
        )

    def count_recent_tokens(self, user_id: str, minutes: int = 60) -> int:
        """Count tokens created in last N minutes (for rate limiting).

        Args:
            user_id: User's UUID
            minutes: Time window in minutes (default 60)

        Returns:
            Number of tokens created within the time window
        """
        now = datetime.now(timezone.utc)
        time_threshold = now - timedelta(minutes=minutes)

        return (
            self.session.query(PasswordResetToken)
            .filter(
                and_(
                    PasswordResetToken.user_id == user_id,
                    PasswordResetToken.created_at > time_threshold,
                )
            )
            .count()
        )
