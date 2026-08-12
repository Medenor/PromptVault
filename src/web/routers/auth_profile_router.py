# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Authentication profile router.

Split out from the original ``auth.py`` god-file. Contains the profile-update
and account-statistics endpoints. Route paths, methods, status codes, tags, and
behavior are unchanged.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from src.db.models.user import User
from src.services.auth.auth_service import AuthService
from src.services.exceptions import (
    EmailAlreadyExistsError,
    UserNotFoundError,
)
from src.web.dependencies.auth import get_current_active_user
from src.web.models.auth_requests import UpdateProfileRequest
from src.web.models.auth_responses import (
    UserResponse,
    UserStatsResponse,
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


@router.patch(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user profile",
    description="""
    Update authenticated user's profile information.

    This endpoint:
    - Updates display name (1-200 characters)
    - Updates email address (must be unique)
    - Validates at least one field is provided
    - Resets email verification if email changes
    - Prevents duplicate emails

    Profile Fields:
    - display_name: User's full name or display name
    - email: Email address (must be unique across all users)

    Security Notes:
    - Requires valid access token
    - Email must be unique (cannot be taken by another user)
    - Email verification is reset when email is changed
    - Consider requiring email re-verification after email change
    - User can only update their own profile
    """,
    responses={
        200: {
            "description": "Profile updated successfully",
            "model": UserResponse,
        },
        400: {
            "description": "Validation error (invalid email or no fields provided)",
        },
        401: {
            "description": "Invalid or expired access token",
        },
        409: {
            "description": "Email already in use by another user",
        },
    },
)
def update_profile(
    request_data: UpdateProfileRequest,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Update user profile.

    Args:
        request_data: Profile update request (display_name, email)
        current_user: Authenticated active user (injected)
        auth_service: Authentication service instance (injected)

    Returns:
        UserResponse: Updated user profile

    Raises:
        HTTPException: 409 if email already in use, 400 for validation errors
    """
    try:
        updated_user = auth_service.update_user_profile(
            user_id=current_user.id,
            display_name=request_data.display_name,
            email=request_data.email,
        )

        logger.info(
            f"Profile updated for user: {current_user.username} (ID: {current_user.id})"
        )

        return UserResponse.model_validate(updated_user)

    except EmailAlreadyExistsError as e:
        logger.warning(
            f"Profile update failed - email already exists: {request_data.email}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=e.user_message,
        ) from e

    except UserNotFoundError as e:
        logger.error(f"Profile update failed - user not found: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.user_message,
        ) from e

    except Exception as e:
        logger.error(f"Unexpected error during profile update: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating profile. Please try again.",
        ) from e


@router.get(
    "/me/stats",
    response_model=UserStatsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get account statistics",
    description="""
    Get detailed statistics for authenticated user's account.

    This endpoint returns comprehensive account information including:

    Account Information:
    - Account creation date and age (in days)
    - Last login timestamp and days since
    - Password change history

    Session Information:
    - Number of currently active sessions
    - Total number of sessions (including revoked)
    - Helps identify suspicious activity

    Security Status:
    - Account lockout status
    - Failed login attempts counter
    - Lockout expiration time (if locked)

    Use Cases:
    - Users monitor account security
    - Identify unauthorized sessions
    - Track login activity
    - Security audit trail viewing

    Security Notes:
    - Requires valid access token
    - User can only view their own statistics
    - Helps detect compromised accounts
    - Useful for security-conscious users
    """,
    responses={
        200: {
            "description": "Statistics retrieved successfully",
            "model": UserStatsResponse,
        },
        401: {
            "description": "Invalid or expired access token",
        },
    },
)
def get_user_stats(
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserStatsResponse:
    """Get account statistics for current user.

    Args:
        current_user: Authenticated active user (injected)
        auth_service: Authentication service instance (injected)

    Returns:
        UserStatsResponse: Detailed account statistics

    Raises:
        HTTPException: 500 if unexpected error occurs
    """
    try:
        stats = auth_service.get_user_stats(user_id=current_user.id)

        logger.info(f"Stats retrieved for user: {current_user.username}")

        return UserStatsResponse(**stats)

    except UserNotFoundError as e:
        logger.error(f"Stats retrieval failed - user not found: {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.user_message,
        ) from e

    except Exception as e:
        logger.error(f"Error retrieving user stats: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while retrieving statistics. Please try again.",
        ) from e
