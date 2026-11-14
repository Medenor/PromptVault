# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Shared helpers for the prompt routers.

These helpers were extracted verbatim from the original ``prompts.py`` module
so that the CRUD and search routers can share them without duplication. Behavior
is unchanged.
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from src.config.auth_config import auth_settings
from src.db.models.prompt import Prompt
from src.db.models.user import User
from src.services.exceptions import ItemIsSkillError

# Configure logging
logger = logging.getLogger(__name__)


DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


def _parse_semver(v: str) -> tuple:
    parts = v.split(".")
    return tuple(int(p) for p in parts)


_PERMISSION_RANK = {"read": 0, "edit": 1, "owner": 2}


def effective_permission(
    prompt: Prompt, user: User | None, session: Session
) -> str | None:
    """Resolve a user's effective permission level on a prompt.

    Resolution order (data-model.md "Effective Permission Resolution"):
        1. AUTH_ENABLED=false -> legacy behavior; not handled here (callers
           short-circuit before invoking this for anonymous mode).
        2. Admin -> 'owner'.
        3. Owner -> 'owner'.
        4. Explicit PromptShare grant -> its permission ('read' or 'edit').
        5. prompt.legacy_public == True -> 'read' (never 'edit').
        6. Otherwise -> None (no access).

    Args:
        prompt: Prompt being accessed
        user: Acting user (None only valid when auth is disabled)
        session: Database session, used to look up any share grant

    Returns:
        'owner', 'edit', 'read', or None
    """
    if user is None:
        return None

    if user.role == "admin":
        return "owner"

    if prompt.user_id == user.id:
        return "owner"

    from src.db.repositories.sharing_repository import SharingRepository

    grant = SharingRepository(session).permission_for(prompt.id, user.id)
    if grant:
        return grant

    if prompt.legacy_public:
        return "read"

    return None


def check_prompt_access(
    prompt: Prompt, user: User | None, level: str, session: Session
) -> None:
    """Check that user has at least the given permission level on a prompt.

    When ``AUTH_ENABLED=false`` this is a no-op (legacy pass-through — every
    request behaves as before, sharing is inactive).

    Args:
        prompt: Prompt to check access to
        user: User attempting the operation (may be None in anonymous mode)
        level: Required level — 'read', 'edit', or 'owner'
        session: Database session, used to look up any share grant

    Raises:
        HTTPException: 403 if the user's effective level is below the
            required one; the caller decides whether to raise 404 instead
            for read-path existence hiding.
    """
    if not auth_settings.auth_enabled:
        return

    effective = effective_permission(prompt, user, session)
    if effective is None or _PERMISSION_RANK[effective] < _PERMISSION_RANK[level]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to perform this action on this prompt.",
        )


def reject_if_skill(prompt: Prompt | None, user: User | None, session: Session) -> None:
    """Refuse a prompt-only operation when the target is a skill (FR-003).

    A skill the caller cannot see is reported as not found (existence hidden,
    like any invisible item); a visible skill gets 409 ``ITEM_IS_SKILL``.
    Does nothing for a missing row or a prompt, so existing 404 handling in
    the caller is unchanged.

    Args:
        prompt: The target row, or None when it does not exist
        user: Acting user (None in anonymous mode)
        session: Database session, used to resolve permissions

    Raises:
        HTTPException: 404 when the skill is invisible to the caller
        ItemIsSkillError: 409 when the skill is visible to the caller
    """
    if prompt is None or prompt.item_type != "skill":
        return
    if (
        auth_settings.auth_enabled
        and effective_permission(prompt, user, session) is None
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt.id} not found",
        )
    raise ItemIsSkillError(context={"prompt_id": prompt.id})


def check_prompt_ownership(
    prompt: Prompt, user: User, session: Session | None = None
) -> None:
    """Check if user owns the prompt or is an admin.

    Kept as the owner-level entry point for existing callers; delegates to
    :func:`check_prompt_access` at the 'owner' level.

    Args:
        prompt: Prompt to check ownership of
        user: User attempting the operation
        session: Database session (unused at 'owner' level, kept for a
            uniform call signature with check_prompt_access)

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


def _parse_tags_field(tags: str | None) -> list[str]:
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
    user_id: str | None,
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


def _prompt_to_dict(
    prompt: Prompt,
    viewer: User | None = None,
    session: Session | None = None,
) -> dict:
    """Convert a Prompt row (prompt or skill) to a dictionary for API responses.

    A prompt item carries its ``prompt`` body. A skill item is a
    ``SkillSummary`` (contracts/skills-api.md): it deliberately omits ``prompt``
    so a large ``SKILL.md`` is never sent with a list page.

    When ``viewer`` and ``session`` are both provided, the payload gains the
    per-viewer sharing fields from contracts/sharing-api.md §4 (``shared``,
    ``legacy_public``, ``permission``). Omitted when either is absent so
    existing callers (e.g. the legacy dict-shaped data_service paths, which
    have no ORM Prompt/session to resolve grants against) are unaffected.

    Args:
        prompt: Prompt model instance
        viewer: The requesting user, for permission resolution (optional)
        session: Database session, for grant lookups (optional)

    Returns:
        dict: Item data formatted for API response
    """
    is_skill = prompt.item_type == "skill"
    result: dict = {
        "id": prompt.id,
        "item_type": "skill" if is_skill else "prompt",
        "title": prompt.title,
        "category": prompt.category.name if prompt.category else "",
        "category_color": prompt.category.color if prompt.category else None,
        "tags": [tag.name for tag in prompt.tags] if prompt.tags else [],
        "tag_colors": (
            {tag.name: tag.color for tag in prompt.tags} if prompt.tags else {}
        ),
        "favorite": prompt.favorite,
        "user_id": prompt.user_id,
        "created_at": prompt.created_at.isoformat() if prompt.created_at else None,
        "updated_at": prompt.updated_at.isoformat() if prompt.updated_at else None,
    }

    if is_skill:
        package = prompt.skill_package
        result.update(
            {
                "skill_identifier": package.skill_identifier if package else "",
                "description": package.description if package else None,
                "file_count": package.file_count if package else 0,
                "total_bytes": package.total_bytes if package else 0,
                "format_warnings": list(package.format_warnings) if package else [],
            }
        )
    else:
        result["prompt"] = prompt.prompt
        result["note"] = prompt.note or ""
        result["semantic_version"] = prompt.semantic_version

    if session is not None:
        result["legacy_public"] = bool(prompt.legacy_public)
        result["permission"] = effective_permission(prompt, viewer, session)
        result["shared"] = _has_explicit_grant(prompt, viewer, session)

    return result


def _has_explicit_grant(prompt: Prompt, viewer: User | None, session: Session) -> bool:
    """True only when an explicit PromptShare names this viewer.

    Never true for owner/admin access or legacy_public-only visibility —
    'shared' in API payloads means "someone explicitly granted me access",
    per contracts/sharing-api.md §4.
    """
    if viewer is None or prompt.user_id == viewer.id:
        return False

    from src.db.repositories.sharing_repository import SharingRepository

    return SharingRepository(session).permission_for(prompt.id, viewer.id) is not None


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
