# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Custom exception hierarchy for PromptVault services.
"""

from typing import Any


class PromptVaultException(Exception):
    """
    Base exception for all service-layer failures.

    Attributes:
        message: Developer-focused error string.
        user_message: Safe message for API consumers.
        http_status: HTTP status code associated with the error.
        log_level: Logging severity to use when reporting the error.
        context: Structured metadata describing the failure (ids, file paths, etc.).
    """

    def __init__(
        self,
        message: str,
        *,
        user_message: str | None = None,
        http_status: int = 500,
        log_level: str = "error",
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.user_message = user_message or "An unexpected error occurred."
        self.http_status = http_status
        self.log_level = log_level
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation for API responses."""
        return {
            "error": self.user_message,
            "details": self.context,
        }


class DataPersistenceError(PromptVaultException):
    """Raised when prompt data cannot be saved or loaded."""

    def __init__(
        self,
        message: str,
        *,
        user_message: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message=user_message or "Unable to persist prompt data.",
            http_status=500,
            log_level="error",
            context=context,
        )


class BackupError(PromptVaultException):
    """Raised for backup/restore failures."""

    def __init__(
        self,
        message: str,
        *,
        user_message: str | None = None,
        context: dict[str, Any] | None = None,
        http_status: int = 500,
    ) -> None:
        super().__init__(
            message,
            user_message=user_message or "Backup operation failed.",
            http_status=http_status,
            log_level="error",
            context=context,
        )


class ImportExportError(PromptVaultException):
    """Raised when import/export operations fail."""

    def __init__(
        self,
        message: str,
        *,
        user_message: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message=user_message
            or "Import/export operation could not be completed.",
            http_status=400,
            log_level="warning",
            context=context,
        )


class ValidationMonitorError(PromptVaultException):
    """Raised when validation monitoring cannot persist metrics."""

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="Validation metrics could not be recorded.",
            http_status=500,
            log_level="warning",
            context=context,
        )


# Authentication Exceptions


class AuthenticationError(PromptVaultException):
    """Base exception for authentication failures."""

    def __init__(
        self,
        message: str,
        *,
        user_message: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message=user_message or "Authentication failed.",
            http_status=401,
            log_level="warning",
            context=context,
        )


class InvalidCredentialsError(AuthenticationError):
    """Raised when user credentials are invalid."""

    def __init__(
        self,
        message: str = "Invalid username or password",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="Invalid username or password.",
            context=context,
        )


class AccountLockedError(AuthenticationError):
    """Raised when user account is locked due to failed login attempts."""

    def __init__(
        self,
        message: str,
        *,
        locked_until: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        user_message = (
            "Account is temporarily locked due to multiple failed login attempts."
        )
        if locked_until:
            user_message += f" Try again after {locked_until}."

        super().__init__(
            message,
            user_message=user_message,
            context=context or {},
        )


class AccountInactiveError(AuthenticationError):
    """Raised when user account is not active."""

    def __init__(
        self,
        message: str = "Account is not active",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="This account has been deactivated. Please contact support.",
            context=context,
        )


class EmailNotVerifiedError(AuthenticationError):
    """Raised when email verification is required but not completed."""

    def __init__(
        self,
        message: str = "Email not verified",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="Email address must be verified before logging in.",
            context=context,
        )


class EmailAlreadyExistsError(PromptVaultException):
    """Raised when attempting to register with an existing email."""

    def __init__(
        self,
        message: str = "Email already registered",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="An account with this email address already exists.",
            http_status=409,
            log_level="warning",
            context=context,
        )


class UsernameAlreadyExistsError(PromptVaultException):
    """Raised when attempting to register with an existing username."""

    def __init__(
        self,
        message: str = "Username already taken",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="This username is already taken. Please choose another.",
            http_status=409,
            log_level="warning",
            context=context,
        )


class PasswordPolicyError(PromptVaultException):
    """Raised when password doesn't meet policy requirements."""

    def __init__(
        self,
        message: str,
        *,
        errors: list | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        ctx = context or {}
        if errors:
            ctx["policy_errors"] = errors

        super().__init__(
            message,
            user_message="Password does not meet security requirements.",
            http_status=400,
            log_level="warning",
            context=ctx,
        )


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid or expired."""

    def __init__(
        self,
        message: str = "Invalid or expired token",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="Invalid or expired authentication token.",
            context=context,
        )


class TokenReuseDetectedError(AuthenticationError):
    """Raised when refresh token reuse is detected (security breach)."""

    def __init__(
        self,
        message: str = "Token reuse detected",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="Security breach detected. All sessions have been revoked. Please log in again.",
            context=context,
        )


class SessionLimitExceededError(PromptVaultException):
    """Raised when user exceeds maximum concurrent sessions."""

    def __init__(
        self,
        message: str,
        *,
        max_sessions: int,
        context: dict[str, Any] | None = None,
    ) -> None:
        ctx = context or {}
        ctx["max_sessions"] = max_sessions

        super().__init__(
            message,
            user_message=f"Maximum number of concurrent sessions ({max_sessions}) exceeded.",
            http_status=429,
            log_level="warning",
            context=ctx,
        )


class SessionNotFoundError(AuthenticationError):
    """Raised when session is not found or has been revoked."""

    def __init__(
        self,
        message: str = "Session not found or revoked",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="Session not found or has been revoked.",
            context=context,
        )


class UnauthorizedError(PromptVaultException):
    """Raised when user lacks permission for the requested operation."""

    def __init__(
        self,
        message: str = "Unauthorized operation",
        *,
        user_message: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message=user_message
            or "You do not have permission to perform this operation.",
            http_status=403,
            log_level="warning",
            context=context,
        )


# Password Reset Exceptions


class TokenExpiredError(AuthenticationError):
    """Raised when password reset token has expired."""

    def __init__(
        self,
        message: str = "Password reset token has expired",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="Password reset token has expired. Please request a new one.",
            context=context,
        )


class TokenAlreadyUsedError(AuthenticationError):
    """Raised when password reset token has already been used."""

    def __init__(
        self,
        message: str = "Password reset token has already been used",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="Password reset token has already been used. Please request a new one.",
            context=context,
        )


class TokenNotFoundError(AuthenticationError):
    """Raised when password reset token is not found."""

    def __init__(
        self,
        message: str = "Password reset token not found",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="Invalid password reset token. Please request a new one.",
            context=context,
        )


class TotpAlreadyEnabledError(PromptVaultException):
    """Raised when a user with 2FA already enabled attempts to re-enroll."""

    def __init__(
        self,
        message: str = "TOTP 2FA is already enabled for this account",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="Two-factor authentication is already enabled.",
            http_status=409,
            log_level="info",
            context=context,
        )


class TotpEnrollmentNotFoundError(PromptVaultException):
    """Raised when confirming 2FA without a pending enrollment."""

    def __init__(
        self,
        message: str = "No pending TOTP enrollment found",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="No pending two-factor authentication enrollment found. Please start enrollment again.",
            http_status=400,
            log_level="info",
            context=context,
        )


class TotpCodeInvalidError(AuthenticationError):
    """Raised when a TOTP or recovery code fails verification."""

    def __init__(
        self,
        message: str = "TOTP code is invalid or expired",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="Invalid or expired authentication code.",
            context=context,
        )


class TotpChallengeExpiredError(PromptVaultException):
    """Raised when a 2FA login-challenge token is expired, consumed, or unknown."""

    def __init__(
        self,
        message: str = "2FA login challenge is expired or already used",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="Your two-factor authentication challenge has expired. Please log in again.",
            http_status=410,
            log_level="info",
            context=context,
        )


class TotpReauthFailedError(AuthenticationError):
    """Raised when password+code re-authentication fails for disable/regenerate.

    Deliberately generic (does not reveal whether the password or the code
    was wrong) per contracts/totp-api.md §3-4.
    """

    def __init__(
        self,
        message: str = "TOTP re-authentication failed (password or code incorrect)",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="Incorrect password or authentication code.",
            context=context,
        )


class RateLimitExceededError(PromptVaultException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        *,
        user_message: str | None = None,
        retry_after: int | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        ctx = context or {}
        if retry_after:
            ctx["retry_after_seconds"] = retry_after

        super().__init__(
            message,
            user_message=user_message or "Too many requests. Please try again later.",
            http_status=429,
            log_level="warning",
            context=ctx,
        )


class ShareGrantError(PromptVaultException):
    """Raised when a prompt share grant cannot be created.

    Deliberately generic: unknown identifier, inactive grantee, self-share,
    and owner-as-grantee all raise this with the same user_message, so the
    API response never lets a caller distinguish "user doesn't exist" from
    "user exists but can't be granted" (FR-010, SC-006 — no user enumeration).
    """

    def __init__(
        self,
        message: str = "Unable to grant share",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="Unable to share this prompt with that user.",
            http_status=400,
            log_level="info",
            context=context,
        )


class UserNotFoundError(PromptVaultException):
    """Raised when user is not found."""

    def __init__(
        self,
        message: str = "User not found",
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            user_message="User not found.",
            http_status=404,
            log_level="warning",
            context=context,
        )


class ItemTypeMismatchError(PromptVaultException):
    """Raised when an endpoint for one item type is called on the other.

    Attributes:
        error_code: Stable machine-readable code returned in the API body.
    """

    error_code = "ITEM_TYPE_MISMATCH"
    default_message = "Item type mismatch."

    def __init__(
        self,
        message: str | None = None,
        *,
        user_message: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message or self.default_message,
            user_message=user_message or self.default_message,
            http_status=409,
            log_level="info",
            context=context,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the standard error body plus the contract's ``detail`` object."""
        body = super().to_dict()
        body["detail"] = {
            "code": self.error_code,
            "message": self.user_message,
            "offending_entry": None,
        }
        return body


class ItemIsSkillError(ItemTypeMismatchError):
    """A prompt-only operation was attempted on a skill (409 ``ITEM_IS_SKILL``)."""

    error_code = "ITEM_IS_SKILL"
    default_message = (
        "This item is a skill. Versions, sharing and prompt editing "
        "do not apply to skills."
    )


class ItemIsPromptError(ItemTypeMismatchError):
    """A skill-only operation was attempted on a prompt (409 ``ITEM_IS_PROMPT``)."""

    error_code = "ITEM_IS_PROMPT"
    default_message = "This item is a prompt, not a skill."
