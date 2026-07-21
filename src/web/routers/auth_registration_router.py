# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Authentication registration router.

Split out from the original ``auth.py`` god-file. Contains the account
registration endpoint. Route path, method, status code, tags, and behavior are
unchanged.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.web.dependencies.auth import (
    get_client_ip,
    get_user_agent,
)
from src.web.models.auth_requests import RegisterRequest
from src.web.models.auth_responses import TokenResponse, UserResponse
from src.services.auth.auth_service import AuthService
from src.services.exceptions import (
    EmailAlreadyExistsError,
    UsernameAlreadyExistsError,
    PasswordPolicyError,
)
from src.web.middleware.rate_limit import (
    limiter,
    auth_register_limit,
)
from src.web.routers.auth_shared import get_auth_service

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
@limiter.limit(auth_register_limit)
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

        user_payload = result["user"]
        user_response = UserResponse.model_validate(user_payload)
        username = getattr(user_payload, "username", None) or user_payload.get(
            "username", "unknown"
        )
        user_id = getattr(user_payload, "id", None) or user_payload.get("id", "unknown")

        # Log successful registration (without sensitive data)
        logger.info(
            f"User registered successfully: {user_response.username} "
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
        from fastapi.responses import JSONResponse

        json_response = JSONResponse(content=response.model_dump(mode="json"))

        # Use default refresh token lifetime for registration (7 days)
        register_cookie_max_age = auth_service.config.jwt_refresh_token_expire_seconds

        # Set access token cookie with same lifetime as refresh token
        # The JWT inside expires in 15 min, but the cookie persists so
        # the frontend can refresh it automatically when it expires
        json_response.set_cookie(
            key="access_token",
            value=result["access_token"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=register_cookie_max_age,  # Match refresh token lifetime
            path="/",
        )

        # Set refresh token cookie (7 days)
        json_response.set_cookie(
            key="refresh_token",
            value=result["refresh_token"],
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite="lax",
            max_age=register_cookie_max_age,
            path="/api/auth",
        )

        # Set status code to 201 for successful registration
        json_response.status_code = status.HTTP_201_CREATED

        return json_response

    except EmailAlreadyExistsError as e:
        logger.warning(f"Registration failed - email exists: {request_data.email}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.user_message,
        )

    except UsernameAlreadyExistsError as e:
        logger.warning(
            f"Registration failed - username exists: {request_data.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.user_message,
        )

    except PasswordPolicyError as e:
        logger.warning(
            f"Registration failed - password policy violation for user: {request_data.username}"
        )
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
