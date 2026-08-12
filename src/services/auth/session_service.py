# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Session-cap enforcement and session management for PromptVault authentication.

This module isolates session-limit enforcement (used during login and token
refresh) and general session listing/revocation, keeping ``AuthService``
focused on orchestrating the register/login/refresh/logout flows.

Security Features:
    - Session limit enforcement per user (oldest session evicted first)
    - Authorization checks when revoking a specific session
"""

import logging

from sqlalchemy.orm import Session

from src.config.auth_config import AuthConfig
from src.db.models.user import User
from src.db.repositories.session_repository import SessionRepository
from src.services.exceptions import UnauthorizedError

logger = logging.getLogger(__name__)


class SessionService:
    """Enforces session limits and manages session listing/revocation.

    Attributes:
        db: Database session for transactional operations
        config: Authentication configuration settings
        session_repo: Session repository for token rotation tracking
    """

    def __init__(
        self, db: Session, config: AuthConfig, session_repo: SessionRepository
    ):
        """Initialize the session service.

        Args:
            db: SQLAlchemy database session
            config: Authentication configuration
            session_repo: Session repository for database operations
        """
        self.db = db
        self.config = config
        self.session_repo = session_repo

    def enforce_login_session_limit(self, user: User) -> None:
        """Free up a session slot when the user is at the session limit.

        When session limits are enforced and the user already has the maximum
        number of active sessions, the oldest session is revoked to make room
        for the new login.

        Args:
            user: User attempting to authenticate
        """
        if not self.config.unlimited_sessions:
            active_sessions = self.session_repo.count_user_sessions(
                user.id, active_only=True
            )
            if active_sessions >= self.config.max_sessions_per_user:
                # Remove oldest session to make room
                oldest_session = self.session_repo.get_oldest_user_session(user.id)
                if oldest_session:
                    self.session_repo.revoke_session(oldest_session.family_id)
                    self.db.commit()

    def enforce_refresh_session_limit(self, user: User, family_id: str) -> None:
        """Revoke oldest sessions to keep the user within the session limit.

        Preserves the session currently being refreshed (identified by
        ``family_id``) and stops once the limit is met or no further sessions
        can be revoked without affecting the current one.

        Args:
            user: The authenticated user
            family_id: Token family of the session being refreshed
        """
        if not self.config.unlimited_sessions:
            active_sessions = self.session_repo.count_user_sessions(
                user.id, active_only=True
            )
            if active_sessions > self.config.max_sessions_per_user:
                # Revoke oldest sessions to maintain limit
                while active_sessions > self.config.max_sessions_per_user:
                    oldest_session = self.session_repo.get_oldest_user_session(user.id)
                    if oldest_session and oldest_session.family_id != family_id:
                        self.session_repo.revoke_session(oldest_session.family_id)
                        logger.info(
                            f"Auto-revoked oldest session {oldest_session.family_id} "
                            f"to maintain session limit for user {user.id}"
                        )
                        active_sessions -= 1
                    else:
                        break  # Can't revoke more without affecting current session

    def get_user_sessions(
        self, user_id: str, current_family_id: str | None = None
    ) -> list[dict[str, any]]:
        """Get all active sessions for a user.

        Args:
            user_id: User's UUID
            current_family_id: Family ID of the current session (optional, to mark as current)

        Returns:
            List of session dictionaries with:
                - id: Session ID
                - family_id: Token family ID
                - user_agent: User agent string
                - ip_address: Client IP address
                - created_at: Session creation timestamp
                - last_used_at: Last token refresh timestamp
                - expires_at: Session expiration timestamp
                - is_revoked: Session revocation status
                - is_current: Whether this is the current session

        Example:
            >>> sessions = session_service.get_user_sessions("123", "family-123")
            >>> [session["user_agent"] for session in sessions]
        """
        sessions = self.session_repo.get_user_sessions(user_id, active_only=True)

        return [
            {
                "id": session.id,
                "family_id": session.family_id,
                "user_agent": session.device_info,
                "device_info": getattr(session, "device_info", None),
                "ip_address": session.ip_address,
                "created_at": session.created_at.isoformat(),
                "last_used_at": (
                    session.last_used_at.isoformat() if session.last_used_at else None
                ),
                "expires_at": session.expires_at.isoformat(),
                "is_revoked": session.is_revoked,
                "is_current": (
                    session.family_id == current_family_id
                    if current_family_id
                    else False
                ),
            }
            for session in sessions
        ]

    def revoke_session(self, session_id: str, user_id: str) -> bool:
        """Revoke a specific user session.

        Args:
            session_id: Session UUID to revoke
            user_id: User's UUID (for authorization check)

        Returns:
            True if session was revoked, False if not found

        Raises:
            UnauthorizedError: If session doesn't belong to user

        Security:
            - Verifies session belongs to requesting user
            - Prevents users from revoking other users' sessions

        Example:
            >>> session_service.revoke_session(
            ...     session_id="session-uuid",
            ...     user_id="user-uuid"
            ... )
            True
        """
        session = self.session_repo.get_by_id(session_id)

        if not session:
            return False

        # Verify session belongs to user
        if session.user_id != user_id:
            raise UnauthorizedError(
                f"Session {session_id} does not belong to user {user_id}",
                context={"session_id": session_id, "user_id": user_id},
            )

        revoked = self.session_repo.revoke_session(session.family_id)
        self.db.commit()

        return revoked

    def revoke_all_sessions(
        self, user_id: str, except_family_id: str | None = None
    ) -> int:
        """Revoke all user sessions except optionally current one.

        Args:
            user_id: User's UUID
            except_family_id: Optional family ID to keep active (current session)

        Returns:
            Number of sessions revoked

        Example:
            >>> # Revoke all sessions (force logout from all devices)
            >>> count = session_service.revoke_all_sessions("user-uuid")
            >>> count
            >>>
            >>> # Revoke all OTHER sessions (keep current session)
            >>> count = session_service.revoke_all_sessions(
            ...     "user-uuid",
            ...     except_family_id="current-family-id"
            ... )
        """
        if except_family_id:
            # Revoke all except specified family
            sessions = self.session_repo.get_user_sessions(user_id, active_only=True)
            count = 0
            for session in sessions:
                if session.family_id != except_family_id:
                    if self.session_repo.revoke_session(session.family_id):
                        count += 1
            self.db.commit()
            return count
        else:
            # Revoke all sessions
            count = self.session_repo.revoke_all_user_sessions(user_id)
            self.db.commit()
            return count
