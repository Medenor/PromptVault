# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Prompt routes for PromptVault with authentication and authorization.

This module is the aggregation point for the prompt routers. The endpoint
implementations were split across two focused modules to keep each file small:

- ``prompts_search_router`` — public read/search endpoints
  (``GET /prompts`` and ``GET /prompts/search``)
- ``prompts_crud_router`` — CRUD endpoints (get / create / update / delete /
  bulk-delete / favorite / copy-with-version)

Shared helper functions live in ``prompts_shared``.

The aggregated ``router`` is exported unchanged so callers (``routers.__init__``
and ``app.py``) keep importing ``from src.web.routers.prompts import router``.

Security Model:
    - Public Read: List and view prompts (optional auth for personalization)
    - Authenticated Write: Create prompts (any authenticated user)
    - Owner or Admin: Update and delete prompts
    - Admin Only: Bulk operations, hard deletes

Available Endpoints:
    GET    /prompts              List prompts (public, personalized if auth)
    GET    /prompts/search       Search prompts (public, personalized if auth)
    POST   /prompts              Create prompt (authenticated)
    GET    /prompts/{id}         Get prompt (public)
    PUT    /prompts/{id}         Update prompt (owner or admin)
    DELETE /prompts/{id}         Delete prompt (owner or admin)
    PUT    /prompts/{id}/favorite Toggle favorite (owner only)
    DELETE /prompts/bulk         Bulk delete (admin only)
"""

from fastapi import APIRouter

from src.web.routers.prompts_search_router import router as _search_router
from src.web.routers.prompts_crud_router import router as _crud_router

# Re-export shared helpers and constants for backward compatibility with any
# code that imported them from this module.
from src.web.routers.prompts_shared import (  # noqa: F401
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    _parse_semver,
    check_prompt_ownership,
    _parse_tags_field,
    _log_prompt_action,
    _prompt_to_dict,
    normalize_pagination,
    _build_pagination_envelope,
    _paginate_mapping,
)

# Aggregate the split routers into a single router exported as ``router``.
#
# The sub-routers already carry the ``/prompts`` prefix, so this aggregator has
# no prefix of its own. app.py mounts this router under ``/api``, yielding the
# original ``/api/prompts`` paths.
#
# Registration order is preserved: the search router (``GET /prompts`` and
# ``GET /prompts/search``) is included before the CRUD router so that the static
# ``/search`` path is registered ahead of the dynamic ``/{prompt_id}`` path.
router = APIRouter()
router.include_router(_search_router)
router.include_router(_crud_router)
