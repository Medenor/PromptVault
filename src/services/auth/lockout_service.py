# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Account lockout enforcement for PromptVault authentication.

This module isolates the failed-login-tracking and account-lockout logic
used during login, keeping ``AuthService.login`` focused on orchestration.

Security Features:
    - Account lockout after a configurable number of failed login attempts
    - Automatic unlock once the lockout period has elapsed
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from src.config.auth_config import AuthConfig
from src.db.models.user import User
from src.db.repositories.user_repository import UserRepository
from src.services.auth.password_service import PasswordService
from src.services.exceptions import AccountLockedError, InvalidCredentialsError


class LockoutService:
    """Enforces failed-login tracking and account lockout during login.

    Attributes:
        db: Database session for transactional operations
        config: Authentication configuration settings
        password_service: Password verification service
        user_repo: User repository for database operations
    """

    def __init__(
        self,
        db: Session,
        config: AuthConfig,
        password_service: PasswordService,
        user_repo: UserRepository,
    ):
        """Initialize the lockout service.

        Args:
            db: SQLAlchemy database session
            config: Authentication configuration
            password_service: Password verification service
            user_repo: User repository for database operations
        """
        self.db = db
        self.config = config
        self.password_service = password_service
        self.user_repo = user_repo

    def enforce_account_lockout(self, user: User) -> None:
        """Reject login when the account is locked, unlocking if lock expired.

        If the account has an active lock, raises AccountLockedError. If the
        lock period has already elapsed, the account is unlocked in place.

        Args:
            user: User attempting to authenticate

        Raises:
            AccountLockedError: If the account is currently locked
        """
        if user.locked_until:
            locked_until = user.locked_until
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            if now < locked_until:
                locked_until_str = user.locked_until.strftime("%Y-%m-%d %H:%M:%S UTC")
                raise AccountLockedError(
                    f"Account locked until {locked_until_str}",
                    locked_until=locked_until_str,
                    context={"user_id": user.id, "locked_until": locked_until_str},
                )
            else:
                # Lock period expired, unlock account
                self.user_repo.unlock_account(user.id)
                self.db.commit()
                self.db.refresh(user)

    def verify_login_password(self, user: User, password: str) -> None:
        """Verify the supplied password, tracking failures and lockout.

        On a wrong password the failed-login counter is incremented and, once
        the configured threshold is reached, the account is locked.

        Args:
            user: User attempting to authenticate
            password: Plain text password to verify

        Raises:
            InvalidCredentialsError: If the password is incorrect
            AccountLockedError: If this failure triggers an account lockout
        """
        if not self.password_service.verify_password(password, user.password_hash):
            # Increment failed login attempts
            self.user_repo.increment_failed_login(user.id)

            # Check if we should lock the account
            failed_attempts = (user.failed_login_attempts or 0) + 1
            if failed_attempts >= self.config.max_login_attempts:
                locked_until = datetime.now(timezone.utc) + timedelta(
                    seconds=self.config.account_lockout_duration_seconds
                )
                self.user_repo.lock_account(user.id, locked_until)
                self.db.commit()

                locked_until_str = locked_until.strftime("%Y-%m-%d %H:%M:%S UTC")
                raise AccountLockedError(
                    f"Account locked after {failed_attempts} failed attempts",
                    locked_until=locked_until_str,
                    context={
                        "user_id": user.id,
                        "failed_attempts": failed_attempts,
                        "locked_until": locked_until_str,
                    },
                )

            self.db.commit()
            raise InvalidCredentialsError(
                "Invalid password",
                context={"user_id": user.id, "failed_attempts": failed_attempts},
            )
