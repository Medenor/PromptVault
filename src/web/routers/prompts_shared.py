# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared helpers for the prompt routers.

These helpers were extracted verbatim from the original ``prompts.py`` module
so that the CRUD and search routers can share them without duplication. Behavior
is unchanged.
"""

import logging
from typing import List

from fastapi import HTTPException, status

from src.db.models.user import User
from src.db.models.prompt import Prompt

# Configure logging
logger = logging.getLogger(__name__)


DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


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
