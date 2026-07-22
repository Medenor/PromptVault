# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Admin global session and statistics routes for PromptVault.

This module provides administrative endpoints that operate across the whole
system rather than a single user: revoking every session globally and
reading aggregate system statistics.

All endpoints require admin authentication and implement proper
authorization and audit logging.

Available Endpoints:
    DELETE /admin/sessions             Revoke all sessions globally
    GET    /admin/stats                Get system statistics
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from sqlalchemy import and_

from src.db.session import get_db
from src.db.models.user import User
from src.db.models.user_session import UserSession
from src.db.repositories.session_repository import SessionRepository
from src.web.dependencies.auth import require_role
from src.web.models.admin_responses import AdminStatsResponse
from src.web.models.auth_responses import RevokeSessionResponse
from src.web.routers.admin_shared import _log_admin_action

# Configure logging
logger = logging.getLogger(__name__)

# Create router with admin tag
router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


# ============================================================================
# Global Session Management Endpoint
# ============================================================================


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
