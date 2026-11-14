# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""ASGI middleware that caps the size of skill uploads while they arrive.

Applies only to ``POST /api/skills/import`` and ``PUT /api/skills/{id}/archive``
(research.md Decision 9). It rejects with 413 ``LIMIT_UPLOAD_SIZE``:

1. before the body is read, when ``Content-Length`` is over the limit, and
2. as soon as the streamed body passes the limit (chunked uploads, or a
   ``Content-Length`` that lies).

The limit is ``SKILL_MAX_UPLOAD_BYTES`` plus 64 KB of multipart overhead.
"""

import json
import re

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.config.skill_config import MULTIPART_OVERHEAD_BYTES, get_skill_settings
from src.services.logging_service import logging_service
from src.services.skills import errors as err
from src.services.skills.errors import SkillArchiveError
from src.web.dependencies.skill_upload import (
    declared_length_exceeds_limit,
    upload_size_error,
)

_IMPORT_PATH = re.compile(r"^/api/skills/import/?$")
_REPLACE_PATH = re.compile(r"^/api/skills/(\d+)/archive/?$")


def _target(scope: Scope) -> tuple[str, str | None] | None:
    """Return ``(audit action, skill id)`` when the request is limited, else None."""
    method = scope.get("method", "")
    path = scope.get("path", "")
    if method == "POST" and _IMPORT_PATH.match(path):
        return "skill.import.rejected", None
    if method == "PUT":
        match = _REPLACE_PATH.match(path)
        if match:
            return "skill.replace.rejected", match.group(1)
    return None


class RequestBodyLimitMiddleware:
    """Reject oversized skill uploads with 413 before or while they stream."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        target = _target(scope) if scope["type"] == "http" else None
        if target is None:
            await self.app(scope, receive, send)
            return

        action, skill_id = target
        settings = get_skill_settings()
        limit = settings.max_upload_bytes + MULTIPART_OVERHEAD_BYTES
        headers = {
            k.decode("latin-1"): v.decode("latin-1") for k, v in scope["headers"]
        }

        rejected = False
        response_started = False

        async def reject() -> None:
            nonlocal rejected
            rejected = True
            error = upload_size_error(settings.max_upload_bytes)
            self._audit(action, skill_id, error)
            body = json.dumps({"detail": error.to_detail()}).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": error.http_status,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode()),
                        (b"connection", b"close"),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})

        if declared_length_exceeds_limit(headers.get("content-length")):
            await reject()
            return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            if rejected:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit and not response_started:
                    await reject()
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal response_started
            if rejected:
                return  # the 413 is already on the wire; drop downstream output
            if message["type"] == "http.response.start":
                response_started = True
            await send(message)

        await self.app(scope, limited_receive, guarded_send)

    @staticmethod
    def _audit(action: str, skill_id: str | None, error: SkillArchiveError) -> None:
        logging_service.log_audit_event(
            action=action,
            resource_type="skill",
            resource_id=skill_id or "none",
            status="failure",
            reason_code=err.LIMIT_UPLOAD_SIZE,
        )
