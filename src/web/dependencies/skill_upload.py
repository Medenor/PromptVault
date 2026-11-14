# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Route dependency that rejects oversized skill uploads by ``Content-Length``.

This is the second layer of the upload limit (research.md Decision 9). FastAPI
parses a form body before it solves dependencies, so on its own this check
cannot stop a large body from being received. ``RequestBodyLimitMiddleware``
does that earlier, from the same header and from the streamed byte count; this
dependency makes sure the handler and ``SkillService`` are never reached by an
oversized request even if the middleware is not installed.
"""

from fastapi import HTTPException, Request

from src.config.skill_config import MULTIPART_OVERHEAD_BYTES, get_skill_settings
from src.services.skills import errors as err
from src.services.skills.errors import SkillArchiveError


def upload_size_error(max_upload_bytes: int) -> SkillArchiveError:
    """Build the ``LIMIT_UPLOAD_SIZE`` rejection for a given limit."""
    megabytes = max_upload_bytes / (1024 * 1024)
    return SkillArchiveError(
        err.LIMIT_UPLOAD_SIZE,
        f"Upload is larger than the {megabytes:g} MB limit",
    )


def declared_length_exceeds_limit(content_length: str | None) -> bool:
    """True when a ``Content-Length`` value is over the allowed upload size."""
    if not content_length:
        return False
    try:
        declared = int(content_length)
    except ValueError:
        return False
    limit = get_skill_settings().max_upload_bytes + MULTIPART_OVERHEAD_BYTES
    return declared > limit


async def enforce_skill_upload_size(request: Request) -> None:
    """Reject with 413 when ``Content-Length`` is over the upload limit.

    Raises:
        HTTPException: 413 with the ``LIMIT_UPLOAD_SIZE`` error body.
    """
    if declared_length_exceeds_limit(request.headers.get("content-length")):
        error = upload_size_error(get_skill_settings().max_upload_bytes)
        raise HTTPException(status_code=error.http_status, detail=error.to_detail())
