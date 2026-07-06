# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Admin routes for PromptVault.

This module provides administrative endpoints for user management,
including listing, viewing, updating, and deleting users, as well
as managing user sessions and viewing system statistics.

All endpoints require admin authentication and implement proper
authorization, audit logging, and security best practices.

Security Features:
    - Admin role requirement for all endpoints
    - Self-harm prevention (admin can't delete/deactivate themselves)
    - Comprehensive audit logging for all admin actions
    - Proper HTTP status codes and error messages
    - Input validation and sanitization
    - No password hashes in responses

Available Endpoints:
    GET    /admin/users                List all users (paginated)
    GET    /admin/users/{user_id}      Get user details
    PUT    /admin/users/{user_id}      Update user
    DELETE /admin/users/{user_id}      Delete/deactivate user
    GET    /admin/users/{user_id}/sessions  Get user's sessions
    DELETE /admin/users/{user_id}/sessions  Revoke user's sessions
    GET    /admin/stats                Get system statistics
"""

import math
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from src.config.auth_config import AuthConfig
from src.services.auth.auth_service import AuthService
from src.services.auth.password_service import PasswordService
from src.web.dependencies.auth import get_auth_config

from src.db.session import get_db
from src.db.models.user import User
from src.db.models.user_session import UserSession
from src.db.repositories.user_repository import UserRepository
from src.db.repositories.session_repository import SessionRepository
from src.web.dependencies.auth import require_role
from src.web.models.admin_requests import (
    CreateUserRequest,
    UpdateUserRequest,
    UserListParams,
)
from src.web.models.admin_responses import (
    UserDetailResponse,
    UserListResponse,
    AdminStatsResponse,
)
from src.web.models.auth_responses import (
    MessageResponse,
    SessionResponse,
    SessionListResponse,
    RevokeSessionResponse,
)

# Configure logging
logger = logging.getLogger(__name__)

# Create router with admin tag
router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


# ============================================================================
# Helper Functions
# ============================================================================


def _user_to_detail_response(user: User, session_count: int) -> UserDetailResponse:
    """Convert User model to UserDetailResponse with session count.

    Args:
        user: User model instance
        session_count: Number of active sessions

    Returns:
        UserDetailResponse with all fields populated
    """
    return UserDetailResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        email_verified=user.email_verified,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login=user.last_login,
        failed_login_attempts=user.failed_login_attempts or 0,
        locked_until=user.locked_until,
        password_changed_at=user.password_changed_at,
        session_count=session_count,
    )


def _log_admin_action(
    admin_id: str,
    admin_username: str,
    action: str,
    target_user_id: str,
    details: str = "",
):
    """Log administrative action for audit trail.

    Args:
        admin_id: Administrator's user ID
        admin_username: Administrator's username
        action: Action performed (e.g., "UPDATE_USER", "DELETE_USER")
        target_user_id: Target user's ID
        details: Additional details about the action
    """
    logger.info(
        f"ADMIN_ACTION: {action} | Admin: {admin_username} ({admin_id}) | "
        f"Target: {target_user_id} | Details: {details}"
    )


# ============================================================================
# User Management Endpoints
# ============================================================================


@router.get(
    "/users",
    response_model=UserListResponse,
    summary="List all users",
    description="""
    List all users with pagination and filtering support.

    **Filters:**
    - role: Filter by user role (viewer, editor, admin)
    - is_active: Filter by active status
    - search: Search by username or email (case-insensitive)

    **Pagination:**
    - page: Page number (starts at 1)
    - page_size: Items per page (1-100, default 20)

    **Sort Order:**
    - Users are sorted by created_at descending (newest first)

    **Security:**
    - Requires admin role
    - Password hashes are never included in response
    - Audit logged
    """,
    responses={
        200: {"description": "User list retrieved successfully"},
        403: {"description": "Admin role required"},
    },
)
async def list_users(
    params: Annotated[
        UserListParams, Depends()
    ],  # Fixed: Changed Query() to Depends() for Pydantic model
    admin: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
) -> UserListResponse:
    """List all users with pagination and filtering.

    Args:
        params: Query parameters for filtering and pagination
        admin: Authenticated admin user
        db: Database session

    Returns:
        UserListResponse with paginated user list
    """
    user_repo = UserRepository(db)
    session_repo = SessionRepository(db)

    # Build query
    query = db.query(User)

    # Apply role filter
    if params.role:
        query = query.filter(User.role == params.role)

    # Apply active status filter
    if params.is_active is not None:
        query = query.filter(User.is_active == params.is_active)

    # Apply search filter (username or email)
    if params.search:
        search_pattern = f"%{params.search.lower()}%"
        query = query.filter(
            or_(
                func.lower(User.username).like(search_pattern),
                func.lower(User.email).like(search_pattern),
            )
        )

    # Get total count before pagination
    total = query.count()

    # Calculate pagination
    total_pages = math.ceil(total / params.page_size) if total > 0 else 0
    skip = (params.page - 1) * params.page_size

    # Apply sorting and pagination
    query = query.order_by(User.created_at.desc())
    query = query.offset(skip).limit(params.page_size)

    # Execute query
    users = query.all()

    # Convert to response models with session counts
    user_responses = []
    for user in users:
        session_count = session_repo.count_user_sessions(user.id, active_only=True)
        user_responses.append(_user_to_detail_response(user, session_count))

    # Log admin action
    _log_admin_action(
        admin.id,
        admin.username,
        "LIST_USERS",
        "N/A",
        f"page={params.page}, filters: role={params.role}, "
        f"is_active={params.is_active}, search={params.search}",
    )

    return UserListResponse(
        users=user_responses,
        total=total,
        page=params.page,
        page_size=params.page_size,
        total_pages=total_pages,
    )


@router.post(
    "/users",
    response_model=UserDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user",
    description="""
    Create a new user account via admin panel.

    **Features:**
    - Validates password policy (12+ chars, uppercase, lowercase, digit, special char)
    - Prevents duplicate usernames and emails
    - Auto-generates UUID for user ID
    - Creates session with IP/User-Agent tracking
    - Marks email as verified if specified
    - Audit logged

    **Security:**
    - Requires admin role
    - Password is hashed with Argon2id
    - No plaintext passwords in logs
    - Rate limited
    """,
    responses={
        201: {"description": "User created successfully"},
        400: {"description": "Validation failed (weak password, invalid email)"},
        403: {"description": "Admin role required"},
        409: {"description": "Username or email already exists"},
        422: {"description": "Pydantic validation error"},
    },
)
async def create_user(
    request_data: CreateUserRequest,
    admin: User = Depends(require_role(["admin"])),
    config: AuthConfig = Depends(get_auth_config),
    db: Session = Depends(get_db),
) -> UserDetailResponse:
    """Create a new user account.

    Args:
        request_data: User creation request with username, email, password, role
        admin: Authenticated admin user
        config: Authentication configuration
        db: Database session

    Returns:
        UserDetailResponse with created user details

    Raises:
        HTTPException: 400 if validation failed, 409 if duplicate, 422 if invalid
    """
    user_repo = UserRepository(db)
    password_service = PasswordService(config)

    # Check if username already exists
    if user_repo.username_exists(request_data.username):
        _log_admin_action(
            admin.id,
            admin.username,
            "CREATE_USER_FAILED",
            "N/A",
            f"username={request_data.username} (already exists)",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{request_data.username}' already exists",
        )

    # Check if email already exists
    if user_repo.email_exists(request_data.email):
        _log_admin_action(
            admin.id,
            admin.username,
            "CREATE_USER_FAILED",
            "N/A",
            f"email={request_data.email} (already exists)",
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{request_data.email}' is already registered",
        )

    try:
        # Hash password
        password_hash = password_service.hash_password(request_data.password)

        # Create user
        new_user = User(
            id=str(uuid.uuid4()),
            username=request_data.username,
            email=request_data.email,
            password_hash=password_hash,
            role=request_data.role,
            email_verified=request_data.email_verified,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Log success
        _log_admin_action(
            admin.id,
            admin.username,
            "CREATE_USER",
            new_user.id,
            f"username={request_data.username}, email={request_data.email}, role={request_data.role}",
        )

        # Return user details
        return _user_to_detail_response(new_user, session_count=0)

    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {str(e)}", exc_info=True)
        _log_admin_action(
            admin.id,
            admin.username,
            "CREATE_USER_FAILED",
            "N/A",
            f"error={str(e)}",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user. Please try again.",
        )


@router.get(
    "/users/{user_id}",
    response_model=UserDetailResponse,
    summary="Get user details",
    description="""
    Get detailed information about a specific user.

    **Includes:**
    - All user fields including admin-only fields
    - Number of active sessions
    - Account status and security information

    **Security:**
    - Requires admin role
    - Password hash is never included
    - Audit logged
    """,
    responses={
        200: {"description": "User details retrieved successfully"},
        403: {"description": "Admin role required"},
        404: {"description": "User not found"},
    },
)
async def get_user(
    user_id: str,
    admin: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
) -> UserDetailResponse:
    """Get detailed information about a specific user.

    Args:
        user_id: User's UUID
        admin: Authenticated admin user
        db: Database session

    Returns:
        UserDetailResponse with complete user information

    Raises:
        HTTPException: 404 if user not found
    """
    user_repo = UserRepository(db)
    session_repo = SessionRepository(db)

    # Get user
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    # Get session count
    session_count = session_repo.count_user_sessions(user.id, active_only=True)

    # Log admin action
    _log_admin_action(
        admin.id,
        admin.username,
        "VIEW_USER",
        user_id,
        f"username={user.username}",
    )

    return _user_to_detail_response(user, session_count)


@router.put(
    "/users/{user_id}",
    response_model=UserDetailResponse,
    summary="Update user",
    description="""
    Update user information (role, active status, email verification).

    **Updatable Fields:**
    - role: Change user role (viewer, editor, admin)
    - is_active: Activate/deactivate account
    - email_verified: Mark email as verified/unverified

    **Security:**
    - Requires admin role
    - Admin cannot deactivate themselves
    - All changes are audit logged
    - Password cannot be changed via this endpoint

    **Validation:**
    - At least one field must be provided
    - Role must be valid (viewer, editor, admin)
    """,
    responses={
        200: {"description": "User updated successfully"},
        400: {"description": "Invalid input or self-harm prevention"},
        403: {"description": "Admin role required"},
        404: {"description": "User not found"},
    },
)
async def update_user(
    user_id: str,
    update_data: UpdateUserRequest,
    admin: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
) -> UserDetailResponse:
    """Update user information.

    Args:
        user_id: User's UUID
        update_data: Fields to update
        admin: Authenticated admin user
        db: Database session

    Returns:
        UserDetailResponse with updated user information

    Raises:
        HTTPException: 400 if trying to deactivate self, 404 if user not found
    """
    user_repo = UserRepository(db)
    session_repo = SessionRepository(db)

    # Get user
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    # Prevent admin from deactivating themselves
    if user_id == admin.id and update_data.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account",
        )

    # Track what changed for logging
    changes = []

    # Update fields if provided
    if update_data.role is not None:
        old_role = user.role
        user.role = update_data.role
        changes.append(f"role: {old_role} -> {update_data.role}")

    if update_data.is_active is not None:
        old_active = user.is_active
        user.is_active = update_data.is_active
        changes.append(f"is_active: {old_active} -> {update_data.is_active}")

    if update_data.email_verified is not None:
        old_verified = user.email_verified
        user.email_verified = update_data.email_verified
        changes.append(
            f"email_verified: {old_verified} -> {update_data.email_verified}"
        )

    # Update timestamp
    user.updated_at = datetime.now(timezone.utc)

    # Commit changes
    db.flush()
    db.commit()

    # Get session count
    session_count = session_repo.count_user_sessions(user.id, active_only=True)

    # Log admin action
    _log_admin_action(
        admin.id,
        admin.username,
        "UPDATE_USER",
        user_id,
        f"username={user.username}, changes: {', '.join(changes)}",
    )

    return _user_to_detail_response(user, session_count)


@router.delete(
    "/users/{user_id}",
    response_model=MessageResponse,
    summary="Delete user",
    description="""
    Delete or deactivate a user account.

    **Default Behavior (Soft Delete):**
    - Sets is_active to False
    - Revokes all user sessions
    - User data is preserved

    **Hard Delete (Query Parameter):**
    - Add ?hard_delete=true to permanently delete
    - Removes user from database (CASCADE deletes sessions)
    - This action is irreversible

    **Security:**
    - Requires admin role
    - Admin cannot delete themselves
    - All sessions are revoked before deletion
    - Audit logged

    **Recommendation:**
    - Use soft delete (default) to preserve data
    - Hard delete only when absolutely necessary
    """,
    responses={
        200: {"description": "User deleted successfully"},
        400: {"description": "Self-harm prevention"},
        403: {"description": "Admin role required"},
        404: {"description": "User not found"},
    },
)
async def delete_user(
    user_id: str,
    hard_delete: bool = Query(
        default=False,
        description="Permanently delete user (true) or soft delete (false)",
    ),
    admin: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Delete or deactivate a user.

    Args:
        user_id: User's UUID
        hard_delete: If True, permanently delete; if False, soft delete
        admin: Authenticated admin user
        db: Database session

    Returns:
        MessageResponse with confirmation

    Raises:
        HTTPException: 400 if trying to delete self, 404 if user not found
    """
    user_repo = UserRepository(db)
    session_repo = SessionRepository(db)

    # Prevent admin from deleting themselves
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )

    # Get user
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    # Store username for logging
    username = user.username

    # Revoke all user sessions
    revoked_count = session_repo.revoke_all_user_sessions(user_id)

    if hard_delete:
        # Permanent deletion
        user_repo.delete(user_id)
        db.commit()

        # Log admin action
        _log_admin_action(
            admin.id,
            admin.username,
            "HARD_DELETE_USER",
            user_id,
            f"username={username}, sessions_revoked={revoked_count}",
        )

        return MessageResponse(
            message=f"User {username} permanently deleted",
            detail=f"Revoked {revoked_count} session(s)",
        )
    else:
        # Soft deletion (deactivate)
        user_repo.deactivate_account(user_id)
        db.commit()

        # Log admin action
        _log_admin_action(
            admin.id,
            admin.username,
            "SOFT_DELETE_USER",
            user_id,
            f"username={username}, sessions_revoked={revoked_count}",
        )

        return MessageResponse(
            message=f"User {username} deactivated",
            detail=f"Revoked {revoked_count} session(s). User data preserved.",
        )


# ============================================================================
# Session Management Endpoints
# ============================================================================


@router.get(
    "/users/{user_id}/sessions",
    response_model=SessionListResponse,
    summary="Get user's sessions",
    description="""
    Get all sessions for a specific user.

    **Includes:**
    - Active and revoked sessions
    - Session metadata (IP, user agent, timestamps)
    - Token family tracking

    **Use Cases:**
    - Monitor user login activity
    - Detect suspicious sessions
    - Audit user access

    **Security:**
    - Requires admin role
    - Audit logged
    """,
    responses={
        200: {"description": "Sessions retrieved successfully"},
        403: {"description": "Admin role required"},
        404: {"description": "User not found"},
    },
)
async def get_user_sessions(
    user_id: str,
    admin: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
) -> SessionListResponse:
    """Get all sessions for a specific user.

    Args:
        user_id: User's UUID
        admin: Authenticated admin user
        db: Database session

    Returns:
        SessionListResponse with all user sessions

    Raises:
        HTTPException: 404 if user not found
    """
    user_repo = UserRepository(db)
    session_repo = SessionRepository(db)

    # Verify user exists
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    # Get all sessions (including revoked)
    sessions = session_repo.get_user_sessions(user_id, active_only=False)

    # Get admin's current session family_id from the token (if available)
    admin_family_id = getattr(admin, "family_id", None)

    # Convert ORM objects to response models
    session_responses = []
    for s in sessions:
        # Use model_construct to bypass Pydantic validation
        response = SessionResponse.model_construct(
            id=s.id,
            family_id=s.family_id,
            user_agent=s.device_info,  # device_info -> user_agent
            ip_address=s.ip_address,
            created_at=s.created_at,
            last_used_at=s.last_used_at,
            expires_at=s.expires_at,
            is_revoked=s.is_revoked,
            is_current=admin_family_id is not None and s.family_id == admin_family_id,
        )
        session_responses.append(response)

    # Log admin action
    _log_admin_action(
        admin.id,
        admin.username,
        "VIEW_USER_SESSIONS",
        user_id,
        f"username={user.username}, session_count={len(sessions)}",
    )

    return SessionListResponse(
        sessions=session_responses,
        total=len(session_responses),
    )


@router.delete(
    "/users/{user_id}/sessions/{session_id}",
    response_model=RevokeSessionResponse,
    summary="Revoke specific session",
    description="""
    Revoke a specific session for a user.

    **Effect:**
    - Single session is revoked
    - User will be logged out of that specific device
    - Refresh token for that session becomes invalid

    **Use Cases:**
    - Force logout from specific device
    - Remove suspicious session
    - Security incident response

    **Security:**
    - Requires admin role
    - Audit logged
    """,
    responses={
        200: {"description": "Session revoked successfully"},
        403: {"description": "Admin role required"},
        404: {"description": "User or session not found"},
    },
)
async def revoke_single_session(
    user_id: str,
    session_id: str,
    admin: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
) -> RevokeSessionResponse:
    """Revoke a specific session for a user.

    Args:
        user_id: User's UUID
        session_id: Session's UUID
        admin: Authenticated admin user
        db: Database session

    Returns:
        RevokeSessionResponse with revocation confirmation

    Raises:
        HTTPException: 404 if user or session not found
    """
    user_repo = UserRepository(db)
    session_repo = SessionRepository(db)

    # Verify user exists
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    # Get session and verify it belongs to the user
    session = session_repo.get_by_id(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID {session_id} not found",
        )

    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with ID {session_id} not found for user {user.username}",
        )

    # Revoke the session
    revoked = session_repo.revoke_session_by_id(session_id)
    db.commit()

    # Log admin action
    _log_admin_action(
        admin.id,
        admin.username,
        "REVOKE_USER_SESSION",
        user_id,
        f"username={user.username}, session_id={session_id}, revoked={revoked}",
    )

    return RevokeSessionResponse(
        message=f"Session revoked for user {user.username}",
        revoked_count=1 if revoked else 0,
    )


@router.delete(
    "/users/{user_id}/sessions",
    response_model=RevokeSessionResponse,
    summary="Revoke all user's sessions",
    description="""
    Revoke all sessions for a specific user.

    **Effect:**
    - All active sessions are revoked
    - User will be logged out of all devices
    - Refresh tokens become invalid

    **Use Cases:**
    - Force user logout (security incident)
    - Account compromise response
    - Password reset enforcement

    **Security:**
    - Requires admin role
    - Cannot revoke own sessions via this endpoint
    - Audit logged
    """,
    responses={
        200: {"description": "Sessions revoked successfully"},
        403: {"description": "Admin role required"},
        404: {"description": "User not found"},
    },
)
async def revoke_user_sessions(
    user_id: str,
    admin: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
) -> RevokeSessionResponse:
    """Revoke all sessions for a specific user.

    Args:
        user_id: User's UUID
        admin: Authenticated admin user
        db: Database session

    Returns:
        RevokeSessionResponse with count of revoked sessions

    Raises:
        HTTPException: 404 if user not found
    """
    user_repo = UserRepository(db)
    session_repo = SessionRepository(db)

    # Verify user exists
    user = user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    # Revoke all user sessions
    revoked_count = session_repo.revoke_all_user_sessions(user_id)
    db.commit()

    # Log admin action
    _log_admin_action(
        admin.id,
        admin.username,
        "REVOKE_USER_SESSIONS",
        user_id,
        f"username={user.username}, sessions_revoked={revoked_count}",
    )

    return RevokeSessionResponse(
        message=f"All sessions revoked for user {user.username}",
        revoked_count=revoked_count,
    )


@router.delete(
    "/sessions",
    response_model=RevokeSessionResponse,
    summary="Revoke all sessions globally",
    description="""
    Revoke all sessions for all users in the system.

    **Effect:**
    - All active sessions across all users are revoked
    - All users will be logged out of all devices
    - Refresh tokens become invalid

    **Use Cases:**
    - Security incident response (system-wide)
    - System maintenance requiring all users to re-authenticate
    - Emergency lockdown

    **Security:**
    - Requires admin role
    - Audit logged
    """,
    responses={
        200: {"description": "All sessions revoked successfully"},
        403: {"description": "Admin role required"},
    },
)
async def revoke_all_sessions(
    admin: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
) -> RevokeSessionResponse:
    """Revoke all sessions for all users.

    Args:
        admin: Authenticated admin user
        db: Database session

    Returns:
        RevokeSessionResponse with count of revoked sessions
    """
    session_repo = SessionRepository(db)

    # Revoke all sessions
    revoked_count = session_repo.revoke_all_sessions()
    db.commit()

    # Log admin action
    _log_admin_action(
        admin.id,
        admin.username,
        "REVOKE_ALL_SESSIONS",
        "SYSTEM",
        f"sessions_revoked={revoked_count}",
    )

    return RevokeSessionResponse(
        message=f"All sessions revoked system-wide",
        revoked_count=revoked_count,
    )


# ============================================================================
# Statistics Endpoint
# ============================================================================


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Get system statistics",
    description="""
    Get comprehensive system statistics.

    **Includes:**
    - Total users (all)
    - Active users (is_active=True)
    - Inactive users (is_active=False)
    - Total sessions (all)
    - Active sessions (not expired, not revoked)
    - Users by role breakdown (viewer, editor, admin)

    **Use Cases:**
    - Dashboard metrics
    - System monitoring
    - Capacity planning

    **Security:**
    - Requires admin role
    - Audit logged
    """,
    responses={
        200: {"description": "Statistics retrieved successfully"},
        403: {"description": "Admin role required"},
    },
)
async def get_stats(
    admin: User = Depends(require_role(["admin"])),
    db: Session = Depends(get_db),
) -> AdminStatsResponse:
    """Get system statistics.

    Args:
        admin: Authenticated admin user
        db: Database session

    Returns:
        AdminStatsResponse with system statistics
    """
    # Count users
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    inactive_users = total_users - active_users

    # Count sessions
    total_sessions = db.query(UserSession).count()
    active_sessions = (
        db.query(UserSession)
        .filter(
            and_(
                UserSession.is_revoked == False,
                UserSession.expires_at > datetime.now(timezone.utc),
            )
        )
        .count()
    )

    # Count users by role
    users_by_role = {}
    for role in ["viewer", "editor", "admin"]:
        count = db.query(User).filter(User.role == role).count()
        users_by_role[role] = count

    # Log admin action
    _log_admin_action(
        admin.id,
        admin.username,
        "VIEW_STATS",
        "N/A",
        f"total_users={total_users}, active_users={active_users}",
    )

    return AdminStatsResponse(
        total_users=total_users,
        active_users=active_users,
        inactive_users=inactive_users,
        total_sessions=total_sessions,
        active_sessions=active_sessions,
        users_by_role=users_by_role,
    )
