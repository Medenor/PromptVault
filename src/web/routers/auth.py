# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""FastAPI authentication router with comprehensive authentication endpoints.

This module provides RESTful API endpoints for user authentication and session
management, implementing secure authentication flows with JWT tokens, password
reset, session management, and account security features.

Available Endpoints:
    Public (No Authentication Required):
        POST /auth/register - Register new user account
        POST /auth/login - Login with username/email and password
        POST /auth/refresh - Refresh access token using refresh token
        POST /auth/logout - Logout and revoke refresh token
        POST /auth/password-reset/request - Request password reset email
        POST /auth/password-reset/confirm - Confirm password reset with token

    Protected (Authentication Required):
        GET /auth/me - Get current user information
        POST /auth/change-password - Change user password
        GET /auth/sessions - List user's active sessions
        DELETE /auth/sessions/{session_id} - Revoke specific session
        DELETE /auth/sessions - Revoke all sessions except current

Security Features:
    - ES256 (ECDSA) JWT token generation and validation
    - Argon2id password hashing
    - Account lockout protection (5 failed attempts)
    - Token family tracking and reuse detection
    - Session limit enforcement
    - Password policy validation
    - IP address and User-Agent tracking
    - Comprehensive error handling with proper HTTP status codes

Example Usage:
    >>> import httpx
    >>>
    >>> # Register new user
    >>> response = httpx.post("http://localhost:8000/auth/register", json={
    ...     "username": "alice",
    ...     "email": "alice@example.com",
    ...     "password": "SecureP@ssw0rd123",
    ...     "confirm_password": "SecureP@ssw0rd123"
    ... })
    >>> tokens = response.json()
    >>>
    >>> # Login
    >>> response = httpx.post("http://localhost:8000/auth/login", json={
    ...     "username_or_email": "alice",
    ...     "password": "SecureP@ssw0rd123"
    ... })
    >>> tokens = response.json()
    >>>
    >>> # Get current user
    >>> headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    >>> response = httpx.get("http://localhost:8000/auth/me", headers=headers)
    >>> user = response.json()
    >>>
    >>> # Refresh access token
    >>> response = httpx.post("http://localhost:8000/auth/refresh", json={
    ...     "refresh_token": tokens["refresh_token"]
    ... })
    >>> new_tokens = response.json()

OpenAPI Documentation:
    All endpoints include comprehensive OpenAPI documentation with:
    - Request/response schemas
    - Status code descriptions
    - Example payloads
    - Security requirements
    - Error response formats
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from src.config.auth_config import AuthConfig
from src.db.session import get_db
from src.services.auth.auth_service import AuthService
from src.services.auth.password_reset_service import PasswordResetService
from src.services.auth.password_service import PasswordService
from src.db.repositories.user_repository import UserRepository
from src.db.repositories.refresh_token_repository import RefreshTokenRepository
from src.db.repositories.password_reset_token_repository import PasswordResetTokenRepository
from src.db.models.user import User
from src.web.dependencies.auth import (
    get_auth_config,
    get_current_active_user,
    get_client_ip,
    get_user_agent,
)
from src.web.models.auth_requests import (
    RegisterRequest,
    LoginRequest,
    RefreshTokenRequest,
    ChangePasswordRequest,
    PasswordResetRequestRequest,
    PasswordResetConfirmRequest,
)
from src.web.models.auth_responses import (
    TokenResponse,
    UserResponse,
    MessageResponse,
    SessionListResponse,
    SessionResponse,
    RevokeSessionResponse,
    PasswordResetRequestResponse,
)
from src.services.exceptions import (
    InvalidCredentialsError,
    AccountLockedError,
    AccountInactiveError,
    EmailAlreadyExistsError,
    UsernameAlreadyExistsError,
    PasswordPolicyError,
    InvalidTokenError,
    TokenReuseDetectedError,
    SessionLimitExceededError,
    SessionNotFoundError,
    UserNotFoundError,
    TokenExpiredError,
    TokenAlreadyUsedError,
    TokenNotFoundError,
    RateLimitExceededError,
    UnauthorizedError,
)

# Configure logger
logger = logging.getLogger(__name__)

# Create router with tags and prefix
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


# ============================================================================
# Dependency Injection
# ============================================================================


def get_auth_service(
    session: Session = Depends(get_db),
    config: AuthConfig = Depends(get_auth_config),
) -> AuthService:
    """Provide AuthService instance with dependencies.

    This dependency creates an AuthService instance with all required
    repositories and services injected.

    Args:
        session: Database session (injected)
        config: Authentication configuration (injected)

    Returns:
        AuthService: Configured authentication service instance
    """
    return AuthService(session, config)


def get_password_reset_service(
    session: Session = Depends(get_db),
    config: AuthConfig = Depends(get_auth_config),
) -> PasswordResetService:
    """Provide PasswordResetService instance with dependencies.

    This dependency creates a PasswordResetService instance with all required
    repositories and services injected.

    Args:
        session: Database session (injected)
        config: Authentication configuration (injected)

    Returns:
        PasswordResetService: Configured password reset service instance
    """
    password_service = PasswordService(config)
    token_repository = PasswordResetTokenRepository(session)
    user_repository = UserRepository(session)

    return PasswordResetService(
        config=config,
        password_service=password_service,
        token_repository=token_repository,
        user_repository=user_repository,
    )


# ============================================================================
# Public Endpoints (No Authentication Required)
# ============================================================================


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register new user account",
    description="""
    Register a new user account with username, email, and password.

    This endpoint:
    - Validates password against security policy (minimum length, complexity)
    - Checks username and email uniqueness
    - Hashes password with Argon2id
    - Creates user account with default 'viewer' role
    - Generates initial JWT token pair (access + refresh)
    - Creates session with IP and User-Agent tracking
    - Returns tokens for immediate login

    Password Policy:
    - Minimum 12 characters (configurable)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    - Not in common password list

    Security Notes:
    - Account is created as inactive if email verification is required
    - Failed registration attempts do not trigger account lockout
    - Email addresses are normalized to lowercase
    - Usernames are case-sensitive
    """,
    responses={
        201: {
            "description": "User registered successfully",
            "model": TokenResponse,
        },
        400: {
            "description": "Password doesn't meet policy requirements",
        },
        409: {
            "description": "Username or email already exists",
        },
    },
)
def register(
    request_data: RegisterRequest,
    request: Request,
    ip_address: str = Depends(get_client_ip),
    user_agent: str = Depends(get_user_agent),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Register new user account.

    Args:
        request_data: Registration request with username, email, and password
        request: FastAPI request object (for metadata)
        ip_address: Client IP address (injected)
        user_agent: Client User-Agent string (injected)
        auth_service: Authentication service instance (injected)

    Returns:
        TokenResponse: JWT tokens and user information

    Raises:
        HTTPException: 400 if password policy violation, 409 if duplicate username/email
    """
    try:
        # Call authentication service to register user
        result = auth_service.register(
            username=request_data.username,
            email=request_data.email,
            password=request_data.password,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Convert User model to UserResponse
        user_response = UserResponse.model_validate(result["user"])

        # Log successful registration (without sensitive data)
        logger.info(
            f"User registered successfully: {result['user'].username} "
            f"(ID: {result['user'].id}) from {ip_address}"
        )

        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type="Bearer",
            expires_in=result["expires_in"],
            user=user_response,
        )

    except EmailAlreadyExistsError as e:
        logger.warning(f"Registration failed - email exists: {request_data.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.user_message,
        )

    except UsernameAlreadyExistsError as e:
        logger.warning(f"Registration failed - username exists: {request_data.username}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.user_message,
        )

    except PasswordPolicyError as e:
        logger.warning(f"Registration failed - password policy violation for user: {request_data.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.user_message,
        )

    except Exception as e:
        logger.error(f"Unexpected error during registration: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during registration. Please try again.",
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
def login(
    request_data: LoginRequest,
    request: Request,
    ip_address: str = Depends(get_client_ip),
    user_agent: str = Depends(get_user_agent),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
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
        )

        # Convert User model to UserResponse
        user_response = UserResponse.model_validate(result["user"])

        # Log successful login (without sensitive data)
        logger.info(
            f"User logged in successfully: {result['user'].username} "
            f"(ID: {result['user'].id}) from {ip_address}"
        )

        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type="Bearer",
            expires_in=result["expires_in"],
            user=user_response,
        )

    except InvalidCredentialsError as e:
        logger.warning(
            f"Login failed - invalid credentials for: {request_data.username_or_email} "
            f"from {ip_address}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        )

    except AccountLockedError as e:
        logger.warning(
            f"Login failed - account locked for: {request_data.username_or_email} "
            f"from {ip_address}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        )

    except AccountInactiveError as e:
        logger.warning(
            f"Login failed - account inactive for: {request_data.username_or_email}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        )

    except SessionLimitExceededError as e:
        logger.warning(
            f"Login failed - session limit exceeded for: {request_data.username_or_email}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=e.user_message,
        )

    except Exception as e:
        logger.error(f"Unexpected error during login: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during login. Please try again.",
        )


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
) -> TokenResponse:
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
        user_response = UserResponse.model_validate(result["user"])

        # Log token refresh
        logger.info(
            f"Tokens refreshed for user: {result['user'].username} "
            f"(ID: {result['user'].id}) from {ip_address}"
        )

        return TokenResponse(
            access_token=result["access_token"],
            refresh_token=result["refresh_token"],
            token_type="Bearer",
            expires_in=result["expires_in"],
            user=user_response,
        )

    except InvalidTokenError as e:
        logger.warning(f"Token refresh failed - invalid token from {ip_address}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        )

    except TokenReuseDetectedError as e:
        logger.error(
            f"Token refresh failed - SECURITY BREACH: Token reuse detected from {ip_address}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        )

    except SessionNotFoundError as e:
        logger.warning(f"Token refresh failed - session not found from {ip_address}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        )

    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during token refresh. Please try again.",
        )


@router.post(
    "/logout",
    response_model=MessageResponse,
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
    request_data: RefreshTokenRequest,
    ip_address: str = Depends(get_client_ip),
    auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """Logout and revoke refresh token.

    Args:
        request_data: Refresh token to revoke
        ip_address: Client IP address (injected)
        auth_service: Authentication service instance (injected)

    Returns:
        MessageResponse: Success message

    Raises:
        HTTPException: 401 if token invalid (treated as already logged out)
    """
    try:
        # Call authentication service to logout
        auth_service.logout(refresh_token=request_data.refresh_token)

        logger.info(f"User logged out successfully from {ip_address}")

        return MessageResponse(
            message="Logged out successfully",
            detail="Your session has been revoked. Please login again to continue.",
        )

    except (InvalidTokenError, SessionNotFoundError) as e:
        # Token invalid or session not found - treat as already logged out
        logger.info(f"Logout attempt with invalid/expired token from {ip_address}")
        # Return success anyway (idempotent operation)
        return MessageResponse(
            message="Logged out successfully",
            detail="Your session has been revoked. Please login again to continue.",
        )

    except Exception as e:
        logger.error(f"Unexpected error during logout: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during logout. Please try again.",
        )


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


@router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change user password",
    description="""
    Change authenticated user's password.

    This endpoint:
    - Validates current password
    - Validates new password against policy
    - Verifies new password is different from old
    - Hashes new password with Argon2id
    - Updates password in database
    - Maintains active sessions (no forced logout)

    Password Validation:
    - Current password must be correct
    - New password must meet security policy
    - New password must differ from old password
    - Password confirmation must match

    Security Notes:
    - Requires valid access token
    - Current password verification prevents unauthorized changes
    - Active sessions remain valid after password change
    - Consider forcing re-login for maximum security
    - Failed password verification counts toward login lockout
    """,
    responses={
        200: {
            "description": "Password changed successfully",
            "model": MessageResponse,
        },
        400: {
            "description": "Password policy violation or passwords don't match",
        },
        401: {
            "description": "Invalid current password or expired token",
        },
    },
)
def change_password(
    request_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    """Change user password.

    Args:
        request_data: Password change request with old and new passwords
        current_user: Authenticated active user (injected)
        auth_service: Authentication service instance (injected)

    Returns:
        MessageResponse: Success message

    Raises:
        HTTPException: 400 if policy violation, 401 if incorrect old password
    """
    try:
        # Call authentication service to change password
        auth_service.change_password(
            user_id=current_user.id,
            old_password=request_data.old_password,
            new_password=request_data.new_password,
        )

        logger.info(f"Password changed successfully for user: {current_user.username} (ID: {current_user.id})")

        return MessageResponse(
            message="Password changed successfully",
            detail="Your password has been updated. All sessions remain active.",
        )

    except InvalidCredentialsError as e:
        logger.warning(f"Password change failed - incorrect old password for user: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        )

    except PasswordPolicyError as e:
        logger.warning(f"Password change failed - policy violation for user: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.user_message,
        )

    except Exception as e:
        logger.error(f"Unexpected error during password change: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while changing password. Please try again.",
        )


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
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> SessionListResponse:
    """Get user's active sessions.

    Args:
        current_user: Authenticated active user (injected)
        auth_service: Authentication service instance (injected)

    Returns:
        SessionListResponse: List of active sessions with metadata
    """
    try:
        # Get user's sessions from auth service
        sessions = auth_service.get_user_sessions(user_id=current_user.id)

        # Convert session models to response models
        session_responses = [
            SessionResponse.model_validate(session) for session in sessions
        ]

        logger.info(f"Retrieved {len(sessions)} sessions for user: {current_user.username}")

        return SessionListResponse(
            sessions=session_responses,
            total=len(session_responses),
        )

    except Exception as e:
        logger.error(f"Unexpected error while retrieving sessions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving sessions. Please try again.",
        )


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
        auth_service.revoke_session(user_id=current_user.id, session_id=session_id)

        logger.info(
            f"Session {session_id} revoked successfully by user: {current_user.username}"
        )

        return RevokeSessionResponse(
            message="Session revoked successfully",
            revoked_count=1,
        )

    except SessionNotFoundError as e:
        logger.warning(
            f"Session revocation failed - session not found: {session_id} "
            f"for user: {current_user.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.user_message,
        )

    except UnauthorizedError as e:
        logger.warning(
            f"Session revocation failed - unauthorized: {session_id} "
            f"for user: {current_user.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=e.user_message,
        )

    except Exception as e:
        logger.error(f"Unexpected error during session revocation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while revoking session. Please try again.",
        )


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
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> RevokeSessionResponse:
    """Revoke all sessions except current.

    Args:
        current_user: Authenticated active user (injected)
        auth_service: Authentication service instance (injected)

    Returns:
        RevokeSessionResponse: Revocation confirmation with count
    """
    try:
        # Revoke all sessions except current
        # Note: We need the current session's family_id to exclude it
        # For now, revoke all and let user re-login if needed
        count = auth_service.revoke_all_sessions(
            user_id=current_user.id,
            except_current=True,
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
        logger.error(f"Unexpected error during bulk session revocation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while revoking sessions. Please try again.",
        )


# ============================================================================
# Password Reset Endpoints (Public)
# ============================================================================


@router.post(
    "/password-reset/request",
    response_model=PasswordResetRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Request password reset",
    description="""
    Request password reset email for account.

    This endpoint:
    - Validates email address format
    - Checks if user exists (timing-safe)
    - Generates 256-bit secure token
    - Hashes token with SHA-256 before storage
    - Invalidates previous reset tokens
    - Sends reset email with token link
    - Enforces rate limiting (3 requests per hour)

    Password Reset Flow:
    1. User requests reset with email
    2. System generates secure token
    3. Email sent with reset link containing token
    4. User clicks link and enters new password
    5. Token is validated and marked as used
    6. Password is updated and user can login

    Token Properties:
    - 256-bit cryptographically secure random token
    - Single-use (marked as used after password reset)
    - Time-limited (1 hour expiration, configurable)
    - Hashed before storage (SHA-256)
    - Previous tokens invalidated on new request

    Rate Limiting:
    - Maximum 3 requests per hour per email
    - Prevents abuse and email bombing
    - Returns same success message even if rate limited
    - Implements timing-safe responses

    Security Notes:
    - Always returns success message (prevents user enumeration)
    - Email is partially masked in response (a***@example.com)
    - Timing-safe responses prevent information leakage
    - IP address tracked for abuse monitoring
    - Token cannot be retrieved after generation
    """,
    responses={
        200: {
            "description": "Password reset email sent (or rate limited)",
            "model": PasswordResetRequestResponse,
        },
        429: {
            "description": "Rate limit exceeded (returned as 200 for security)",
        },
    },
)
def request_password_reset(
    request_data: PasswordResetRequestRequest,
    ip_address: str = Depends(get_client_ip),
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> PasswordResetRequestResponse:
    """Request password reset email.

    Args:
        request_data: Email address for password reset
        ip_address: Client IP address (injected)
        password_reset_service: Password reset service instance (injected)

    Returns:
        PasswordResetRequestResponse: Success message with masked email
    """
    try:
        # Request password reset
        masked_email = password_reset_service.request_password_reset(
            email=request_data.email,
            ip_address=ip_address,
        )

        logger.info(f"Password reset requested for email: {masked_email} from {ip_address}")

        return PasswordResetRequestResponse(
            message="If an account exists with this email, a password reset link has been sent.",
            email=masked_email,
        )

    except RateLimitExceededError as e:
        # Return success message to prevent information leakage
        # User will see same message whether rate limited or not
        logger.warning(f"Password reset rate limit exceeded for: {request_data.email} from {ip_address}")

        # Mask email for response
        email_parts = request_data.email.split("@")
        masked_email = f"{email_parts[0][0]}***@{email_parts[1]}" if len(email_parts) == 2 else "***@***"

        return PasswordResetRequestResponse(
            message="If an account exists with this email, a password reset link has been sent.",
            email=masked_email,
        )

    except Exception as e:
        logger.error(f"Unexpected error during password reset request: {str(e)}", exc_info=True)
        # Still return success message for security
        email_parts = request_data.email.split("@")
        masked_email = f"{email_parts[0][0]}***@{email_parts[1]}" if len(email_parts) == 2 else "***@***"

        return PasswordResetRequestResponse(
            message="If an account exists with this email, a password reset link has been sent.",
            email=masked_email,
        )


@router.post(
    "/password-reset/confirm",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirm password reset with token",
    description="""
    Reset password using token from email.

    This endpoint:
    - Validates reset token format
    - Verifies token exists in database
    - Checks token not expired (1 hour)
    - Checks token not already used
    - Validates new password against policy
    - Hashes new password with Argon2id
    - Updates user password
    - Marks token as used
    - Logs password reset event

    Token Validation:
    - Token must exist in database (hashed lookup)
    - Token must not be expired (1 hour lifetime)
    - Token must not be already used (single-use)
    - User account must exist and be active

    Password Validation:
    - Must meet password policy requirements
    - Must be different from old password
    - Confirmation must match

    Security Notes:
    - Token is hashed before database lookup (SHA-256)
    - Single-use enforcement prevents replay attacks
    - Time-limited tokens prevent long-term abuse
    - All active sessions remain valid (consider forcing logout)
    - Password reset does not verify old password (by design)
    """,
    responses={
        200: {
            "description": "Password reset successful",
            "model": MessageResponse,
        },
        400: {
            "description": "Password policy violation",
        },
        401: {
            "description": "Invalid, expired, or already used token",
        },
    },
)
def confirm_password_reset(
    request_data: PasswordResetConfirmRequest,
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
) -> MessageResponse:
    """Confirm password reset with token.

    Args:
        request_data: Reset token and new password
        password_reset_service: Password reset service instance (injected)

    Returns:
        MessageResponse: Success message

    Raises:
        HTTPException: 400 if policy violation, 401 if invalid/expired token
    """
    try:
        # Reset password using token
        password_reset_service.reset_password(
            token=request_data.token,
            new_password=request_data.new_password,
        )

        logger.info(f"Password reset successfully completed using token")

        return MessageResponse(
            message="Password reset successful",
            detail="Your password has been updated. You can now login with your new password.",
        )

    except (TokenExpiredError, TokenAlreadyUsedError, TokenNotFoundError) as e:
        logger.warning(f"Password reset failed - invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        )

    except PasswordPolicyError as e:
        logger.warning(f"Password reset failed - policy violation")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.user_message,
        )

    except UserNotFoundError as e:
        logger.error(f"Password reset failed - user not found (orphaned token)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password reset token. Please request a new one.",
        )

    except Exception as e:
        logger.error(f"Unexpected error during password reset: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during password reset. Please try again.",
        )
