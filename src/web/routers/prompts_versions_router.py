# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Prompt version-history routes.

Extracted from the original ``app.py`` god-file. Contains the version-related
endpoints for a prompt:

- ``GET  /prompts/{id}/versions``                     list version history
- ``GET  /prompts/{id}/versions/compare``             compare two versions
- ``GET  /prompts/{id}/versions/{version_id}``        get a specific version
- ``POST /prompts/{id}/versions/{version_id}/revert`` revert to a version

Route paths, methods, response shapes, and status codes are unchanged. The
router carries the ``/prompts`` prefix and is mounted under ``/api`` by
``routing_setup``, yielding the original ``/api/prompts/...`` paths.

Data access goes through the module-level ``data_service`` global on
``src.web.app`` (looked up lazily per-request, mirroring the other prompt
routers), so test fixtures that reconfigure services at runtime are honored.
"""

from typing import Any

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from src.config.auth_config import auth_settings
from src.db.models.user import User
from src.db.repositories.prompt_repository import PromptRepository
from src.db.session import get_db
from src.utils.diff_utils import compute_character_diff
from src.web.dependencies.bypass import (
    get_current_user_or_default,
    get_current_user_or_none,
)
from src.web.middleware.rate_limit import limiter, write_limit
from src.web.models import VersionRevertRequest
from src.web.routers.prompts_shared import effective_permission

router = APIRouter(
    prefix="/prompts",
    tags=["Legacy"],
)


def _data_service():
    """Return the app-level data service (looked up lazily per request)."""
    from src.web import app as web_app

    return web_app.data_service


def _record_validation_event(*args, **kwargs):
    from src.web import app as web_app

    web_app.record_validation_event(*args, **kwargs)


def _check_read_access(prompt_id_int: int, user: User | None, db: Session) -> bool:
    """Return False (caller should 404) when the prompt is invisible to user.

    Looks the prompt up via the ORM (not data_service's legacy dict shape)
    since check_prompt_access needs a Prompt instance. A prompt visible only
    through the legacy data_service dict path (no DB row) has no sharing
    concept to enforce, so it is treated as visible — matching that path's
    existing public-access behavior elsewhere in the prompt routers.
    """
    if not auth_settings.auth_enabled:
        return True
    prompt = PromptRepository(db).get_by_id(prompt_id_int)
    if prompt is None:
        return True
    return effective_permission(prompt, user, db) is not None


def _check_edit_access(prompt_id_int: int, user: User | None, db: Session) -> bool:
    """Return False (caller should 403) when user lacks 'edit' level.

    Revert requires 'edit' (owner, admin, or an edit-grantee) — a
    legacy_public prompt alone is insufficient (data-model.md). Unlike read
    paths, insufficient-but-visible access reports 403, not 404 (contract
    §6: mutation attempts on visible prompts are 403).
    """
    if not auth_settings.auth_enabled:
        return True
    prompt = PromptRepository(db).get_by_id(prompt_id_int)
    if prompt is None:
        return True
    level = effective_permission(prompt, user, db)
    return level in ("edit", "owner")


@router.get("/{prompt_id}/versions")
async def get_version_history(
    prompt_id: str,
    user: User | None = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    """Get version history for a specific prompt"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})

    data_service = _data_service()
    prompts = data_service.load_prompts()
    if prompt_id_int not in prompts:
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    if not _check_read_access(prompt_id_int, user, db):
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    versions = data_service.get_prompt_versions(prompt_id_int)

    sorted_versions = sorted(
        versions, key=lambda v: v.get("timestamp", ""), reverse=True
    )

    version_list = []
    for version in sorted_versions:
        version_list.append(
            {
                "version_id": version.get("version_id"),
                "version_number": version.get("version_number"),
                "timestamp": version.get("timestamp"),
                "author": version.get("author"),
                "message": version.get("message"),
                "parents": version.get("parents", []),
                "semantic_version": version.get("semantic_version"),
            }
        )

    return JSONResponse(content={"versions": version_list})


@router.get("/{prompt_id}/versions/compare")
async def compare_versions(
    prompt_id: str,
    v1: str | None = None,
    v2: str | None = None,
    user: User | None = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    """Compare two versions of a prompt"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})

    if not v1 or not v2:
        return JSONResponse(
            status_code=400,
            content={"error": "Both v1 and v2 version IDs are required"},
        )

    data_service = _data_service()
    prompts = data_service.load_prompts()
    if prompt_id_int not in prompts:
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    if not _check_read_access(prompt_id_int, user, db):
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    versions = data_service.get_prompt_versions(prompt_id_int)

    version1 = None
    version2 = None
    for version in versions:
        if version.get("version_id") == v1:
            version1 = version
        if version.get("version_id") == v2:
            version2 = version

    if not version1 or not version2:
        return JSONResponse(
            status_code=404, content={"error": "One or both versions not found"}
        )

    data1 = version1.get("data", {})
    data2 = version2.get("data", {})

    diff: dict[str, Any] = {"v1_id": v1, "v2_id": v2, "changes": {}}

    # String fields that get character-level diffs
    string_fields = ["title", "prompt", "note"]
    # Array/categorical fields that don't get diffs yet
    other_fields = ["category", "tags"]
    # Top-level metadata fields (outside the "data" sub-dict)
    metadata_fields = ["semantic_version"]

    # Process string fields with character-level diffs
    for field in string_fields:
        val1 = data1.get(field)
        val2 = data2.get(field)
        if val1 != val2:
            diff["changes"][field] = {
                "old": val1,
                "new": val2,
                "diff": compute_character_diff(val1, val2),
            }

    # Process other fields without diffs (backward compatibility)
    for field in other_fields:
        val1 = data1.get(field)
        val2 = data2.get(field)
        if val1 != val2:
            diff["changes"][field] = {"old": val1, "new": val2}

    # Process metadata fields (top-level version attributes)
    for field in metadata_fields:
        val1 = version1.get(field)
        val2 = version2.get(field)
        if val1 != val2:
            diff["changes"][field] = {"old": val1, "new": val2}

    # Ensure prompt key appears when comparing different versions
    if (
        version1.get("version_id") != version2.get("version_id")
        and "prompt" not in diff["changes"]
    ):
        val1 = data1.get("prompt")
        val2 = data2.get("prompt")
        diff["changes"]["prompt"] = {
            "old": val1,
            "new": val2,
            "diff": compute_character_diff(val1, val2),
        }

    return JSONResponse(content=diff)


@router.get("/{prompt_id}/versions/{version_id}")
async def get_specific_version(
    prompt_id: str,
    version_id: str,
    user: User | None = Depends(get_current_user_or_none),
    db: Session = Depends(get_db),
):
    """Get a specific version of a prompt"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})

    data_service = _data_service()
    prompts = data_service.load_prompts()
    if prompt_id_int not in prompts:
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    if not _check_read_access(prompt_id_int, user, db):
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    versions = data_service.get_prompt_versions(prompt_id_int)

    for version in versions:
        if version.get("version_id") == version_id:
            return JSONResponse(content=version)

    return JSONResponse(status_code=404, content={"error": "Version not found"})


@router.post(
    "/{prompt_id}/versions/{version_id}/revert",
    responses={429: {"description": "Rate limit exceeded"}},
)
@limiter.limit(write_limit)
async def revert_to_version(
    prompt_id: str,
    version_id: str,
    request: Request,
    commit_message: str = Form("Revert to previous version"),
    user: User = Depends(get_current_user_or_default),
    db: Session = Depends(get_db),
):
    """Revert a prompt to a specific version with validation."""
    try:
        validated_data = VersionRevertRequest(commit_message=commit_message)

        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})
    except ValidationError as e:
        _record_validation_event(
            endpoint="/api/prompts/version/revert",
            success=False,
            errors=[err.get("msg", "") for err in e.errors()],
        )
        return JSONResponse(
            status_code=422,
            content={"error": "Validation failed", "details": e.errors()},
        )

    data_service = _data_service()
    prompts = data_service.load_prompts()
    if prompt_id_int not in prompts:
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    if not _check_read_access(prompt_id_int, user, db):
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})
    if not _check_edit_access(prompt_id_int, user, db):
        return JSONResponse(
            status_code=403,
            content={"error": "You don't have permission to revert this prompt."},
        )

    versions = data_service.get_prompt_versions(prompt_id_int)

    version_to_revert = None
    for version in versions:
        if version.get("version_id") == version_id:
            version_to_revert = version
            break

    if not version_to_revert:
        return JSONResponse(status_code=404, content={"error": "Version not found"})

    reverted_data = version_to_revert.get("data", {}).copy()

    success = data_service.revert_prompt_to_version(
        prompt_id_int,
        reverted_data,
        validated_data.commit_message,
        author=user.username if user else None,
    )

    if success:
        new_versions = data_service.get_prompt_versions(prompt_id_int)
        new_version_id = new_versions[-1].get("version_id") if new_versions else None
        _record_validation_event(
            endpoint="/api/prompts/version/revert",
            success=True,
        )
        return JSONResponse(
            content={
                "success": True,
                "message": f"Reverted to version {version_id}",
                "new_version_id": new_version_id,
            }
        )
    else:
        return JSONResponse(
            status_code=500, content={"error": "Failed to revert version"}
        )
