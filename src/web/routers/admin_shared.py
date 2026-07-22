# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared helpers for the admin routers.

These helpers were extracted verbatim from the original ``admin.py`` module
so that the user-administration and session/stats routers can share them
without duplication. Behavior is unchanged.
"""

import logging

from src.db.models.user import User
from src.web.models.admin_responses import UserDetailResponse

# Configure logging
logger = logging.getLogger(__name__)


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
