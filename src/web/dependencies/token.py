# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""JWT token extraction/validation and user-retrieval dependencies.

This module provides the core FastAPI dependencies for authenticating a
request: config/service providers, Bearer/cookie token extraction, JWT
validation, and looking up the authenticated user from the database.

Dependencies:
    - get_auth_config(): Provides auth configuration singleton
    - get_jwt_service(): Provides JWT service instance
    - get_current_user_token(): Extracts and validates JWT from Authorization header
    - get_current_user(): Gets authenticated user from database
    - get_current_active_user(): Gets authenticated active user
    - get_optional_user(): Gets user if authenticated, None otherwise

Security Features:
    - Bearer token extraction and validation
    - JWT signature verification with ES256
    - Token expiration checking
    - User account status validation (active, locked)
    - Proper HTTP status codes (401)
    - WWW-Authenticate headers for 401 responses
"""

from datetime import datetime, timezone
from typing import Optional
from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidSignatureError,
    InvalidTokenError,
)

from src.config.auth_config import AuthConfig
from src.services.auth.jwt_service import JWTService
from src.db.session import get_db
from src.db.models.user import User
from src.db.repositories.user_repository import UserRepository

# ============================================================================
# Configuration Dependencies
# ============================================================================


def get_auth_config() -> AuthConfig:
    """Provide authentication configuration singleton.

    This dependency returns the global auth_settings instance, which loads
    configuration from environment variables and provides validation.

    Returns:
        AuthConfig: Immutable authentication configuration

    Example:
        >>> @router.get("/config/password-policy")
        >>> def get_password_policy(config: AuthConfig = Depends(get_auth_config)):
        ...     return {
        ...         "min_length": config.password_min_length,
        ...         "description": config.password_policy_description
        ...     }
    """
    # Import fresh auth_settings to handle test environment reloading
    from src.config.auth_config import auth_settings

    if isinstance(auth_settings, AuthConfig):
        return auth_settings

    def _export_settings():
        # Prefer Pydantic v2 export, fall back to v1
        exporter = getattr(auth_settings, "model_dump", None) or getattr(
            auth_settings, "dict", None
        )
        if callable(exporter):
            return exporter()
        return {}

    try:
        return AuthConfig(**_export_settings())
    except Exception:
        return AuthConfig()


def get_jwt_service(config: AuthConfig = Depends(get_auth_config)) -> JWTService:
    """Provide JWT service instance.

    Creates a JWTService instance with the current authentication configuration.
    The service handles JWT token generation, validation, and inspection.

    Args:
        config: Authentication configuration (injected)

    Returns:
        JWTService: JWT service instance

    Example:
        >>> @router.post("/debug/validate-token")
        >>> def validate_token(
        ...     token: str,
        ...     jwt_service: JWTService = Depends(get_jwt_service)
        ... ):
        ...     try:
        ...         claims = jwt_service.validate_access_token(token)
        ...         return {"valid": True, "claims": claims}
        ...     except Exception as e:
        ...         return {"valid": False, "error": str(e)}
    """
    return JWTService(config)


# ============================================================================
# Token Extraction and Validation
# ============================================================================


def _extract_bearer_or_cookie_token(
    authorization: Optional[str], access_token_cookie: Optional[str]
) -> Optional[str]:
    """Parse a Bearer token from an Authorization header or a cookie fallback.

    Returns None if neither source yields a token. Raises 401 if an
    Authorization header is present but malformed (wrong scheme).
    """
    if authorization:
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme. Expected: Bearer <token>",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return parts[1]

    if access_token_cookie:
        return access_token_cookie

    return None


def _validate_access_token_claims(jwt_service: JWTService, token: str) -> dict:
    """Validate an access token and return its claims, mapping JWT errors to 401s."""
    try:
        return jwt_service.validate_access_token(token)

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token has expired",
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="Token expired"'
            },
        )

    except InvalidSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token signature",
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="Invalid signature"'
            },
        )

    except InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
        )

    except Exception:
        # Catch-all for unexpected errors
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _resolve_active_user(session: Session, user_id: str) -> User:
    """Look up a user by id and verify they have at least one active session.

    Shared by dependencies that must raise 401 on missing user / revoked
    sessions (as opposed to the bypass variants, which swallow failures).
    """
    user_repo = UserRepository(session)
    user = user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="User not found"'
            },
        )

    # Check if user has at least one active (non-revoked) session
    # This ensures revoked sessions invalidate access tokens
    from src.db.repositories.session_repository import SessionRepository

    session_repo = SessionRepository(session)
    active_session_count = session_repo.count_user_sessions(user_id, active_only=True)

    if active_session_count == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="All sessions have been revoked. Please log in again.",
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="Session revoked"'
            },
        )

    return user


def get_current_user_token(
    authorization: Optional[str] = Header(
        None, description="Bearer token in format: Bearer <token>"
    ),
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> dict:
    """Extract and validate access token from Authorization header or cookie.

    This dependency extracts the JWT token from the Authorization header or
    HTTP-only cookie, validates the Bearer scheme format (for header), and
    verifies the token signature, expiration, and claims.

    Args:
        authorization: Authorization header value (injected)
        access_token_cookie: Access token from HTTP-only cookie (injected)
        jwt_service: JWT service instance (injected)

    Returns:
        dict: Token claims including user_id, username, email, role, etc.

    Raises:
        HTTPException: 401 if token is missing, invalid, expired, or malformed

    Token Format:
        Authorization: Bearer <jwt_token>
        OR
        Cookie: access_token=<jwt_token>

    Example:
        >>> @router.get("/token-info")
        >>> def get_token_info(token_data: dict = Depends(get_current_user_token)):
        ...     return {
        ...         "user_id": token_data["sub"],
        ...         "role": token_data["role"],
        ...         "expires": token_data["exp"]
        ...     }

    Security Notes:
        - Validates Bearer scheme to prevent token type confusion
        - Verifies ES256 signature to prevent tampering
        - Checks expiration to prevent stale tokens
        - Validates issuer and audience claims
        - Returns 401 with WWW-Authenticate header per RFC 6750
        - Supports both header and HTTP-only cookie authentication
    """
    token = _extract_bearer_or_cookie_token(authorization, access_token_cookie)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _validate_access_token_claims(jwt_service, token)


# ============================================================================
# User Retrieval Dependencies
# ============================================================================


def get_current_user(
    token_data: dict = Depends(get_current_user_token),
    session: Session = Depends(get_db),
) -> User:
    """Get current authenticated user from token.

    Retrieves the user from the database using the user_id from the validated
    JWT token. This dependency does NOT check if the user is active or if
    their account is locked - use get_current_active_user for that.

    Args:
        token_data: Validated token claims (injected)
        session: Database session (injected)

    Returns:
        User: User model instance

    Raises:
        HTTPException: 401 if user not found in database

    Example:
        >>> @router.get("/me")
        >>> def get_current_user_info(user: User = Depends(get_current_user)):
        ...     return {
        ...         "id": user.id,
        ...         "username": user.username,
        ...         "email": user.email,
        ...         "role": user.role,
        ...         "is_active": user.is_active
        ...     }

    Security Notes:
        - User existence is verified in database
        - Token may be valid but user could be deleted
        - Does NOT check account status (active, locked)
        - Use get_current_active_user for additional checks
    """
    user_id = token_data.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = _resolve_active_user(session, user_id)

    # Attach family_id from token for session identification
    user.family_id = token_data.get("family_id")

    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """Get current active user with account status validation.

    This dependency extends get_current_user by adding validation for:
    - Account active status (is_active = True)
    - Account lockout status (locked_until has expired or is None)

    Args:
        user: Authenticated user (injected)

    Returns:
        User: Active user model instance

    Raises:
        HTTPException: 401 if account is inactive or locked

    Example:
        >>> @router.post("/prompts")
        >>> def create_prompt(
        ...     prompt_data: dict,
        ...     user: User = Depends(get_current_active_user)
        ... ):
        ...     # Only active, unlocked users can create prompts
        ...     return {"created": True, "user_id": user.id}

    Security Notes:
        - Enforces account suspension (is_active = False)
        - Enforces account lockout (locked_until)
        - Provides clear error messages for each failure type
        - This is the recommended dependency for most protected routes
    """
    # Check if account is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account has been deactivated. Please contact support.",
            headers={
                "WWW-Authenticate": 'Bearer error="invalid_token", error_description="Account inactive"'
            },
        )

    # Check if account is locked
    if user.locked_until:
        now = datetime.now(timezone.utc)
        if now < user.locked_until:
            # Account is still locked
            remaining = (user.locked_until - now).total_seconds()
            minutes = int(remaining / 60)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Account is temporarily locked due to multiple failed login attempts. Try again in {minutes} minutes.",
                headers={
                    "WWW-Authenticate": 'Bearer error="invalid_token", error_description="Account locked"'
                },
            )
        # Lock has expired, but we don't clear it here (that's the auth service's job)
        # Still allow access since the lock period has passed

    return user


def get_optional_user(
    authorization: Optional[str] = Header(None, description="Optional Bearer token"),
    jwt_service: JWTService = Depends(get_jwt_service),
    session: Session = Depends(get_db),
) -> Optional[User]:
    """Get user if authenticated, None otherwise (optional authentication).

    This dependency allows routes to support both authenticated and anonymous
    access. If a valid token is provided, the user is returned. If no token
    is provided, None is returned. Invalid tokens still raise exceptions.

    Args:
        authorization: Optional Authorization header (injected)
        jwt_service: JWT service instance (injected)
        session: Database session (injected)

    Returns:
        Optional[User]: User if authenticated, None if no token provided

    Raises:
        HTTPException: 401 if token is provided but invalid

    Example:
        >>> @router.get("/prompts")
        >>> def list_prompts(
        ...     user: Optional[User] = Depends(get_optional_user),
        ...     db: Session = Depends(get_db)
        ... ):
        ...     if user:
        ...         # Return user's prompts + public prompts
        ...         prompts = get_user_prompts(user.id, db)
        ...     else:
        ...         # Return only public prompts
        ...         prompts = get_public_prompts(db)
        ...     return {"prompts": prompts}

    Security Notes:
        - No token = returns None (not an error)
        - Invalid token = raises 401 (security error)
        - Valid token = returns user
        - Use for public endpoints with optional personalization
    """
    # No token provided - this is OK for optional auth
    if not authorization:
        return None

    # Token provided - must be valid
    try:
        token = _extract_bearer_or_cookie_token(authorization, None)

        # Validate JWT token
        claims = jwt_service.validate_access_token(token)

        # Get user from database
        user_id = claims.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing user identifier",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = _resolve_active_user(session, user_id)

        # Optionally check if user is active (recommended)
        if not user.is_active:
            return None  # Treat inactive users as unauthenticated

        return user

    except HTTPException:
        # Invalid token - re-raise the exception
        raise
    except Exception:
        # Any validation failure -> treat as invalid token for optional flows
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
