# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Upload size limits: 413 before and while the body arrives (research.md Decision 9)."""

import asyncio
import json
import os
import tempfile

import pytest
from fixtures.skills import build_fixtures as bf

from src.config.skill_config import MULTIPART_OVERHEAD_BYTES, get_skill_settings
from src.web.middleware.request_body_limit import RequestBodyLimitMiddleware

IMPORT = "/api/skills/import"
OVER_LIMIT = get_skill_settings().max_upload_bytes + MULTIPART_OVERHEAD_BYTES + 1024


@pytest.fixture
def small_limit(monkeypatch):
    """A 1 KB upload limit (plus the fixed multipart overhead)."""
    monkeypatch.setenv("SKILL_MAX_UPLOAD_BYTES", "1024")
    get_skill_settings.cache_clear()
    yield 1024 + MULTIPART_OVERHEAD_BYTES
    monkeypatch.delenv("SKILL_MAX_UPLOAD_BYTES")
    get_skill_settings.cache_clear()


@pytest.fixture
def no_service_calls(monkeypatch):
    """Fail the test if the service is reached at all."""
    from src.services.skills.skill_service import SkillService

    def _boom(*args, **kwargs):
        raise AssertionError("SkillService must not be called for an oversized upload")

    monkeypatch.setattr(SkillService, "import_skill", _boom)
    monkeypatch.setattr(SkillService, "replace_skill_archive", _boom)


def _random_zip(size: int) -> bytes:
    """A valid skill zip whose size is roughly ``size`` (incompressible, stored)."""
    import zipfile

    return bf.build_zip(
        [("SKILL.md", bf.SKILL_MD_VALID), ("blob.bin", os.urandom(size))],
        compression=zipfile.ZIP_STORED,
    )


def _run_asgi(middleware, scope, messages):
    """Drive the middleware directly and return (sent messages, receive calls)."""
    sent: list[dict] = []
    receive_calls = 0
    queue = list(messages)

    async def receive():
        nonlocal receive_calls
        receive_calls += 1
        return queue.pop(0) if queue else {"type": "http.disconnect"}

    async def send(message):
        sent.append(message)

    asyncio.run(middleware(scope, receive, send))
    return sent, receive_calls


def _scope(method="POST", path="/api/skills/import", headers=()):
    return {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [(k.encode(), v.encode()) for k, v in headers],
    }


class _DownstreamApp:
    """A stand-in app that records whether it ran and reads the whole body."""

    def __init__(self):
        self.called = False
        self.body_chunks = 0

    async def __call__(self, scope, receive, send):
        self.called = True
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                break
            self.body_chunks += 1
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"downstream"})


class TestContentLengthRejection:
    def test_over_limit_content_length_is_413_without_reading_the_body(self):
        app = _DownstreamApp()
        sent, receive_calls = _run_asgi(
            RequestBodyLimitMiddleware(app),
            _scope(headers=[("content-length", str(OVER_LIMIT))]),
            [{"type": "http.request", "body": b"x", "more_body": False}],
        )
        assert receive_calls == 0  # the body was never read
        assert app.called is False
        assert sent[0]["status"] == 413
        detail = json.loads(sent[1]["body"])["detail"]
        assert detail["code"] == "LIMIT_UPLOAD_SIZE"

    def test_through_the_app_the_handler_and_service_are_never_called(
        self, skill_api, skill_owner, skill_audit, no_service_calls
    ):
        response = skill_api.client.post(
            IMPORT,
            headers={**skill_owner, "content-type": "multipart/form-data; boundary=x"},
            content=b"x" * OVER_LIMIT,
        )
        assert response.status_code == 413
        assert response.json()["detail"]["code"] == "LIMIT_UPLOAD_SIZE"
        assert skill_api.count_rows("skill_packages") == 0
        events = [e for e in skill_audit if e["action"] == "skill.import.rejected"]
        assert [e["reason_code"] for e in events] == ["LIMIT_UPLOAD_SIZE"]

    def test_413_responses_still_carry_the_security_headers(
        self, skill_api, skill_owner, no_service_calls
    ):
        response = skill_api.client.post(
            IMPORT,
            headers={**skill_owner, "content-type": "multipart/form-data; boundary=x"},
            content=b"x" * OVER_LIMIT,
        )
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert "Content-Security-Policy" in response.headers

    def test_replace_endpoint_is_limited_too(
        self, skill_api, skill_owner, skill_audit, no_service_calls
    ):
        skill_id = skill_api.seed_skill("skill-owner-id")
        response = skill_api.client.put(
            f"/api/skills/{skill_id}/archive",
            headers={**skill_owner, "content-type": "multipart/form-data; boundary=x"},
            content=b"x" * OVER_LIMIT,
        )
        assert response.status_code == 413
        events = [e for e in skill_audit if e["action"] == "skill.replace.rejected"]
        assert len(events) == 1 and events[0]["resource_id"] == str(skill_id)

    def test_other_routes_are_not_limited(self):
        app = _DownstreamApp()
        sent, _ = _run_asgi(
            RequestBodyLimitMiddleware(app),
            _scope(path="/api/prompts", headers=[("content-length", str(OVER_LIMIT))]),
            [{"type": "http.request", "body": b"x", "more_body": False}],
        )
        assert app.called is True
        assert sent[0]["status"] == 200


class TestStreamedBodyRejection:
    def test_chunked_upload_without_content_length_is_413_once_over_the_limit(
        self,
    ):
        limit = get_skill_settings().max_upload_bytes + MULTIPART_OVERHEAD_BYTES
        chunk = b"x" * (256 * 1024)
        chunks_needed = limit // len(chunk) + 2
        messages = [
            {"type": "http.request", "body": chunk, "more_body": True}
            for _ in range(chunks_needed)
        ]
        app = _DownstreamApp()
        sent, receive_calls = _run_asgi(
            RequestBodyLimitMiddleware(app), _scope(), messages
        )

        assert sent[0]["status"] == 413
        assert b"LIMIT_UPLOAD_SIZE" in sent[1]["body"]
        assert len(sent) == 2  # nothing the app tried to send afterwards got through
        assert receive_calls <= chunks_needed  # stopped as soon as the limit passed
        assert app.body_chunks < chunks_needed

    def test_a_lying_content_length_is_still_caught_while_streaming(self):
        app = _DownstreamApp()
        messages = [
            {"type": "http.request", "body": b"y" * 70_000, "more_body": True},
            {"type": "http.request", "body": b"y" * 70_000, "more_body": False},
        ]
        os.environ["SKILL_MAX_UPLOAD_BYTES"] = "1024"
        get_skill_settings.cache_clear()
        try:
            sent, _ = _run_asgi(
                RequestBodyLimitMiddleware(app),
                _scope(headers=[("content-length", "10")]),
                messages,
            )
        finally:
            del os.environ["SKILL_MAX_UPLOAD_BYTES"]
            get_skill_settings.cache_clear()
        assert sent[0]["status"] == 413

    def test_a_body_under_the_limit_passes_through_untouched(self):
        app = _DownstreamApp()
        sent, _ = _run_asgi(
            RequestBodyLimitMiddleware(app),
            _scope(headers=[("content-length", "5")]),
            [{"type": "http.request", "body": b"hello", "more_body": False}],
        )
        assert app.called and sent[0]["status"] == 200

    def test_non_http_scopes_pass_through(self):
        class _Echo:
            seen: str | None = None

            async def __call__(self, scope, receive, send):
                self.seen = scope["type"]

        echo = _Echo()
        asyncio.run(RequestBodyLimitMiddleware(echo)({"type": "lifespan"}, None, None))
        assert echo.seen == "lifespan"


class TestConfiguredLimit:
    def test_limit_follows_the_environment(
        self, skill_api, skill_owner, small_limit, make_skill_zip
    ):
        too_big = _random_zip(small_limit + 5000)
        ok = make_skill_zip([("SKILL.md", bf.SKILL_MD_VALID)])
        assert skill_api.import_zip(too_big, skill_owner).status_code == 413
        assert skill_api.import_zip(ok, skill_owner).status_code == 201


class TestNoLeftovers:
    def test_spooled_upload_is_gone_after_success_and_rejection(
        self, skill_api, skill_owner, tmp_path, monkeypatch, skill_zip_valid_wrapped
    ):
        monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
        big_valid = _random_zip(2 * 1024 * 1024)  # > 1 MB, so Starlette spools to disk

        assert skill_api.import_zip(big_valid, skill_owner).status_code == 201
        assert list(tmp_path.iterdir()) == []

        assert skill_api.import_zip(bf.symbolic_link(), skill_owner).status_code == 400
        assert list(tmp_path.iterdir()) == []

    def test_nothing_is_written_under_the_data_directory(
        self, api_client_context, skill_api, skill_owner, skill_zip_valid_wrapped
    ):
        data_dir = api_client_context["temp_dir"]

        def snapshot():
            return sorted(
                os.path.join(root, name)
                for root, _dirs, names in os.walk(data_dir)
                for name in names
            )

        before = snapshot()
        skill_api.import_zip(skill_zip_valid_wrapped, skill_owner)
        skill_api.import_zip(bf.path_traversal(), skill_owner)
        assert snapshot() == before
