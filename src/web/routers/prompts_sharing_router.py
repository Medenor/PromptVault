# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Prompt sharing routes.

- ``POST   /prompts/{id}/shares``            grant (or update) a share
- ``GET    /prompts/{id}/shares``             list a prompt's grants (US3)
- ``DELETE /prompts/{id}/shares/{user_id}``   revoke a share (US3)

All endpoints require authentication and are owner/admin-only
(``check_prompt_access`` at the ``owner`` level). When ``AUTH_ENABLED=false``
these routes are not mounted at all (see routing_setup.py), so requests
naturally 404 — the feature is inactive in anonymous mode.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from src.db.session import get_db
from src.db.models.user import User
from src.db.repositories.prompt_repository import PromptRepository
from src.db.repositories.sharing_repository import SharingRepository
from src.db.repositories.user_repository import UserRepository
from src.services.exceptions import ShareGrantError
from src.services.logging_service import logging_service
from src.web.dependencies.bypass import get_current_user_or_default
from src.web.middleware.rate_limit import limiter, write_limit, read_limit
from src.web.models.sharing_requests import ShareGrantRequest
from src.web.models.sharing_responses import ShareResponse, ShareListResponse
from src.web.routers.prompts_shared import check_prompt_access, effective_permission

router = APIRouter(
    prefix="/prompts",
    tags=["Sharing"],
)


def _data_service():
    """Return the app-level data service (looked up lazily per request)."""
    from src.web import app as web_app

    return web_app.data_service


@router.post(
    "/{prompt_id}/shares",
    status_code=status.HTTP_201_CREATED,
    summary="Grant (or update) a prompt share",
    description="""
    Grant a teammate read or edit access to a prompt, or update an existing
    grant's permission level.

    **Authorization:** prompt owner or admin only.

    **Behavior:**
    - New grant: 201 Created
    - Existing grant, permission updated: 200 OK
    - Unknown/inactive grantee, self-share, or sharing to the owner: 400
      (generic message — these cases are indistinguishable to avoid user
      enumeration)
    """,
    responses={
        201: {"description": "Share granted"},
        200: {"description": "Existing share's permission updated"},
        400: {"description": "Grant failed (generic — no user enumeration)"},
        403: {"description": "Requester is neither owner nor admin"},
        404: {"description": "Prompt not found or invisible"},
        422: {"description": "Validation failed"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(write_limit)
async def grant_share(
    prompt_id: int,
    body: ShareGrantRequest,
    request: Request,
    user: User = Depends(get_current_user_or_default),
    db: Session = Depends(get_db),
):
    """Grant or update a prompt share (owner or admin only)."""
    prompt_repo = PromptRepository(db)
    prompt = prompt_repo.get_by_id(prompt_id)
    if not prompt or effective_permission(prompt, user, db) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found",
        )

    check_prompt_access(prompt, user, "owner", db)

    existing_permission = None
    grantee_lookup = UserRepository(db).get_by_email_or_username(body.identifier)
    if grantee_lookup:
        existing_permission = SharingRepository(db).permission_for(
            prompt_id, grantee_lookup.id
        )

    try:
        result = _data_service().grant_share(
            prompt_id=prompt_id,
            identifier=body.identifier,
            permission=body.permission,
            acting_user=user,
        )
    except ShareGrantError as exc:
        logging_service.log_audit_event(
            action="prompt.share.granted",
            resource_type="prompt",
            resource_id=str(prompt_id),
            actor=user.username,
            status="failure",
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.user_message,
        )

    response = ShareResponse(**result)
    status_code = status.HTTP_200_OK if existing_permission else status.HTTP_201_CREATED
    return JSONResponse(
        status_code=status_code, content=response.model_dump(mode="json")
    )


@router.get(
    "/{prompt_id}/shares",
    response_model=ShareListResponse,
    summary="List a prompt's grants",
    description="""
    List all active share grants on a prompt.

    **Authorization:** prompt owner or admin only — a grantee (even at
    `edit` level) gets 403.
    """,
    responses={
        200: {"description": "Grant list"},
        403: {"description": "Requester is neither owner nor admin"},
        404: {"description": "Prompt not found or invisible"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(read_limit)
async def list_shares(
    prompt_id: int,
    request: Request,
    user: User = Depends(get_current_user_or_default),
    db: Session = Depends(get_db),
):
    """List a prompt's share grants (owner or admin only)."""
    prompt_repo = PromptRepository(db)
    prompt = prompt_repo.get_by_id(prompt_id)
    if not prompt or effective_permission(prompt, user, db) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found",
        )

    check_prompt_access(prompt, user, "owner", db)

    result = _data_service().list_shares(prompt_id)
    return ShareListResponse(**result)


@router.delete(
    "/{prompt_id}/shares/{user_id}",
    summary="Revoke a prompt share",
    description="""
    Revoke a grantee's access to a prompt. Access ends immediately.

    **Authorization:** prompt owner or admin only.
    """,
    responses={
        200: {"description": "Share revoked"},
        403: {"description": "Requester is neither owner nor admin"},
        404: {"description": "Prompt invisible/nonexistent, or no grant for that user"},
        429: {"description": "Rate limit exceeded"},
    },
)
@limiter.limit(write_limit)
async def revoke_share(
    prompt_id: int,
    user_id: str,
    request: Request,
    user: User = Depends(get_current_user_or_default),
    db: Session = Depends(get_db),
):
    """Revoke a prompt share grant (owner or admin only)."""
    prompt_repo = PromptRepository(db)
    prompt = prompt_repo.get_by_id(prompt_id)
    if not prompt or effective_permission(prompt, user, db) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prompt with ID {prompt_id} not found",
        )

    check_prompt_access(prompt, user, "owner", db)

    removed = _data_service().revoke_share(prompt_id, user_id, acting_user=user)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No share grant found for that user on this prompt",
        )

    return {"message": "Share revoked"}
