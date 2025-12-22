# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""SessionRepository for JWT refresh token session management."""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.sql import func

from src.db.models.user_session import UserSession
from src.db.repositories.base import BaseRepository


class SessionRepository(BaseRepository[UserSession]):
    """Repository for UserSession model with JWT token rotation.

    Provides methods for session management, token rotation,
    and token reuse detection through family tracking.
    """

    def __init__(self, session: Session):
        """Initialize SessionRepository.

        Args:
            session: Database session
        """
        super().__init__(UserSession, session)

    def create_session(
        self,
        user_id: str,
        family_id: str,
        refresh_token_jti: str,
        expires_at: datetime,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> UserSession:
        """Create a new user session.

        Args:
            user_id: User's UUID
            family_id: Token family UUID
            refresh_token_jti: Refresh token JTI (JWT ID)
            expires_at: Session expiration timestamp
            device_info: Optional user agent/device info
            ip_address: Optional IP address

        Returns:
            Created UserSession instance
        """
        return self.create(
            user_id=user_id,
            family_id=family_id,
            refresh_token_jti=refresh_token_jti,
            expires_at=expires_at,
            device_info=device_info,
            ip_address=ip_address
        )

    def get_by_family_id(self, family_id: str) -> Optional[UserSession]:
        """Find session by family ID.

        Args:
            family_id: Token family UUID

        Returns:
            UserSession instance or None if not found
        """
        return self.session.query(UserSession).filter(
            UserSession.family_id == family_id
        ).first()

    def get_by_jti(self, refresh_token_jti: str) -> Optional[UserSession]:
        """Find session by current JTI.

        Args:
            refresh_token_jti: Refresh token JTI (JWT ID)

        Returns:
            UserSession instance or None if not found
        """
        return self.session.query(UserSession).filter(
            UserSession.refresh_token_jti == refresh_token_jti
        ).first()

    def get_by_id(self, session_id: str) -> Optional[UserSession]:
        """Find session by session ID.

        Args:
            session_id: Session UUID

        Returns:
            UserSession instance or None if not found
        """
        return self.session.query(UserSession).filter(
            UserSession.id == session_id
        ).first()

    def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = True
    ) -> List[UserSession]:
        """Get all sessions for a user.

        Args:
            user_id: User's UUID
            active_only: If True, only return non-revoked sessions

        Returns:
            List of UserSession instances
        """
        query = self.session.query(UserSession).filter(
            UserSession.user_id == user_id
        )

        if active_only:
            query = query.filter(UserSession.is_revoked == False)

        return query.all()

    def count_user_sessions(
        self,
        user_id: str,
        active_only: bool = True
    ) -> int:
        """Count user's sessions.

        Args:
            user_id: User's UUID
            active_only: If True, only count non-revoked sessions

        Returns:
            Number of sessions
        """
        query = self.session.query(UserSession).filter(
            UserSession.user_id == user_id
        )

        if active_only:
            query = query.filter(UserSession.is_revoked == False)

        return query.count()

    def update_session_token(
        self,
        family_id: str,
        new_jti: str
    ) -> Optional[UserSession]:
        """Rotate token (update JTI and last_used_at).

        Args:
            family_id: Token family UUID
            new_jti: New refresh token JTI

        Returns:
            Updated UserSession instance or None if not found
        """
        session = self.get_by_family_id(family_id)
        if session:
            session.refresh_token_jti = new_jti
            session.last_used_at = datetime.now(timezone.utc)
            self.session.flush()
        return session

    def revoke_session(self, family_id: str) -> bool:
        """Revoke a session by family ID.

        Args:
            family_id: Token family UUID

        Returns:
            True if revoked, False if not found
        """
        session = self.get_by_family_id(family_id)
        if session:
            session.is_revoked = True
            self.session.flush()
            return True
        return False

    def revoke_session_by_id(self, session_id: str) -> bool:
        """Revoke a session by session ID.

        Args:
            session_id: Session UUID

        Returns:
            True if revoked, False if not found or already revoked
        """
        session = self.get_by_id(session_id)
        if session and not session.is_revoked:
            session.is_revoked = True
            self.session.flush()
            return True
        return False

    def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revoke all sessions for a user.

        Args:
            user_id: User's UUID

        Returns:
            Number of sessions revoked
        """
        count = self.session.query(UserSession).filter(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_revoked == False
            )
        ).update(
            {UserSession.is_revoked: True},
            synchronize_session=False
        )
        self.session.flush()
        return count

    def revoke_all_sessions(self) -> int:
        """Revoke all sessions for all users in the system.

        Returns:
            Number of sessions revoked
        """
        count = self.session.query(UserSession).filter(
            UserSession.is_revoked == False
        ).update(
            {UserSession.is_revoked: True},
            synchronize_session=False
        )
        self.session.flush()
        return count

    def revoke_token_family(self, family_id: str) -> int:
        """Revoke entire token family (for reuse detection).

        This revokes ALL sessions with the given family_id,
        which is used when token reuse is detected.

        Args:
            family_id: Token family UUID

        Returns:
            Number of sessions revoked
        """
        count = self.session.query(UserSession).filter(
            and_(
                UserSession.family_id == family_id,
                UserSession.is_revoked == False
            )
        ).update(
            {UserSession.is_revoked: True},
            synchronize_session=False
        )
        self.session.flush()
        return count

    def cleanup_expired_sessions(self) -> int:
        """Delete expired sessions (where expires_at < now).

        Returns:
            Number of sessions deleted
        """
        count = self.session.query(UserSession).filter(
            UserSession.expires_at < func.now()
        ).delete(synchronize_session=False)
        self.session.flush()
        return count

    def get_expired_sessions(self, limit: int = 100) -> List[UserSession]:
        """Get expired sessions for cleanup.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of expired UserSession instances
        """
        return self.session.query(UserSession).filter(
            UserSession.expires_at < func.now()
        ).limit(limit).all()

    def delete_expired_sessions(self) -> int:
        """Delete all expired sessions.

        Returns:
            Number of sessions deleted
        """
        count = self.session.query(UserSession).filter(
            UserSession.expires_at < func.now()
        ).delete(synchronize_session=False)
        self.session.flush()
        return count

    def get_oldest_user_session(self, user_id: str) -> Optional[UserSession]:
        """Get oldest active session for a user.

        Args:
            user_id: User's UUID

        Returns:
            Oldest active UserSession instance or None
        """
        return self.session.query(UserSession).filter(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_revoked == False
            )
        ).order_by(UserSession.created_at.asc()).first()
