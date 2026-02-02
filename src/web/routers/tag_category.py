# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Category and tag management routes."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.db.repositories.category_repository import CategoryRepository
from src.db.repositories.tag_repository import TagRepository
from src.web.dependencies.auth import get_current_active_user
from src.web.models.auth_responses import MessageResponse
from src.web.models.tag_category_requests import (
    CategoryCreateRequest,
    CategoryUpdateRequest,
    TagCreateRequest,
    TagUpdateRequest,
    MergeRequest,
    BulkDeleteRequest,
    CategoryFindReplaceRequest,
    TagFindReplaceRequest,
    ReorderRequest,
    BulkTagUpdateRequest,
    TagSuggestRequest,
    CategoryImportRequest,
    TagImportRequest,
    CategoryAssignOrphansRequest,
)
from src.web.models.tag_category_responses import (
    CategoryResponse,
    TagResponse,
    CategoryListResponse,
    TagListResponse,
    BulkActionResponse,
    OrphanPromptsResponse,
    OrphanPromptDetailsResponse,
    OrphanPromptItem,
    TagSuggestionResponse,
    TagSuggestionItem,
)
from src.db.models.user import User
from src.services.undo_service import UndoService
from src.web.dependencies.undo import get_undo_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["Tag/Category Management"],
)


def _category_response(category, usage_count: int) -> CategoryResponse:
    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        color=category.color,
        sort_order=category.sort_order,
        created_at=category.created_at,
        updated_at=category.updated_at,
        usage_count=usage_count or 0,
    )


def _tag_response(tag, usage_count: int) -> TagResponse:
    return TagResponse(
        id=tag.id,
        name=tag.name,
        description=tag.description,
        color=tag.color,
        parent_tag_id=tag.parent_tag_id,
        created_at=tag.created_at,
        updated_at=tag.updated_at,
        usage_count=usage_count or 0,
    )


def _category_snapshot(category) -> dict:
    return {
        "name": category.name,
        "description": category.description,
        "color": category.color,
        "sort_order": category.sort_order,
    }


def _tag_snapshot(tag) -> dict:
    return {
        "name": tag.name,
        "description": tag.description,
        "color": tag.color,
        "parent_tag_id": tag.parent_tag_id,
    }


def _is_descendant(tag_repo: TagRepository, tag_id: int, potential_parent_id: int) -> bool:
    """Return True if potential_parent_id is a descendant of tag_id."""
    seen = set()
    current_id = potential_parent_id
    while current_id is not None and current_id not in seen:
        seen.add(current_id)
        if current_id == tag_id:
            return True
        current = tag_repo.get_by_id(current_id)
        if not current:
            return False
        current_id = current.parent_tag_id
    return False

# ============================================================================
# Category Management
# ============================================================================


@router.get(
    "/categories/manage",
    response_model=CategoryListResponse,
    summary="List categories with metadata and usage counts",
)
async def list_categories_manage(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    category_repo = CategoryRepository(db)
    results = category_repo.list_all_with_counts()
    items = [_category_response(category, count) for category, count in results]
    return CategoryListResponse(items=items)


@router.post(
    "/categories",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a category",
)
async def create_category(
    payload: CategoryCreateRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    category_repo = CategoryRepository(db)
    existing = category_repo.get_by_name_case_insensitive(payload.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category name already exists",
        )

    category = category_repo.create(
        name=payload.name,
        description=payload.description,
        color=payload.color,
        sort_order=payload.sort_order,
    )
    db.commit()
    db.refresh(category)
    usage_count = category_repo.count_usage(category.id)
    return _category_response(category, usage_count)


@router.put(
    "/categories/{category_id}",
    response_model=CategoryResponse,
    summary="Update a category",
)
async def update_category(
    category_id: int,
    payload: CategoryUpdateRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    category_repo = CategoryRepository(db)
    category = category_repo.get_by_id(category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if payload.name:
        existing = category_repo.get_by_name_case_insensitive(payload.name)
        if existing and existing.id != category_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category name already exists",
            )

    before = _category_snapshot(category)
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    category = category_repo.update(category_id, **updates)
    db.commit()
    db.refresh(category)
    usage_count = category_repo.count_usage(category_id)
    undo_service.push(
        user_id=user.id,
        entity_type="category",
        operation="update",
        payload={"id": category_id, "before": before},
    )
    db.commit()
    return _category_response(category, usage_count)


@router.delete(
    "/categories/{category_id}",
    response_model=MessageResponse,
    summary="Delete a category",
)
async def delete_category(
    category_id: int,
    force: bool = False,
    confirm: bool = False,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Confirmation required",
        )
    category_repo = CategoryRepository(db)
    category = category_repo.get_by_id(category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    usage_count = category_repo.count_usage(category_id)
    prompt_ids = []
    if usage_count > 0:
        from src.db.models import Prompt
        prompt_ids = [row[0] for row in db.query(Prompt.id).filter(Prompt.category_id == category_id).all()]
    if usage_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Category is in use. Use force=true to remove from prompts and delete.",
        )

    from src.db.models import Prompt, PromptVersion

    if usage_count > 0 and force:
        db.query(Prompt).filter(Prompt.category_id == category_id).update(
            {Prompt.category_id: None},
            synchronize_session=False,
        )

    # Clear historical references to avoid FK violations on delete.
    db.query(PromptVersion).filter(PromptVersion.category_id == category_id).update(
        {PromptVersion.category_id: None},
        synchronize_session=False,
    )

    category_repo.delete(category_id)
    db.commit()
    undo_service.push(
        user_id=user.id,
        entity_type="category",
        operation="delete",
        payload={"category": _category_snapshot(category), "prompt_ids": prompt_ids},
    )
    db.commit()
    return MessageResponse(message="Category deleted")


@router.post(
    "/categories/merge",
    response_model=BulkActionResponse,
    summary="Merge categories into a target category",
)
async def merge_categories(
    payload: MergeRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Confirmation required",
        )
    category_repo = CategoryRepository(db)
    target = category_repo.get_by_id(payload.target_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target category not found")

    if payload.target_id in payload.source_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target category cannot be included in source categories",
        )

    missing = [
        source_id for source_id in payload.source_ids
        if category_repo.get_by_id(source_id) is None
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source categories not found: {missing}",
        )

    sources_payload = []
    for source_id in payload.source_ids:
        source = category_repo.get_by_id(source_id)
        if not source:
            continue
        prompt_ids = []
        from src.db.models import Prompt
        prompt_ids = [row[0] for row in db.query(Prompt.id).filter(Prompt.category_id == source_id).all()]
        sources_payload.append(
            {"category": _category_snapshot(source), "prompt_ids": prompt_ids}
        )
    merged = category_repo.merge_categories(payload.source_ids, payload.target_id)
    db.commit()
    if sources_payload:
        undo_service.push(
            user_id=user.id,
            entity_type="category",
            operation="merge",
            payload={"target_id": payload.target_id, "sources": sources_payload},
        )
        db.commit()
    return BulkActionResponse(success=True, affected=merged)


@router.post(
    "/categories/bulk-delete",
    response_model=BulkActionResponse,
    summary="Bulk delete categories",
)
async def bulk_delete_categories(
    payload: BulkDeleteRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Confirmation required",
        )
    category_repo = CategoryRepository(db)
    blocked: List[int] = []

    for category_id in payload.ids:
        usage_count = category_repo.count_usage(category_id)
        if usage_count > 0 and not payload.force:
            blocked.append(category_id)

    if blocked:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Categories in use: {blocked}",
        )

    # Collect prompt_ids BEFORE clearing category assignments
    from src.db.models import Prompt
    delete_payloads = []
    for category_id in payload.ids:
        category = category_repo.get_by_id(category_id)
        if category:
            prompt_ids = [row[0] for row in db.query(Prompt.id).filter(Prompt.category_id == category_id).all()]
            delete_payloads.append({"category": _category_snapshot(category), "prompt_ids": prompt_ids})

    # Clear historical references to avoid FK violations on delete.
    from src.db.models import PromptVersion
    db.query(PromptVersion).filter(PromptVersion.category_id.in_(payload.ids)).update(
        {PromptVersion.category_id: None},
        synchronize_session=False,
    )

    # Now clear category assignments if force=true
    if payload.force:
        db.query(Prompt).filter(Prompt.category_id.in_(payload.ids)).update(
            {Prompt.category_id: None},
            synchronize_session=False,
        )

    deleted = category_repo.delete_many(payload.ids)
    db.commit()
    if delete_payloads:
        undo_service.push(
            user_id=user.id,
            entity_type="category",
            operation="bulk-delete",
            payload={"items": delete_payloads},
        )
        db.commit()
    return BulkActionResponse(success=True, affected=deleted)


@router.post(
    "/categories/find-replace",
    response_model=BulkActionResponse,
    summary="Find and replace a category name across prompts",
)
async def find_replace_categories(
    payload: CategoryFindReplaceRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Confirmation required",
        )

    category_repo = CategoryRepository(db)
    find_category = category_repo.get_by_name_case_insensitive(payload.find)
    if not find_category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    replace_category = category_repo.get_by_name_case_insensitive(payload.replace)
    if not replace_category:
        replace_category = category_repo.create(name=payload.replace)

    if find_category.id != replace_category.id:
        from src.db.models import Prompt
        prompt_ids = [row[0] for row in db.query(Prompt.id).filter(Prompt.category_id == find_category.id).all()]
        category_repo.merge_categories([find_category.id], replace_category.id)
        undo_service.push(
            user_id=user.id,
            entity_type="category",
            operation="find-replace",
            payload={
                "target_id": replace_category.id,
                "sources": [
                    {"category": _category_snapshot(find_category), "prompt_ids": prompt_ids}
                ],
            },
        )

    db.commit()
    return BulkActionResponse(success=True, affected=1)


@router.post(
    "/categories/reorder",
    response_model=BulkActionResponse,
    summary="Reorder categories",
)
async def reorder_categories(
    payload: ReorderRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    category_repo = CategoryRepository(db)
    categories = category_repo.get_all()
    category_ids = {category.id for category in categories}
    missing = [category_id for category_id in payload.ordered_ids if category_id not in category_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Categories not found: {missing}",
        )

    for order, category_id in enumerate(payload.ordered_ids, start=1):
        category_repo.update(category_id, sort_order=order)

    db.commit()
    return BulkActionResponse(success=True, affected=len(payload.ordered_ids))


@router.get(
    "/categories/orphans",
    response_model=OrphanPromptsResponse,
    summary="List prompts without categories",
)
async def category_orphans(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from src.db.models import Prompt

    results = db.query(Prompt.id).filter(Prompt.category_id.is_(None)).all()
    prompt_ids = [row[0] for row in results]
    return OrphanPromptsResponse(prompt_ids=prompt_ids, count=len(prompt_ids))


@router.get(
    "/categories/orphans/details",
    response_model=OrphanPromptDetailsResponse,
    summary="List prompts without categories (detailed)",
)
async def category_orphans_details(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from src.db.models import Prompt

    prompts = db.query(Prompt.id, Prompt.title).filter(Prompt.category_id.is_(None)).all()
    items = [OrphanPromptItem(id=row[0], title=row[1] or "") for row in prompts]
    return OrphanPromptDetailsResponse(items=items, count=len(items))


@router.get(
    "/categories/unused",
    response_model=CategoryListResponse,
    summary="List unused categories",
)
async def category_unused(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    category_repo = CategoryRepository(db)
    results = category_repo.list_all_with_counts()
    items = [
        _category_response(category, count)
        for category, count in results
        if (count or 0) == 0
    ]
    return CategoryListResponse(items=items)


@router.post(
    "/categories/assign-orphans",
    response_model=BulkActionResponse,
    summary="Assign orphan prompts to a category",
)
async def assign_category_orphans(
    payload: CategoryAssignOrphansRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Confirmation required",
        )

    from src.db.models import Prompt

    category_repo = CategoryRepository(db)
    category = category_repo.get_by_name_case_insensitive(payload.category)
    if not category:
        category = category_repo.create(name=payload.category)

    prompts = db.query(Prompt).filter(Prompt.id.in_(payload.prompt_ids)).all()
    found_ids = {prompt.id for prompt in prompts}
    missing = [prompt_id for prompt_id in payload.prompt_ids if prompt_id not in found_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompts not found: {missing}",
        )

    for prompt in prompts:
        prompt.category_id = category.id

    db.commit()
    return BulkActionResponse(success=True, affected=len(prompts))


@router.get(
    "/categories/analytics",
    summary="Category usage analytics",
)
async def category_analytics(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    category_repo = CategoryRepository(db)
    results = category_repo.list_all_with_counts()
    total = len(results)
    used = len([1 for _, count in results if (count or 0) > 0])
    unused = total - used
    top = [
        {"id": category.id, "name": category.name, "count": count or 0}
        for category, count in sorted(results, key=lambda item: (item[1] or 0), reverse=True)[:10]
    ]
    bottom = [
        {"id": category.id, "name": category.name, "count": count or 0}
        for category, count in sorted(results, key=lambda item: (item[1] or 0))[:10]
    ]
    return {
        "total": total,
        "used": used,
        "unused": unused,
        "top": top,
        "bottom": bottom,
    }


# ============================================================================
# Tag Management
# ============================================================================


@router.get(
    "/tags/manage",
    response_model=TagListResponse,
    summary="List tags with metadata and usage counts",
)
async def list_tags_manage(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    tag_repo = TagRepository(db)
    results = tag_repo.list_all_with_counts()
    items = [_tag_response(tag, count) for tag, count in results]
    return TagListResponse(items=items)


@router.post(
    "/tags",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tag",
)
async def create_tag(
    payload: TagCreateRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    tag_repo = TagRepository(db)
    existing = tag_repo.get_by_name_case_insensitive(payload.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tag name already exists",
        )

    if payload.parent_tag_id is not None:
        parent = tag_repo.get_by_id(payload.parent_tag_id)
        if not parent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parent tag not found",
            )

    tag = tag_repo.create(
        name=payload.name,
        description=payload.description,
        color=payload.color,
        parent_tag_id=payload.parent_tag_id,
    )
    db.commit()
    db.refresh(tag)
    usage_count = tag_repo.count_usage(tag.id)
    return _tag_response(tag, usage_count)


@router.put(
    "/tags/{tag_id}",
    response_model=TagResponse,
    summary="Update a tag",
)
async def update_tag(
    tag_id: int,
    payload: TagUpdateRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    tag_repo = TagRepository(db)
    tag = tag_repo.get_by_id(tag_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    if payload.name:
        existing = tag_repo.get_by_name_case_insensitive(payload.name)
        if existing and existing.id != tag_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tag name already exists",
            )

    before = _tag_snapshot(tag)
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)
    if "parent_tag_id" in updates:
        parent_id = updates["parent_tag_id"]
        if parent_id is not None:
            parent = tag_repo.get_by_id(parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent tag not found",
                )
            if parent_id == tag_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Tag cannot be its own parent",
                )
            if _is_descendant(tag_repo, tag_id, parent_id):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Tag hierarchy cycle detected",
                )
    tag = tag_repo.update(tag_id, **updates)
    db.commit()
    db.refresh(tag)
    usage_count = tag_repo.count_usage(tag_id)
    undo_service.push(
        user_id=user.id,
        entity_type="tag",
        operation="update",
        payload={"id": tag_id, "before": before},
    )
    db.commit()
    return _tag_response(tag, usage_count)


@router.delete(
    "/tags/{tag_id}",
    response_model=MessageResponse,
    summary="Delete a tag",
)
async def delete_tag(
    tag_id: int,
    force: bool = False,
    confirm: bool = False,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Confirmation required",
        )
    tag_repo = TagRepository(db)
    tag = tag_repo.get_by_id(tag_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    usage_count = tag_repo.count_usage(tag_id)
    prompt_ids = [prompt.id for prompt in tag.prompts] if tag.prompts else []
    if usage_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Tag is in use. Use force=true to remove from prompts and delete.",
        )

    if usage_count > 0 and force:
        tag.prompts.clear()

    tag_repo.delete(tag_id)
    db.commit()
    undo_service.push(
        user_id=user.id,
        entity_type="tag",
        operation="delete",
        payload={"tag": _tag_snapshot(tag), "prompt_ids": prompt_ids},
    )
    db.commit()
    return MessageResponse(message="Tag deleted")


@router.post(
    "/tags/merge",
    response_model=BulkActionResponse,
    summary="Merge tags into a target tag",
)
async def merge_tags(
    payload: MergeRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Confirmation required",
        )
    tag_repo = TagRepository(db)
    target = tag_repo.get_by_id(payload.target_id)
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target tag not found")

    missing = [
        source_id for source_id in payload.source_ids
        if tag_repo.get_by_id(source_id) is None
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source tags not found: {missing}",
        )

    sources_payload = []
    # Track which prompts already have the target tag before merge
    target_prompt_ids = {prompt.id for prompt in target.prompts}

    for source_id in payload.source_ids:
        source = tag_repo.get_by_id(source_id)
        if not source:
            continue
        prompt_ids = [prompt.id for prompt in source.prompts]
        # Track which prompts will gain the target tag (didn't have it before)
        prompts_gaining_target = [pid for pid in prompt_ids if pid not in target_prompt_ids]
        sources_payload.append({
            "tag": _tag_snapshot(source),
            "prompt_ids": prompt_ids,
            "prompts_gaining_target": prompts_gaining_target
        })

    merged = tag_repo.merge_tags_bulk(payload.source_ids, payload.target_id)
    db.commit()
    if sources_payload:
        undo_service.push(
            user_id=user.id,
            entity_type="tag",
            operation="merge",
            payload={"target_id": payload.target_id, "sources": sources_payload},
        )
        db.commit()
    return BulkActionResponse(success=True, affected=merged)


@router.post(
    "/tags/bulk-delete",
    response_model=BulkActionResponse,
    summary="Bulk delete tags",
)
async def bulk_delete_tags(
    payload: BulkDeleteRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Confirmation required",
        )
    tag_repo = TagRepository(db)
    blocked: List[int] = []

    for tag_id in payload.ids:
        usage_count = tag_repo.count_usage(tag_id)
        if usage_count > 0 and not payload.force:
            blocked.append(tag_id)

    if blocked:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Tags in use: {blocked}",
        )

    # Collect prompt_ids for all tags BEFORE clearing associations
    from sqlalchemy import select, delete
    from src.db.models.associations import prompt_tags

    delete_payloads = []
    for tag_id in payload.ids:
        tag = tag_repo.get_by_id(tag_id)
        if tag:
            prompt_ids = [
                row[0] for row in db.execute(
                    select(prompt_tags.c.prompt_id).where(prompt_tags.c.tag_id == tag_id)
                ).all()
            ]
            delete_payloads.append({"tag": _tag_snapshot(tag), "prompt_ids": prompt_ids})

    # THEN clear tag-prompt associations if force=true
    if payload.force:
        db.execute(
            delete(prompt_tags).where(prompt_tags.c.tag_id.in_(payload.ids))
        )

    deleted = tag_repo.delete_many(payload.ids)
    db.commit()
    if delete_payloads:
        undo_service.push(
            user_id=user.id,
            entity_type="tag",
            operation="bulk-delete",
            payload={"items": delete_payloads},
        )
        db.commit()
    return BulkActionResponse(success=True, affected=deleted)


@router.post(
    "/tags/find-replace",
    response_model=BulkActionResponse,
    summary="Find and replace a tag name across prompts",
)
async def find_replace_tags(
    payload: TagFindReplaceRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Confirmation required",
        )

    tag_repo = TagRepository(db)
    find_tag = tag_repo.get_by_name_case_insensitive(payload.find)
    if not find_tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    replace_tag = tag_repo.get_by_name_case_insensitive(payload.replace)
    if not replace_tag:
        replace_tag = tag_repo.create(name=payload.replace)

    if find_tag.id != replace_tag.id:
        prompt_ids = [prompt.id for prompt in find_tag.prompts]
        # Track which prompts already have the replace tag before merge
        replace_prompt_ids = {prompt.id for prompt in replace_tag.prompts}
        prompts_gaining_target = [pid for pid in prompt_ids if pid not in replace_prompt_ids]
        tag_repo.merge_tags(find_tag.id, replace_tag.id)
        undo_service.push(
            user_id=user.id,
            entity_type="tag",
            operation="find-replace",
            payload={
                "target_id": replace_tag.id,
                "sources": [
                    {
                        "tag": _tag_snapshot(find_tag),
                        "prompt_ids": prompt_ids,
                        "prompts_gaining_target": prompts_gaining_target
                    }
                ],
            },
        )

    db.commit()
    return BulkActionResponse(success=True, affected=1)


@router.get(
    "/tags/orphans",
    response_model=TagListResponse,
    summary="List unused tags",
)
async def tag_orphans(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    tag_repo = TagRepository(db)
    results = tag_repo.list_all_with_counts()
    items = [
        _tag_response(tag, count)
        for tag, count in results
        if (count or 0) == 0
    ]
    return TagListResponse(items=items)


@router.get(
    "/tags/orphan-prompts",
    response_model=OrphanPromptsResponse,
    summary="List prompts without tags",
)
async def tag_orphan_prompts(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from src.db.models import Prompt, prompt_tags

    results = (
        db.query(Prompt.id)
        .outerjoin(prompt_tags, Prompt.id == prompt_tags.c.prompt_id)
        .filter(prompt_tags.c.tag_id.is_(None))
        .all()
    )
    prompt_ids = [row[0] for row in results]
    return OrphanPromptsResponse(prompt_ids=prompt_ids, count=len(prompt_ids))


@router.get(
    "/tags/orphan-prompts/details",
    response_model=OrphanPromptDetailsResponse,
    summary="List prompts without tags (detailed)",
)
async def tag_orphan_prompts_details(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from src.db.models import Prompt, prompt_tags

    prompts = (
        db.query(Prompt.id, Prompt.title)
        .outerjoin(prompt_tags, Prompt.id == prompt_tags.c.prompt_id)
        .filter(prompt_tags.c.tag_id.is_(None))
        .all()
    )
    items = [OrphanPromptItem(id=row[0], title=row[1] or "") for row in prompts]
    return OrphanPromptDetailsResponse(items=items, count=len(items))


@router.get(
    "/tags/analytics",
    summary="Tag usage analytics",
)
async def tag_analytics(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    tag_repo = TagRepository(db)
    results = tag_repo.list_all_with_counts()
    total = len(results)
    used = len([1 for _, count in results if (count or 0) > 0])
    unused = total - used
    top = [
        {"id": tag.id, "name": tag.name, "count": count or 0}
        for tag, count in sorted(results, key=lambda item: (item[1] or 0), reverse=True)[:10]
    ]
    bottom = [
        {"id": tag.id, "name": tag.name, "count": count or 0}
        for tag, count in sorted(results, key=lambda item: (item[1] or 0))[:10]
    ]
    co_occurrence = []
    try:
        from sqlalchemy.orm import joinedload
        from src.db.models import Prompt

        prompts = db.query(Prompt).options(joinedload(Prompt.tags)).all()
        pair_counts = {}
        for prompt in prompts:
            tag_names = sorted({tag.name for tag in prompt.tags})
            for i, tag_a in enumerate(tag_names):
                for tag_b in tag_names[i + 1 :]:
                    key = (tag_a, tag_b)
                    pair_counts[key] = pair_counts.get(key, 0) + 1
        for (tag_a, tag_b), count in sorted(pair_counts.items(), key=lambda item: item[1], reverse=True)[:50]:
            co_occurrence.append({"tag_a": tag_a, "tag_b": tag_b, "count": count})
    except Exception:
        logger.warning("Failed to compute tag co-occurrence", exc_info=True)
    return {
        "total": total,
        "used": used,
        "unused": unused,
        "top": top,
        "bottom": bottom,
        "co_occurrence": co_occurrence,
    }


@router.post(
    "/categories/undo",
    response_model=BulkActionResponse,
    summary="Undo last category management operation",
)
async def undo_category_operation(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    op = undo_service.pop(user.id, "category")
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No undo operation available")

    category_repo = CategoryRepository(db)
    from src.db.models import Prompt

    if op["operation"] == "update":
        category_repo.update(op["payload"]["id"], **op["payload"]["before"])
        db.commit()
        return BulkActionResponse(success=True, affected=1)

    if op["operation"] in {"delete", "merge", "find-replace"}:
        sources = op["payload"].get("sources")
        if not sources and "category" in op["payload"]:
            sources = [op["payload"]]
        affected = 0
        for source in sources:
            category_data = source["category"]
            existing = category_repo.get_by_name_case_insensitive(category_data["name"])
            if existing:
                category = existing
            else:
                category = category_repo.create(**category_data)
            prompt_ids = source.get("prompt_ids", [])
            if prompt_ids:
                db.query(Prompt).filter(Prompt.id.in_(prompt_ids)).update(
                    {Prompt.category_id: category.id},
                    synchronize_session=False,
                )
            affected += 1
        db.commit()
        return BulkActionResponse(success=True, affected=affected)

    if op["operation"] == "bulk-delete":
        affected = 0
        for item in op["payload"].get("items", []):
            category_data = item["category"]
            existing = category_repo.get_by_name_case_insensitive(category_data["name"])
            if existing:
                category = existing
            else:
                category = category_repo.create(**category_data)
            prompt_ids = item.get("prompt_ids", [])
            if prompt_ids:
                db.query(Prompt).filter(Prompt.id.in_(prompt_ids)).update(
                    {Prompt.category_id: category.id},
                    synchronize_session=False,
                )
            affected += 1
        db.commit()
        return BulkActionResponse(success=True, affected=affected)

    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Undo operation not supported")


@router.post(
    "/tags/undo",
    response_model=BulkActionResponse,
    summary="Undo last tag management operation",
)
async def undo_tag_operation(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    op = undo_service.pop(user.id, "tag")
    if not op:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No undo operation available")

    tag_repo = TagRepository(db)
    from src.db.models import Prompt

    if op["operation"] == "update":
        tag_repo.update(op["payload"]["id"], **op["payload"]["before"])
        db.commit()
        return BulkActionResponse(success=True, affected=1)

    if op["operation"] in {"delete", "merge", "find-replace"}:
        sources = op["payload"].get("sources")
        if not sources and "tag" in op["payload"]:
            sources = [op["payload"]]
        affected = 0
        target_id = op["payload"].get("target_id")
        target_tag = tag_repo.get_by_id(target_id) if target_id else None
        for source in sources:
            tag_data = source["tag"]
            existing = tag_repo.get_by_name_case_insensitive(tag_data["name"])
            if existing:
                tag = existing
            else:
                tag = tag_repo.create(**tag_data)
            prompt_ids = source.get("prompt_ids", [])
            if prompt_ids:
                prompts = db.query(Prompt).filter(Prompt.id.in_(prompt_ids)).all()
                # Get list of prompts that gained the target tag during merge
                prompts_gaining_target = source.get("prompts_gaining_target", [])
                prompts_gaining_target_set = set(prompts_gaining_target)
                for prompt in prompts:
                    if tag not in prompt.tags:
                        prompt.tags.append(tag)
                    # Only remove target tag from prompts that gained it during merge
                    if target_tag and target_tag in prompt.tags and prompt.id in prompts_gaining_target_set:
                        prompt.tags.remove(target_tag)
            affected += 1
        db.commit()
        return BulkActionResponse(success=True, affected=affected)

    if op["operation"] == "bulk-delete":
        affected = 0
        for item in op["payload"].get("items", []):
            tag_data = item["tag"]
            existing = tag_repo.get_by_name_case_insensitive(tag_data["name"])
            if existing:
                tag = existing
            else:
                tag = tag_repo.create(**tag_data)
            prompt_ids = item.get("prompt_ids", [])
            if prompt_ids:
                prompts = db.query(Prompt).filter(Prompt.id.in_(prompt_ids)).all()
                for prompt in prompts:
                    if tag not in prompt.tags:
                        prompt.tags.append(tag)
            affected += 1
        db.commit()
        return BulkActionResponse(success=True, affected=affected)

    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Undo operation not supported")


@router.post(
    "/tags/bulk-update",
    response_model=BulkActionResponse,
    summary="Bulk add/remove tags across prompts",
)
async def bulk_update_tags(
    payload: BulkTagUpdateRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Confirmation required",
        )

    from src.db.models import Prompt

    prompts = db.query(Prompt).filter(Prompt.id.in_(payload.prompt_ids)).all()
    found_ids = {prompt.id for prompt in prompts}
    missing = [prompt_id for prompt_id in payload.prompt_ids if prompt_id not in found_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompts not found: {missing}",
        )

    tag_repo = TagRepository(db)
    tags_to_add = tag_repo.get_or_create_many(payload.add) if payload.add else []

    tags_to_remove = []
    if payload.remove:
        for tag_name in payload.remove:
            tag = tag_repo.get_by_name_case_insensitive(tag_name)
            if tag:
                tags_to_remove.append(tag)

    for prompt in prompts:
        for tag in tags_to_add:
            if tag not in prompt.tags:
                prompt.tags.append(tag)
        for tag in tags_to_remove:
            if tag in prompt.tags:
                prompt.tags.remove(tag)

    db.commit()
    return BulkActionResponse(success=True, affected=len(prompts))


@router.post(
    "/tags/suggest",
    response_model=TagSuggestionResponse,
    summary="Suggest tags based on prompt content",
)
async def suggest_tags(
    payload: TagSuggestRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    from src.db.models import Prompt
    from src.services.tag_suggestion_service import suggest_tags as suggest_tags_service

    content = payload.content
    if payload.prompt_id is not None and not content:
        prompt = db.query(Prompt).filter(Prompt.id == payload.prompt_id).first()
        if not prompt:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
        content = prompt.prompt or ""

    tag_repo = TagRepository(db)
    existing_tags = [tag.name for tag in tag_repo.get_all()]
    suggestions = suggest_tags_service(content or "", existing_tags, limit=payload.limit)
    items = [TagSuggestionItem(name=name, score=score) for name, score in suggestions]
    return TagSuggestionResponse(suggestions=items)


@router.get(
    "/categories/export",
    summary="Export category definitions",
)
async def export_categories(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    category_repo = CategoryRepository(db)
    categories = category_repo.get_all()
    items = [
        {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "color": category.color,
            "sort_order": category.sort_order,
            "created_at": category.created_at,
            "updated_at": category.updated_at,
        }
        for category in categories
    ]
    return {"items": items}


@router.post(
    "/categories/import",
    response_model=BulkActionResponse,
    summary="Import category definitions",
)
async def import_categories(
    payload: CategoryImportRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    category_repo = CategoryRepository(db)
    created = 0
    updated = 0

    for item in payload.items:
        existing = category_repo.get_by_name_case_insensitive(item.name)
        if existing:
            category_repo.update(
                existing.id,
                description=item.description,
                color=item.color,
                sort_order=item.sort_order,
            )
            updated += 1
            continue

        category_repo.create(
            name=item.name,
            description=item.description,
            color=item.color,
            sort_order=item.sort_order,
        )
        created += 1

    db.commit()
    return BulkActionResponse(success=True, affected=created + updated)


@router.get(
    "/tags/export",
    summary="Export tag definitions",
)
async def export_tags(
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    tag_repo = TagRepository(db)
    tags = tag_repo.get_all()
    items = [
        {
            "id": tag.id,
            "name": tag.name,
            "description": tag.description,
            "color": tag.color,
            "created_at": tag.created_at,
            "updated_at": tag.updated_at,
        }
        for tag in tags
    ]
    return {"items": items}


@router.post(
    "/tags/import",
    response_model=BulkActionResponse,
    summary="Import tag definitions",
)
async def import_tags(
    payload: TagImportRequest,
    user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    tag_repo = TagRepository(db)
    created = 0
    updated = 0

    for item in payload.items:
        existing = tag_repo.get_by_name_case_insensitive(item.name)
        if existing:
            if item.parent_tag_id is not None:
                if item.parent_tag_id == existing.id:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Tag cannot be its own parent",
                    )
                if _is_descendant(tag_repo, existing.id, item.parent_tag_id):
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail="Tag hierarchy cycle detected",
                    )
                parent = tag_repo.get_by_id(item.parent_tag_id)
                if not parent:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Parent tag not found",
                    )
            tag_repo.update(
                existing.id,
                description=item.description,
                color=item.color,
                parent_tag_id=item.parent_tag_id,
            )
            updated += 1
            continue

        parent_id = item.parent_tag_id
        if parent_id is not None:
            parent = tag_repo.get_by_id(parent_id)
            if not parent:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Parent tag not found",
                )
        tag_repo.create(
            name=item.name,
            description=item.description,
            color=item.color,
            parent_tag_id=parent_id,
        )
        created += 1

    db.commit()
    return BulkActionResponse(success=True, affected=created + updated)
