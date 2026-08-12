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
)


def _visibility_scope(user: Optional[User]) -> Optional[str]:
    """Resolve the visible_to_user_id argument for PromptRepository scoping.

    Admins and anonymous-mode (user=None with auth disabled) see everything
    (None = unscoped). Any other authenticated user is scoped to their own
    owned + shared + legacy-public prompts. When auth is enabled but the
    request is unauthenticated, scope to a sentinel that matches nothing —
    an anonymous caller under AUTH_ENABLED=true has no visibility (research
    §1: read-visibility scoping only applies when auth is enabled).
    """
    if not auth_settings.auth_enabled:
        return None
    if user is None:
        return "__no_such_user__"
    if user.role == "admin":
        return None
    return user.id


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
    filter: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    """List prompts with offset pagination (public access with optional personalization).

    Args:
        page: Page number, 1-indexed
        limit: Page size
        filter: 'shared-with-me' narrows to explicit grants only (excludes
            legacy-public prompts); any other value is ignored
        user: Authenticated user (optional)
        db: Database session

    Returns:
        dict: Pagination envelope with prompts dictionary keyed by ID
    """
    page, limit = normalize_pagination(page, limit)

    prompt_repo = PromptRepository(db)
    visible_to_user_id = _visibility_scope(user)
    shared_only = filter == "shared-with-me"
    total_count = prompt_repo.count(
        visible_to_user_id=visible_to_user_id, shared_only=shared_only
    )
    # Use search() rather than get_all() so results are stably ordered
    # (get_all() has no ORDER BY, which makes OFFSET/LIMIT pagination
    # non-deterministic across pages). No search query here, so search()
    # takes the plain-listing path regardless of `ranked`.
    prompts = prompt_repo.search(
        limit=limit,
        offset=(page - 1) * limit,
        visible_to_user_id=visible_to_user_id,
        shared_only=shared_only,
    )

    prompts_dict = {}
    for prompt, _match_context in prompts:
        prompt_dict = _prompt_to_dict(prompt, viewer=user, session=db)
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

    **Full-text ranking:**
    - `search` runs against a full-text index (SQLite FTS5 / PostgreSQL
      tsvector+GIN), ranked title > prompt body > note. Bare multi-word
      queries are OR-joined, so partial-word matches are still returned,
      just ranked below all-words matches. `"quoted phrases"` match as a
      unit. An unparseable/operator-only query never errors — it falls
      back to a plain substring search and still returns `200`.
    - Each result may include an optional `match_context` field: a snippet
      of the matched body/note text with the match wrapped in
      `[[MATCH]]...[[/MATCH]]` sentinels (not HTML). Present when the
      ranked engine produced a body/note snippet; absent for title-only
      matches, `ranked=false`, or `case_sensitive=true`. Clients must
      HTML-escape the string first, then replace the sentinels with
      `<mark>`/`</mark>` — never render it as raw HTML.

    **Query Parameters:**
    - search: Text to search for in title, prompt content, or notes
    - category: Filter by specific category
    - tag: Filter by specific tag
    - favorites: Show only favorite prompts (requires authentication)
    - case_sensitive: Enable case-sensitive search (exact substring match;
      disables ranking and `match_context` snippets)
    - ranked: Order results by relevance instead of `updated_at desc`
      (default `true`); explicit `sort` selections, when supported, still
      override relevance. Set `false` to restore the legacy ordering.
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
    ranked: bool = True,
    page: int = 1,
    limit: int = DEFAULT_PAGE_SIZE,
    filter: Optional[str] = None,
    user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    """Search and filter prompts with offset pagination.

    Args:
        search: Text search query
        category: Category filter
        tag: Tag filter
        favorites: Filter by favorites (requires auth)
        case_sensitive: Case-sensitive search (disables ranking/snippets)
        ranked: Order by relevance (title > body > note) instead of the
            legacy updated_at-desc ordering; default True
        page: Page number, 1-indexed
        limit: Page size
        filter: 'shared-with-me' narrows to explicit grants only (excludes
            legacy-public prompts); any other value is ignored
        user: Authenticated user (optional)
        db: Database session

    Returns:
        dict: Pagination envelope with filtered prompts; each prompt gains
            an optional `match_context` field (sentinel-wrapped snippet,
            see contracts/search-api.md) when the ranked engine produced
            a body/note match.

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

    prompt_repo = PromptRepository(db)

    search_query = search if search else None
    category_filter = category if category else None
    tag_filter = [tag] if tag else None
    favorite_filter = favorites if favorites else None
    visible_to_user_id = _visibility_scope(user)
    shared_only = filter == "shared-with-me"

    total_count = prompt_repo.count(
        query=search_query,
        category=category_filter,
        tags=tag_filter,
        favorite=favorite_filter,
        case_sensitive=case_sensitive,
        visible_to_user_id=visible_to_user_id,
        shared_only=shared_only,
        ranked=ranked,
    )
    prompts = prompt_repo.search(
        query=search_query,
        category=category_filter,
        tags=tag_filter,
        favorite=favorite_filter,
        limit=limit,
        offset=(page - 1) * limit,
        case_sensitive=case_sensitive,
        visible_to_user_id=visible_to_user_id,
        shared_only=shared_only,
        ranked=ranked,
    )

    prompts_dict = {}
    for prompt, match_context in prompts:
        prompt_dict = _prompt_to_dict(prompt, viewer=user, session=db)
        if match_context is not None:
            prompt_dict["match_context"] = match_context
        prompts_dict[str(prompt.id)] = prompt_dict

    return _build_pagination_envelope(prompts_dict, page, limit, total_count)
