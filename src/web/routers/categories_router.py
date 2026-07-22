# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Category management routes.

Split out from the original ``tag_category.py`` god-file. Contains every
``/categories/*`` endpoint. Route paths, methods, response models, and behavior
are unchanged.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.db.repositories.category_repository import CategoryRepository
from src.db.repositories.prompt_repository import PromptRepository
from src.web.dependencies.auth import get_current_user_or_none
from src.web.models.auth_responses import MessageResponse
from src.web.models.tag_category_requests import (
    CategoryCreateRequest,
    CategoryUpdateRequest,
    MergeRequest,
    BulkDeleteRequest,
    CategoryFindReplaceRequest,
    ReorderRequest,
    CategoryImportRequest,
    CategoryAssignOrphansRequest,
)
from src.web.models.tag_category_responses import (
    CategoryResponse,
    CategoryListResponse,
    BulkActionResponse,
    OrphanPromptsResponse,
    OrphanPromptDetailsResponse,
    OrphanPromptItem,
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


def _category_snapshot(category) -> dict:
    return {
        "name": category.name,
        "description": category.description,
        "color": category.color,
        "sort_order": category.sort_order,
    }


# ============================================================================
# Category Management
# ============================================================================


@router.get("/categories")
async def get_categories():
    """Get all categories (legacy compatibility endpoint)."""
    from src.web import app as web_app

    categories = web_app.data_service.get_categories()
    return {"categories": categories}


@router.get(
    "/categories/manage",
    response_model=CategoryListResponse,
    summary="List categories with metadata and usage counts",
)
async def list_categories_manage(
    user: Optional[User] = Depends(get_current_user_or_none),
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
    user: Optional[User] = Depends(get_current_user_or_none),
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
    user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    category_repo = CategoryRepository(db)
    category = category_repo.get_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    if payload.name:
        existing = category_repo.get_by_name_case_insensitive(payload.name)
        if existing and existing.id != category_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category name already exists",
            )

    before = _category_snapshot(category)
    updates = payload.model_dump(exclude_unset=True)
    category = category_repo.update(category_id, **updates)
    db.commit()
    db.refresh(category)
    usage_count = category_repo.count_usage(category_id)
    undo_service.push(
        user_id=user.id if user else None,
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
    user: Optional[User] = Depends(get_current_user_or_none),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    usage_count = category_repo.count_usage(category_id)
    prompt_ids = []
    if usage_count > 0:
        prompt_ids = category_repo.get_prompt_ids(category_id)
    if usage_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Category is in use. Use force=true to remove from prompts and delete.",
        )

    if usage_count > 0 and force:
        category_repo.clear_from_prompts(category_id)

    # Clear historical references to avoid FK violations on delete.
    category_repo.clear_from_prompt_versions(category_id)

    category_repo.delete(category_id)
    db.commit()
    undo_service.push(
        user_id=user.id if user else None,
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
    user: Optional[User] = Depends(get_current_user_or_none),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Target category not found"
        )

    if payload.target_id in payload.source_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target category cannot be included in source categories",
        )

    missing = [
        source_id
        for source_id in payload.source_ids
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
        prompt_ids = category_repo.get_prompt_ids(source_id)
        sources_payload.append(
            {"category": _category_snapshot(source), "prompt_ids": prompt_ids}
        )
    merged = category_repo.merge_categories(payload.source_ids, payload.target_id)
    db.commit()
    if sources_payload:
        undo_service.push(
            user_id=user.id if user else None,
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
    user: Optional[User] = Depends(get_current_user_or_none),
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
    delete_payloads = []
    for category_id in payload.ids:
        category = category_repo.get_by_id(category_id)
        if category:
            prompt_ids = category_repo.get_prompt_ids(category_id)
            delete_payloads.append(
                {"category": _category_snapshot(category), "prompt_ids": prompt_ids}
            )

    # Clear historical references to avoid FK violations on delete.
    category_repo.bulk_clear_from_prompt_versions(payload.ids)

    # Now clear category assignments if force=true
    if payload.force:
        category_repo.bulk_clear_from_prompts(payload.ids)

    deleted = category_repo.delete_many(payload.ids)
    db.commit()
    if delete_payloads:
        undo_service.push(
            user_id=user.id if user else None,
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
    user: Optional[User] = Depends(get_current_user_or_none),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )

    replace_category = category_repo.get_by_name_case_insensitive(payload.replace)
    if not replace_category:
        replace_category = category_repo.create(name=payload.replace)

    if find_category.id != replace_category.id:
        prompt_ids = category_repo.get_prompt_ids(find_category.id)
        category_repo.merge_categories([find_category.id], replace_category.id)
        undo_service.push(
            user_id=user.id if user else None,
            entity_type="category",
            operation="find-replace",
            payload={
                "target_id": replace_category.id,
                "sources": [
                    {
                        "category": _category_snapshot(find_category),
                        "prompt_ids": prompt_ids,
                    }
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
    user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    category_repo = CategoryRepository(db)
    categories = category_repo.get_all()
    category_ids = {category.id for category in categories}
    missing = [
        category_id
        for category_id in payload.ordered_ids
        if category_id not in category_ids
    ]
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
    user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    category_repo = CategoryRepository(db)
    prompt_ids = category_repo.get_orphan_prompt_ids()
    return OrphanPromptsResponse(prompt_ids=prompt_ids, count=len(prompt_ids))


@router.get(
    "/categories/orphans/details",
    response_model=OrphanPromptDetailsResponse,
    summary="List prompts without categories (detailed)",
)
async def category_orphans_details(
    user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    category_repo = CategoryRepository(db)
    prompts = category_repo.get_orphan_prompts()
    items = [OrphanPromptItem(id=row[0], title=row[1] or "") for row in prompts]
    return OrphanPromptDetailsResponse(items=items, count=len(items))


@router.get(
    "/categories/unused",
    response_model=CategoryListResponse,
    summary="List unused categories",
)
async def category_unused(
    user: Optional[User] = Depends(get_current_user_or_none),
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
    user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Confirmation required",
        )

    category_repo = CategoryRepository(db)
    prompt_repo = PromptRepository(db)
    category = category_repo.get_by_name_case_insensitive(payload.category)
    if not category:
        category = category_repo.create(name=payload.category)

    prompts = prompt_repo.get_by_ids(payload.prompt_ids)
    found_ids = {prompt.id for prompt in prompts}
    missing = [
        prompt_id for prompt_id in payload.prompt_ids if prompt_id not in found_ids
    ]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompts not found: {missing}",
        )

    affected = category_repo.assign_prompts(payload.prompt_ids, category.id)

    db.commit()
    return BulkActionResponse(success=True, affected=affected)


@router.get(
    "/categories/analytics",
    summary="Category usage analytics",
)
async def category_analytics(
    user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    category_repo = CategoryRepository(db)
    results = category_repo.list_all_with_counts()
    total = len(results)
    used = len([1 for _, count in results if (count or 0) > 0])
    unused = total - used
    top = [
        {"id": category.id, "name": category.name, "count": count or 0}
        for category, count in sorted(
            results, key=lambda item: (item[1] or 0), reverse=True
        )[:10]
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


@router.post(
    "/categories/undo",
    response_model=BulkActionResponse,
    summary="Undo last category management operation",
)
async def undo_category_operation(
    user: Optional[User] = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    op = undo_service.pop(user.id if user else None, "category")
    if not op:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No undo operation available"
        )

    category_repo = CategoryRepository(db)

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
                category_repo.restore_prompts_category(prompt_ids, category.id)
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
                category_repo.restore_prompts_category(prompt_ids, category.id)
            affected += 1
        db.commit()
        return BulkActionResponse(success=True, affected=affected)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Undo operation not supported",
    )


@router.get(
    "/categories/export",
    summary="Export category definitions",
)
async def export_categories(
    user: Optional[User] = Depends(get_current_user_or_none),
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
    user: Optional[User] = Depends(get_current_user_or_none),
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
