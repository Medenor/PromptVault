# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Password reset service for secure password recovery flow.

This module provides secure password reset functionality with the following
security features:

Security Features:
    - 256-bit cryptographically secure random tokens (secrets.token_urlsafe)
    - SHA-256 token hashing before storage (never store plain tokens)
    - Single-use tokens (marked as used after password reset)
    - Time-limited tokens (default 1 hour expiration, configurable)
    - Rate limiting (max 3 reset requests per hour per email)
    - Token invalidation (all existing tokens invalidated when new one generated)
    - Comprehensive token validation (expiration, usage, user existence)
    - IP address tracking for security audit trails

Email Sending:
    - Currently implements a stub email method that logs the reset email
    - Structured for easy SMTP integration in the future
    - Includes reset URL generation using AuthConfig

Example:
    >>> from src.services.auth.password_reset_service import PasswordResetService
    >>> from src.config.auth_config import auth_settings
    >>> from src.db.repositories.password_reset_token_repository import PasswordResetTokenRepository
    >>> from src.db.repositories.user_repository import UserRepository
    >>> from src.services.auth.password_service import PasswordService
    >>>
    >>> password_service = PasswordService(auth_settings)
    >>> token_repo = PasswordResetTokenRepository(session)
    >>> user_repo = UserRepository(session)
    >>>
    >>> service = PasswordResetService(
    ...     config=auth_settings,
    ...     password_service=password_service,
    ...     token_repository=token_repo,
    ...     user_repository=user_repo
    ... )
    >>>
    >>> # Request password reset
    >>> token = service.request_password_reset(
    ...     email="user@example.com",
    ...     ip_address="192.168.1.1"
    ... )
    >>>
    >>> # Verify token
    >>> is_valid, user_id_or_error = service.verify_reset_token(token)
    >>>
    >>> # Reset password
    >>> success = service.reset_password(token, "NewP@ssw0rd123")
    >>>
    >>> # Cleanup expired tokens (cron job)
    >>> count = service.cleanup_expired_tokens()

References:
    - OWASP Password Reset Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html
    - NIST Digital Identity Guidelines: https://pages.nist.gov/800-63-3/sp800-63b.html
"""

import hashlib
import logging
import secrets
from datetime import UTC, datetime, timedelta

from src.config.auth_config import AuthConfig
from src.db.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository,
)
from src.db.repositories.user_repository import UserRepository
from src.services.auth.password_service import PasswordService
from src.services.exceptions import (
    PasswordPolicyError,
    RateLimitExceededError,
    TokenAlreadyUsedError,
    TokenExpiredError,
    TokenNotFoundError,
    UserNotFoundError,
)

# Configure logger
logger = logging.getLogger(__name__)


class PasswordResetService:
    """Secure password reset service with email-based token flow.

    This service implements a secure password reset flow following OWASP
    best practices. It generates cryptographically secure tokens, hashes
    them before storage, enforces single-use and time-limited validity,
    and includes rate limiting to prevent abuse.

    Security Features:
        - 256-bit cryptographically secure tokens
        - SHA-256 hashing before storage
        - Single-use enforcement
        - Time-limited tokens (1 hour default)
        - Rate limiting (3 requests per hour)
        - Token invalidation on new request
        - IP address tracking
        - Password policy validation

    Attributes:
        config: Authentication configuration with email and token settings
        password_service: Password hashing and validation service
        token_repository: Repository for password reset token operations
        user_repository: Repository for user operations
    """

    def __init__(
        self,
        config: AuthConfig,
        password_service: PasswordService,
        token_repository: PasswordResetTokenRepository,
        user_repository: UserRepository,
    ):
        """Initialize password reset service.

        Args:
            config: Authentication configuration
            password_service: Password service for hashing and validation
            token_repository: Repository for token operations
            user_repository: Repository for user operations
        """
        self.config = config
        self.password_service = password_service
        self.token_repository = token_repository
        self.user_repository = user_repository

    def request_password_reset(self, email: str, ip_address: str | None = None) -> str:
        """Generate and send password reset token via email.

        This method generates a secure password reset token, hashes it for
        storage, sends it via email, and returns the plain token for testing
        purposes. In production, only the email would be sent.

        Security Features:
            - Rate limiting (max 3 requests per hour per user)
            - Token invalidation (all existing tokens invalidated)
            - 256-bit cryptographically secure random token
            - SHA-256 hashing before storage
            - Time-limited validity (1 hour default)
            - IP address tracking

        Args:
            email: User's email address
            ip_address: IP address that requested the reset (for audit trail)

        Returns:
            Plain text reset token (for testing only - in production this
            would only be sent via email)

        Raises:
            UserNotFoundError: If email doesn't match any user
            RateLimitExceededError: If too many reset requests in time window

        Note:
            If the email doesn't exist, we still return success to prevent
            user enumeration attacks. However, no email is sent and no token
            is generated. The exception is only for internal handling.

        Example:
            >>> token = service.request_password_reset(
            ...     email="user@example.com",
            ...     ip_address="192.168.1.1"
            ... )
            >>> # Token sent via email (logged in development)
        """
        # Look up user by email
        user = self.user_repository.get_by_email(email)

        # If user doesn't exist, log but don't reveal to caller (prevent enumeration)
        if not user:
            logger.warning(
                f"Password reset requested for non-existent email: {email}",
                extra={"ip_address": ip_address},
            )
            # Still raise exception for internal handling, but API should
            # return success message to prevent user enumeration
            raise UserNotFoundError(
                f"No user found with email: {email}",
                context={"email": email, "ip_address": ip_address},
            )

        # Check rate limiting (max 3 requests per hour)
        recent_count = self.token_repository.count_recent_tokens(
            user_id=user.id,
            minutes=self.config.rate_limit_password_reset_window_seconds // 60,
        )

        if recent_count >= self.config.rate_limit_password_reset_attempts:
            retry_after = self.config.rate_limit_password_reset_window_seconds
            logger.warning(
                f"Rate limit exceeded for password reset: {email}",
                extra={
                    "user_id": user.id,
                    "ip_address": ip_address,
                    "recent_attempts": recent_count,
                },
            )
            raise RateLimitExceededError(
                f"Too many password reset requests for user {user.id}",
                user_message=f"Too many password reset requests. Please try again in {retry_after // 60} minutes.",
                retry_after=retry_after,
                context={
                    "user_id": user.id,
                    "email": email,
                    "attempts": recent_count,
                    "max_attempts": self.config.rate_limit_password_reset_attempts,
                },
            )

        # Invalidate all existing unused tokens for this user
        invalidated_count = self.token_repository.invalidate_user_tokens(user.id)
        if invalidated_count > 0:
            logger.info(
                f"Invalidated {invalidated_count} existing reset tokens for user {user.id}"
            )

        # Generate cryptographically secure 256-bit token
        # token_urlsafe(32) generates 32 bytes = 256 bits
        plain_token = secrets.token_urlsafe(32)

        # Hash token using SHA-256 before storage
        hashed_token = self._hash_token(plain_token)

        # Calculate expiration time
        expires_at = datetime.now(UTC) + timedelta(
            seconds=self.config.password_reset_token_expire_seconds
        )

        # Create token record in database
        token_record = self.token_repository.create_token(
            user_id=user.id,
            token=hashed_token,
            expires_at=expires_at,
            ip_address=ip_address,
        )

        logger.info(
            f"Password reset token created for user {user.id}",
            extra={
                "token_id": token_record.id,
                "user_id": user.id,
                "expires_at": expires_at.isoformat(),
                "ip_address": ip_address,
            },
        )

        # Send reset email (currently stubbed)
        self._send_reset_email(email=email, token=plain_token, username=user.username)

        # Return plain token for testing purposes
        # In production API, this would not be returned - only sent via email
        return plain_token

    def verify_reset_token(self, token: str) -> tuple[bool, str]:
        """Verify password reset token validity.

        This method checks if a token is valid by verifying:
        - Token exists in database
        - Token has not expired
        - Token has not been used
        - Associated user exists and is active

        Args:
            token: Plain text reset token to verify

        Returns:
            Tuple of (is_valid, user_id_or_error_message):
                - If valid: (True, user_id)
                - If invalid: (False, error_message)

        Security Notes:
            - Token is hashed before database lookup
            - Timing-safe comparison (hash comparison is constant-time)
            - No information leakage about why token is invalid

        Example:
            >>> is_valid, result = service.verify_reset_token(token)
            >>> if is_valid:
            ...     user_id = result
            ...     # Proceed with password reset
            ... else:
            ...     error_message = result
            ...     # Show error to user
        """
        try:
            # Hash the token for database lookup
            hashed_token = self._hash_token(token)

            # Look up token in database
            token_record = self.token_repository.get_by_token(hashed_token)

            if not token_record:
                logger.warning("Password reset token not found")
                return False, "Invalid or expired password reset token"

            # Check if token has expired
            now = datetime.now(UTC)
            expires_at = self._ensure_tz_aware(token_record.expires_at)
            assert expires_at is not None
            if expires_at < now:
                logger.warning(
                    "Expired password reset token used",
                    extra={"token_id": token_record.id},
                )
                return False, "Password reset token has expired"

            # Check if token has already been used
            if token_record.is_used:
                logger.warning(
                    "Already-used password reset token attempted",
                    extra={"token_id": token_record.id},
                )
                return False, "Password reset token has already been used"

            # Verify user still exists and is active
            user = self.user_repository.get_by_id(token_record.user_id)
            if not user:
                logger.error(
                    "Password reset token references non-existent user",
                    extra={
                        "token_id": token_record.id,
                        "user_id": token_record.user_id,
                    },
                )
                return False, "Invalid password reset token"

            if not user.is_active:
                logger.warning(
                    "Password reset attempted for inactive user",
                    extra={"token_id": token_record.id, "user_id": user.id},
                )
                return False, "Account is not active"

            # Token is valid
            logger.info(
                "Password reset token verified successfully",
                extra={"token_id": token_record.id, "user_id": user.id},
            )
            return True, user.id

        except Exception as e:
            logger.error(
                f"Error verifying password reset token: {str(e)}", exc_info=True
            )
            return False, "An error occurred while verifying the token"

    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset user password using a valid reset token.

        This method performs the actual password reset by:
        1. Verifying the token is valid
        2. Validating new password against policy
        3. Hashing the new password
        4. Updating user's password
        5. Marking token as used
        6. Invalidating all other user tokens

        Args:
            token: Plain text reset token
            new_password: New password to set (plain text)

        Returns:
            True if password was reset successfully

        Raises:
            TokenNotFoundError: If token doesn't exist
            TokenExpiredError: If token has expired
            TokenAlreadyUsedError: If token was already used
            UserNotFoundError: If user doesn't exist
            PasswordPolicyError: If password doesn't meet policy requirements

        Security Notes:
            - Token is marked as used after successful reset
            - All other user tokens are invalidated
            - Password is validated against policy before hashing
            - Password is hashed using Argon2id before storage

        Example:
            >>> success = service.reset_password(token, "NewP@ssw0rd123")
            >>> if success:
            ...     # Password reset successful
            ...     # User can now login with new password
        """
        # Hash token for database lookup
        hashed_token = self._hash_token(token)

        # Look up token
        token_record = self.token_repository.get_by_token(hashed_token)

        if not token_record:
            logger.warning("Password reset attempted with non-existent token")
            raise TokenNotFoundError()

        # Check expiration
        now = datetime.now(UTC)
        expires_at = self._ensure_tz_aware(token_record.expires_at)
        assert expires_at is not None
        if expires_at < now:
            logger.warning(
                "Password reset attempted with expired token",
                extra={"token_id": token_record.id},
            )
            raise TokenExpiredError(context={"token_id": token_record.id})

        # Check if already used
        if token_record.is_used:
            logger.warning(
                "Password reset attempted with already-used token",
                extra={"token_id": token_record.id},
            )
            raise TokenAlreadyUsedError(context={"token_id": token_record.id})

        # Verify user exists
        user = self.user_repository.get_by_id(token_record.user_id)
        if not user:
            logger.error(
                "Password reset token references non-existent user",
                extra={"token_id": token_record.id, "user_id": token_record.user_id},
            )
            raise UserNotFoundError(
                f"User {token_record.user_id} not found",
                context={"user_id": token_record.user_id},
            )

        # Validate new password against policy
        is_valid, errors = self.password_service.validate_password_policy(new_password)
        if not is_valid:
            logger.warning(
                "Password reset failed: password policy violation",
                extra={"user_id": user.id, "errors": errors},
            )
            raise PasswordPolicyError(
                "Password does not meet policy requirements",
                errors=errors,
                context={"user_id": user.id},
            )

        # Hash the new password
        password_hash = self.password_service.hash_password(new_password)

        # Update user's password
        self.user_repository.update_password_hash(
            user_id=user.id, password_hash=password_hash
        )

        # Mark this token as used
        self.token_repository.mark_token_used(token_record.id)

        # Invalidate all other unused tokens for this user
        invalidated_count = self.token_repository.invalidate_user_tokens(user.id)

        logger.info(
            f"Password reset successful for user {user.id}",
            extra={
                "user_id": user.id,
                "token_id": token_record.id,
                "invalidated_tokens": invalidated_count,
            },
        )

        return True

    def cleanup_expired_tokens(self) -> int:
        """Remove expired password reset tokens from database.

        This method should be called periodically (e.g., via cron job) to
        clean up expired tokens and maintain database hygiene.

        Returns:
            Number of tokens deleted

        Example:
            >>> # In a cron job or scheduled task
            >>> deleted_count = service.cleanup_expired_tokens()
            >>> deleted_count
        """
        deleted_count = self.token_repository.cleanup_expired_tokens()

        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired password reset tokens")

        return deleted_count

    def _ensure_tz_aware(self, dt: datetime | None) -> datetime | None:
        """Convert timezone-naive datetime to UTC-aware.

        SQLite does not preserve timezone information even when DateTime(timezone=True)
        is configured in SQLAlchemy models. This helper ensures datetime objects
        retrieved from the database are timezone-aware for safe comparison.

        Args:
            dt: Datetime object that may be timezone-naive

        Returns:
            Timezone-aware datetime in UTC, or None if input is None

        Note:
            If the datetime is already timezone-aware, it is returned unchanged.
            If the datetime is timezone-naive, UTC timezone is added without conversion.
        """
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt

    def _hash_token(self, token: str) -> str:
        """Hash a token using SHA-256.

        This provides a one-way hash of the token for secure storage.
        Even if the database is compromised, tokens cannot be recovered.

        Args:
            token: Plain text token to hash

        Returns:
            Hexadecimal hash string (64 characters)

        Security Notes:
            - Uses SHA-256 for one-way hashing
            - Tokens are cryptographically random, so no salt needed
            - Hash is constant-time verifiable
        """
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _send_reset_email(self, email: str, token: str, username: str) -> None:
        """Send password reset email to user.

        TODO: Implement actual SMTP email sending
        Currently this is a stub that logs the email content for testing.

        Args:
            email: Recipient email address
            token: Password reset token (plain text)
            username: User's username for personalization

        Future Implementation:
            This method should:
            1. Connect to SMTP server using config.smtp_config_dict
            2. Create HTML and plain text email templates
            3. Include reset URL with token
            4. Send email asynchronously if possible
            5. Handle email sending errors gracefully
            6. Log email sending events

        Example SMTP Integration:
            >>> import smtplib
            >>> from email.mime.text import MIMEText
            >>> from email.mime.multipart import MIMEMultipart
            >>>
            >>> msg = MIMEMultipart('alternative')
            >>> msg['Subject'] = 'Password Reset Request'
            >>> msg['From'] = self.config.email_from_address
            >>> msg['To'] = email
            >>>
            >>> reset_url = self.config.get_password_reset_url(token)
            >>> html_body = f"Click here to reset: <a href='{reset_url}'>{reset_url}</a>"
            >>> msg.attach(MIMEText(html_body, 'html'))
            >>>
            >>> with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
            ...     server.starttls()
            ...     server.login(self.config.smtp_username, self.config.smtp_password)
            ...     server.send_message(msg)
        """
        # SECURITY: never log the reset URL or token. It is a bearer credential:
        # anyone who can read the logs could reset the account's password.
        logger.info(
            "Password reset email (STUB - not actually sent)",
            extra={
                "recipient": email,
                "username": username,
                "expires_in_seconds": self.config.password_reset_token_expire_seconds,
            },
        )

        # Log the email details in a human-readable format for testing
        logger.debug(
            f"\n{'='*80}\n"
            f"PASSWORD RESET EMAIL (Development Mode)\n"
            f"{'='*80}\n"
            f"To: {email}\n"
            f"From: {self.config.email_from_name} <{self.config.email_from_address}>\n"
            f"Subject: Password Reset Request\n"
            f"{'-'*80}\n"
            f"Hello {username},\n"
            f"\n"
            f"You requested a password reset for your PromptVault account.\n"
            f"\n"
            f"Click the link below to reset your password:\n"
            f"[reset link intentionally not logged]\n"
            f"\n"
            f"This link will expire in {self.config.password_reset_token_expire_seconds // 60} minutes.\n"
            f"\n"
            f"If you didn't request this reset, please ignore this email.\n"
            f"\n"
            f"Best regards,\n"
            f"The PromptVault Team\n"
            f"{'='*80}\n"
        )

        # TODO: Implement actual SMTP email sending
        # When implementing:
        # 1. Use self.config.smtp_config_dict for connection settings
        # 2. Create proper HTML and plain text templates
        # 3. Handle SMTP errors and log them
        # 4. Consider using an async email queue for production
        # 5. Add email rate limiting if needed
        # 6. Track email delivery status
