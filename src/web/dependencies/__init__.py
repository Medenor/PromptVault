# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""FastAPI dependencies for PromptVault.

This package contains reusable dependency functions for FastAPI route handlers,
providing authentication, authorization, and request context utilities.
"""

from src.web.dependencies.auth import (
    # Composite dependencies
    get_admin_user,
    # Configuration
    get_auth_config,
    # Request metadata
    get_client_ip,
    get_current_active_user,
    get_current_user,
    # Authentication
    get_current_user_token,
    get_editor_or_admin_user,
    get_jwt_service,
    get_optional_user,
    get_user_agent,
    # Authorization (RBAC)
    require_role,
    require_verified_email,
)
from src.web.dependencies.undo import (
    get_undo_service,
)

__all__ = [
    # Configuration
    "get_auth_config",
    "get_jwt_service",
    # Authentication
    "get_current_user_token",
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
    # Services
    "get_undo_service",
]
