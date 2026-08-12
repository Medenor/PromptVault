# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Authentication password router.

Split out from the original ``auth.py`` god-file. Contains the change-password
and password-reset endpoints. Route paths, methods, status codes, tags, and
behavior are unchanged.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from src.db.models.user import User
from src.db.session import get_db
from src.services.auth.auth_service import AuthService
from src.services.auth.password_reset_service import PasswordResetService
from src.services.exceptions import (
    InvalidCredentialsError,
    PasswordPolicyError,
    RateLimitExceededError,
    TokenAlreadyUsedError,
    TokenExpiredError,
    TokenNotFoundError,
    UserNotFoundError,
)
from src.web.dependencies.auth import (
    get_client_ip,
    get_current_active_user,
)
from src.web.middleware.rate_limit import (
    limiter,
    password_reset_limit,
)
from src.web.models.auth_requests import (
    ChangePasswordRequest,
    PasswordResetConfirmRequest,
    PasswordResetRequestRequest,
)
from src.web.models.auth_responses import (
    MessageResponse,
    PasswordResetRequestResponse,
)
from src.web.routers.auth_shared import get_auth_service, get_password_reset_service

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

        logger.info(
            f"Password changed successfully for user: {current_user.username} (ID: {current_user.id})"
        )

        return MessageResponse(
            message="Password changed successfully",
            detail="Your password has been updated. All sessions remain active.",
        )

    except InvalidCredentialsError as e:
        logger.warning(
            f"Password change failed - incorrect old password for user: {current_user.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        ) from e

    except PasswordPolicyError as e:
        logger.warning(
            f"Password change failed - policy violation for user: {current_user.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.user_message,
        ) from e

    except Exception as e:
        logger.error(
            f"Unexpected error during password change: {str(e)}", exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while changing password. Please try again.",
        ) from e


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
@limiter.limit(password_reset_limit)
def request_password_reset(
    request: Request,
    request_data: PasswordResetRequestRequest,
    ip_address: str = Depends(get_client_ip),
    password_reset_service: PasswordResetService = Depends(get_password_reset_service),
    session: Session = Depends(get_db),
) -> Response:
    """Request password reset email.

    Args:
        request: FastAPI request object (for rate limiting)
        request_data: Email address for password reset
        ip_address: Client IP address (injected)
        password_reset_service: Password reset service instance (injected)

    Returns:
        PasswordResetRequestResponse: Success message with masked email
    """
    from fastapi.responses import JSONResponse

    def build_response(masked_email: str) -> JSONResponse:
        payload = PasswordResetRequestResponse(
            message="If an account exists with this email, a password reset link has been sent.",
            email=masked_email,
        )
        return JSONResponse(content=payload.model_dump(mode="json"))

    try:
        masked_email = password_reset_service.request_password_reset(
            email=request_data.email,
            ip_address=ip_address,
        )
        email_parts = masked_email.split("@")
        if len(email_parts) == 2 and email_parts[0]:
            masked_email = f"{email_parts[0][0]}***@{email_parts[1]}"
        else:
            masked_email = "***@***"

        logger.info(
            f"Password reset requested for email: {masked_email} from {ip_address}"
        )

        # Commit the session to persist the password reset token
        session.commit()

        return build_response(masked_email)

    except UserNotFoundError:
        logger.info(
            f"Password reset requested for non-existent email: {request_data.email}"
        )
        email_parts = request_data.email.split("@")
        masked_email = (
            f"{email_parts[0][0]}***@{email_parts[1]}"
            if len(email_parts) == 2
            else "***@***"
        )
        return build_response(masked_email)

    except RateLimitExceededError:
        logger.warning(
            f"Password reset rate limit exceeded for: {request_data.email} from {ip_address}"
        )
        email_parts = request_data.email.split("@")
        masked_email = (
            f"{email_parts[0][0]}***@{email_parts[1]}"
            if len(email_parts) == 2
            else "***@***"
        )
        return build_response(masked_email)

    except Exception as e:
        logger.error(
            f"Unexpected error during password reset request: {str(e)}", exc_info=True
        )
        email_parts = request_data.email.split("@")
        masked_email = (
            f"{email_parts[0][0]}***@{email_parts[1]}"
            if len(email_parts) == 2
            else "***@***"
        )
        return build_response(masked_email)


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
    session: Session = Depends(get_db),
) -> MessageResponse:
    """Confirm password reset with token.

    Args:
        request_data: Reset token and new password
        password_reset_service: Password reset service instance (injected)
        session: Database session (injected)

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

        # Commit the session to persist password and token changes
        session.commit()

        logger.info("Password reset successfully completed using token")

        return MessageResponse(
            message="Password reset successful",
            detail="Your password has been updated. You can now login with your new password.",
        )

    except (TokenExpiredError, TokenAlreadyUsedError, TokenNotFoundError) as e:
        logger.warning(f"Password reset failed - invalid token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.user_message,
        ) from e

    except PasswordPolicyError as e:
        logger.warning("Password reset failed - policy violation")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.user_message,
        ) from e

    except UserNotFoundError as e:
        logger.error("Password reset failed - user not found (orphaned token)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid password reset token. Please request a new one.",
        ) from e

    except Exception as e:
        logger.error(f"Unexpected error during password reset: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during password reset. Please try again.",
        ) from e
