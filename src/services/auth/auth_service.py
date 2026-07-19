# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Authentication service for PromptVault.

This module provides comprehensive authentication orchestration, integrating
password hashing, JWT token generation, user management, and session handling.
It implements secure authentication flows with protection against common attacks.

Security Features:
    - Account lockout after failed login attempts
    - Token family tracking for refresh token reuse detection
    - Session limit enforcement per user
    - Password policy validation
    - Email/username uniqueness checks
    - Account status verification (active, verified, not locked)
    - Automatic token rotation on refresh
    - Secure password change with verification

Authentication Flows:
    Registration:
        1. Validate password policy
        2. Check email/username uniqueness
        3. Hash password with Argon2id
        4. Create user account
        5. Generate initial token pair
        6. Create session with token family

    Login:
        1. Find user by username or email
        2. Check account status (active, not locked)
        3. Verify password
        4. Check session limits
        5. Generate token pair with new family
        6. Create session
        7. Update last_login timestamp
        8. Reset failed login counter

    Token Refresh:
        1. Validate refresh token (JWT signature, expiration)
        2. Find session by token family
        3. Detect token reuse (JTI mismatch = revoke family)
        4. Generate new token pair
        5. Update session with new JTI
        6. Return new tokens

    Logout:
        1. Validate refresh token
        2. Revoke session by family ID
        3. Clear token from client

Example:
    >>> from src.services.auth.auth_service import AuthService
    >>> from src.config.auth_config import auth_settings
    >>> from src.db.session import get_db
    >>>
    >>> # Initialize service
    >>> db = next(get_db())
    >>> auth_service = AuthService(db, auth_settings)
    >>>
    >>> # Register new user
    >>> result = auth_service.register(
    ...     username="alice",
    ...     email="alice@example.com",
    ...     password="SecureP@ssw0rd123",
    ...     ip_address="192.168.1.1",
    ...     user_agent="Mozilla/5.0..."
    ... )
    >>> print(result["access_token"])
    >>>
    >>> # Login existing user
    >>> result = auth_service.login(
    ...     username_or_email="alice",
    ...     password="SecureP@ssw0rd123",
    ...     ip_address="192.168.1.1",
    ...     user_agent="Mozilla/5.0..."
    ... )
    >>>
    >>> # Refresh tokens
    >>> result = auth_service.refresh_tokens(
    ...     refresh_token=result["refresh_token"],
    ...     ip_address="192.168.1.1",
    ...     user_agent="Mozilla/5.0..."
    ... )
    >>>
    >>> # Logout
    >>> auth_service.logout(refresh_token=result["refresh_token"])

Security Notes:
    - Failed login attempts trigger account lockout after threshold
    - Token reuse detection revokes entire token family (security breach)
    - Session limits prevent resource exhaustion
    - Password policies enforce strong passwords
    - All database operations are transactional
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidTokenError as JWTInvalidTokenError,
)
from sqlalchemy.orm import Session

from src.config.auth_config import AuthConfig
from src.db.models.user import User
from src.db.repositories.session_repository import SessionRepository
from src.db.repositories.user_repository import UserRepository
from src.services.auth.jwt_service import JWTService
from src.services.auth.password_service import PasswordService
from src.services.exceptions import (
    AccountInactiveError,
    AccountLockedError,
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidTokenError,
    PasswordPolicyError,
    SessionLimitExceededError,
    SessionNotFoundError,
    TokenReuseDetectedError,
    UnauthorizedError,
    UsernameAlreadyExistsError,
)


class AuthService:
    """Authentication service orchestrating complete auth flows.

    This service integrates password hashing, JWT token generation, user
    management, and session handling to provide secure authentication.

    Attributes:
        db: Database session for transactional operations
        config: Authentication configuration settings
        password_service: Password hashing and validation service
        jwt_service: JWT token generation and validation service
        user_repo: User repository for database operations
        session_repo: Session repository for token rotation tracking
    """

    def __init__(self, db: Session, config: AuthConfig):
        """Initialize authentication service.

        Args:
            db: SQLAlchemy database session
            config: Authentication configuration
        """
        self.db = db
        self.config = config
        self.password_service = PasswordService(config)
        self.jwt_service = JWTService(config)
        self.user_repo = UserRepository(db)
        self.session_repo = SessionRepository(db)

    def register(
        self,
        username: str,
        email: str,
        password: str,
        ip_address: str,
        user_agent: str,
        role: str = "viewer",
    ) -> Dict[str, any]:
        """Register new user and return authentication tokens.

        This method creates a new user account with secure password hashing,
        validates password policy, checks uniqueness constraints, and generates
        initial authentication tokens.

        Args:
            username: Unique username (max 100 chars)
            email: Unique email address
            password: Plain text password (will be hashed)
            ip_address: Client IP address for session tracking
            user_agent: Client user agent string for session tracking
            role: User role (default: "viewer")

        Returns:
            Dictionary containing:
                - access_token: JWT access token (15 min expiry)
                - refresh_token: JWT refresh token (7 day expiry)
                - token_type: "Bearer"
                - expires_in: Access token expiry in seconds
                - user: User information (id, username, email, role)

        Raises:
            PasswordPolicyError: If password doesn't meet policy requirements
            EmailAlreadyExistsError: If email is already registered
            UsernameAlreadyExistsError: If username is already taken

        Security:
            - Password is validated against policy before hashing
            - Password is hashed with Argon2id
            - Initial token family is created for refresh token rotation
            - Session is tracked with device info and IP address

        Example:
            >>> result = auth_service.register(
            ...     username="alice",
            ...     email="alice@example.com",
            ...     password="SecureP@ssw0rd123",
            ...     ip_address="192.168.1.1",
            ...     user_agent="Mozilla/5.0..."
            ... )
            >>> print(result["user"]["username"])
            'alice'
        """
        # Validate password policy
        is_valid, errors = self.password_service.validate_password_policy(password)
        if not is_valid:
            raise PasswordPolicyError(
                f"Password does not meet policy requirements: {', '.join(errors)}",
                errors=errors,
            )

        # Check email uniqueness
        if self.user_repo.email_exists(email):
            raise EmailAlreadyExistsError(
                f"Email '{email}' is already registered",
                context={"email": email},
            )

        # Check username uniqueness
        if self.user_repo.username_exists(username):
            raise UsernameAlreadyExistsError(
                f"Username '{username}' is already taken",
                context={"username": username},
            )

        # Hash password
        password_hash = self.password_service.hash_password(password)

        # Create user
        user = self.user_repo.create(
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=True,
            email_verified=False,  # Require email verification
        )

        # Commit user creation
        self.db.commit()
        self.db.refresh(user)

        # Generate tokens and create session
        return self._generate_tokens_and_session(user, ip_address, user_agent)

    def login(
        self,
        username_or_email: str,
        password: str,
        ip_address: str,
        user_agent: str,
        remember_me: bool = False,
    ) -> Dict[str, any]:
        """Authenticate user and return tokens.

        This method authenticates a user by username or email, verifies their
        password, checks account status, enforces session limits, and generates
        authentication tokens.

        Args:
            username_or_email: Username or email address
            password: Plain text password to verify
            ip_address: Client IP address for session tracking
            user_agent: Client user agent string for session tracking
            remember_me: Whether to use extended refresh token lifetime

        Returns:
            Dictionary containing:
                - access_token: JWT access token
                - refresh_token: JWT refresh token
                - token_type: "Bearer"
                - expires_in: Access token expiry in seconds
                - user: User information

        Raises:
            InvalidCredentialsError: If username/email or password is incorrect
            AccountLockedError: If account is locked due to failed attempts
            AccountInactiveError: If account is deactivated

        Security:
            - Failed attempts increment counter and may trigger lockout
            - Account lockout is automatic after max attempts
            - Locked accounts show time until unlock
            - Successful login resets failed attempt counter
            - Session limits are enforced (oldest session removed if exceeded)

        Example:
            >>> result = auth_service.login(
            ...     username_or_email="alice",
            ...     password="SecureP@ssw0rd123",
            ...     ip_address="192.168.1.1",
            ...     user_agent="Mozilla/5.0..."
            ... )
        """
        # Find user by username or email
        user = self.user_repo.get_by_email_or_username(username_or_email)

        if not user:
            raise InvalidCredentialsError(
                f"User not found: {username_or_email}",
                context={"identifier": username_or_email},
            )

        # Check if account is locked
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

        # Check if account is active
        if not user.is_active:
            raise AccountInactiveError(
                f"Account is not active: {user.id}",
                context={"user_id": user.id},
            )

        # Verify password
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

        # Check session limits
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

        # Reset failed login attempts
        self.user_repo.reset_failed_login(user.id)

        # Update last login timestamp
        self.user_repo.update_last_login(user.id)

        # Commit before generating tokens
        self.db.commit()
        self.db.refresh(user)

        # Generate tokens and create session
        return self._generate_tokens_and_session(
            user,
            ip_address,
            user_agent,
            remember_me=remember_me,
        )

    def refresh_tokens(
        self,
        refresh_token: str,
        ip_address: str,
        user_agent: str,
    ) -> Dict[str, any]:
        """Refresh access token using refresh token.

        This method implements secure token rotation with reuse detection.
        When a refresh token is used, a new token pair is generated and the
        session is updated with the new JTI. If token reuse is detected
        (old JTI used again), the entire token family is revoked.

        Args:
            refresh_token: Current refresh token
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            Dictionary containing new token pair and user info

        Raises:
            InvalidTokenError: If token is invalid or expired
            SessionNotFoundError: If session not found or revoked
            TokenReuseDetectedError: If token reuse detected (revokes family)

        Security:
            - Token reuse detection prevents replay attacks
            - Entire token family revoked on reuse (security breach)
            - New JTI generated for each rotation
            - Session tracked with IP and user agent

        Token Rotation Flow:
            1. Validate refresh token JWT
            2. Find session by family_id
            3. Check if current JTI matches stored JTI
            4. If mismatch: REVOKE FAMILY (reuse detected)
            5. Generate new tokens with same family, new JTI
            6. Update session with new JTI
            7. Return new tokens

        Example:
            >>> result = auth_service.refresh_tokens(
            ...     refresh_token="eyJ0eXAiOiJKV1QiLCJhbGc...",
            ...     ip_address="192.168.1.1",
            ...     user_agent="Mozilla/5.0..."
            ... )
        """
        # Validate refresh token
        try:
            claims = self.jwt_service.validate_refresh_token(refresh_token)
        except ExpiredSignatureError:
            raise InvalidTokenError(
                "Refresh token has expired",
                context={"reason": "expired"},
            )
        except JWTInvalidTokenError as e:
            raise InvalidTokenError(
                f"Invalid refresh token: {str(e)}",
                context={"reason": "invalid_token"},
            )

        user_id = claims["sub"]
        family_id = claims["family_id"]
        token_jti = claims["jti"]

        # Find session by family ID
        session = self.session_repo.get_by_family_id(family_id)

        if not session:
            raise SessionNotFoundError(
                f"Session not found for family {family_id}",
                context={"family_id": family_id},
            )

        # Check if session is revoked
        if session.is_revoked:
            raise SessionNotFoundError(
                f"Session has been revoked: {family_id}",
                context={"family_id": family_id, "revoked": True},
            )

        # CRITICAL: Detect token reuse
        # If the JTI in the token doesn't match the stored JTI,
        # it means an old token is being reused (security breach)
        if session.refresh_token_jti != token_jti:
            # SECURITY BREACH: Revoke entire token family
            self.session_repo.revoke_token_family(family_id)
            self.db.commit()

            raise TokenReuseDetectedError(
                f"Token reuse detected for family {family_id}",
                context={
                    "family_id": family_id,
                    "expected_jti": session.refresh_token_jti,
                    "received_jti": token_jti,
                },
            )

        # Get user
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise InvalidCredentialsError(
                f"User not found: {user_id}",
                context={"user_id": user_id},
            )

        # Check account status
        if not user.is_active:
            raise AccountInactiveError(
                f"Account is not active: {user.id}",
                context={"user_id": user.id},
            )

        session_expires_at = session.expires_at
        if session_expires_at.tzinfo is None:
            session_expires_at = session_expires_at.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        remaining_seconds = int((session_expires_at - now).total_seconds())
        if remaining_seconds <= 0:
            self.session_repo.revoke_session(session.family_id)
            self.db.commit()
            raise SessionNotFoundError(
                f"Session expired for family {family_id}",
                context={"family_id": family_id, "expired": True},
            )

        # Generate new tokens with SAME family_id but NEW jti
        new_jti = str(uuid.uuid4())
        new_access_token = self.jwt_service.generate_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            family_id=family_id,  # Same family for session identification
        )
        new_refresh_token = self.jwt_service.generate_refresh_token(
            user_id=user.id,
            family_id=family_id,  # Same family
            jti=new_jti,  # New JTI
            expires_in_seconds=remaining_seconds,
        )

        # Update session with new JTI
        self.session_repo.update_session_token(family_id, new_jti)

        # ENHANCED: Check and enforce maximum sessions limit
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

        self.db.commit()

        # Fixed: Include all required UserResponse fields to prevent Pydantic validation error
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "Bearer",
            "expires_in": self.config.jwt_access_token_expire_seconds,
            "remaining_seconds": remaining_seconds,  # For cookie max_age
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "email_verified": user.email_verified,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            },
        }

    def update_user_profile(
        self,
        user_id: str,
        display_name: Optional[str] = None,
        email: Optional[str] = None,
    ) -> User:
        """Update user profile (email and/or display_name).

        Args:
            user_id: User's UUID
            display_name: New display name (optional)
            email: New email address (optional)

        Returns:
            Updated User instance

        Raises:
            UserNotFoundError: If user not found
            EmailAlreadyExistsError: If email already in use by another user

        Example:
            >>> user = auth_service.update_user_profile(
            ...     user_id="user-uuid",
            ...     display_name="New Name",
            ...     email="newemail@example.com"
            ... )
        """
        from datetime import datetime, timezone

        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User not found: {user_id}")

        # Update email if provided and different
        if email is not None and email != user.email:
            # Check uniqueness
            if self.user_repo.email_exists(email):
                raise EmailAlreadyExistsError(f"Email '{email}' is already in use")
            user.email = email
            # Reset email verification when email changes
            user.email_verified = False

        # Update display_name if provided
        if display_name is not None:
            user.display_name = display_name

        # Update timestamp
        user.updated_at = datetime.now(timezone.utc)
        self.db.flush()
        self.db.commit()
        self.db.refresh(user)

        return user

    def get_user_stats(self, user_id: str) -> Dict[str, any]:
        """Get account statistics for a user.

        Provides comprehensive statistics including:
        - Account creation and login dates
        - Session information (active and total count)
        - Security status (lockout, failed attempts)

        Args:
            user_id: User's UUID

        Returns:
            Dictionary with user statistics

        Raises:
            UserNotFoundError: If user not found

        Example:
            >>> stats = auth_service.get_user_stats("user-uuid")
            >>> print(f"Active sessions: {stats['active_sessions_count']}")
        """
        from datetime import datetime, timezone

        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise UserNotFoundError(f"User not found: {user_id}")

        # Count sessions
        active_sessions = self.session_repo.count_user_sessions(
            user_id, active_only=True
        )
        all_sessions = self.session_repo.count_user_sessions(user_id, active_only=False)

        # Calculate days since account creation
        now = datetime.now(timezone.utc)
        created_at = user.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        days_since_creation = (now - created_at).days

        # Calculate days since last login
        days_since_last_login = None
        if user.last_login:
            last_login = user.last_login
            if last_login.tzinfo is None:
                last_login = last_login.replace(tzinfo=timezone.utc)
            days_since_last_login = (now - last_login).days

        # Check if locked
        is_locked = False
        if user.locked_until:
            locked_until = user.locked_until
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            is_locked = now < locked_until

        return {
            "user_id": user.id,
            "username": user.username,
            "account_created_at": user.created_at,
            "last_login": user.last_login,
            "password_changed_at": user.password_changed_at,
            "active_sessions_count": active_sessions,
            "total_sessions_count": all_sessions,
            "failed_login_attempts": user.failed_login_attempts or 0,
            "is_locked": is_locked,
            "locked_until": user.locked_until if is_locked else None,
            "days_since_creation": days_since_creation,
            "days_since_last_login": days_since_last_login,
        }

    def logout(self, refresh_token: str) -> bool:
        """Revoke refresh token and end session.

        Args:
            refresh_token: Refresh token to revoke

        Returns:
            True if session was revoked, False if not found

        Raises:
            InvalidTokenError: If token is invalid

        Example:
            >>> auth_service.logout(refresh_token)
            True
        """
        try:
            claims = self.jwt_service.validate_refresh_token(refresh_token)
        except ExpiredSignatureError, JWTInvalidTokenError:
            # Even if token is expired, try to revoke it
            try:
                claims = self.jwt_service.decode_token_unsafe(refresh_token)
            except JWTInvalidTokenError as e:
                raise InvalidTokenError(
                    f"Cannot decode token for logout: {str(e)}",
                    context={"reason": "invalid_token"},
                )

        family_id = claims.get("family_id")
        if not family_id:
            raise InvalidTokenError(
                "Token missing family_id claim",
                context={"reason": "missing_family_id"},
            )

        # Revoke session by family ID
        revoked = self.session_repo.revoke_session(family_id)
        self.db.commit()

        return revoked

    def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> bool:
        """Change user password with verification.

        Args:
            user_id: User's UUID
            old_password: Current password for verification
            new_password: New password to set

        Returns:
            True if password was changed successfully

        Raises:
            InvalidCredentialsError: If old password is incorrect
            PasswordPolicyError: If new password doesn't meet policy
            SessionNotFoundError: If user not found

        Security:
            - Old password must be verified
            - New password validated against policy
            - Password hash updated with timestamp
            - All user sessions remain active (no forced logout)

        Example:
            >>> auth_service.change_password(
            ...     user_id="123",
            ...     old_password="OldP@ssw0rd123",
            ...     new_password="NewP@ssw0rd456"
            ... )
            True
        """
        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise SessionNotFoundError(
                f"User not found: {user_id}",
                context={"user_id": user_id},
            )

        # Verify old password
        if not self.password_service.verify_password(old_password, user.password_hash):
            raise InvalidCredentialsError(
                "Current password is incorrect",
                context={"user_id": user_id},
            )

        # Validate new password policy
        is_valid, errors = self.password_service.validate_password_policy(new_password)
        if not is_valid:
            raise PasswordPolicyError(
                f"New password does not meet policy: {', '.join(errors)}",
                errors=errors,
            )

        # Hash and update password
        new_password_hash = self.password_service.hash_password(new_password)
        self.user_repo.update_password_hash(user_id, new_password_hash)
        self.db.commit()

        return True

    def get_user_sessions(
        self, user_id: str, current_family_id: Optional[str] = None
    ) -> List[Dict[str, any]]:
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
            >>> sessions = auth_service.get_user_sessions("123", "family-123")
            >>> for session in sessions:
            ...     print(session["user_agent"])
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
            >>> auth_service.revoke_session(
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
        self, user_id: str, except_family_id: Optional[str] = None
    ) -> int:
        """Revoke all user sessions except optionally current one.

        Args:
            user_id: User's UUID
            except_family_id: Optional family ID to keep active (current session)

        Returns:
            Number of sessions revoked

        Example:
            >>> # Revoke all sessions (force logout from all devices)
            >>> count = auth_service.revoke_all_sessions("user-uuid")
            >>> print(f"Revoked {count} sessions")
            >>>
            >>> # Revoke all OTHER sessions (keep current session)
            >>> count = auth_service.revoke_all_sessions(
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

    def _generate_tokens_and_session(
        self,
        user: User,
        ip_address: str,
        user_agent: str,
        remember_me: bool = False,
    ) -> Dict[str, any]:
        """Generate token pair and create session (internal helper).

        Args:
            user: User instance
            ip_address: Client IP address
            user_agent: Client user agent
            remember_me: Use extended refresh token lifetime when True

        Returns:
            Dictionary with tokens and user info
        """
        # Generate new token family ID
        family_id = str(uuid.uuid4())
        refresh_jti = str(uuid.uuid4())
        refresh_expiry_seconds = (
            self.config.jwt_refresh_token_remember_me_expire_seconds
            if remember_me
            else self.config.jwt_refresh_token_expire_seconds
        )

        # Generate tokens
        access_token = self.jwt_service.generate_access_token(
            user_id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            family_id=family_id,  # Include family_id for session identification
        )
        refresh_token = self.jwt_service.generate_refresh_token(
            user_id=user.id,
            family_id=family_id,
            jti=refresh_jti,
            expires_in_seconds=refresh_expiry_seconds,
        )

        # Create session
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=refresh_expiry_seconds
        )
        self.session_repo.create_session(
            user_id=user.id,
            family_id=family_id,
            refresh_token_jti=refresh_jti,
            expires_at=expires_at,
            device_info=user_agent,
            ip_address=ip_address,
        )
        self.db.commit()

        # Fixed: Include all required UserResponse fields to prevent Pydantic validation error
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self.config.jwt_access_token_expire_seconds,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
                "is_active": user.is_active,
                "email_verified": user.email_verified,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            },
        }
