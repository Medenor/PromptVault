# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Integration tests for the general-API rate-limiting taxonomy.

These exercise the pieces added when rate limiting was extended beyond auth:

- per-user keying (JWT ``sub`` from header/cookie, falling back to IP),
- the four config-driven limit buckets and their env-var overrides,
- ``429`` responses carrying ``Retry-After`` + ``X-RateLimit-*`` headers,
- audit-logging of threshold breaches (metadata only, no bodies),
- exemption of undecorated routes (health/read).

The application wires rate limits at *decoration* time (the ``DynamicLimiter``
returns the function unchanged when disabled), and the test suite imports the
app with rate limiting disabled. To get deterministic, fast coverage we build a
small self-contained FastAPI app here with a *real* limiter and memory storage,
mirroring the production wiring (``app.state.limiter`` + the exception handler),
and drive it with real JWTs minted by ``JWTService``.
"""

from typing import Dict

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from slowapi.errors import RateLimitExceeded

from src.services.auth.jwt_service import JWTService
from src.web.middleware import rate_limit as rl


class _SettingsOverride:
    """Delegates to the real settings but overrides the write budget.

    ``auth_settings`` is a frozen pydantic model, so we wrap the module-level
    reference the builders (and the JWT key function) read from, overriding only
    the write-bucket fields. All other attributes — including the JWT signing
    keys used by ``get_rate_limit_key`` — pass through to the real settings.
    This mirrors the per-field env-var override available in production.
    """

    def __init__(self, base, attempts: int, window_seconds: int):
        self._base = base
        self.rate_limit_write_attempts = attempts
        self.rate_limit_write_window_seconds = window_seconds

    def __getattr__(self, name):
        return getattr(self._base, name)


def _override_write_budget(monkeypatch, attempts: int, window_seconds: int = 60):
    """Override the write-bucket budget the limit builders read from."""
    override = _SettingsOverride(rl.auth_settings, attempts, window_seconds)
    monkeypatch.setattr(rl, "auth_settings", override)


def _auth_headers(user_id: str, username: str) -> Dict[str, str]:
    """Mint a real Bearer token for the given user."""
    from src.config import auth_config

    jwt_service = JWTService(auth_config.auth_settings)
    token = jwt_service.generate_access_token(
        user_id=user_id,
        username=username,
        email=f"{username}@example.com",
        role="editor",
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def enable_rate_limiting(monkeypatch):
    """Force rate limiting ON regardless of ENVIRONMENT for the test body."""
    monkeypatch.setenv("DISABLE_RATE_LIMITING", "false")
    yield


def _build_app(limit_callable) -> FastAPI:
    """Build a self-contained app with a real limiter and one write endpoint."""
    limiter = rl.create_limiter()
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rl.rate_limit_exceeded_handler)

    @app.post("/api/thing")
    @limiter.limit(limit_callable)
    async def create_thing(request: Request):
        return JSONResponse(content={"ok": True})

    @app.get("/api/health")
    async def health(request: Request):
        return JSONResponse(content={"status": "ok"})

    return app


class TestPerUserIsolation:
    """A throttled user must not affect a different user's budget."""

    def test_users_have_independent_budgets(self, enable_rate_limiting, monkeypatch):
        # Tiny write budget: 2 per minute.
        _override_write_budget(monkeypatch, attempts=2)
        app = _build_app(rl.write_limit)
        client = TestClient(app)

        user_a = _auth_headers("user-a", "usera")
        user_b = _auth_headers("user-b", "userb")

        # User A exhausts the budget.
        assert client.post("/api/thing", headers=user_a).status_code == 200
        assert client.post("/api/thing", headers=user_a).status_code == 200
        assert client.post("/api/thing", headers=user_a).status_code == 429

        # User B, keyed by a different JWT sub, is unaffected.
        assert client.post("/api/thing", headers=user_b).status_code == 200
        assert client.post("/api/thing", headers=user_b).status_code == 200
        assert client.post("/api/thing", headers=user_b).status_code == 429


class TestRateLimitHeaders:
    """A 429 must carry Retry-After and the X-RateLimit-* headers."""

    def test_429_headers_present(self, enable_rate_limiting, monkeypatch):
        _override_write_budget(monkeypatch, attempts=1)
        app = _build_app(rl.write_limit)
        client = TestClient(app)
        headers = _auth_headers("user-h", "userh")

        assert client.post("/api/thing", headers=headers).status_code == 200
        resp = client.post("/api/thing", headers=headers)
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers
        assert "X-RateLimit-Limit" in resp.headers
        assert "X-RateLimit-Remaining" in resp.headers
        assert "X-RateLimit-Reset" in resp.headers
        # The limit header must be a clean numeric value, not a repr of the
        # slowapi Limit wrapper object.
        assert resp.headers["X-RateLimit-Limit"] == "1"
        assert "object at 0x" not in resp.headers["X-RateLimit-Limit"]
        assert resp.headers["X-RateLimit-Remaining"] == "0"


class TestEnvVarOverrides:
    """The bucket budgets must honor env-var / settings overrides."""

    def test_write_limit_override_changes_threshold(
        self, enable_rate_limiting, monkeypatch
    ):
        # Override to 3/minute and assert the endpoint throttles at 3.
        _override_write_budget(monkeypatch, attempts=3)
        assert rl.write_limit() == "3/minute"

        app = _build_app(rl.write_limit)
        client = TestClient(app)
        headers = _auth_headers("user-o", "usero")

        for _ in range(3):
            assert client.post("/api/thing", headers=headers).status_code == 200
        assert client.post("/api/thing", headers=headers).status_code == 429


class TestExemptRoutes:
    """Undecorated routes (health/read) must never be throttled."""

    def test_health_never_throttled(self, enable_rate_limiting, monkeypatch):
        _override_write_budget(monkeypatch, attempts=1)
        app = _build_app(rl.write_limit)
        client = TestClient(app)

        # Far more requests than any write budget — all succeed.
        for _ in range(10):
            assert client.get("/api/health").status_code == 200


class TestAuditOnBreach:
    """A breach must emit a rate_limit.exceeded audit event, no bodies."""

    def test_breach_is_audit_logged(self, enable_rate_limiting, monkeypatch):
        _override_write_budget(monkeypatch, attempts=1)
        recorded = []

        def _capture(**kwargs):
            recorded.append(kwargs)

        monkeypatch.setattr(
            "src.services.logging_service.logging_service.log_audit_event",
            _capture,
        )

        app = _build_app(rl.write_limit)
        client = TestClient(app)
        headers = _auth_headers("user-audit", "useraudit")

        assert client.post("/api/thing", headers=headers).status_code == 200
        assert client.post("/api/thing", headers=headers).status_code == 429

        breaches = [r for r in recorded if r.get("action") == "rate_limit.exceeded"]
        assert breaches, "expected a rate_limit.exceeded audit event"
        entry = breaches[0]
        assert entry["resource_type"] == "rate_limit"
        assert entry["resource_id"] == "user:user-audit"
        assert entry["endpoint"] == "/api/thing"
        assert entry["method"] == "POST"
        # No prompt/note bodies leak into the audit payload.
        assert "prompt" not in entry
        assert "body" not in entry


class TestKeyFunctionJwtDecode:
    """get_rate_limit_key must resolve the JWT sub statelessly."""

    def test_key_uses_jwt_sub_from_header(self):
        from starlette.requests import Request as StarletteRequest

        headers = _auth_headers("sub-xyz", "subuser")
        scope = {
            "type": "http",
            "headers": [
                (k.lower().encode(), v.encode()) for k, v in headers.items()
            ],
            "state": {},
            "client": ("127.0.0.1", 0),
        }
        request = StarletteRequest(scope)
        assert rl.get_rate_limit_key(request) == "user:sub-xyz"

    def test_key_falls_back_to_ip_without_token(self):
        from starlette.requests import Request as StarletteRequest

        scope = {
            "type": "http",
            "headers": [],
            "state": {},
            "client": ("203.0.113.7", 0),
        }
        request = StarletteRequest(scope)
        assert rl.get_rate_limit_key(request) == "ip:203.0.113.7"
