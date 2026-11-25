# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Prompt CRUD routes (get / create / update / delete / favorite / copy).

Split out from the original ``prompts.py`` god-file. Route paths, methods,
authorization, and response shapes are unchanged. The internal registration
order (notably ``/bulk`` before ``/{prompt_id}``) is preserved from the
original file.
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.config.auth_config import auth_settings
from src.db.models.user import User
from src.db.repositories.category_repository import CategoryRepository
from src.db.repositories.prompt_repository import PromptRepository
from src.db.repositories.tag_repository import TagRepository
from src.db.repositories.version_repository import VersionRepository
from src.db.session import get_db
from src.services.exceptions import ShareGrantError
from src.services.skills.skill_service import prepare_skill_deleted_audit
from src.web.dependencies.auth import (
    get_admin_or_bypass,
    get_current_user_or_default,
    get_current_user_or_none,
    get_optional_user,
)
from src.web.middleware.rate_limit import bulk_limit, limiter, write_limit
from src.web.models.requests import (
    BulkDeleteRequest,
    PromptCreateRequest,
    PromptUpdateRequest,
)
from src.web.models.sharing_requests import PromptVisibilityUpdateRequest
from src.web.routers.prompts_shared import (
    _log_prompt_action,
    _parse_semver,
    _parse_tags_field,
    _prompt_to_dict,
    check_prompt_access,
    check_prompt_ownership,
    effective_permission,
    reject_if_skill,
)

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/prompts",
    tags=["Prompts"],
)


@router.get(
    "/{prompt_id}",
    summary="Get prompt by ID",
    description="""
    Get a specific prompt by ID.

    **Access:**
    - Anonymous mode (AUTH_ENABLED=false): anyone can view (legacy behavior)
    - Authenticated: owner, admin, any share grantee, or a legacy_public
      prompt (`read` level or above); otherwise 404 (existence hidden)

    **Response:**
    - Returns complete prompt data
    - Includes category, tags, metadata, and the viewer's `shared`,
      `legacy_public`, and `permission` fields
    """,
    responses={
        200: {"description": "Prompt retrieved successfully"},
        404: {"description": "Prompt not found or invisible to requester"},
    },
)
async def get_prompt(
    prompt_id: int,
    user: User | None = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    """Get a specific prompt by ID (read-level access).

    Args:
        prompt_id: Prompt ID
        user: Authenticated user (optional)
        db: Database session

    Returns:
        dict: Prompt data

    Raises:
        HTTPException: 404 if prompt not found or invisible to requester
    """
    prompt_repo = PromptRepository(db)

    prompt = prompt_repo.get_with_relationships(prompt_id)

    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found",
        )

    if auth_settings.auth_enabled and effective_permission(prompt, user, db) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found",
        )

    return _prompt_to_dict(prompt, viewer=user, session=db)


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
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(write_limit)
async def create_prompt(
    request: Request,
    response: Response,
    title: str = Form(...),
    prompt: str = Form(...),
    category: str = Form(""),
    tags: str = Form(""),
    commit_message: str = Form("Initial commit"),
    semantic_version: str = Form(""),
    user: User | None = Depends(get_current_user_or_none),
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
    new_prompt = prompt_repo.create_with_tags(
        tag_objects,
        title=validated_data.title,
        prompt=validated_data.prompt,
        category_id=category_obj.id if category_obj else None,
        note="",
        favorite=False,
        semantic_version=validated_data.semantic_version,
        user_id=user.id if user else None,
        created_at=datetime.now(UTC),
    )
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
    prompt_repo.create_main_branch(new_prompt.id, version.version_id)
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
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(write_limit)
async def update_prompt(
    prompt_id: int,
    request: Request,
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

    reject_if_skill(existing_prompt, user, db)

    # Content/category/tags are editable at 'edit' level (owner, admin, or
    # an edit-grantee); a read-only grant or legacy_public-only visibility
    # is insufficient (data-model.md's action table).
    check_prompt_access(existing_prompt, user, "edit", db)

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
        except ValueError, AttributeError:
            pass

    # Update prompt
    update_fields = {
        "title": validated_data.title,
        "prompt": validated_data.prompt,
        "category_id": category_obj.id if category_obj else None,
        "updated_at": datetime.now(UTC),
    }
    if validated_data.semantic_version is not None:
        update_fields["semantic_version"] = validated_data.semantic_version

    existing_prompt = prompt_repo.apply_update(
        instance=existing_prompt, tags=tag_objects, **update_fields
    )

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
        main_branch = prompt_repo.create_main_branch(
            existing_prompt.id, version.version_id
        )

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


@router.patch(
    "/{prompt_id}",
    summary="Un-grandfather a legacy-public prompt",
    description="""
    Flip a legacy-public prompt to private (owner + admin + explicit grants
    only). One-way — there is no path back to `legacy_public: true`.

    **Authorization:** prompt owner or admin only (`owner` level) — same as
    favorite/delete.

    **Behavior:**
    - Creates no `PromptShare` rows; a user who could previously view the
      prompt only via `legacy_public` loses that access immediately.
    """,
    responses={
        200: {"description": "Prompt un-grandfathered"},
        400: {
            "description": "legacy_public: true submitted (one-way) or prompt already private"
        },
        403: {"description": "Requester is neither owner nor admin"},
        404: {"description": "Prompt not found or invisible"},
        422: {"description": "Validation failed"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(write_limit)
async def update_prompt_visibility(
    prompt_id: int,
    body: PromptVisibilityUpdateRequest,
    request: Request,
    response: Response,
    user: User = Depends(get_current_user_or_default),
    db: Session = Depends(get_db),
):
    """Un-grandfather a legacy-public prompt (owner or admin only).

    Args:
        prompt_id: Prompt ID
        body: Request body — only `legacy_public: false` is accepted
        user: Authenticated user
        db: Database session

    Returns:
        dict: Updated prompt payload

    Raises:
        HTTPException: 400 if `legacy_public: true` submitted or the prompt
            is already private; 403 if not owner/admin; 404 if not found
    """
    if body.legacy_public is True:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="legacy_public cannot be set back to true (one-way transition)",
        )

    prompt_repo = PromptRepository(db)
    existing_prompt = prompt_repo.get_by_id(prompt_id)
    if not existing_prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found",
        )

    reject_if_skill(existing_prompt, user, db)
    check_prompt_access(existing_prompt, user, "owner", db)

    from src.web import app as web_app

    assert (
        web_app.data_service is not None
    ), "configure_services() must run before requests"
    try:
        web_app.data_service.set_legacy_public(prompt_id, acting_user=user)
    except ShareGrantError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.user_message,
        ) from exc

    db.refresh(existing_prompt)
    return _prompt_to_dict(existing_prompt, viewer=user, session=db)


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
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(bulk_limit)
async def bulk_delete_prompts(
    request: Request,
    response: Response,
    body: BulkDeleteRequest,
    admin: User | None = Depends(get_admin_or_bypass),
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
    pending_audits = []

    for prompt_id in body.prompt_ids:
        try:
            # Check if prompt exists
            prompt = prompt_repo.get_by_id(prompt_id)
            if prompt:
                emit_audit = prepare_skill_deleted_audit(
                    prompt, actor=admin.username if admin else None
                )
                prompt_repo.delete(prompt_id)
                pending_audits.append(emit_audit)
                deleted_count += 1
            else:
                failed_count += 1
                failed_ids.append(prompt_id)
        except Exception as e:
            logger.error(f"Failed to delete prompt {prompt_id}: {str(e)}")
            failed_count += 1
            failed_ids.append(prompt_id)

    db.commit()

    # Skill audit events are written only after the commit (FR-025a).
    for emit_audit in pending_audits:
        emit_audit()

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
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(write_limit)
async def delete_prompt(
    prompt_id: int,
    request: Request,
    response: Response,
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

    # A skill is audited as skill.delete (FR-025a); prompts are unaffected.
    emit_audit = prepare_skill_deleted_audit(existing_prompt, actor=user.username)

    # Delete prompt (cascade deletes versions, tags associations)
    prompt_repo.delete(prompt_id)
    db.commit()
    emit_audit()

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

    # Skills change favorite through PATCH /api/skills/{id}, which applies the
    # owner-only skill policy (FR-003).
    reject_if_skill(existing_prompt, user, db)

    # Check ownership (only owner can toggle favorite)
    check_prompt_ownership(existing_prompt, user)

    # Toggle favorite
    new_favorite_status = not existing_prompt.favorite
    prompt_repo.update(
        prompt_id,
        favorite=new_favorite_status,
        updated_at=datetime.now(UTC),
    )

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
    user: User | None = Depends(get_optional_user),
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

    reject_if_skill(prompt, user, db)

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
