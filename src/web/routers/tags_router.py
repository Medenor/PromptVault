# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tag management routes.

Split out from the original ``tag_category.py`` god-file. Contains every
``/tags/*`` endpoint. Route paths, methods, response models, and behavior are
unchanged.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.config.auth_config import auth_settings
from src.db.models.user import User
from src.db.repositories.prompt_repository import PromptRepository
from src.db.repositories.tag_repository import TagRepository
from src.db.session import get_db
from src.services.undo_service import UndoService
from src.web.dependencies.auth import get_current_user_or_none
from src.web.dependencies.undo import get_undo_service
from src.web.models.auth_responses import MessageResponse
from src.web.models.tag_category_requests import (
    BulkDeleteRequest,
    BulkTagUpdateRequest,
    MergeRequest,
    TagCreateRequest,
    TagFindReplaceRequest,
    TagImportRequest,
    TagSuggestRequest,
    TagUpdateRequest,
)
from src.web.models.tag_category_responses import (
    BulkActionResponse,
    OrphanPromptDetailsResponse,
    OrphanPromptItem,
    OrphanPromptsResponse,
    TagListResponse,
    TagResponse,
    TagSuggestionItem,
    TagSuggestionResponse,
)
from src.web.routers.prompts_shared import check_prompt_ownership

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["Tag/Category Management"],
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


def _tag_snapshot(tag) -> dict:
    return {
        "name": tag.name,
        "description": tag.description,
        "color": tag.color,
        "parent_tag_id": tag.parent_tag_id,
    }


def _is_descendant(
    tag_repo: TagRepository, tag_id: int, potential_parent_id: int
) -> bool:
    """Return True if potential_parent_id is a descendant of tag_id."""
    seen = set()
    current_id: int | None = potential_parent_id
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
# Tag Management
# ============================================================================


@router.get("/tags")
async def get_tags():
    """Get all tags with usage counts (legacy compatibility endpoint)."""
    try:
        from src.db.repositories.tag_repository import TagRepository
        from src.db.session import get_db_session

        with get_db_session() as session:
            tag_repo = TagRepository(session)
            results = tag_repo.list_all_with_counts()
            tags_with_counts = [
                {"name": tag.name, "count": count or 0} for tag, count in results
            ]
            return {"tags": tags_with_counts}
    except Exception:
        from src.web import app as web_app

        tags_with_counts = web_app.data_service.get_tags_with_counts()
        return {"tags": tags_with_counts}


@router.get(
    "/tags/manage",
    response_model=TagListResponse,
    summary="List tags with metadata and usage counts",
)
async def list_tags_manage(
    user: User | None = Depends(get_current_user_or_none),
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
    user: User | None = Depends(get_current_user_or_none),
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
    user: User | None = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    tag_repo = TagRepository(db)
    tag = tag_repo.get_by_id(tag_id)
    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )

    if payload.name:
        existing = tag_repo.get_by_name_case_insensitive(payload.name)
        if existing and existing.id != tag_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tag name already exists",
            )

    before = _tag_snapshot(tag)
    updates = payload.model_dump(exclude_unset=True)
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
        user_id=user.id if user else None,
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
    user: User | None = Depends(get_current_user_or_none),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )

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
        user_id=user.id if user else None,
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
    user: User | None = Depends(get_current_user_or_none),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Target tag not found"
        )

    missing = [
        source_id
        for source_id in payload.source_ids
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
        prompts_gaining_target = [
            pid for pid in prompt_ids if pid not in target_prompt_ids
        ]
        sources_payload.append(
            {
                "tag": _tag_snapshot(source),
                "prompt_ids": prompt_ids,
                "prompts_gaining_target": prompts_gaining_target,
            }
        )

    merged = tag_repo.merge_tags_bulk(payload.source_ids, payload.target_id)
    db.commit()
    if sources_payload:
        undo_service.push(
            user_id=user.id if user else None,
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
    user: User | None = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Confirmation required",
        )
    tag_repo = TagRepository(db)
    blocked: list[int] = []

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
    delete_payloads = []
    for tag_id in payload.ids:
        tag = tag_repo.get_by_id(tag_id)
        if tag:
            prompt_ids = tag_repo.get_prompt_ids(tag_id)
            delete_payloads.append(
                {"tag": _tag_snapshot(tag), "prompt_ids": prompt_ids}
            )

    # THEN clear tag-prompt associations if force=true
    if payload.force:
        tag_repo.clear_associations(payload.ids)

    deleted = tag_repo.delete_many(payload.ids)
    db.commit()
    if delete_payloads:
        undo_service.push(
            user_id=user.id if user else None,
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
    user: User | None = Depends(get_current_user_or_none),
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
        )

    replace_tag = tag_repo.get_by_name_case_insensitive(payload.replace)
    if not replace_tag:
        replace_tag = tag_repo.create(name=payload.replace)

    if find_tag.id != replace_tag.id:
        prompt_ids = [prompt.id for prompt in find_tag.prompts]
        # Track which prompts already have the replace tag before merge
        replace_prompt_ids = {prompt.id for prompt in replace_tag.prompts}
        prompts_gaining_target = [
            pid for pid in prompt_ids if pid not in replace_prompt_ids
        ]
        tag_repo.merge_tags(find_tag.id, replace_tag.id)
        undo_service.push(
            user_id=user.id if user else None,
            entity_type="tag",
            operation="find-replace",
            payload={
                "target_id": replace_tag.id,
                "sources": [
                    {
                        "tag": _tag_snapshot(find_tag),
                        "prompt_ids": prompt_ids,
                        "prompts_gaining_target": prompts_gaining_target,
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
    user: User | None = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    tag_repo = TagRepository(db)
    results = tag_repo.list_all_with_counts()
    items = [_tag_response(tag, count) for tag, count in results if (count or 0) == 0]
    return TagListResponse(items=items)


@router.get(
    "/tags/orphan-prompts",
    response_model=OrphanPromptsResponse,
    summary="List prompts without tags",
)
async def tag_orphan_prompts(
    user: User | None = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    tag_repo = TagRepository(db)
    prompt_ids = tag_repo.get_orphan_prompt_ids()
    return OrphanPromptsResponse(prompt_ids=prompt_ids, count=len(prompt_ids))


@router.get(
    "/tags/orphan-prompts/details",
    response_model=OrphanPromptDetailsResponse,
    summary="List prompts without tags (detailed)",
)
async def tag_orphan_prompts_details(
    user: User | None = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    tag_repo = TagRepository(db)
    prompts = tag_repo.get_orphan_prompts()
    items = [OrphanPromptItem(id=row[0], title=row[1] or "") for row in prompts]
    return OrphanPromptDetailsResponse(items=items, count=len(items))


@router.get(
    "/tags/analytics",
    summary="Tag usage analytics",
)
async def tag_analytics(
    user: User | None = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    tag_repo = TagRepository(db)
    results = tag_repo.list_all_with_counts()
    total = len(results)
    used = len([1 for _, count in results if (count or 0) > 0])
    unused = total - used
    top = [
        {"id": tag.id, "name": tag.name, "count": count or 0}
        for tag, count in sorted(
            results, key=lambda item: (item[1] or 0), reverse=True
        )[:10]
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
        pair_counts: dict[tuple[str, str], int] = {}
        for prompt in prompts:
            tag_names = sorted({tag.name for tag in prompt.tags})
            for i, tag_a in enumerate(tag_names):
                for tag_b in tag_names[i + 1 :]:
                    key = (tag_a, tag_b)
                    pair_counts[key] = pair_counts.get(key, 0) + 1
        for (tag_a, tag_b), count in sorted(
            pair_counts.items(), key=lambda item: item[1], reverse=True
        )[:50]:
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
    "/tags/undo",
    response_model=BulkActionResponse,
    summary="Undo last tag management operation",
)
async def undo_tag_operation(
    user: User | None = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
    undo_service: UndoService = Depends(get_undo_service),
):
    op = undo_service.pop(user.id if user else None, "tag")
    if not op:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No undo operation available"
        )

    tag_repo = TagRepository(db)
    prompt_repo = PromptRepository(db)

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
                prompts = prompt_repo.get_by_ids(prompt_ids)
                # Get list of prompts that gained the target tag during merge
                prompts_gaining_target = source.get("prompts_gaining_target", [])
                prompts_gaining_target_set = set(prompts_gaining_target)
                for prompt in prompts:
                    if tag not in prompt.tags:
                        prompt.tags.append(tag)
                    # Only remove target tag from prompts that gained it during merge
                    if (
                        target_tag
                        and target_tag in prompt.tags
                        and prompt.id in prompts_gaining_target_set
                    ):
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
                prompts = prompt_repo.get_by_ids(prompt_ids)
                for prompt in prompts:
                    if tag not in prompt.tags:
                        prompt.tags.append(tag)
            affected += 1
        db.commit()
        return BulkActionResponse(success=True, affected=affected)

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Undo operation not supported",
    )


@router.post(
    "/tags/bulk-update",
    response_model=BulkActionResponse,
    summary="Bulk add/remove tags across prompts",
)
async def bulk_update_tags(
    payload: BulkTagUpdateRequest,
    user: User | None = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Confirmation required",
        )

    prompt_repo = PromptRepository(db)

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

    # Every item must be one the caller may modify (owner or admin); skills
    # follow the same rule, so a skill id cannot be retagged by anyone else.
    if auth_settings.auth_enabled:
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        for prompt in prompts:
            check_prompt_ownership(prompt, user)

    tag_repo = TagRepository(db)
    tags_to_add = tag_repo.get_or_create_many(payload.add) if payload.add else []

    tags_to_remove = []
    if payload.remove:
        for tag_name in payload.remove:
            tag = tag_repo.get_by_name_case_insensitive(tag_name)
            if tag:
                tags_to_remove.append(tag)

    prompt_repo.bulk_update_tags(prompts, tags_to_add, tags_to_remove)

    db.commit()
    return BulkActionResponse(success=True, affected=len(prompts))


@router.post(
    "/tags/suggest",
    response_model=TagSuggestionResponse,
    summary="Suggest tags based on prompt content",
)
async def suggest_tags(
    payload: TagSuggestRequest,
    user: User | None = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    from src.db.models import Prompt
    from src.services.tag_suggestion_service import suggest_tags as suggest_tags_service

    content = payload.content
    if payload.prompt_id is not None and not content:
        prompt = db.query(Prompt).filter(Prompt.id == payload.prompt_id).first()
        if not prompt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found"
            )
        content = prompt.prompt or ""

    tag_repo = TagRepository(db)
    existing_tags = [tag.name for tag in tag_repo.get_all()]
    suggestions = suggest_tags_service(
        content or "", existing_tags, limit=payload.limit
    )
    items = [TagSuggestionItem(name=name, score=score) for name, score in suggestions]
    return TagSuggestionResponse(suggestions=items)


@router.get(
    "/tags/export",
    summary="Export tag definitions",
)
async def export_tags(
    user: User | None = Depends(get_current_user_or_none),
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
    user: User | None = Depends(get_current_user_or_none),
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
