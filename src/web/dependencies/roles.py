# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Role-based access control (RBAC) dependencies.

This module provides dependency factories and composite dependencies that
enforce role requirements on top of the base authentication dependencies in
:mod:`src.web.dependencies.token`.

Dependencies:
    - require_role(): Creates role-based access control dependency
    - require_verified_email(): Requires email verification
    - get_admin_user(): Requires admin role
    - get_editor_or_admin_user(): Requires editor or admin role

Security Features:
    - Role-based access control (RBAC)
    - Email verification enforcement
    - Proper HTTP status codes (403)
"""

from typing import Callable
from fastapi import Depends, HTTPException, status

from src.db.models.user import User
from src.web.dependencies.token import get_current_active_user, get_current_user

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
    return require_role(["admin"])(user)


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
    return require_role(["admin", "editor"])(user)
