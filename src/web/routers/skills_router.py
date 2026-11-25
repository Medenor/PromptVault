# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Skill routes (``/api/skills/*``), see contracts/skills-api.md.

Thin HTTP layer over ``SkillService``. Auth follows the prompt endpoints:
the same dependencies and, in anonymous mode, the same configuration-level
behaviour. A skill the caller does not own is reported as not found.
"""

import logging
from collections.abc import Iterator
from typing import IO, Any
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from src.db.models.user import User
from src.services.skills.errors import SkillArchiveError
from src.services.skills.skill_service import SkillLookupError, SkillService
from src.web.dependencies.auth import (
    get_current_user_or_default,
    get_current_user_or_none,
)
from src.web.dependencies.skill_upload import enforce_skill_upload_size
from src.web.middleware.rate_limit import expensive_limit, limiter
from src.web.models.skill_requests import SkillUpdateRequest
from src.web.models.skill_responses import (
    SkillDetailResponse,
    SkillFileContentResponse,
    SkillImportResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skills", tags=["Skills"])

_DOWNLOAD_CHUNK_BYTES = 64 * 1024
_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"description": "Archive rejected (see the error code)"},
    404: {"description": "Skill or file not found"},
    409: {"description": "The id is a prompt, not a skill"},
    413: {"description": "Upload larger than the configured limit"},
}


def _service() -> SkillService:
    return SkillService()


def _not_found(exc: SkillLookupError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": exc.code, "message": exc.message, "offending_entry": None},
    )


def _rejected(exc: SkillArchiveError) -> HTTPException:
    return HTTPException(status_code=exc.http_status, detail=exc.to_detail())


async def _read_upload(archive: UploadFile) -> bytes:
    """Read an upload into memory and always release its spooled temp file."""
    try:
        return await archive.read()
    finally:
        await archive.close()


@router.post(
    "/import",
    status_code=status.HTTP_201_CREATED,
    response_model=SkillImportResponse,
    summary="Import a skill from a zip archive",
    responses=_ERROR_RESPONSES,
    dependencies=[Depends(enforce_skill_upload_size)],
)
@limiter.limit(expensive_limit)
async def import_skill(
    request: Request,
    response: Response,
    archive: UploadFile = File(...),
    category: str = Form(""),
    tags: str = Form(""),
    user: User = Depends(get_current_user_or_default),
):
    """Import a skill. Nothing is stored if the archive is rejected."""
    data = await _read_upload(archive)
    try:
        skill = _service().import_skill(
            data, archive.filename or "skill.zip", user, category, tags
        )
    except SkillArchiveError as exc:
        raise _rejected(exc) from exc
    return {"skill": skill, "warnings": skill["format_warnings"]}


@router.get(
    "/{skill_id}",
    response_model=SkillDetailResponse,
    summary="Skill detail",
    responses=_ERROR_RESPONSES,
)
async def get_skill(
    skill_id: int,
    user: User | None = Depends(get_current_user_or_none),
):
    """Metadata, sanitised instructions and the file list."""
    try:
        return _service().get_skill_detail(skill_id, user)
    except SkillLookupError as exc:
        raise _not_found(exc) from exc


@router.get(
    "/{skill_id}/files/content",
    response_model=SkillFileContentResponse,
    summary="Text preview of one file",
    responses=_ERROR_RESPONSES,
)
async def get_skill_file_content(
    skill_id: int,
    path: str = Query(..., min_length=1, max_length=1024),
    user: User | None = Depends(get_current_user_or_none),
):
    """Text of a stored file, cut to the preview limit. Binary files return null."""
    try:
        return _service().get_file_preview(skill_id, path, user)
    except SkillLookupError as exc:
        raise _not_found(exc) from exc


@router.get(
    "/{skill_id}/files/raw",
    summary="Download one file",
    responses=_ERROR_RESPONSES,
)
async def get_skill_file_raw(
    skill_id: int,
    path: str = Query(..., min_length=1, max_length=1024),
    user: User | None = Depends(get_current_user_or_none),
):
    """The exact bytes of a stored file, never rendered inline by the browser."""
    try:
        raw = _service().get_file_raw(skill_id, path, user)
    except SkillLookupError as exc:
        raise _not_found(exc) from exc
    basename = raw.path.rsplit("/", 1)[-1]
    return Response(
        content=raw.content,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(basename)}",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "sandbox",
        },
    )


def _iter_and_close(archive: IO[bytes]) -> Iterator[bytes]:
    try:
        while chunk := archive.read(_DOWNLOAD_CHUNK_BYTES):
            yield chunk
    finally:
        archive.close()


@router.get(
    "/{skill_id}/download",
    summary="Export a skill as a zip archive",
    responses=_ERROR_RESPONSES,
)
async def download_skill(
    skill_id: int,
    user: User | None = Depends(get_current_user_or_none),
):
    """Standard-layout ``<skill-id>.zip``, built per request and never stored."""
    try:
        export = _service().export_skill(skill_id, user)
    except SkillLookupError as exc:
        raise _not_found(exc) from exc
    return StreamingResponse(
        _iter_and_close(export.archive),
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{export.identifier}.zip"',
            "Content-Length": str(export.size),
        },
    )


@router.patch(
    "/{skill_id}",
    response_model=SkillDetailResponse,
    summary="Edit skill metadata",
    responses=_ERROR_RESPONSES,
)
async def update_skill(
    skill_id: int,
    body: SkillUpdateRequest,
    user: User = Depends(get_current_user_or_default),
):
    """Title, category, tags, note and favorite. Never creates a version."""
    try:
        return _service().update_skill_metadata(skill_id, body, user)
    except SkillLookupError as exc:
        raise _not_found(exc) from exc


@router.put(
    "/{skill_id}/archive",
    response_model=SkillImportResponse,
    summary="Replace a skill's files",
    responses=_ERROR_RESPONSES,
    dependencies=[Depends(enforce_skill_upload_size)],
)
@limiter.limit(expensive_limit)
async def replace_skill_archive(
    skill_id: int,
    request: Request,
    response: Response,
    archive: UploadFile = File(...),
    user: User = Depends(get_current_user_or_default),
):
    """Swap every file for a new archive; the skill is unchanged on any error."""
    data = await _read_upload(archive)
    try:
        skill = _service().replace_skill_archive(
            skill_id, data, archive.filename or "skill.zip", user
        )
    except SkillLookupError as exc:
        raise _not_found(exc) from exc
    except SkillArchiveError as exc:
        raise _rejected(exc) from exc
    return {"skill": skill, "warnings": skill["format_warnings"]}


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a skill",
    responses=_ERROR_RESPONSES,
)
async def delete_skill(
    skill_id: int,
    user: User = Depends(get_current_user_or_default),
):
    """Permanently delete a skill and its files (not undoable)."""
    try:
        _service().delete_skill(skill_id, user)
    except SkillLookupError as exc:
        raise _not_found(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
