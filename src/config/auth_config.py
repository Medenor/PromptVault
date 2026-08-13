# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Authentication and security configuration for PromptVault.

This module provides comprehensive authentication configuration settings using
Pydantic BaseSettings. All settings are loaded from environment variables with
sensible defaults for development environments.

Environment Variables:
    JWT Configuration:
        JWT_PRIVATE_KEY_PATH: Path to ES256 private key for signing tokens
        JWT_PUBLIC_KEY_PATH: Path to ES256 public key for verifying tokens
        JWT_ACCESS_TOKEN_EXPIRE_SECONDS: Access token lifetime in seconds
        JWT_REFRESH_TOKEN_EXPIRE_SECONDS: Refresh token lifetime in seconds
        JWT_ISSUER: JWT token issuer identifier
        JWT_AUDIENCE: JWT token audience identifier

    TOTP 2FA Configuration:
        TOTP_ENCRYPTION_KEY: Server-held symmetric key for encrypting TOTP secrets at rest

    Password Policy:
        PASSWORD_MIN_LENGTH: Minimum password length
        PASSWORD_REQUIRE_UPPERCASE: Require uppercase letters
        PASSWORD_REQUIRE_LOWERCASE: Require lowercase letters
        PASSWORD_REQUIRE_DIGIT: Require digits
        PASSWORD_REQUIRE_SPECIAL: Require special characters

    Authentication Toggle:
        AUTH_ENABLED: Enable authentication subsystem (default true; false = anonymous mode)

    Account Security:
        MAX_LOGIN_ATTEMPTS: Max failed login attempts before lockout
        ACCOUNT_LOCKOUT_DURATION_SECONDS: Lockout duration in seconds
        MAX_SESSIONS_PER_USER: Maximum concurrent sessions per user
        SESSION_INACTIVE_TIMEOUT_SECONDS: Session timeout in seconds

    Rate Limiting:
        REDIS_URL: Redis connection URL for rate limiting
        RATE_LIMIT_LOGIN_ATTEMPTS: Login attempts per window
        RATE_LIMIT_LOGIN_WINDOW_SECONDS: Login rate limit window
        RATE_LIMIT_REGISTER_ATTEMPTS: Registration attempts per window
        RATE_LIMIT_REGISTER_WINDOW_SECONDS: Registration rate limit window
        RATE_LIMIT_PASSWORD_RESET_ATTEMPTS: Password reset attempts per window
        RATE_LIMIT_PASSWORD_RESET_WINDOW_SECONDS: Password reset rate limit window

    Email Configuration:
        SMTP_HOST: SMTP server hostname
        SMTP_PORT: SMTP server port
        SMTP_USE_TLS: Enable TLS for SMTP
        SMTP_USERNAME: SMTP authentication username
        SMTP_PASSWORD: SMTP authentication password
        EMAIL_FROM_ADDRESS: Sender email address
        EMAIL_FROM_NAME: Sender display name
        PASSWORD_RESET_TOKEN_EXPIRE_SECONDS: Password reset token lifetime
        APP_BASE_URL: Application base URL for email links

Example:
    >>> from src.config.auth_config import auth_settings
    >>> auth_settings.jwt_algorithm
    'ES256'
    >>> auth_settings.password_min_length
    12
"""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthConfig(BaseSettings):
    """Authentication and security configuration settings.

    This class loads all authentication-related configuration from environment
    variables and provides validation, type safety, and helper properties.
    The configuration is immutable after initialization to prevent accidental
    modifications at runtime.

    Attributes:
        Environment:
            environment: Current deployment environment (development/testing/production)
            disable_rate_limiting: Disable API rate limiting (dev/test only)

        JWT Configuration:
            jwt_private_key_path: Path to ES256 private key file
            jwt_public_key_path: Path to ES256 public key file
            jwt_algorithm: JWT signing algorithm (always ES256)
            jwt_access_token_expire_seconds: Access token lifetime
            jwt_refresh_token_expire_seconds: Refresh token lifetime
            jwt_issuer: Token issuer identifier
            jwt_audience: Token audience identifier

        Password Policy:
            password_min_length: Minimum required password length
            password_require_uppercase: Require uppercase letters
            password_require_lowercase: Require lowercase letters
            password_require_digit: Require numeric digits
            password_require_special: Require special characters

        Account Security:
            max_login_attempts: Failed attempts before lockout
            account_lockout_duration_seconds: Lockout duration
            max_sessions_per_user: Maximum concurrent sessions (0 = unlimited)
            session_inactive_timeout_seconds: Session inactivity timeout

        Rate Limiting:
            redis_url: Redis connection URL
            rate_limit_login_attempts: Login attempts allowed per window
            rate_limit_login_window_seconds: Login rate limit window
            rate_limit_register_attempts: Registration attempts per window
            rate_limit_register_window_seconds: Registration rate limit window
            rate_limit_password_reset_attempts: Password reset attempts per window
            rate_limit_password_reset_window_seconds: Password reset rate limit window

        Email Configuration:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            smtp_use_tls: Enable TLS encryption
            smtp_username: SMTP authentication username
            smtp_password: SMTP authentication password
            email_from_address: Sender email address
            email_from_name: Sender display name
            password_reset_token_expire_seconds: Reset token lifetime
            app_base_url: Application base URL
    """

    # Environment
    environment: str = Field(
        default="development",
        description="Environment (development/testing/production)",
    )
    disable_rate_limiting: bool = Field(
        default=False,
        description="Disable rate limiting (dev/test only; never enable in production)",
    )
    auth_enabled: bool = Field(
        default=True,
        description="Enable authentication subsystem. Set to false for anonymous/local mode.",
    )

    # JWT Configuration
    jwt_private_key_path: str = Field(
        default="secrets/jwt/private_key.pem",
        description="Path to ES256 private key for signing JWT tokens",
    )
    jwt_public_key_path: str = Field(
        default="secrets/jwt/public_key.pem",
        description="Path to ES256 public key for verifying JWT tokens",
    )
    jwt_algorithm: str = Field(
        default="ES256",
        description="JWT signing algorithm (ES256 for ECDSA with SHA-256)",
    )
    jwt_access_token_expire_seconds: int = Field(
        default=900, gt=0, description="Access token lifetime in seconds"  # 15 minutes
    )
    jwt_refresh_token_expire_seconds: int = Field(
        default=604800, gt=0, description="Refresh token lifetime in seconds"  # 7 days
    )
    jwt_refresh_token_remember_me_expire_seconds: int = Field(
        default=2592000,  # 30 days
        gt=0,
        description="Refresh token lifetime when 'remember me' is enabled",
    )
    jwt_issuer: str = Field(
        default="promptvault", description="JWT token issuer identifier"
    )
    jwt_audience: str = Field(
        default="promptvault-api", description="JWT token audience identifier"
    )

    # TOTP 2FA Configuration
    totp_encryption_key: str = Field(
        default="",
        description=(
            "Server-held symmetric key used to derive the AES-256-GCM key that "
            "encrypts TOTP secrets at rest. Required when any user has 2FA "
            "enabled; analogous to jwt_private_key_path for JWT signing."
        ),
    )

    # Password Policy
    password_min_length: int = Field(
        default=12,
        ge=8,
        le=128,
        description="Minimum password length (8-128 characters)",
    )
    password_require_uppercase: bool = Field(
        default=True, description="Require at least one uppercase letter"
    )
    password_require_lowercase: bool = Field(
        default=True, description="Require at least one lowercase letter"
    )
    password_require_digit: bool = Field(
        default=True, description="Require at least one digit"
    )
    password_require_special: bool = Field(
        default=True, description="Require at least one special character"
    )

    # Account Security
    max_login_attempts: int = Field(
        default=5,
        gt=0,
        description="Maximum failed login attempts before account lockout",
    )
    account_lockout_duration_seconds: int = Field(
        default=900,  # 15 minutes
        gt=0,
        description="Account lockout duration in seconds",
    )
    max_sessions_per_user: int = Field(
        default=5,
        ge=0,
        description="Maximum concurrent sessions per user (0 = unlimited)",
    )
    session_inactive_timeout_seconds: int = Field(
        default=2592000,  # 30 days
        gt=0,
        description="Session inactivity timeout in seconds",
    )

    # Rate Limiting
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for rate limiting storage",
    )
    rate_limit_login_attempts: int = Field(
        default=5, gt=0, description="Login attempts allowed per time window"
    )
    rate_limit_login_window_seconds: int = Field(
        default=900,  # 15 minutes
        gt=0,
        description="Login rate limit time window in seconds",
    )
    rate_limit_register_attempts: int = Field(
        default=3, gt=0, description="Registration attempts allowed per time window"
    )
    rate_limit_register_window_seconds: int = Field(
        default=3600,  # 1 hour
        gt=0,
        description="Registration rate limit time window in seconds",
    )
    rate_limit_password_reset_attempts: int = Field(
        default=3, gt=0, description="Password reset attempts allowed per time window"
    )
    rate_limit_password_reset_window_seconds: int = Field(
        default=3600,  # 1 hour
        gt=0,
        description="Password reset rate limit time window in seconds",
    )

    # Rate Limiting — general API taxonomy (per-user, falling back to IP).
    # Applied to state-changing and expensive endpoints beyond auth. Each
    # bucket is overridable via its uppercased env var (e.g. RATE_LIMIT_WRITE_ATTEMPTS).
    rate_limit_read_attempts: int = Field(
        default=300, gt=0, description="Read-endpoint requests allowed per time window"
    )
    rate_limit_read_window_seconds: int = Field(
        default=60, gt=0, description="Read-endpoint rate limit time window in seconds"
    )
    rate_limit_write_attempts: int = Field(
        default=60,
        gt=0,
        description="Write-endpoint (create/update/delete) requests per time window",
    )
    rate_limit_write_window_seconds: int = Field(
        default=60, gt=0, description="Write-endpoint rate limit time window in seconds"
    )
    rate_limit_expensive_attempts: int = Field(
        default=10,
        gt=0,
        description="Expensive-op (import/export/backup/restore) requests per time window",
    )
    rate_limit_expensive_window_seconds: int = Field(
        default=60,
        gt=0,
        description="Expensive-op rate limit time window in seconds",
    )
    rate_limit_bulk_attempts: int = Field(
        default=5,
        gt=0,
        description="Bulk-op (bulk delete, delete-all, compress) requests per time window",
    )
    rate_limit_bulk_window_seconds: int = Field(
        default=60, gt=0, description="Bulk-op rate limit time window in seconds"
    )

    # Email Configuration
    smtp_host: str = Field(
        default="smtp.example.com", description="SMTP server hostname"
    )
    smtp_port: int = Field(default=587, gt=0, le=65535, description="SMTP server port")
    smtp_use_tls: bool = Field(
        default=True, description="Enable TLS encryption for SMTP connection"
    )
    smtp_username: str = Field(
        default="noreply@example.com", description="SMTP authentication username"
    )
    smtp_password: str = Field(
        default="changeme", description="SMTP authentication password"
    )
    email_from_address: str = Field(
        default="noreply@example.com", description="Email sender address"
    )
    email_from_name: str = Field(
        default="PromptVault", description="Email sender display name"
    )
    password_reset_token_expire_seconds: int = Field(
        default=3600,  # 1 hour
        gt=0,
        description="Password reset token validity in seconds",
    )
    app_base_url: str = Field(
        default="http://localhost:8000",
        description="Application base URL for email links",
    )

    # Scheduler Configuration
    cleanup_interval_hours: int = Field(
        default=1, gt=0, description="Session cleanup scheduler interval in hours"
    )
    cleanup_batch_size: int = Field(
        default=100, gt=0, description="Number of expired sessions to cleanup per batch"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # Allow case-insensitive env var matching
        extra="ignore",  # Ignore extra environment variables
        frozen=True,  # Make config immutable after initialization
        validate_assignment=True,  # Validate on assignment attempts
    )

    @field_validator("jwt_private_key_path", "jwt_public_key_path")
    @classmethod
    def validate_key_path(cls, v: str) -> str:
        """Validate that JWT key paths are specified.

        Note: We don't check file existence here because keys might be
        generated after config initialization. The JWT service will
        validate actual file existence when loading keys.

        Args:
            v: The key path to validate

        Returns:
            The validated path

        Raises:
            ValueError: If path is empty or whitespace only
        """
        if not v or not v.strip():
            raise ValueError("JWT key path cannot be empty")
        return v.strip()

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, v: str) -> str:
        """Validate JWT algorithm is ES256.

        PromptVault uses ES256 (ECDSA with SHA-256) for JWT signing
        to provide strong security with smaller key sizes.

        Args:
            v: The algorithm name

        Returns:
            The validated algorithm

        Raises:
            ValueError: If algorithm is not ES256
        """
        if v.upper() != "ES256":
            raise ValueError("Only ES256 algorithm is supported for JWT tokens")
        return "ES256"

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, v: str) -> str:
        """Validate Redis URL format.

        Args:
            v: The Redis URL

        Returns:
            The validated URL

        Raises:
            ValueError: If URL doesn't start with redis:// or rediss://
        """
        if not v.startswith(("redis://", "rediss://")):
            raise ValueError("Redis URL must start with redis:// or rediss://")
        return v

    @field_validator("email_from_address", "smtp_username")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email address format (basic validation).

        Args:
            v: The email address

        Returns:
            The validated email

        Raises:
            ValueError: If email format is invalid
        """
        if "@" not in v or "." not in v.split("@")[1]:
            raise ValueError(f"Invalid email address format: {v}")
        return v.lower()

    @field_validator("app_base_url")
    @classmethod
    def validate_app_url(cls, v: str) -> str:
        """Validate application base URL format.

        Args:
            v: The base URL

        Returns:
            The validated URL (with trailing slash removed)

        Raises:
            ValueError: If URL format is invalid
        """
        if not v.startswith(("http://", "https://")):
            raise ValueError("APP_BASE_URL must start with http:// or https://")
        # Remove trailing slash for consistency
        return v.rstrip("/")

    # Helper Properties

    @property
    def jwt_private_key_absolute_path(self) -> Path:
        """Get absolute path to JWT private key.

        Returns:
            Absolute Path object to private key file
        """
        return Path(self.jwt_private_key_path).resolve()

    @property
    def jwt_public_key_absolute_path(self) -> Path:
        """Get absolute path to JWT public key.

        Returns:
            Absolute Path object to public key file
        """
        return Path(self.jwt_public_key_path).resolve()

    @property
    def private_key_exists(self) -> bool:
        """Check if JWT private key file exists.

        Returns:
            True if private key file exists, False otherwise
        """
        return self.jwt_private_key_absolute_path.exists()

    @property
    def public_key_exists(self) -> bool:
        """Check if JWT public key file exists.

        Returns:
            True if public key file exists, False otherwise
        """
        return self.jwt_public_key_absolute_path.exists()

    @property
    def keys_exist(self) -> bool:
        """Check if both JWT key files exist.

        Returns:
            True if both private and public keys exist, False otherwise
        """
        return self.private_key_exists and self.public_key_exists

    @property
    def password_policy_description(self) -> str:
        """Get human-readable password policy description.

        Returns:
            Formatted string describing password requirements
        """
        requirements = [f"at least {self.password_min_length} characters"]

        if self.password_require_uppercase:
            requirements.append("one uppercase letter")
        if self.password_require_lowercase:
            requirements.append("one lowercase letter")
        if self.password_require_digit:
            requirements.append("one digit")
        if self.password_require_special:
            requirements.append("one special character")

        if len(requirements) == 1:
            return requirements[0]
        elif len(requirements) == 2:
            return " and ".join(requirements)
        else:
            return ", ".join(requirements[:-1]) + ", and " + requirements[-1]

    @property
    def redis_host(self) -> str:
        """Extract Redis host from URL.

        Returns:
            Redis hostname
        """
        # Parse redis://host:port/db or rediss://host:port/db
        url = self.redis_url.replace("redis://", "").replace("rediss://", "")
        if "@" in url:  # Handle redis://user:pass@host:port/db
            url = url.split("@")[1]
        host_port = url.split("/")[0]
        return host_port.split(":")[0] if ":" in host_port else host_port

    @property
    def redis_port(self) -> int:
        """Extract Redis port from URL.

        Returns:
            Redis port number (default: 6379)
        """
        url = self.redis_url.replace("redis://", "").replace("rediss://", "")
        if "@" in url:
            url = url.split("@")[1]
        host_port = url.split("/")[0]
        if ":" in host_port:
            try:
                return int(host_port.split(":")[1])
            except ValueError, IndexError:
                return 6379
        return 6379

    @property
    def redis_db(self) -> int:
        """Extract Redis database number from URL.

        Returns:
            Redis database number (default: 0)
        """
        url = self.redis_url.replace("redis://", "").replace("rediss://", "")
        if "/" in url:
            try:
                return int(url.split("/")[1].split("?")[0])
            except ValueError, IndexError:
                return 0
        return 0

    @property
    def redis_password(self) -> str | None:
        """Extract Redis password from URL if present.

        Returns:
            Redis password or None if not specified
        """
        if "@" not in self.redis_url:
            return None
        # Extract password from redis://user:password@host or redis://:password@host
        auth_part = self.redis_url.split("://")[1].split("@")[0]
        if ":" in auth_part:
            return auth_part.split(":")[1]
        return None

    @property
    def smtp_config_dict(self) -> dict:
        """Get SMTP configuration as dictionary for email libraries.

        Returns:
            Dictionary with SMTP connection parameters
        """
        return {
            "host": self.smtp_host,
            "port": self.smtp_port,
            "use_tls": self.smtp_use_tls,
            "username": self.smtp_username,
            "password": self.smtp_password,
        }

    @property
    def unlimited_sessions(self) -> bool:
        """Check if unlimited sessions per user are allowed.

        Returns:
            True if max_sessions_per_user is 0 (unlimited), False otherwise
        """
        return self.max_sessions_per_user == 0

    def get_password_reset_url(self, token: str) -> str:
        """Generate password reset URL with token.

        Args:
            token: Password reset token

        Returns:
            Complete password reset URL
        """
        return f"{self.app_base_url}/auth/reset-password?token={token}"

    def get_email_verification_url(self, token: str) -> str:
        """Generate email verification URL with token.

        Args:
            token: Email verification token

        Returns:
            Complete email verification URL
        """
        return f"{self.app_base_url}/auth/verify-email?token={token}"


# Global authentication settings instance
# This will be imported and used throughout the application
auth_settings = AuthConfig()
