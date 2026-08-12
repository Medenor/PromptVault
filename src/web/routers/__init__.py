# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""FastAPI routers package for PromptVault API endpoints."""

from src.web.routers.admin_sessions_router import router as admin_sessions_router
from src.web.routers.admin_users_router import router as admin_users_router
from src.web.routers.auth import router as auth_router
from src.web.routers.import_export_router import router as import_export_router
from src.web.routers.pages import router as pages_router
from src.web.routers.prompts import router as prompts_router
from src.web.routers.prompts_sharing_router import router as prompts_sharing_router
from src.web.routers.prompts_versions_router import router as prompts_versions_router
from src.web.routers.tag_category import router as tag_category_router
from src.web.routers.users_router import router as users_router

__all__ = [
    "auth_router",
    "admin_users_router",
    "admin_sessions_router",
    "prompts_router",
    "prompts_versions_router",
    "prompts_sharing_router",
    "users_router",
    "import_export_router",
    "tag_category_router",
    "pages_router",
]
