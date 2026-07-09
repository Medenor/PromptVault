# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""FastAPI dependency functions for authentication and authorization.

This module provides reusable dependency functions for FastAPI route handlers
to implement secure authentication and authorization using JWT tokens and RBAC.

Dependencies:
    - get_auth_config(): Provides auth configuration singleton
    - get_jwt_service(): Provides JWT service instance
    - get_current_user_token(): Extracts and validates JWT from Authorization header
    - get_current_user(): Gets authenticated user from database
    - get_current_active_user(): Gets authenticated active user
    - get_optional_user(): Gets user if authenticated, None otherwise
    - require_role(): Creates role-based access control dependency
    - require_verified_email(): Requires email verification
    - get_client_ip(): Extracts client IP address with proxy support
    - get_user_agent(): Extracts User-Agent header

Security Features:
    - Bearer token extraction and validation
    - JWT signature verification with ES256
    - Token expiration checking
    - User account status validation (active, locked)
    - Role-based access control (RBAC)
    - Email verification enforcement
    - Proper HTTP status codes (401, 403)
    - WWW-Authenticate headers for 401 responses
    - Proxy-aware IP extraction (X-Forwarded-For, X-Real-IP)

Example Usage:
    >>> from fastapi import APIRouter, Depends
    >>> from src.web.dependencies.auth import (
    ...     get_current_user,
    ...     get_current_active_user,
    ...     require_role,
    ...     require_verified_email
    ... )
    >>>
    >>> router = APIRouter()
    >>>
    >>> # Basic authentication
    >>> @router.get("/profile")
    >>> async def get_profile(user: User = Depends(get_current_active_user)):
    ...     return {"username": user.username, "email": user.email}
    >>>
    >>> # Role-based access control
    >>> @router.delete("/users/{user_id}")
    >>> async def delete_user(
    ...     user_id: str,
    ...     admin: User = Depends(require_role(["admin"]))
    ... ):
    ...     # Only admins can delete users
    ...     return {"deleted": user_id}
    >>>
    >>> # Email verification required
    >>> @router.post("/prompts")
    >>> async def create_prompt(
    ...     prompt_data: dict,
    ...     user: User = Depends(require_verified_email)
    ... ):
    ...     # Only verified users can create prompts
    ...     return {"created": True}
    >>>
    >>> # Optional authentication
    >>> @router.get("/public-prompts")
    >>> async def list_prompts(user: Optional[User] = Depends(get_optional_user)):
    ...     if user:
    ...         # Return personalized results
    ...         pass
    ...     # Return public results
    ...     pass
"""

from typing import Callable, Optional
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidSignatureError,
    InvalidTokenError,
)

from src.config.auth_config import AuthConfig, auth_settings
from src.services.auth.jwt_service import JWTService
from src.db.session import get_db
from src.db.models.user import User
from src.db.repositories.user_repository import UserRepository
from src.services.exceptions import (
    AuthenticationError,
    InvalidTokenError as ServiceInvalidTokenError,
    AccountInactiveError,
    AccountLockedError,
    UnauthorizedError,
    UserNotFoundError,
)

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
    token = None

    # Check Authorization header first
    if authorization:
        # Validate Bearer scheme format
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme. Expected: Bearer <token>",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = parts[1]

    # Fall back to cookie if no header
    elif access_token_cookie:
        token = access_token_cookie

    # No token found in either location
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate JWT token
    try:
        claims = jwt_service.validate_access_token(token)
        return claims

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

    except Exception as e:
        # Catch-all for unexpected errors
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


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

    # Retrieve user from database
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
    from datetime import datetime, timezone

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
        # Extract token from Bearer scheme
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme. Expected: Bearer <token>",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token = parts[1]

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

        # Retrieve user from database
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
        active_session_count = session_repo.count_user_sessions(
            user_id, active_only=True
        )

        if active_session_count == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="All sessions have been revoked. Please log in again.",
                headers={
                    "WWW-Authenticate": 'Bearer error="invalid_token", error_description="Session revoked"'
                },
            )

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


# ============================================================================
# Authorization Dependencies (RBAC)
# ============================================================================


def require_role(allowed_roles: list[str]) -> Callable:
    """Create a dependency that requires specific role(s).

    This is a dependency factory that creates a FastAPI dependency function
    which enforces role-based access control (RBAC). The returned dependency
    checks if the authenticated user's role matches one of the allowed roles.

    Args:
        allowed_roles: List of role names that are permitted (e.g., ["admin", "editor"])

    Returns:
        Callable: FastAPI dependency function that validates user role

    Raises:
        HTTPException: 403 if user's role is not in allowed_roles

    Example:
        >>> # Single role requirement
        >>> @router.delete("/users/{user_id}")
        >>> def delete_user(
        ...     user_id: str,
        ...     admin: User = Depends(require_role(["admin"]))
        ... ):
        ...     # Only admins can access this endpoint
        ...     return {"deleted": user_id}
        >>>
        >>> # Multiple role requirement
        >>> @router.post("/prompts")
        >>> def create_prompt(
        ...     prompt_data: dict,
        ...     user: User = Depends(require_role(["admin", "editor"]))
        ... ):
        ...     # Admins and editors can create prompts
        ...     return {"created": True}
        >>>
        >>> # Reusable role requirements
        >>> require_admin = require_role(["admin"])
        >>> require_editor_or_admin = require_role(["admin", "editor"])
        >>>
        >>> @router.get("/admin/users")
        >>> def list_users(admin: User = Depends(require_admin)):
        ...     return {"users": [...]}

    Security Notes:
        - Always checks if user is active first (via get_current_active_user)
        - Returns 403 Forbidden (not 401) per HTTP semantics
        - Provides clear error message listing allowed roles
        - Case-sensitive role matching
    """

    def check_user_role(user: User = Depends(get_current_active_user)) -> User:
        """Validate that user has one of the required roles.

        Args:
            user: Authenticated active user (injected)

        Returns:
            User: User instance if role is authorized

        Raises:
            HTTPException: 403 if user role not in allowed_roles
        """
        if user.role not in allowed_roles:
            # Build helpful error message
            if len(allowed_roles) == 1:
                role_msg = f"'{allowed_roles[0]}' role"
            else:
                role_list = "', '".join(allowed_roles)
                role_msg = f"one of the following roles: '{role_list}'"

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. This operation requires {role_msg}. Your role: '{user.role}'",
            )

        return user

    return check_user_role


def require_verified_email(user: User = Depends(get_current_user)) -> User:
    """Require email verification for the authenticated user.

    This dependency enforces that the user's email address has been verified
    before allowing access to the protected route. Useful for operations that
    should only be available to verified users.

    Args:
        user: Authenticated user (injected)

    Returns:
        User: User instance if email is verified

    Raises:
        HTTPException: 403 if email is not verified

    Example:
        >>> @router.post("/prompts/publish")
        >>> def publish_prompt(
        ...     prompt_id: str,
        ...     user: User = Depends(require_verified_email)
        ... ):
        ...     # Only verified users can publish prompts
        ...     return {"published": prompt_id}
        >>>
        >>> @router.post("/api-keys")
        >>> def create_api_key(user: User = Depends(require_verified_email)):
        ...     # Only verified users can create API keys
        ...     return {"api_key": "..."}

    Security Notes:
        - Does NOT check if user is active (combine with get_current_active_user if needed)
        - Returns 403 Forbidden per HTTP semantics
        - Provides clear error message with verification instructions
        - Consider sending verification email in response
    """
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required. Please verify your email address to access this feature.",
        )

    return user


# ============================================================================
# Request Metadata Dependencies
# ============================================================================


def get_client_ip(request: Request) -> str:
    """Extract client IP address with proxy support.

    This dependency extracts the client's IP address from the request,
    handling common proxy headers (X-Forwarded-For, X-Real-IP) used by
    reverse proxies like Nginx, Cloudflare, and AWS ALB.

    Args:
        request: FastAPI request object (injected)

    Returns:
        str: Client IP address (IPv4 or IPv6)

    Priority Order:
        1. X-Forwarded-For (first IP in list)
        2. X-Real-IP
        3. request.client.host (direct connection)
        4. "unknown" (fallback)

    Example:
        >>> @router.post("/auth/login")
        >>> def login(
        ...     credentials: LoginRequest,
        ...     ip_address: str = Depends(get_client_ip),
        ...     db: Session = Depends(get_db)
        ... ):
        ...     # Log login attempt with IP address
        ...     logger.info(f"Login attempt from {ip_address}")
        ...     # Store IP in session for security tracking
        ...     session = create_session(user_id, ip_address=ip_address)
        ...     return {"token": "..."}

    Security Notes:
        - X-Forwarded-For can be spoofed by malicious clients
        - Only trust these headers if behind a reverse proxy
        - For rate limiting, consider hashing IP addresses
        - IPv6 addresses may include privacy extensions
        - "unknown" indicates IP could not be determined
    """
    # X-Forwarded-For header (set by reverse proxies)
    # Format: "client, proxy1, proxy2"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Get first IP (client) from comma-separated list
        ip = forwarded_for.split(",")[0].strip()
        if ip:
            return ip

    # X-Real-IP header (alternative to X-Forwarded-For)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Direct connection (no proxy)
    if request.client and request.client.host:
        return request.client.host

    # Fallback if IP cannot be determined
    return "unknown"


def get_user_agent(request: Request) -> str:
    """Extract User-Agent header from request.

    This dependency extracts and truncates the User-Agent string, which
    identifies the client software (browser, mobile app, API client).
    Useful for session tracking, analytics, and security monitoring.

    Args:
        request: FastAPI request object (injected)

    Returns:
        str: User-Agent string (truncated to 255 chars)

    Example:
        >>> @router.post("/auth/login")
        >>> def login(
        ...     credentials: LoginRequest,
        ...     user_agent: str = Depends(get_user_agent),
        ...     db: Session = Depends(get_db)
        ... ):
        ...     # Store user agent in session
        ...     session = create_session(
        ...         user_id,
        ...         user_agent=user_agent
        ...     )
        ...     return {"token": "..."}
        >>>
        >>> @router.get("/sessions")
        >>> def list_sessions(
        ...     user: User = Depends(get_current_active_user),
        ...     db: Session = Depends(get_db)
        ... ):
        ...     sessions = get_user_sessions(user.id, db)
        ...     # Each session includes user_agent for identification
        ...     return {"sessions": sessions}

    Security Notes:
        - User-Agent can be spoofed by clients
        - Truncated to 255 chars to prevent database overflow
        - "unknown" if header is missing
        - Useful for detecting suspicious sessions (different device)
        - Consider parsing for browser/OS detection
    """
    user_agent = request.headers.get("User-Agent", "unknown")

    # Truncate to 255 characters to fit database column
    if len(user_agent) > 255:
        user_agent = user_agent[:255]

    return user_agent


# ============================================================================
# Composite Dependencies (Common Combinations)
# ============================================================================


def get_admin_user(user: User = Depends(get_current_active_user)) -> User:
    """Get current user and verify admin role.

    Convenience dependency that combines authentication and admin authorization.
    Checks that the user has admin role.

    Args:
        user: Authenticated active user (injected)

    Returns:
        User: Admin user instance

    Raises:
        HTTPException: 401 if not authenticated/active, 403 if not admin

    Example:
        >>> @router.delete("/users/{user_id}")
        >>> def delete_user(
        ...     user_id: str,
        ...     admin: User = Depends(get_admin_user)
        ... ):
        ...     # Only admins can delete users
        ...     return {"deleted": user_id}
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. This operation requires 'admin' role. Your role: '{user.role}'",
        )
    return user


def get_editor_or_admin_user(user: User = Depends(get_current_active_user)) -> User:
    """Get current user and verify editor or admin role.

    Convenience dependency for routes that require content editing permissions.
    Allows both editors and admins to access the route.

    Args:
        user: Authenticated active user (injected)

    Returns:
        User: Editor or admin user instance

    Raises:
        HTTPException: 401 if not authenticated/active, 403 if not editor/admin

    Example:
        >>> @router.post("/prompts")
        >>> def create_prompt(
        ...     prompt_data: dict,
        ...     user: User = Depends(get_editor_or_admin_user)
        ... ):
        ...     # Editors and admins can create prompts
        ...     return {"created": True, "user_id": user.id}
    """
    if user.role not in ["admin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. This operation requires 'admin' or 'editor' role. Your role: '{user.role}'",
        )
    return user


# ============================================================================
# Anonymous-Mode (AUTH_ENABLED=false) Bypass Dependencies
# ============================================================================
#
# When authentication is disabled, these dependencies short-circuit to None so
# that data endpoints remain publicly accessible. When auth is enabled they
# enforce the normal requirements (active user / admin role). All callers must
# guard ``user`` attribute accesses (``user.id``, ``user.username``) with
# ``if user:`` or ``user.id if user else None`` fallbacks.


async def get_current_user_or_none(
    authorization: Optional[str] = Header(None, description="Optional Bearer token"),
    access_token_cookie: Optional[str] = Cookie(None, alias="access_token"),
    jwt_service: JWTService = Depends(get_jwt_service),
    session: Session = Depends(get_db),
) -> Optional[User]:
    """Get the current active user, or None when auth is disabled/unauthenticated.

    This is the bypass-friendly variant of :func:`get_current_active_user` used
    on data endpoints that must remain accessible when ``AUTH_ENABLED=false``.

    Behavior:
        - ``AUTH_ENABLED=false``: returns ``None`` immediately (anonymous mode).
        - ``AUTH_ENABLED=true`` with no token: returns ``None``.
        - ``AUTH_ENABLED=true`` with a valid token: returns the active user.
        - Invalid/expired tokens: returns ``None`` (never raises 401).

    Returns:
        Optional[User]: The authenticated user, or None.
    """
    if not auth_settings.auth_enabled:
        return None

    if not authorization and not access_token_cookie:
        return None

    try:
        token = None
        if authorization:
            parts = authorization.split()
            if len(parts) == 2 and parts[0].lower() == "bearer":
                token = parts[1]
        elif access_token_cookie:
            token = access_token_cookie

        if not token:
            return None

        claims = jwt_service.validate_access_token(token)
        user_id = claims.get("sub")
        if not user_id:
            return None

        user_repo = UserRepository(session)
        user = user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            return None

        # Attach family_id from token for session identification
        user.family_id = claims.get("family_id")
        return user
    except Exception:
        return None


async def get_current_user_or_default(
    user: Optional[User] = Depends(get_current_user_or_none),
    session: Session = Depends(get_db),
) -> User:
    """Get the current user, falling back to the shared system user.

    Mutation endpoints (create/update/delete) need an owner to run under.
    When auth is enabled this simply requires a valid authenticated user
    (401 otherwise). When ``AUTH_ENABLED=false`` there is no logged-in user
    by design, so this resolves to the shared 'system' user instead of
    rejecting the request — anonymous/single-user deployments remain fully
    functional while still recording an owner for ownership checks and undo
    history. See constitution principle III: destructive endpoints must stay
    guarded by configuration (network exposure), not by disabling writes.

    Raises:
        HTTPException: 401 if auth is enabled but no user is authenticated.
    """
    if user:
        return user

    if auth_settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(session)
    return user_repo.get_or_create_default_user()


async def get_admin_or_bypass(
    user: Optional[User] = Depends(get_current_user_or_none),
) -> Optional[User]:
    """Require admin when auth is enabled; bypass (None) when disabled.

    Replaces :func:`get_admin_user` on admin-only endpoints so they remain
    functional in anonymous mode. When ``AUTH_ENABLED=false`` this returns
    ``None`` without performing any role check.

    Raises:
        HTTPException: 401 if auth enabled but unauthenticated, 403 if not admin.
    """
    if not auth_settings.auth_enabled:
        return None
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. This operation requires 'admin' role. Your role: '{user.role}'",
        )
    return user


async def get_editor_or_admin_or_bypass(
    user: Optional[User] = Depends(get_current_user_or_none),
) -> Optional[User]:
    """Require editor/admin when auth is enabled; bypass (None) when disabled.

    Replaces :func:`get_editor_or_admin_user` on editor endpoints so they
    remain functional in anonymous mode.

    Raises:
        HTTPException: 401 if auth enabled but unauthenticated, 403 if not editor/admin.
    """
    if not auth_settings.auth_enabled:
        return None
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.role not in ["admin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. This operation requires 'admin' or 'editor' role. Your role: '{user.role}'",
        )
    return user
