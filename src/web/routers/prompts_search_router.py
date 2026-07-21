# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Prompt read/search routes (public with optional authentication).

Split out from the original ``prompts.py`` god-file. Contains the list and
search endpoints. Behavior, route paths, methods, and response shapes are
unchanged.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.db.models.user import User
from src.db.repositories.prompt_repository import PromptRepository
from src.config.auth_config import auth_settings
from src.web.dependencies.auth import (
    get_optional_user,
    get_current_user_or_none,
)
from src.web.routers.prompts_shared import (
    DEFAULT_PAGE_SIZE,
    _prompt_to_dict,
    normalize_pagination,
    _build_pagination_envelope,
    _paginate_mapping,
)

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/prompts",
    tags=["Prompts"],
)


# ============================================================================
# Read Endpoints (Public with Optional Authentication)
# ============================================================================


@router.get(
    "",
    summary="List all prompts",
    description="""
    List all prompts with optional personalization for authenticated users.

    **Public Access:**
    - Anyone can view prompts
    - No authentication required

    **Personalized Results (Optional):**
    - If authenticated, user's own prompts are marked
    - Future: Could filter or sort by user preferences

    **Response:**
    - Returns one page of prompts with pagination metadata
    - Includes category and tags

    **Query Parameters:**
    - page: Page number, 1-indexed (default 1; values <1 normalize to 1)
    - limit: Page size (default 50; clamped to a maximum of 100)
    """,
    responses={
        200: {"description": "Prompts retrieved successfully"},
    },
)
async def list_prompts(
    page: int = 1,
    limit: int = DEFAULT_PAGE_SIZE,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """List prompts with offset pagination (public access with optional personalization).

    Args:
        page: Page number, 1-indexed
        limit: Page size
        user: Authenticated user (optional)
        db: Database session

    Returns:
        dict: Pagination envelope with prompts dictionary keyed by ID
    """
    page, limit = normalize_pagination(page, limit)

    # Prefer legacy data service when available (also tolerates legacy
    # dict shapes without a "data" wrapper; tests may monkeypatch it)
    try:
        from src.web import app as web_app

        legacy_prompts = web_app.data_service.load_prompts()
    except Exception:
        legacy_prompts = None

    if legacy_prompts:
        all_prompts_dict = {}
        for pid, info in legacy_prompts.items():
            data = info["data"] if "data" in info else info
            all_prompts_dict[str(pid)] = {
                "id": pid,
                "title": data.get("title", ""),
                "prompt": data.get("prompt", ""),
                "category": data.get("category", ""),
                "category_color": None,
                "tags": data.get("tags", []),
                "tag_colors": {},
                "note": data.get("note", ""),
                "favorite": data.get("favorite", False),
                "user_id": data.get("user_id"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
            }
        prompts_dict, total_count = _paginate_mapping(all_prompts_dict, page, limit)
        result = _build_pagination_envelope(prompts_dict, page, limit, total_count)
    else:
        prompt_repo = PromptRepository(db)
        total_count = prompt_repo.count()
        # Use search() rather than get_all() so results are stably ordered
        # (get_all() has no ORDER BY, which makes OFFSET/LIMIT pagination
        # non-deterministic across pages).
        prompts = prompt_repo.search(limit=limit, offset=(page - 1) * limit)

        prompts_dict = {}
        for prompt in prompts:
            prompt_dict = _prompt_to_dict(prompt)
            prompt_dict.pop("semantic_version", None)
            prompts_dict[str(prompt.id)] = prompt_dict

        result = _build_pagination_envelope(prompts_dict, page, limit, total_count)

    if user:
        logger.debug(f"User {user.username} ({user.id}) accessed prompt list")

    return result


@router.get(
    "/search",
    summary="Search prompts",
    description="""
    Search and filter prompts based on various criteria.

    **Public Access:**
    - Anyone can search prompts
    - No authentication required

    **Query Parameters:**
    - search: Text to search for in title, prompt content, or notes
    - category: Filter by specific category
    - tag: Filter by specific tag
    - favorites: Show only favorite prompts (requires authentication)
    - case_sensitive: Enable case-sensitive search
    - page: Page number, 1-indexed (default 1; values <1 normalize to 1)
    - limit: Page size (default 50; clamped to a maximum of 100)

    **Authentication:**
    - Optional for general search
    - Required for favorites filter
    """,
    responses={
        200: {"description": "Search results retrieved successfully"},
        400: {"description": "Invalid search parameters"},
    },
)
async def search_prompts(
    search: str = "",
    category: str = "",
    tag: str = "",
    favorites: bool = False,
    case_sensitive: bool = False,
    page: int = 1,
    limit: int = DEFAULT_PAGE_SIZE,
    user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    """Search and filter prompts with offset pagination.

    Args:
        search: Text search query
        category: Category filter
        tag: Tag filter
        favorites: Filter by favorites (requires auth)
        case_sensitive: Case-sensitive search
        page: Page number, 1-indexed
        limit: Page size
        user: Authenticated user (optional)
        db: Database session

    Returns:
        dict: Pagination envelope with filtered prompts

    Raises:
        HTTPException: 401 if favorites filter used without authentication
    """
    # Favorites filter requires authentication (only enforced when auth is enabled;
    # anonymous-mode deployments have no logged-in user by design)
    if favorites and not user and auth_settings.auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to filter by favorites",
            headers={"WWW-Authenticate": "Bearer"},
        )

    page, limit = normalize_pagination(page, limit)

    try:
        # Legacy fallback for tests that monkeypatch data_service (also
        # tolerates legacy dict shapes without a "data" wrapper)
        from src.web import app as web_app

        legacy_prompts = web_app.data_service.load_prompts()
    except HTTPException:
        raise
    except Exception:
        return JSONResponse(
            status_code=500,
            content={"error": "Search failed: internal error"},
        )

    if legacy_prompts:
        filtered = {}
        for pid, info in legacy_prompts.items():
            data = info["data"] if "data" in info else info
            if favorites and not data.get("favorite", False):
                continue
            if category and data.get("category") != category:
                continue
            if tag and tag not in data.get("tags", []):
                continue
            if search:
                haystacks = [
                    data.get("title", ""),
                    data.get("prompt", ""),
                    data.get("note", ""),
                ]
                matched = False
                for hay in haystacks:
                    if hay is None:
                        continue
                    if case_sensitive:
                        if search in hay:
                            matched = True
                            break
                    else:
                        if search.lower() in hay.lower():
                            matched = True
                            break
                if not matched:
                    continue
            filtered[str(pid)] = {
                "id": pid,
                "title": data.get("title", ""),
                "prompt": data.get("prompt", ""),
                "category": data.get("category", ""),
                "category_color": None,
                "tags": data.get("tags", []),
                "tag_colors": {},
                "note": data.get("note", ""),
                "favorite": data.get("favorite", False),
                "user_id": data.get("user_id"),
                "created_at": data.get("created_at"),
                "updated_at": data.get("updated_at"),
            }
        prompts_dict, total_count = _paginate_mapping(filtered, page, limit)
        return _build_pagination_envelope(prompts_dict, page, limit, total_count)

    # Fallback when data_service has no data (e.g. empty DB): search directly
    prompt_repo = PromptRepository(db)

    search_query = search if search else None
    category_filter = category if category else None
    tag_filter = [tag] if tag else None
    favorite_filter = favorites if favorites else None

    total_count = prompt_repo.count(
        query=search_query,
        category=category_filter,
        tags=tag_filter,
        favorite=favorite_filter,
        case_sensitive=case_sensitive,
    )
    prompts = prompt_repo.search(
        query=search_query,
        category=category_filter,
        tags=tag_filter,
        favorite=favorite_filter,
        limit=limit,
        offset=(page - 1) * limit,
        case_sensitive=case_sensitive,
    )

    prompts_dict = {}
    for prompt in prompts:
        prompts_dict[str(prompt.id)] = _prompt_to_dict(prompt)

    return _build_pagination_envelope(prompts_dict, page, limit, total_count)
