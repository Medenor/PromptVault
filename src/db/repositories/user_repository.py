# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""UserRepository for authentication-related user operations."""

from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from sqlalchemy.sql import func

from src.db.models.user import User
from src.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User model with authentication operations.

    Provides methods for user authentication, account management,
    and security operations like lockout and verification.
    """

    def __init__(self, session: Session):
        """Initialize UserRepository.

        Args:
            session: Database session
        """
        super().__init__(User, session)

    def get_by_email(self, email: str) -> Optional[User]:
        """Find user by email address.

        Args:
            email: User's email address

        Returns:
            User instance or None if not found
        """
        return self.session.query(User).filter(User.email == email).first()

    def get_by_username(self, username: str) -> Optional[User]:
        """Find user by username.

        Args:
            username: User's username

        Returns:
            User instance or None if not found
        """
        return self.session.query(User).filter(User.username == username).first()

    def get_by_email_or_username(self, identifier: str) -> Optional[User]:
        """Find user by either email or username.

        Args:
            identifier: Email address or username

        Returns:
            User instance or None if not found
        """
        return (
            self.session.query(User)
            .filter(or_(User.email == identifier, User.username == identifier))
            .first()
        )

    def email_exists(self, email: str) -> bool:
        """Check if email already exists.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        return self.session.query(User).filter(User.email == email).first() is not None

    def username_exists(self, username: str) -> bool:
        """Check if username already exists.

        Args:
            username: Username to check

        Returns:
            True if username exists, False otherwise
        """
        return (
            self.session.query(User).filter(User.username == username).first()
            is not None
        )

    def increment_failed_login(self, user_id: str) -> None:
        """Increment failed login attempts counter.

        Args:
            user_id: User's ID
        """
        user = self.get_by_id(user_id)
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            self.session.flush()

    def reset_failed_login(self, user_id: str) -> None:
        """Reset failed login attempts counter to 0.

        Args:
            user_id: User's ID
        """
        user = self.get_by_id(user_id)
        if user:
            user.failed_login_attempts = 0
            self.session.flush()

    def lock_account(self, user_id: str, locked_until: datetime) -> None:
        """Lock account until specified time.

        Args:
            user_id: User's ID
            locked_until: Datetime when account should be unlocked
        """
        user = self.get_by_id(user_id)
        if user:
            user.locked_until = locked_until
            self.session.flush()

    def unlock_account(self, user_id: str) -> None:
        """Unlock account by clearing locked_until timestamp.

        Args:
            user_id: User's ID
        """
        user = self.get_by_id(user_id)
        if user:
            user.locked_until = None
            user.failed_login_attempts = 0
            self.session.flush()

    def update_last_login(self, user_id: str) -> None:
        """Update last_login timestamp to current time.

        Args:
            user_id: User's ID
        """
        user = self.get_by_id(user_id)
        if user:
            user.last_login = datetime.now(timezone.utc)
            self.session.flush()

    def verify_email(self, user_id: str) -> None:
        """Mark user's email as verified.

        Args:
            user_id: User's ID
        """
        user = self.get_by_id(user_id)
        if user:
            user.email_verified = True
            self.session.flush()

    def deactivate_account(self, user_id: str) -> None:
        """Deactivate user account by setting is_active to False.

        Args:
            user_id: User's ID
        """
        user = self.get_by_id(user_id)
        if user:
            user.is_active = False
            self.session.flush()

    def activate_account(self, user_id: str) -> None:
        """Activate user account by setting is_active to True.

        Args:
            user_id: User's ID
        """
        user = self.get_by_id(user_id)
        if user:
            user.is_active = True
            self.session.flush()

    def update_password_hash(self, user_id: str, password_hash: str) -> None:
        """Update user's password hash and password_changed_at timestamp.

        Args:
            user_id: User's ID
            password_hash: New password hash (should be Argon2id)
        """
        user = self.get_by_id(user_id)
        if user:
            user.password_hash = password_hash
            user.password_changed_at = datetime.now(timezone.utc)
            self.session.flush()

    def get_active_users(
        self, skip: int = 0, limit: Optional[int] = None
    ) -> List[User]:
        """Get all active users with optional pagination.

        Args:
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of active User instances
        """
        query = self.session.query(User).filter(User.is_active == True).offset(skip)

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_users_by_role(
        self, role: str, skip: int = 0, limit: Optional[int] = None
    ) -> List[User]:
        """Get users by role with optional pagination.

        Args:
            role: User role ('viewer', 'editor', 'admin')
            skip: Number of records to skip (offset)
            limit: Maximum number of records to return

        Returns:
            List of User instances with specified role
        """
        query = self.session.query(User).filter(User.role == role).offset(skip)

        if limit:
            query = query.limit(limit)

        return query.all()

    def count_by_role(self, role: str) -> int:
        """Count users by role.

        Args:
            role: User role ('viewer', 'editor', 'admin')

        Returns:
            Number of users with specified role
        """
        return self.session.query(User).filter(User.role == role).count()
