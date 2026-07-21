# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""FastAPI authentication router (aggregation module).

The endpoint implementations were split into four focused modules to keep each
file small and single-responsibility:

- ``auth_registration_router`` — ``POST /auth/register``
- ``auth_session_router`` — login / refresh / logout / current-user / sessions
- ``auth_password_router`` — change-password / password-reset request+confirm
- ``auth_profile_router`` — profile update / account statistics

Shared dependency-injection providers (``get_auth_service``,
``get_password_reset_service``, ``get_jwt_service``) live in ``auth_shared``.

The aggregated ``router`` is exported unchanged so ``routers.__init__`` keeps
importing ``from src.web.routers.auth import router as auth_router`` and
``app.py``'s ``include_router(auth_router, prefix="/api")`` is unaffected — same
prefix, paths, tags, and per-route metadata.

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
        PATCH /auth/me - Update user profile
        GET /auth/me/stats - Get account statistics
        POST /auth/change-password - Change user password
        GET /auth/sessions - List user's active sessions
        DELETE /auth/sessions/{session_id} - Revoke specific session
        DELETE /auth/sessions - Revoke all sessions except current
"""

from fastapi import APIRouter

from src.web.routers.auth_registration_router import router as _registration_router
from src.web.routers.auth_session_router import router as _session_router
from src.web.routers.auth_password_router import router as _password_router
from src.web.routers.auth_profile_router import router as _profile_router

# Re-export shared DI providers for backward compatibility with any code that
# imported them from this module.
from src.web.routers.auth_shared import (  # noqa: F401
    get_auth_service,
    get_password_reset_service,
    get_jwt_service,
)

# Aggregate the split routers into a single router exported as ``router``.
#
# The sub-routers already carry the ``/auth`` prefix and the ``Authentication``
# tag, so this aggregator has no prefix of its own. app.py mounts this router
# under ``/api``, yielding the original ``/api/auth/*`` paths.
#
# All auth endpoints occupy distinct path + method combinations, so include
# order does not affect route matching.
router = APIRouter()
router.include_router(_registration_router)
router.include_router(_session_router)
router.include_router(_password_router)
router.include_router(_profile_router)
