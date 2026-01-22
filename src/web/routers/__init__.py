# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""FastAPI routers package for PromptVault API endpoints."""

from src.web.routers.auth import router as auth_router
from src.web.routers.admin import router as admin_router
from src.web.routers.prompts import router as prompts_router
from src.web.routers.tag_category import router as tag_category_router
from src.web.routers.pages import router as pages_router

__all__ = [
    "auth_router",
    "admin_router",
    "prompts_router",
    "tag_category_router",
    "pages_router",
]
