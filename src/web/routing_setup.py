# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Router registration for the PromptVault FastAPI app.

Centralizes every `app.include_router(...)` call so the mount order and
prefixes are visible in one place, separate from app construction
(`factory.py`) and middleware wiring (`middleware_setup.py`).
"""

from fastapi import FastAPI

from src.config.auth_config import auth_settings
from src.services.logging_service import logging_service
from src.web.routers import (
    auth_router,
    admin_router,
    prompts_router,
    prompts_versions_router,
    import_export_router,
    tag_category_router,
    pages_router,
)
from src.web.routers.scheduler import router as scheduler_router
from src.web.routers.backup import router as backup_router

logger = logging_service.get_logger(__name__)


def _warn_if_auth_disabled() -> None:
    """Emit a loud startup warning when authentication is disabled.

    Extracted as a helper so it can be exercised by the test suite.
    """
    if not auth_settings.auth_enabled:
        logger.warning(
            "AUTH_ENABLED=false — Authentication is DISABLED. All endpoints are "
            "publicly accessible. Do NOT use this mode in a multi-user or "
            "network-exposed deployment."
        )


def configure_routing(app: FastAPI) -> None:
    """Register all API and page routers on `app`.

    - /api/auth - Authentication endpoints (public + protected)
    - /api/admin - Admin endpoints (admin role required)
    - /api/admin/scheduler - Scheduler management endpoints (admin role required)
    - /api/prompts - Prompt CRUD with authentication

    Authentication and admin routers are only mounted when auth is enabled.
    When AUTH_ENABLED=false the app runs in anonymous mode and these routes
    are unmounted (return 404).
    """
    app.include_router(prompts_router, prefix="/api")
    app.include_router(prompts_versions_router, prefix="/api")
    app.include_router(import_export_router, prefix="/api")
    app.include_router(tag_category_router, prefix="/api")
    app.include_router(scheduler_router, prefix="/api")
    app.include_router(backup_router)

    if auth_settings.auth_enabled:
        app.include_router(auth_router, prefix="/api")
        app.include_router(admin_router, prefix="/api")
        logger.info(
            "Authentication enabled: /api/auth and /api/admin routes registered"
        )
    else:
        _warn_if_auth_disabled()
        print(
            "⚠ AUTH_ENABLED=false — Authentication is DISABLED. All endpoints are "
            "publicly accessible."
        )

    # Register HTML page routes (no /api prefix)
    # - /auth/* - Authentication pages (login, register, profile, etc.)
    # - /admin/* - Admin pages (users, sessions)
    app.include_router(pages_router)

    logger.info(
        "API routers registered: /api/auth, /api/admin, /api/prompts, /api/categories, /api/tags"
    )
    logger.info("HTML page routes registered: /auth/*, /admin/*")
