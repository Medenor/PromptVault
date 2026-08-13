# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Authentication session/token-lifecycle router.

Split out from the original ``auth.py`` god-file. Contains the login, refresh,
logout, current-user, and session-management endpoints. Route paths, methods,
status codes, tags, and behavior are unchanged.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from src.db.models.user import User
from src.services.auth.auth_service import AuthService
from src.services.auth.jwt_service import JWTService
from src.services.exceptions import (
    AccountInactiveError,
    AccountLockedError,
    InvalidCredentialsError,
    InvalidTokenError,
    SessionLimitExceededError,
    SessionNotFoundError,
    TokenReuseDetectedError,
    TotpChallengeExpiredError,
    TotpCodeInvalidError,
    UnauthorizedError,
)
from src.services.logging_service import logging_service
from src.web.dependencies.auth import (
    get_client_ip,
    get_current_active_user,
    get_user_agent,
)
from src.web.middleware.rate_limit import (
    auth_login_limit,
    limiter,
)
from src.web.models.auth_requests import (
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TotpChallengeExchangeRequest,
)
from src.web.models.auth_responses import (
    MessageResponse,
    RevokeSessionResponse,
    SessionListResponse,
    SessionResponse,
    TokenResponse,
    TotpChallengeIssuedResponse,
    UserResponse,
)
from src.web.routers.auth_shared import get_auth_service, get_jwt_service

# Configure logger
logger = logging.getLogger(__name__)

# Create router with tags and prefix (matches the original auth router).
router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
    responses={
        401: {"description": "Authentication failed - Invalid credentials or token"},
        403: {"description": "Access forbidden - Insufficient permissions"},
        429: {"description": "Rate limit exceeded - Too many requests"},
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with username/email and password",
    description="""
    Authenticate user with username or email and password.

    This endpoint:
    - Accepts either username or email for identification
    - Verifies password using Argon2id
    - Checks account status (active, not locked)
    - Tracks failed login attempts (locks after 5 failures)
    - Enforces session limits per user
    - Generates new JWT token pair
    - Creates session with token family tracking
    - Updates last_login timestamp
    - Resets failed login counter on success

    Account Lockout:
    - Account locks after 5 consecutive failed attempts
    - Lockout duration: 15 minutes (configurable)
    - Counter resets on successful login
    - Locked accounts cannot login until lockout expires

    Security Notes:
    - Timing-safe password comparison to prevent timing attacks
    - Generic error message on failure to prevent user enumeration
    - IP address and User-Agent tracked for security monitoring
    - Old sessions may be revoked if session limit exceeded
    """,
    responses={
        200: {
            "description": "Login successful",
            "model": TokenResponse,
        },
        401: {
            "description": "Invalid credentials or account locked",
        },
        429: {
            "description": "Too many login attempts - rate limited",
        },
    },
)
@limiter.limit(auth_login_limit)
def login(
    request_data: LoginRequest,
    request: Request,
    ip_address: str = Depends(get_client_ip),
    user_agent: str = Depends(get_user_agent),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    """Login with username/email and password.

    Args:
        request_data: Login request with username_or_email and password
        request: FastAPI request object (for metadata)
        ip_address: Client IP address (injected)
        user_agent: Client User-Agent string (injected)
        auth_service: Authentication service instance (injected)

    Returns:
        TokenResponse: JWT tokens and user information

    Raises:
        HTTPException: 401 if invalid credentials or account locked
    """
    try:
        # Call authentication service to login user
        result = auth_service.login(
            username_or_email=request_data.username_or_email,
            password=request_data.password,
            ip_address=ip_address,
            user_agent=user_agent,
            remember_me=request_data.remember_me,
        )

        # 2FA-enabled accounts get a challenge instead of tokens (FR-005) —
        # no session/cookies are set until POST /api/auth/login/2fa succeeds.
        if "challenge_token" in result:
            logger.info(
                f"2FA challenge issued for: {request_data.username_or_email} "
                f"from {ip_address}"
            )
            return JSONResponse(
                content=TotpChallengeIssuedResponse(
                    challenge_token=result["challenge_token"],
                    expires_in=result["expires_in"],
                ).model_dump(mode="json")
            )

        # Convert User model to UserResponse
        user_response = UserResponse.model_validate(result["user"])

        # Log successful login (without sensitive data)
        logger.info(
            f"User logged in successfully: {user_response.username} "
            f"(ID: {user_response.id}) from {ip_address}"
        )

        # Create response with tokens
        response = TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type="Bearer",
            expires_in=result["expires_in"],
            user=user_response,
        )

        # Set HTTP-only cookies for web clients
        json_response = JSONResponse(content=response.model_dump(mode="json"))
        refresh_max_age = (
            auth_service.config.jwt_refresh_token_remember_me_expire_seconds
            if request_data.remember_me
            else auth_service.config.jwt_refresh_token_expire_seconds
        )

        # Set access token cookie with same lifetime as refresh token
        # The JWT inside expires in 15 min, but the cookie persists so
        # the frontend can refresh it automatically when it expires
        json_response.set_cookie(
            key="access_token",
            value=result["access_token"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=refresh_max_age,  # Match refresh token lifetime for auto-refresh
            path="/",
        )

        # Set refresh token cookie (7 days or 30 days with remember_me)
        json_response.set_cookie(
            key="refresh_token",
            value=result["refresh_token"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=refresh_max_age,
            path="/api/auth",
        )

        return json_response

    except InvalidCredentialsError as e:
        logger.warning(
            f"Login failed - invalid credentials for: {request_data.username_or_email} "
            f"from {ip_address}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        ) from e

    except AccountLockedError as e:
        logger.warning(
            f"Login failed - account locked for: {request_data.username_or_email} "
            f"from {ip_address}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        ) from e

    except AccountInactiveError as e:
        logger.warning(
            f"Login failed - account inactive for: {request_data.username_or_email}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        ) from e

    except SessionLimitExceededError as e:
        logger.warning(
            f"Login failed - session limit exceeded for: {request_data.username_or_email}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.user_message,
        ) from e

    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login. Please try again.",
        ) from e


@router.post(
    "/login/2fa",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Exchange a 2FA login challenge for tokens",
    description="""
    Complete login for a 2FA-enabled account by exchanging the challenge
    token issued by POST /api/auth/login for a full session.

    This endpoint:
    - Validates the challenge token (signature, expiry, single-use)
    - Accepts either a current TOTP code or an unused recovery code
    - Issues access/refresh tokens and creates a session on success
    - Counts wrong codes toward the shared account-lockout counter (FR-010)

    A consumed or expired challenge cannot be reused — the client must
    restart from POST /api/auth/login.
    """,
    responses={
        200: {
            "description": "2FA verified, login complete",
            "model": TokenResponse,
        },
        401: {
            "description": "Invalid code (counts toward lockout) or account locked",
        },
        410: {
            "description": "Challenge expired or already consumed",
        },
        429: {
            "description": "Too many attempts - rate limited",
        },
    },
)
@limiter.limit(auth_login_limit)
def exchange_2fa_challenge(
    request_data: TotpChallengeExchangeRequest,
    request: Request,
    ip_address: str = Depends(get_client_ip),
    user_agent: str = Depends(get_user_agent),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    """Exchange a 2FA login challenge for authentication tokens.

    Args:
        request_data: Challenge token and TOTP/recovery code
        request: FastAPI request object (for rate limiting)
        ip_address: Client IP address (injected)
        user_agent: Client User-Agent string (injected)
        auth_service: Authentication service instance (injected)

    Returns:
        TokenResponse: JWT tokens and user information

    Raises:
        HTTPException: 401 if code invalid/account locked, 410 if challenge
            expired or already consumed
    """
    try:
        result = auth_service.exchange_2fa_challenge(
            challenge_token=request_data.challenge_token,
            code=request_data.code,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        user_response = UserResponse.model_validate(result["user"])

        logger.info(
            f"2FA challenge exchanged successfully for user: {user_response.username} "
            f"(ID: {user_response.id}) from {ip_address}"
        )
        logging_service.log_audit_event(
            action=(
                "2fa.recovery_code_used"
                if result.get("used_recovery_code")
                else "2fa.challenge_succeeded"
            ),
            resource_type="user",
            resource_id=user_response.id,
        )

        response = TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type="Bearer",
            expires_in=result["expires_in"],
            user=user_response,
        )

        json_response = JSONResponse(content=response.model_dump(mode="json"))
        refresh_max_age = auth_service.config.jwt_refresh_token_expire_seconds

        json_response.set_cookie(
            key="access_token",
            value=result["access_token"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=refresh_max_age,
            path="/",
        )
        json_response.set_cookie(
            key="refresh_token",
            value=result["refresh_token"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=refresh_max_age,
            path="/api/auth",
        )

        return json_response

    except TotpChallengeExpiredError as e:
        logger.info(
            f"2FA challenge exchange failed - expired/consumed from {ip_address}"
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=e.user_message,
        ) from e

    except TotpCodeInvalidError as e:
        logger.warning(
            f"2FA challenge exchange failed - invalid code from {ip_address}"
        )
        logging_service.log_audit_event(
            action="2fa.challenge_failed",
            resource_type="user",
            resource_id=e.context.get("user_id") or "unknown",
            status="failure",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        ) from e

    except AccountLockedError as e:
        logger.warning(
            f"2FA challenge exchange failed - account locked from {ip_address}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        ) from e

    except AccountInactiveError as e:
        logger.warning(
            f"2FA challenge exchange failed - account inactive from {ip_address}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        ) from e

    except SessionLimitExceededError as e:
        logger.warning(
            f"2FA challenge exchange failed - session limit from {ip_address}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.user_message,
        ) from e

    except Exception as e:
        logger.error(
            f"Unexpected error during 2FA challenge exchange: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during 2FA verification. Please try again.",
        ) from e


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description="""
    Generate new access token using refresh token.

    This endpoint:
    - Validates refresh token (signature, expiration)
    - Finds session by token family ID
    - Detects token reuse (security breach)
    - Generates new access and refresh tokens
    - Updates session with new JTI
    - Revokes entire token family if reuse detected

    Token Rotation:
    - Both access and refresh tokens are rotated
    - Old refresh token becomes invalid immediately
    - New tokens have new JTI (JWT ID) for tracking
    - Session is updated with new token metadata

    Token Reuse Detection:
    - If old refresh token is reused, indicates security breach
    - Entire token family is revoked (all sessions)
    - User must login again with credentials
    - Helps prevent stolen token abuse

    Security Notes:
    - Refresh tokens have longer lifetime (7 days default)
    - Access tokens have short lifetime (15 minutes default)
    - Token family tracking prevents token replay attacks
    - IP address and User-Agent tracked for anomaly detection
    """,
    responses={
        200: {
            "description": "Tokens refreshed successfully",
            "model": TokenResponse,
        },
        401: {
            "description": "Invalid or expired refresh token, or token reuse detected",
        },
    },
)
def refresh(
    request_data: RefreshTokenRequest,
    ip_address: str = Depends(get_client_ip),
    user_agent: str = Depends(get_user_agent),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    """Refresh access token using refresh token.

    Args:
        request_data: Refresh token request
        ip_address: Client IP address (injected)
        user_agent: Client User-Agent string (injected)
        auth_service: Authentication service instance (injected)

    Returns:
        TokenResponse: New JWT tokens and user information

    Raises:
        HTTPException: 401 if token invalid, expired, or reuse detected
    """
    try:
        # Call authentication service to refresh tokens
        result = auth_service.refresh_tokens(
            refresh_token=request_data.refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Convert User model to UserResponse
        user_payload = result["user"]
        user_response = UserResponse.model_validate(user_payload)
        username = getattr(user_payload, "username", None) or user_payload.get(
            "username", "unknown"
        )
        user_id = getattr(user_payload, "id", None) or user_payload.get("id", "unknown")

        # Log token refresh
        logger.info(
            f"Tokens refreshed for user: {username} "
            f"(ID: {user_id}) from {ip_address}"
        )

        # Create response with tokens
        response = TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type="Bearer",
            expires_in=result["expires_in"],
            user=user_response,
        )

        # Set HTTP-only cookies with new tokens
        # Use the remaining session lifetime for cookie max_age
        from fastapi.responses import JSONResponse

        json_response = JSONResponse(content=response.model_dump(mode="json"))

        # Get remaining session lifetime (from the refresh token's remaining time)
        remaining_seconds = result.get(
            "remaining_seconds", auth_service.config.jwt_refresh_token_expire_seconds
        )

        # Set access token cookie with remaining session lifetime
        json_response.set_cookie(
            key="access_token",
            value=result["access_token"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=remaining_seconds,
            path="/",
        )

        # Set refresh token cookie with remaining session lifetime
        json_response.set_cookie(
            key="refresh_token",
            value=result["refresh_token"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=remaining_seconds,
            path="/api/auth",
        )

        return json_response

    except InvalidTokenError as e:
        logger.warning(f"Token refresh failed - invalid token from {ip_address}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        ) from e

    except TokenReuseDetectedError as e:
        logger.error(
            f"Token refresh failed - SECURITY BREACH: Token reuse detected from {ip_address}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token reuse detected. All sessions have been revoked. Please log in again.",
        ) from e

    except SessionNotFoundError as e:
        logger.warning(f"Token refresh failed - session not found from {ip_address}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        ) from e

    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during token refresh. Please try again.",
        ) from e


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout and revoke refresh token",
    description="""
    Logout user by revoking refresh token and session.

    This endpoint:
    - Validates refresh token
    - Finds session by token family ID
    - Revokes session (marks as revoked)
    - Invalidates all tokens in family
    - Logs logout event

    Session Revocation:
    - Session is marked as revoked in database
    - All tokens in token family become invalid
    - Access token becomes invalid immediately
    - Refresh token cannot be used to get new tokens
    - Session no longer appears in active sessions list

    Security Notes:
    - Client should delete tokens from local storage
    - Access token remains valid until expiration (short-lived)
    - For immediate invalidation, implement token blacklist
    - Failed logout (invalid token) is not an error (idempotent)
    """,
    responses={
        200: {
            "description": "Logout successful",
            "model": MessageResponse,
        },
        401: {
            "description": "Invalid refresh token (treated as already logged out)",
        },
    },
)
def logout(
    request: Request,
    request_data: LogoutRequest,
    ip_address: str = Depends(get_client_ip),
    auth_service: AuthService = Depends(get_auth_service),
) -> Response:
    """Logout and revoke refresh token.

    Args:
        request: HTTP request (for cookie fallback)
        request_data: Optional refresh token in body
        ip_address: Client IP address (injected)
        auth_service: Authentication service instance (injected)

    Returns:
        MessageResponse: Success message

    Raises:
        HTTPException: 401 if token invalid (treated as already logged out)
    """
    # Prefer body token, fall back to cookie (cookie-only clients won't have it in body)
    refresh_token = request_data.refresh_token or request.cookies.get("refresh_token")

    try:
        if refresh_token:
            auth_service.logout(refresh_token=refresh_token)

        logger.info(f"User logged out successfully from {ip_address}")

    except InvalidTokenError, SessionNotFoundError:
        # Token invalid or session not found - treat as already logged out
        logger.info(f"Logout attempt with invalid/expired token from {ip_address}")

    except Exception as e:
        logger.error(f"Unexpected error during logout: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during logout. Please try again.",
        ) from e

    json_response = JSONResponse(
        content={
            "message": "Logged out successfully",
            "detail": "Your session has been revoked. Please login again to continue.",
        }
    )
    json_response.delete_cookie(key="access_token", path="/")
    json_response.delete_cookie(key="refresh_token", path="/api/auth")
    return json_response


# ============================================================================
# Protected Endpoints (Authentication Required)
# ============================================================================


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user information",
    description="""
    Get authenticated user's account information.

    This endpoint:
    - Validates access token from Authorization header
    - Retrieves user from database
    - Returns user profile data
    - Checks account is active and not locked

    Returned Information:
    - User ID (UUID)
    - Username
    - Email address
    - Role (viewer/editor/admin)
    - Account status (active, email verified)
    - Account timestamps (created, updated)

    Security Notes:
    - Requires valid access token in Authorization header
    - Access token must not be expired
    - Account must be active and not locked
    - Password hash is never returned
    """,
    responses={
        200: {
            "description": "User information retrieved successfully",
            "model": UserResponse,
        },
        401: {
            "description": "Invalid or expired access token",
        },
    },
)
def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """Get current authenticated user information.

    Args:
        current_user: Authenticated active user (injected)

    Returns:
        UserResponse: User profile information
    """
    # Convert User model to UserResponse
    return UserResponse.model_validate(current_user)


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List user's active sessions",
    description="""
    Get list of authenticated user's active sessions.

    This endpoint:
    - Retrieves all non-revoked sessions for user
    - Returns session metadata (IP, User-Agent, timestamps)
    - Sorts by creation date (newest first)
    - Excludes revoked sessions

    Session Information:
    - Session ID (UUID)
    - Token family ID
    - Creation timestamp
    - Last used timestamp
    - Expiration timestamp
    - IP address (for identification)
    - User-Agent string (browser/device info)
    - Revocation status

    Security Notes:
    - Requires valid access token
    - User can only see their own sessions
    - Helps identify unauthorized sessions
    - Use for security monitoring and session management
    - Consider highlighting suspicious sessions (different IP/device)
    """,
    responses={
        200: {
            "description": "Sessions retrieved successfully",
            "model": SessionListResponse,
        },
        401: {
            "description": "Invalid or expired access token",
        },
    },
)
def get_user_sessions(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> SessionListResponse:
    """Get user's active sessions.

    Args:
        request: HTTP request object (to extract access token)
        current_user: Authenticated active user (injected)
        auth_service: Authentication service instance (injected)
        jwt_service: JWT service instance (injected)

    Returns:
        SessionListResponse: List of active sessions with parsed metadata
    """
    from src.services.user_agent_parser import UserAgentParser

    try:
        # Extract current session's family_id from JWT token
        current_family_id = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            try:
                claims = jwt_service.decode_token(token)
                current_family_id = claims.get("family_id")
            except Exception:
                # If token decode fails, continue without marking current session
                pass

        # Get user's sessions from auth service
        sessions = auth_service.get_user_sessions(
            user_id=current_user.id, current_family_id=current_family_id
        )

        # Convert session models to response models with parsed metadata
        parser = UserAgentParser()
        session_responses = []
        for session in sessions:
            # Parse user agent to extract device/browser/os
            # Handle both dict and object types
            user_agent = (
                session.get("user_agent")
                if isinstance(session, dict)
                else session.user_agent
            )
            ua_info = parser.parse_user_agent(user_agent)

            # Create response model with parsed metadata
            response = SessionResponse.model_validate(session)
            response.device = ua_info.get("device", "Unknown Device")
            response.browser = ua_info.get("browser", "Unknown Browser")
            response.os = ua_info.get("os", "Unknown OS")
            session_responses.append(response)

        logger.info(
            f"Retrieved {len(sessions)} sessions for user: {current_user.username}"
        )

        return SessionListResponse(
            sessions=session_responses,
            total=len(session_responses),
        )

    except Exception as e:
        logger.error(
            f"Unexpected error while retrieving sessions: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving sessions. Please try again.",
        ) from e


@router.delete(
    "/sessions/{session_id}",
    response_model=RevokeSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke specific session",
    description="""
    Revoke a specific session by ID.

    This endpoint:
    - Validates session belongs to authenticated user
    - Revokes session (marks as revoked)
    - Invalidates all tokens in session's family
    - Prevents further token refresh
    - Logs revocation event

    Session Revocation:
    - Session is marked as revoked in database
    - Access and refresh tokens become invalid
    - Session no longer appears in active sessions list
    - Cannot revoke current session (use logout instead)

    Use Cases:
    - User noticed unauthorized session
    - User wants to logout from specific device
    - Security cleanup after potential breach
    - Session management and security monitoring

    Security Notes:
    - Requires valid access token
    - User can only revoke their own sessions
    - Revocation is immediate and permanent
    - Cannot revoke the session used for authentication (use /logout)
    """,
    responses={
        200: {
            "description": "Session revoked successfully",
            "model": RevokeSessionResponse,
        },
        401: {
            "description": "Invalid or expired access token",
        },
        403: {
            "description": "Cannot revoke session (not owner or current session)",
        },
        404: {
            "description": "Session not found",
        },
    },
)
def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> RevokeSessionResponse:
    """Revoke specific session by ID.

    Args:
        session_id: UUID of session to revoke
        current_user: Authenticated active user (injected)
        auth_service: Authentication service instance (injected)

    Returns:
        RevokeSessionResponse: Revocation confirmation

    Raises:
        HTTPException: 403 if not owner, 404 if session not found
    """
    try:
        # Revoke specific session
        revoked = auth_service.revoke_session(
            user_id=current_user.id, session_id=session_id
        )

        logger.info(
            f"Session {session_id} revoked successfully by user: {current_user.username}"
        )

        if revoked:
            return RevokeSessionResponse(
                message="Session revoked successfully",
                revoked_count=1,
            )
        raise SessionNotFoundError("Session not found")
    except SessionNotFoundError as e:
        logger.warning(
            f"Session revocation failed - session not found: {session_id} "
            f"for user: {current_user.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.user_message,
        ) from e

    except UnauthorizedError as e:
        logger.warning(
            f"Session revocation failed - unauthorized: {session_id} "
            f"for user: {current_user.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.user_message,
        ) from e

    except Exception as e:
        logger.error(
            f"Unexpected error during session revocation: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while revoking session. Please try again.",
        ) from e


@router.delete(
    "/sessions",
    response_model=RevokeSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke all sessions except current",
    description="""
    Revoke all user sessions except the current one.

    This endpoint:
    - Identifies all active sessions for user
    - Excludes current session from revocation
    - Revokes all other sessions
    - Returns count of revoked sessions
    - Logs bulk revocation event

    Session Revocation:
    - All sessions except current are marked as revoked
    - Current session remains active
    - User can continue using current session
    - All other devices/browsers are logged out
    - All tokens in revoked sessions become invalid

    Use Cases:
    - User suspects account compromise
    - Security cleanup after password change
    - User wants to logout all other devices
    - Enforce single-device policy

    Security Notes:
    - Requires valid access token
    - Current session is preserved (determined by token family)
    - Revocation is immediate and permanent
    - Users should change password if compromise suspected
    - Consider showing notification about active sessions before revocation
    """,
    responses={
        200: {
            "description": "Sessions revoked successfully",
            "model": RevokeSessionResponse,
        },
        401: {
            "description": "Invalid or expired access token",
        },
    },
)
def revoke_all_sessions(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
    jwt_service: JWTService = Depends(get_jwt_service),
) -> RevokeSessionResponse:
    """Revoke all sessions except current.

    Args:
        request: HTTP request object (for extracting Authorization header)
        current_user: Authenticated active user (injected)
        auth_service: Authentication service instance (injected)
        jwt_service: JWT service instance (injected)

    Returns:
        RevokeSessionResponse: Revocation confirmation with count
    """
    try:
        # Extract current session's family_id from JWT token
        current_family_id = None
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                claims = jwt_service.decode_token(token)
                current_family_id = claims.get("family_id")
                logger.debug(f"Extracted current family_id: {current_family_id}")
            except Exception as e:
                logger.warning(f"Failed to extract family_id from token: {e}")

        # Revoke all sessions except current
        count = auth_service.revoke_all_sessions(
            user_id=current_user.id, except_family_id=current_family_id
        )

        logger.info(
            f"Revoked {count} sessions for user: {current_user.username} "
            f"(current session preserved)"
        )

        return RevokeSessionResponse(
            message=f"Successfully revoked {count} session(s)",
            revoked_count=count,
        )

    except Exception as e:
        logger.error(
            f"Unexpected error during bulk session revocation: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while revoking sessions. Please try again.",
        ) from e
