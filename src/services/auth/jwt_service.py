# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""JWT token generation and validation service for PromptVault.

This module provides secure JWT token operations using ES256 (ECDSA with SHA-256)
algorithm. It handles both access tokens (short-lived, contain user claims) and
refresh tokens (long-lived, minimal claims for token rotation).

Security Features:
    - ES256 algorithm (ECDSA P-256) prevents key confusion attacks
    - Algorithm validation prevents none/HS256 algorithm substitution
    - Short-lived access tokens (15 minutes default)
    - JTI (JWT ID) for token tracking and revocation
    - Issuer and audience validation
    - Comprehensive expiration checking
    - Cryptographically secure random JTI generation

Token Types:
    Access Token:
        - Contains: user_id, username, email, role, jti
        - Short-lived (15 minutes)
        - Used for API authentication
        - Includes full user context for authorization

    Refresh Token:
        - Contains: user_id, family_id, jti, type="refresh"
        - Long-lived (7 days)
        - Used only for obtaining new access tokens
        - Minimal claims to reduce exposure

Example:
    >>> from src.services.auth.jwt_service import JWTService
    >>> from src.config.auth_config import auth_settings
    >>>
    >>> jwt_service = JWTService(auth_settings)
    >>>
    >>> # Generate access token
    >>> access_token = jwt_service.generate_access_token(
    ...     user_id="123",
    ...     username="alice",
    ...     email="alice@example.com",
    ...     role="user"
    ... )
    >>>
    >>> # Validate and decode
    >>> claims = jwt_service.validate_access_token(access_token)
    >>> print(claims["sub"])  # "123"
    >>> print(claims["role"])  # "user"

Security Notes:
    - NEVER use HS256 - it's vulnerable to key confusion attacks
    - ALWAYS validate the algorithm claim in token header
    - Store private keys securely with restrictive permissions (0600)
    - Rotate keys periodically and maintain key versioning
    - Implement token revocation using JTI tracking
    - Use HTTPS in production to prevent token interception
    - Consider implementing token fingerprinting for additional security
"""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import jwt
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidAlgorithmError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    InvalidTokenError,
    MissingRequiredClaimError,
)

from src.config.auth_config import AuthConfig


class JWTService:
    """Service for generating and validating JWT tokens with ES256 algorithm.

    This service provides secure JWT token operations using ECDSA (ES256)
    signatures. It loads ES256 key pairs from filesystem and provides methods
    for token generation, validation, and inspection.

    Attributes:
        config: AuthConfig instance with JWT settings
        algorithm: JWT algorithm (always ES256)
        private_key: ECDSA private key for signing (loaded lazily)
        public_key: ECDSA public key for verification (loaded lazily)

    Security:
        - Uses ES256 (ECDSA with P-256 and SHA-256)
        - Validates algorithm to prevent substitution attacks
        - Checks issuer, audience, expiration, and signature
        - Generates cryptographically secure JTI for tracking
    """

    def __init__(self, config: AuthConfig):
        """Initialize JWT service with configuration.

        Args:
            config: AuthConfig instance with JWT settings

        Note:
            Keys are loaded lazily on first use, not during initialization.
            This allows the service to be instantiated before keys exist.
        """
        self.config = config
        self.algorithm = "ES256"  # ECDSA with P-256 curve and SHA-256
        self._private_key: Optional[bytes] = None
        self._public_key: Optional[bytes] = None

    def _load_private_key(self) -> bytes:
        """Load ES256 private key from filesystem.

        Returns:
            Private key bytes in PEM format

        Raises:
            FileNotFoundError: If private key file doesn't exist
            ValueError: If private key file is invalid or corrupted
            PermissionError: If private key file isn't readable
        """
        if self._private_key is not None:
            return self._private_key

        key_path = self.config.jwt_private_key_absolute_path

        if not key_path.exists():
            raise FileNotFoundError(
                f"JWT private key not found at {key_path}. "
                f"Generate keys using scripts/generate_jwt_keys.py"
            )

        try:
            self._private_key = key_path.read_bytes()
        except PermissionError as e:
            raise PermissionError(
                f"Cannot read JWT private key at {key_path}. "
                f"Check file permissions (should be 0600): {e}"
            )
        except Exception as e:
            raise ValueError(
                f"Failed to load JWT private key from {key_path}: {e}"
            )

        if not self._private_key or len(self._private_key) < 50:
            raise ValueError(
                f"JWT private key at {key_path} appears to be invalid or empty"
            )

        return self._private_key

    def _load_public_key(self) -> bytes:
        """Load ES256 public key from filesystem.

        Returns:
            Public key bytes in PEM format

        Raises:
            FileNotFoundError: If public key file doesn't exist
            ValueError: If public key file is invalid or corrupted
            PermissionError: If public key file isn't readable
        """
        if self._public_key is not None:
            return self._public_key

        key_path = self.config.jwt_public_key_absolute_path

        if not key_path.exists():
            raise FileNotFoundError(
                f"JWT public key not found at {key_path}. "
                f"Generate keys using scripts/generate_jwt_keys.py"
            )

        try:
            self._public_key = key_path.read_bytes()
        except PermissionError as e:
            raise PermissionError(
                f"Cannot read JWT public key at {key_path}. "
                f"Check file permissions: {e}"
            )
        except Exception as e:
            raise ValueError(
                f"Failed to load JWT public key from {key_path}: {e}"
            )

        if not self._public_key or len(self._public_key) < 50:
            raise ValueError(
                f"JWT public key at {key_path} appears to be invalid or empty"
            )

        return self._public_key

    def _generate_jti(self) -> str:
        """Generate cryptographically secure JWT ID (jti).

        Uses secrets module for cryptographically strong random generation.
        The JTI can be used to track and revoke individual tokens.

        Returns:
            Unique JWT ID as UUID4 string

        Security:
            Uses secrets.token_bytes() for cryptographically secure randomness
            instead of standard uuid.uuid4() which may use weaker RNG.
        """
        # Generate 16 cryptographically secure random bytes
        random_bytes = secrets.token_bytes(16)
        # Convert to UUID4 format for standard representation
        return str(uuid.UUID(bytes=random_bytes, version=4))

    def generate_access_token(
        self,
        user_id: str,
        username: str,
        email: str,
        role: str,
        family_id: str = None,
    ) -> str:
        """Generate JWT access token with user claims.

        Creates a short-lived JWT token containing user identity and role
        information for API authentication and authorization.

        Args:
            user_id: Unique user identifier (typically database ID)
            username: User's username
            email: User's email address
            role: User's role (e.g., "user", "admin", "moderator")
            family_id: Token family ID for rotation tracking (optional)

        Returns:
            Signed JWT token string

        Raises:
            FileNotFoundError: If private key file doesn't exist
            ValueError: If private key is invalid
            Exception: If token generation fails

        Security:
            - Short-lived (15 minutes by default)
            - Contains full user context for authorization
            - Includes JTI for tracking and potential revocation
            - Includes family_id for session identification
            - Signed with ES256 algorithm

        Example:
            >>> token = jwt_service.generate_access_token(
            ...     user_id="123",
            ...     username="alice",
            ...     email="alice@example.com",
            ...     role="user",
            ...     family_id="family-uuid"
            ... )
        """
        now = datetime.now(timezone.utc)
        expiry = now + timedelta(seconds=self.config.jwt_access_token_expire_seconds)

        claims = {
            # Standard claims (RFC 7519)
            "sub": user_id,  # Subject (user ID)
            "exp": expiry,  # Expiration time
            "iat": now,  # Issued at
            "iss": self.config.jwt_issuer,  # Issuer
            "aud": self.config.jwt_audience,  # Audience
            "jti": self._generate_jti(),  # JWT ID for tracking
            # Custom claims
            "username": username,
            "email": email,
            "role": role,
        }
        
        # Add family_id if provided (for identifying current session)
        if family_id:
            claims["family_id"] = family_id

        private_key = self._load_private_key()

        return jwt.encode(
            claims,
            private_key,
            algorithm=self.algorithm,
        )

    def generate_refresh_token(
        self,
        user_id: str,
        family_id: str,
        jti: str,
        expires_in_seconds: Optional[int] = None,
    ) -> str:
        """Generate JWT refresh token with minimal claims.

        Creates a long-lived JWT token for obtaining new access tokens.
        Contains minimal claims to reduce information exposure if compromised.

        Args:
            user_id: Unique user identifier
            family_id: Token family ID for rotation tracking
            jti: JWT ID (should be stored for revocation checking)
            expires_in_seconds: Optional custom expiration in seconds

        Returns:
            Signed JWT refresh token string

        Raises:
            FileNotFoundError: If private key file doesn't exist
            ValueError: If private key is invalid
            Exception: If token generation fails

        Security:
            - Long-lived (7 days by default)
            - Minimal claims to reduce exposure
            - Includes type="refresh" to prevent use as access token
            - Family ID enables token rotation and revocation
            - JTI enables individual token revocation

        Token Rotation:
            When a refresh token is used, generate a new refresh token with
            the SAME family_id but NEW jti. This enables detection of token
            reuse attacks.

        Example:
            >>> family_id = str(uuid.uuid4())
            >>> jti = str(uuid.uuid4())
            >>> token = jwt_service.generate_refresh_token(
            ...     user_id="123",
            ...     family_id=family_id,
            ...     jti=jti,
            ...     expires_in_seconds=1209600  # 14 days
            ... )
            >>> # Store jti in database for revocation checking
        """
        now = datetime.now(timezone.utc)
        expiry_seconds = (
            expires_in_seconds or self.config.jwt_refresh_token_expire_seconds
        )
        expiry = now + timedelta(seconds=expiry_seconds)

        claims = {
            # Standard claims
            "sub": user_id,
            "exp": expiry,
            "iat": now,
            "iss": self.config.jwt_issuer,
            "aud": self.config.jwt_audience,
            "jti": jti,
            # Custom claims for refresh token
            "family_id": family_id,
            "type": "refresh",  # Distinguish from access tokens
        }

        private_key = self._load_private_key()

        return jwt.encode(
            claims,
            private_key,
            algorithm=self.algorithm,
        )

    def validate_access_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode access token.

        Performs comprehensive validation including signature verification,
        expiration checking, and claims validation.

        Args:
            token: JWT token string to validate

        Returns:
            Dictionary of token claims if valid

        Raises:
            ExpiredSignatureError: If token has expired
            InvalidSignatureError: If signature verification fails
            InvalidAlgorithmError: If token uses wrong algorithm
            InvalidAudienceError: If audience claim doesn't match
            InvalidIssuerError: If issuer claim doesn't match
            InvalidTokenError: If token is malformed or invalid
            MissingRequiredClaimError: If required claims are missing

        Security Validations:
            1. Algorithm is ES256 (prevents algorithm substitution)
            2. Signature is valid (prevents tampering)
            3. Token hasn't expired (exp claim)
            4. Issuer matches configuration (iss claim)
            5. Audience matches configuration (aud claim)
            6. Token is not used before nbf if present

        Example:
            >>> try:
            ...     claims = jwt_service.validate_access_token(token)
            ...     user_id = claims["sub"]
            ...     role = claims["role"]
            ... except ExpiredSignatureError:
            ...     # Token expired, need to refresh
            ... except InvalidTokenError:
            ...     # Token invalid, require re-authentication
        """
        public_key = self._load_public_key()

        try:
            # Decode and validate token
            claims = jwt.decode(
                token,
                public_key,
                algorithms=[self.algorithm],  # Only allow ES256
                issuer=self.config.jwt_issuer,
                audience=self.config.jwt_audience,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    "verify_aud": True,
                    "require": ["sub", "exp", "iat", "iss", "aud", "jti"],
                },
            )

            # Additional validation: ensure it's not a refresh token
            if claims.get("type") == "refresh":
                raise InvalidTokenError(
                    "Refresh token cannot be used as access token"
                )

            return claims

        except ExpiredSignatureError:
            raise  # Re-raise for caller to handle
        except InvalidSignatureError:
            raise  # Re-raise for caller to handle
        except InvalidAlgorithmError:
            raise  # Re-raise for caller to handle
        except InvalidAudienceError:
            raise  # Re-raise for caller to handle
        except InvalidIssuerError:
            raise  # Re-raise for caller to handle
        except MissingRequiredClaimError:
            raise  # Re-raise for caller to handle
        except (DecodeError, InvalidTokenError) as e:
            raise InvalidTokenError(f"Invalid token: {str(e)}")

    def validate_refresh_token(self, token: str) -> Dict[str, Any]:
        """Validate and decode refresh token.

        Performs comprehensive validation specifically for refresh tokens,
        ensuring they contain the correct type claim.

        Args:
            token: JWT refresh token string to validate

        Returns:
            Dictionary of token claims if valid

        Raises:
            ExpiredSignatureError: If token has expired
            InvalidSignatureError: If signature verification fails
            InvalidAlgorithmError: If token uses wrong algorithm
            InvalidAudienceError: If audience claim doesn't match
            InvalidIssuerError: If issuer claim doesn't match
            InvalidTokenError: If token is malformed, invalid, or not a refresh token
            MissingRequiredClaimError: If required claims are missing

        Security Validations:
            Same as access token validation, plus:
            - Token must have type="refresh" claim
            - Token must have family_id claim for rotation

        Example:
            >>> try:
            ...     claims = jwt_service.validate_refresh_token(token)
            ...     user_id = claims["sub"]
            ...     family_id = claims["family_id"]
            ...     jti = claims["jti"]
            ...     # Check if JTI is revoked in database
            ...     # Generate new access token
            ... except ExpiredSignatureError:
            ...     # Refresh token expired, require re-authentication
        """
        public_key = self._load_public_key()

        try:
            # Decode and validate token
            claims = jwt.decode(
                token,
                public_key,
                algorithms=[self.algorithm],  # Only allow ES256
                issuer=self.config.jwt_issuer,
                audience=self.config.jwt_audience,
                options={
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_iss": True,
                    "verify_aud": True,
                    "require": ["sub", "exp", "iat", "iss", "aud", "jti", "family_id"],
                },
            )

            # Validate it's a refresh token
            if claims.get("type") != "refresh":
                raise InvalidTokenError(
                    "Token is not a valid refresh token (missing type='refresh')"
                )

            return claims

        except ExpiredSignatureError:
            raise  # Re-raise for caller to handle
        except InvalidSignatureError:
            raise  # Re-raise for caller to handle
        except InvalidAlgorithmError:
            raise  # Re-raise for caller to handle
        except InvalidAudienceError:
            raise  # Re-raise for caller to handle
        except InvalidIssuerError:
            raise  # Re-raise for caller to handle
        except MissingRequiredClaimError:
            raise  # Re-raise for caller to handle
        except (DecodeError, InvalidTokenError) as e:
            raise InvalidTokenError(f"Invalid refresh token: {str(e)}")

    def decode_token_unsafe(self, token: str) -> Dict[str, Any]:
        """Decode token without validation (inspection only).

        Decodes JWT token without verifying signature or validating claims.
        Useful for inspection, logging, or extracting metadata before validation.

        WARNING: NEVER use claims from this method for authentication or
        authorization decisions! Always use validate_access_token() or
        validate_refresh_token() for security-critical operations.

        Args:
            token: JWT token string to decode

        Returns:
            Dictionary of token claims (unverified)

        Raises:
            InvalidTokenError: If token is malformed and cannot be decoded

        Use Cases:
            - Logging token metadata (iss, exp, jti)
            - Extracting JTI for revocation checking
            - Debugging token issues
            - Rate limiting by user_id before full validation

        Example:
            >>> # Extract JTI for logging before validation
            >>> try:
            ...     unverified = jwt_service.decode_token_unsafe(token)
            ...     jti = unverified.get("jti")
            ...     logger.info(f"Processing token {jti}")
            ...     # NOW validate
            ...     claims = jwt_service.validate_access_token(token)
            ... except InvalidTokenError:
            ...     logger.error("Invalid token structure")
        """
        try:
            return jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False},
            )
        except (DecodeError, InvalidTokenError) as e:
            raise InvalidTokenError(f"Cannot decode token: {str(e)}")

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate JWT token (access or refresh).

        Validates token signature, expiration, and claims.
        Automatically determines if token is access or refresh type.

        Args:
            token: JWT token string to validate

        Returns:
            Dictionary of validated token claims

        Raises:
            InvalidTokenError: If token is invalid or malformed
            ExpiredSignatureError: If token is expired

        Example:
            >>> try:
            ...     claims = jwt_service.decode_token(token)
            ...     family_id = claims.get("family_id")  # For access tokens
            ... except InvalidTokenError as e:
            ...     # Handle invalid token
            ...     pass
        """
        try:
            # First try as access token
            claims = self.validate_access_token(token)
            return claims
        except (InvalidTokenError, MissingRequiredClaimError):
            try:
                # If access token validation fails, try refresh token
                claims = self.validate_refresh_token(token)
                return claims
            except Exception:
                # If both fail, raise original access token error
                raise InvalidTokenError("Invalid token format")

    def get_token_expiry(self, token: str) -> datetime:
        """Get token expiration datetime.

        Extracts expiration timestamp from token without full validation.
        Useful for checking if token needs refresh before making API call.

        Args:
            token: JWT token string

        Returns:
            Datetime object representing token expiration (UTC)

        Raises:
            InvalidTokenError: If token is malformed or missing exp claim

        Note:
            This method does NOT validate the token signature or other claims.
            It only extracts the expiration claim for informational purposes.

        Example:
            >>> expiry = jwt_service.get_token_expiry(token)
            >>> time_remaining = expiry - datetime.now(timezone.utc)
            >>> if time_remaining.total_seconds() < 60:
            ...     # Token expires in less than 1 minute, refresh it
            ...     new_token = refresh_access_token()
        """
        try:
            claims = self.decode_token_unsafe(token)
            exp_timestamp = claims.get("exp")

            if exp_timestamp is None:
                raise InvalidTokenError("Token missing exp claim")

            return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

        except InvalidTokenError:
            raise
        except Exception as e:
            raise InvalidTokenError(f"Cannot extract expiry from token: {str(e)}")

    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired.

        Checks token expiration without full validation. Useful for
        quick expiration checks before attempting validation.

        Args:
            token: JWT token string

        Returns:
            True if token is expired, False if still valid

        Raises:
            InvalidTokenError: If token is malformed or missing exp claim

        Note:
            This method does NOT validate the token signature. A token can
            be non-expired but still invalid due to signature issues.

        Example:
            >>> if jwt_service.is_token_expired(access_token):
            ...     # Try to refresh
            ...     if not jwt_service.is_token_expired(refresh_token):
            ...         new_access_token = get_new_access_token(refresh_token)
            ...     else:
            ...         # Both expired, require re-authentication
            ...         redirect_to_login()
        """
        try:
            expiry = self.get_token_expiry(token)
            now = datetime.now(timezone.utc)
            return now >= expiry

        except InvalidTokenError:
            raise
