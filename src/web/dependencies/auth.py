# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""FastAPI dependency functions for authentication and authorization.

This module re-exports the authentication/authorization dependencies that
used to live here directly. The implementation is now split across:

    - :mod:`src.web.dependencies.token` — config, JWT extraction/validation,
      user-retrieval dependencies (get_current_user, get_current_active_user,
      get_optional_user, etc.)
    - :mod:`src.web.dependencies.roles` — RBAC (require_role,
      require_verified_email, get_admin_user, get_editor_or_admin_user)
    - :mod:`src.web.dependencies.request_context` — client IP / User-Agent
      extraction
    - :mod:`src.web.dependencies.bypass` — AUTH_ENABLED=false bypass variants

This module is kept as a compatibility re-export so existing imports
(``from src.web.dependencies.auth import ...``) across routers, ``app.py``,
and tests continue to work unchanged.

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
"""

from src.web.dependencies.bypass import (
    get_admin_or_bypass,
    get_current_user_or_default,
    get_current_user_or_none,
    get_editor_or_admin_or_bypass,
    get_user_or_bypass,
    has_valid_auth_cookie,
    require_role_or_bypass,
)
from src.web.dependencies.request_context import (
    get_client_ip,
    get_user_agent,
)
from src.web.dependencies.roles import (
    get_admin_user,
    get_editor_or_admin_user,
    require_role,
    require_verified_email,
)
from src.web.dependencies.token import (
    get_auth_config,
    get_current_active_user,
    get_current_user,
    get_current_user_token,
    get_jwt_service,
    get_optional_user,
)

__all__ = [
    # Configuration
    "get_auth_config",
    "get_jwt_service",
    # Token extraction/validation
    "get_current_user_token",
    # User retrieval
    "get_current_user",
    "get_current_active_user",
    "get_optional_user",
    # Authorization (RBAC)
    "require_role",
    "require_verified_email",
    # Request metadata
    "get_client_ip",
    "get_user_agent",
    # Composite dependencies
    "get_admin_user",
    "get_editor_or_admin_user",
    # Anonymous-mode bypass dependencies
    "get_current_user_or_none",
    "get_current_user_or_default",
    "require_role_or_bypass",
    "get_user_or_bypass",
    "has_valid_auth_cookie",
    "get_admin_or_bypass",
    "get_editor_or_admin_or_bypass",
]
