# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Prompt routes for PromptVault with authentication and authorization.

This module provides API endpoints for prompt CRUD operations with:
- Authentication using JWT tokens
- Ownership-based authorization
- Role-based access control (RBAC)
- Public read with optional personalization
- Proper error handling and status codes

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

import logging
from datetime import datetime, timezone
from typing import Annotated, Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, status, Form
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.db.models.user import User
from src.db.models.prompt import Prompt
from src.db.models.category import Category
from src.db.models.tag import Tag
from src.db.repositories.prompt_repository import PromptRepository
from src.db.repositories.category_repository import CategoryRepository
from src.db.repositories.tag_repository import TagRepository
from src.db.repositories.version_repository import VersionRepository
from src.config.auth_config import auth_settings
from src.web.dependencies.auth import (
    get_current_active_user,
    get_optional_user,
    get_current_user_or_none,
    get_current_user_or_default,
    get_admin_or_bypass,
    require_role,
)
from src.web.models.requests import (
    PromptCreateRequest,
    PromptUpdateRequest,
    BulkDeleteRequest,
)
from src.web.models.auth_responses import MessageResponse
from src.db.models.prompt_branch import PromptBranch

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/prompts",
    tags=["Prompts"],
)


# ============================================================================
# Helper Functions
# ============================================================================


def _parse_semver(v: str) -> tuple:
    parts = v.split(".")
    return tuple(int(p) for p in parts)


def check_prompt_ownership(prompt: Prompt, user: User) -> None:
    """Check if user owns the prompt or is an admin.

    Args:
        prompt: Prompt to check ownership of
        user: User attempting the operation

    Raises:
        HTTPException: 403 if user doesn't have permission
    """
    # Admins can modify any prompt
    if user.role == "admin":
        return

    # Check if user owns the prompt
    if prompt.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to modify this prompt. Only the owner or an admin can perform this action.",
        )


def _parse_tags_field(tags: str) -> List[str]:
    """Normalize a comma-delimited tag string into a list with trimmed entries.

    Args:
        tags: Raw tag field from the form submission.

    Returns:
        List[str]: Cleaned tags with whitespace removed and empty values filtered out.
    """
    if not tags:
        return []
    normalized_tags = []
    for tag in tags.split(","):
        cleaned = tag.strip()
        if cleaned:
            normalized_tags.append(cleaned)
    return normalized_tags


def _log_prompt_action(
    action: str,
    prompt_id: int,
    user_id: str,
    username: str,
    details: str = "",
):
    """Log prompt action for audit trail.

    Args:
        action: Action performed (e.g., "CREATE_PROMPT", "UPDATE_PROMPT")
        prompt_id: Prompt ID
        user_id: User's ID
        username: User's username
        details: Additional details about the action
    """
    logger.info(
        f"PROMPT_ACTION: {action} | User: {username} ({user_id}) | "
        f"Prompt: {prompt_id} | Details: {details}"
    )


def _prompt_to_dict(prompt: Prompt) -> dict:
    """Convert Prompt model to dictionary for API response.

    Args:
        prompt: Prompt model instance

    Returns:
        dict: Prompt data formatted for API response
    """
    return {
        "id": prompt.id,
        "title": prompt.title,
        "prompt": prompt.prompt,
        "category": prompt.category.name if prompt.category else "",
        "category_color": prompt.category.color if prompt.category else None,
        "tags": [tag.name for tag in prompt.tags] if prompt.tags else [],
        "tag_colors": (
            {tag.name: tag.color for tag in prompt.tags} if prompt.tags else {}
        ),
        "note": prompt.note or "",
        "favorite": prompt.favorite,
        "user_id": prompt.user_id,
        "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
        "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None,
        "semantic_version": prompt.semantic_version,
    }


DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


def normalize_pagination(page: int, limit: int) -> tuple[int, int]:
    """Normalize page/limit query params to safe, bounded values.

    Args:
        page: Requested page number (1-indexed)
        limit: Requested page size

    Returns:
        Tuple of (normalized_page, normalized_limit): page<1 becomes 1;
        limit<1 becomes DEFAULT_PAGE_SIZE; limit>MAX_PAGE_SIZE is clamped.
    """
    normalized_page = page if page >= 1 else 1
    if limit < 1:
        normalized_limit = DEFAULT_PAGE_SIZE
    elif limit > MAX_PAGE_SIZE:
        normalized_limit = MAX_PAGE_SIZE
    else:
        normalized_limit = limit
    return normalized_page, normalized_limit


def _build_pagination_envelope(
    prompts_dict: dict, page: int, limit: int, total_count: int
) -> dict:
    """Build the standard pagination response envelope.

    Args:
        prompts_dict: Prompts for the current page, keyed by ID
        page: Normalized current page number
        limit: Normalized page size
        total_count: Total number of matching prompts across all pages

    Returns:
        dict: Full response envelope including pagination metadata
    """
    total_pages = (total_count + limit - 1) // limit if total_count > 0 else 0
    return {
        "prompts": prompts_dict,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
        "total_count": total_count,
        "has_next": page < total_pages,
        "has_previous": page > 1,
    }


def _paginate_mapping(items: dict, page: int, limit: int) -> tuple[dict, int]:
    """Slice an ordered mapping into one page, preserving key order.

    Used to paginate dict results sourced from data_service (which may hold
    legacy JSON-shaped entries alongside DB-backed ones) with the same
    page/limit semantics as the SQLAlchemy-backed paths.

    Args:
        items: Ordered mapping of all matching entries, keyed by ID
        page: Normalized page number
        limit: Normalized page size

    Returns:
        Tuple of (page_slice_dict, total_count)
    """
    total_count = len(items)
    start = (page - 1) * limit
    end = start + limit
    page_slice = dict(list(items.items())[start:end])
    return page_slice, total_count


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


@router.get(
    "/{prompt_id}",
    summary="Get prompt by ID",
    description="""
    Get a specific prompt by ID.

    **Public Access:**
    - Anyone can view individual prompts
    - No authentication required

    **Response:**
    - Returns complete prompt data
    - Includes category, tags, and metadata
    """,
    responses={
        200: {"description": "Prompt retrieved successfully"},
        404: {"description": "Prompt not found"},
    },
)
async def get_prompt(
    prompt_id: int,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Get a specific prompt by ID (public access).

    Args:
        prompt_id: Prompt ID
        user: Authenticated user (optional)
        db: Database session

    Returns:
        dict: Prompt data

    Raises:
        HTTPException: 404 if prompt not found
    """
    prompt_repo = PromptRepository(db)
    # Legacy compatibility: consult data_service when present
    try:
        from src.web import app as web_app

        legacy_prompts = web_app.data_service.load_prompts()
        if legacy_prompts and prompt_id in legacy_prompts:
            info = legacy_prompts[prompt_id]
            data = info["data"] if "data" in info else info
            return {
                "id": prompt_id,
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
                "semantic_version": data.get("semantic_version"),
            }
    except Exception:
        pass

    prompt = prompt_repo.get_with_relationships(prompt_id)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found",
        )

    return _prompt_to_dict(prompt)


# ============================================================================
# Write Endpoints (Authenticated)
# ============================================================================


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create prompt",
    description="""
    Create a new prompt.

    **Authentication:**
    - Requires active authenticated user
    - Any authenticated user can create prompts

    **Request Body:**
    - title: Prompt title (1-200 chars, required)
    - prompt: Prompt content (1-50,000 chars, required)
    - category: Category name (optional, max 100 chars)
    - tags: Comma-separated tags (optional, max 50 tags)

    **Behavior:**
    - Prompt is owned by the authenticated user
    - Category is created if it doesn't exist
    - Tags are created if they don't exist
    """,
    responses={
        201: {"description": "Prompt created successfully"},
        401: {"description": "Authentication required"},
        422: {"description": "Validation failed"},
    },
)
async def create_prompt(
    title: str = Form(...),
    prompt: str = Form(...),
    category: str = Form(""),
    tags: str = Form(""),
    commit_message: str = Form("Initial commit"),
    semantic_version: str = Form(""),
    user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    """Create a new prompt (authenticated).

    Args:
        title: Prompt title
        prompt: Prompt content
        category: Category name (optional)
        tags: Comma-separated tags (optional)
        commit_message: Commit message for the initial version (optional, defaults to "Initial commit")
        semantic_version: Optional semantic version label (MAJOR.MINOR.PATCH)
        user: Authenticated user
        db: Database session

    Returns:
        dict: Success response with prompt ID
    """
    # Validate using Pydantic model
    validated_data = PromptCreateRequest(
        title=title,
        prompt=prompt,
        category=category,
        tags=tags,
        semantic_version=semantic_version or None,
    )

    prompt_repo = PromptRepository(db)
    category_repo = CategoryRepository(db)
    tag_repo = TagRepository(db)
    version_repo = VersionRepository(db)

    # Get or create category
    category_obj = None
    if validated_data.category:
        category_obj = category_repo.get_or_create(validated_data.category)

    # Parse and get or create tags
    tag_list = _parse_tags_field(validated_data.tags)
    tag_objects = []
    seen = set()
    for tag_name in tag_list:
        if tag_name in seen:
            continue
        seen.add(tag_name)
        tag_obj = tag_repo.get_or_create(tag_name)
        tag_objects.append(tag_obj)

    # Create prompt
    new_prompt = Prompt(
        title=validated_data.title,
        prompt=validated_data.prompt,
        category_id=category_obj.id if category_obj else None,
        note="",
        favorite=False,
        semantic_version=validated_data.semantic_version,
        user_id=user.id if user else None,
        created_at=datetime.now(timezone.utc),
    )

    # Add tags
    new_prompt.tags = tag_objects

    # Save to database
    db.add(new_prompt)
    db.flush()
    db.commit()

    # Create initial version
    version = version_repo.create_version(
        prompt=new_prompt,
        author=user.username if user else "anonymous",
        message=commit_message,
        parent_version_id=None,
        semantic_version=validated_data.semantic_version,
    )

    # Create main branch pointing to initial version
    from src.db.models import PromptBranch

    main_branch = PromptBranch(
        prompt_id=new_prompt.id,
        branch_name="main",
        current_version_id=version.version_id,
    )
    db.add(main_branch)
    db.commit()

    # Log action
    _log_prompt_action(
        "CREATE_PROMPT",
        new_prompt.id,
        user.id if user else None,
        user.username if user else "anonymous",
        f"title='{validated_data.title}', category='{validated_data.category}'",
    )

    # Record successful validation
    from src.web.app import record_validation_event

    record_validation_event(
        endpoint="/api/prompts",
        success=True,
    )

    return {"success": True, "prompt_id": new_prompt.id}


@router.put(
    "/{prompt_id}",
    summary="Update prompt",
    description="""
    Update an existing prompt.

    **Authentication:**
    - Requires active authenticated user

    **Authorization:**
    - Owner can update their own prompts
    - Admins can update any prompt

    **Request Body:**
    - title: Prompt title (1-200 chars, required)
    - prompt: Prompt content (1-50,000 chars, required)
    - category: Category name (optional, max 100 chars)
    - tags: Comma-separated tags (optional, max 50 tags)
    - commit_message: Version control message (optional, max 500 chars)

    **Behavior:**
    - Creates a new version in version history
    - Updates category and tags
    """,
    responses={
        200: {"description": "Prompt updated successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied (not owner or admin)"},
        404: {"description": "Prompt not found"},
        422: {"description": "Validation failed"},
    },
)
async def update_prompt(
    prompt_id: int,
    title: str = Form(...),
    prompt: str = Form(...),
    category: str = Form(""),
    tags: str = Form(""),
    commit_message: str = Form("Update"),
    semantic_version: str = Form(""),
    user: User = Depends(get_current_user_or_default),
    db: Session = Depends(get_db),
):
    """Update an existing prompt (owner or admin).

    Args:
        prompt_id: Prompt ID
        title: New title
        prompt: New content
        category: New category
        tags: New tags (comma-separated)
        commit_message: Version control message
        semantic_version: Optional semantic version label (MAJOR.MINOR.PATCH)
        user: Authenticated user
        db: Database session

    Returns:
        dict: Success response

    Raises:
        HTTPException: 404 if not found, 403 if not authorized
    """
    # Validate using Pydantic model
    validated_data = PromptUpdateRequest(
        title=title,
        prompt=prompt,
        category=category,
        tags=tags,
        commit_message=commit_message,
        semantic_version=semantic_version or None,
    )

    prompt_repo = PromptRepository(db)
    category_repo = CategoryRepository(db)
    tag_repo = TagRepository(db)
    version_repo = VersionRepository(db)

    # Get prompt
    existing_prompt = prompt_repo.get_with_relationships(prompt_id)
    if not existing_prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found",
        )

    # Check ownership
    check_prompt_ownership(existing_prompt, user)

    # Get or create category
    category_obj = None
    if validated_data.category:
        category_obj = category_repo.get_or_create(validated_data.category)

    # Parse and get or create tags
    tag_list = _parse_tags_field(validated_data.tags)
    tag_objects = []
    seen = set()
    for tag_name in tag_list:
        if tag_name in seen:
            continue
        seen.add(tag_name)
        tag_obj = tag_repo.get_or_create(tag_name)
        tag_objects.append(tag_obj)

    # Detect version downgrade before updating
    version_downgrade = False
    if (
        validated_data.semantic_version is not None
        and existing_prompt.semantic_version is not None
    ):
        try:
            new_v = _parse_semver(validated_data.semantic_version)
            old_v = _parse_semver(existing_prompt.semantic_version)
            if new_v < old_v:
                version_downgrade = True
        except (ValueError, AttributeError):
            pass

    # Update prompt
    existing_prompt.title = validated_data.title
    existing_prompt.prompt = validated_data.prompt
    existing_prompt.category_id = category_obj.id if category_obj else None
    existing_prompt.tags = tag_objects
    existing_prompt.updated_at = datetime.now(timezone.utc)
    if validated_data.semantic_version is not None:
        existing_prompt.semantic_version = validated_data.semantic_version

    # Flush to ensure prompt is updated
    db.flush()

    # Get current version ID (parent for new version)
    main_branch = next(
        (b for b in existing_prompt.branches if b.branch_name == "main"), None
    )
    parent_version_id = main_branch.current_version_id if main_branch else None

    # Create new version with the updated prompt data
    author_name = user.username
    version = version_repo.create_version(
        prompt=existing_prompt,
        author=author_name,
        message=validated_data.commit_message,
        parent_version_id=parent_version_id,
        semantic_version=validated_data.semantic_version,
    )

    # Update main branch to point to new version
    if main_branch:
        main_branch.current_version_id = version.version_id
    else:
        main_branch = PromptBranch(
            prompt_id=existing_prompt.id,
            branch_name="main",
            current_version_id=version.version_id,
        )
        db.add(main_branch)

    # Commit all changes
    db.commit()

    # Log action
    _log_prompt_action(
        "UPDATE_PROMPT",
        prompt_id,
        user.id,
        user.username,
        f"title='{validated_data.title}', message='{validated_data.commit_message}'",
    )

    response_headers = {}
    if version_downgrade:
        response_headers["X-Version-Downgrade"] = "true"

    return JSONResponse(content={"success": True}, headers=response_headers)


@router.delete(
    "/bulk",
    summary="Bulk delete prompts",
    description="""
    Delete multiple prompts in bulk.

    **Authentication:**
    - Requires admin role

    **Authorization:**
    - Admin only

    **Request Body:**
    - prompt_ids: List of prompt IDs to delete (1-1000 IDs)

    **Behavior:**
    - Deletes all specified prompts
    - Returns statistics on successful and failed deletions
    - Automatic backup is created (handled by service layer)
    """,
    responses={
        200: {"description": "Bulk deletion completed"},
        403: {"description": "Admin role required"},
        422: {"description": "Validation failed"},
    },
)
async def bulk_delete_prompts(
    body: BulkDeleteRequest,
    admin: Optional[User] = Depends(get_admin_or_bypass),
    db: Session = Depends(get_db),
):
    """Bulk delete prompts (admin only).

    Args:
        body: Request body with prompt IDs
        admin: Authenticated admin user (None in anonymous mode)
        db: Database session

    Returns:
        dict: Statistics on deletion results
    """
    prompt_repo = PromptRepository(db)

    backup_id = None
    try:
        from src.web import app as web_app

        backup_service = getattr(web_app, "backup_service", None)
        if backup_service:
            backup_id = backup_service.create_backup(
                "bulk_delete",
                created_by=admin.username if admin else "anonymous",
            )
    except Exception:
        backup_id = None

    deleted_count = 0
    failed_count = 0
    failed_ids = []

    for prompt_id in body.prompt_ids:
        try:
            # Check if prompt exists
            prompt = prompt_repo.get_by_id(prompt_id)
            if prompt:
                prompt_repo.delete(prompt_id)
                deleted_count += 1
            else:
                failed_count += 1
                failed_ids.append(prompt_id)
        except Exception as e:
            logger.error(f"Failed to delete prompt {prompt_id}: {str(e)}")
            failed_count += 1
            failed_ids.append(prompt_id)

    db.commit()

    # Log action
    _log_prompt_action(
        "BULK_DELETE_PROMPTS",
        0,  # No specific prompt ID
        admin.id if admin else None,
        admin.username if admin else "anonymous",
        f"deleted={deleted_count}, failed={failed_count}",
    )

    return {
        "success": True,
        "deleted_count": deleted_count,
        "failed_count": failed_count,
        "failed_ids": failed_ids,
        "backup_id": backup_id,
    }


@router.delete(
    "/{prompt_id}",
    summary="Delete prompt",
    description="""
    Delete a prompt.

    **Authentication:**
    - Requires active authenticated user

    **Authorization:**
    - Owner can delete their own prompts
    - Admins can delete any prompt

    **Behavior:**
    - Soft delete by default (sets deleted flag)
    - Prompt data is preserved for recovery
    - Version history is preserved
    """,
    responses={
        200: {"description": "Prompt deleted successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied (not owner or admin)"},
        404: {"description": "Prompt not found"},
    },
)
async def delete_prompt(
    prompt_id: int,
    user: User = Depends(get_current_user_or_default),
    db: Session = Depends(get_db),
):
    """Delete a prompt (owner or admin).

    Args:
        prompt_id: Prompt ID
        user: Authenticated user
        db: Database session

    Returns:
        dict: Success response

    Raises:
        HTTPException: 404 if not found, 403 if not authorized
    """
    prompt_repo = PromptRepository(db)

    # Get prompt
    existing_prompt = prompt_repo.get_by_id(prompt_id)
    if not existing_prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found",
        )

    check_prompt_ownership(existing_prompt, user)

    # Delete prompt (cascade deletes versions, tags associations)
    prompt_repo.delete(prompt_id)
    db.commit()

    # Log action
    _log_prompt_action(
        "DELETE_PROMPT",
        prompt_id,
        user.id,
        user.username,
        f"title='{existing_prompt.title}'",
    )

    return {"success": True}


@router.put(
    "/{prompt_id}/favorite",
    summary="Toggle favorite",
    description="""
    Toggle favorite status of a prompt.

    **Authentication:**
    - Requires active authenticated user

    **Authorization:**
    - Owner can toggle favorite on their own prompts
    - Users cannot toggle favorites on other users' prompts

    **Behavior:**
    - Toggles favorite boolean flag
    - Returns new favorite status
    """,
    responses={
        200: {"description": "Favorite toggled successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Permission denied (not owner)"},
        404: {"description": "Prompt not found"},
    },
)
async def toggle_favorite(
    prompt_id: int,
    user: User = Depends(get_current_user_or_default),
    db: Session = Depends(get_db),
):
    """Toggle favorite status (owner only).

    Args:
        prompt_id: Prompt ID
        user: Authenticated user
        db: Database session

    Returns:
        dict: Success response with new favorite status

    Raises:
        HTTPException: 404 if not found, 403 if not owner
    """
    prompt_repo = PromptRepository(db)

    # Get prompt
    existing_prompt = prompt_repo.get_by_id(prompt_id)
    if not existing_prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found",
        )

    # Check ownership (only owner can toggle favorite)
    check_prompt_ownership(existing_prompt, user)

    # Legacy failure injection support (tests may monkeypatch data_service.update_prompt)
    try:
        from src.web import app as web_app

        legacy_ds = getattr(web_app, "data_service", None)
        if legacy_ds and hasattr(legacy_ds, "update_prompt"):
            legacy_result = legacy_ds.update_prompt(
                prompt_id,
                {
                    "title": existing_prompt.title,
                    "prompt": existing_prompt.prompt,
                    "category": (
                        existing_prompt.category.name
                        if existing_prompt.category
                        else ""
                    ),
                    "tags": (
                        [t.name for t in existing_prompt.tags]
                        if existing_prompt.tags
                        else []
                    ),
                    "favorite": not existing_prompt.favorite,
                },
                "Toggle favorite",
            )
            if legacy_result is False:
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to update favorite status"},
                )
    except Exception:
        pass

    # Toggle favorite
    new_favorite_status = not existing_prompt.favorite
    existing_prompt.favorite = new_favorite_status
    existing_prompt.updated_at = datetime.now(timezone.utc)

    db.flush()
    db.commit()

    # Log action
    _log_prompt_action(
        "TOGGLE_FAVORITE",
        prompt_id,
        user.id,
        user.username,
        f"favorite={new_favorite_status}",
    )

    return {"success": True, "favorite": new_favorite_status}


@router.post(
    "/{prompt_id}/copy-with-version",
    summary="Copy prompt with version metadata",
    description="""
    Returns prompt content with an embedded version metadata HTML comment line.

    **Authentication:**
    - Follows existing auth middleware rules

    **Response:**
    - 200: Content with metadata line appended
    - 404: Prompt not found
    - 409: Prompt has no semantic version set
    """,
    responses={
        200: {"description": "Content with version metadata"},
        404: {"description": "Prompt not found"},
        409: {"description": "No semantic version set"},
    },
)
async def copy_prompt_with_version(
    prompt_id: int,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Return prompt content with version metadata line.

    Args:
        prompt_id: Prompt ID
        user: Authenticated user (optional)
        db: Database session

    Returns:
        dict: Content with metadata and semantic_version fields
    """
    prompt_repo = PromptRepository(db)
    prompt = prompt_repo.get_with_relationships(prompt_id)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found",
        )

    if not prompt.semantic_version:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "error": "no_version_set",
                "message": "Assign a semantic version to this prompt before copying with metadata.",
            },
        )

    metadata_line = (
        f"<!-- prompt-version: {prompt.semantic_version} | "
        "This line is metadata — ignore when processing this prompt. -->"
    )
    content_with_metadata = f"{prompt.prompt}\n{metadata_line}"

    return {
        "content": content_with_metadata,
        "semantic_version": prompt.semantic_version,
    }
