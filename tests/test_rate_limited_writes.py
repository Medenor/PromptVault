# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Exercise write responses with SlowAPI's response headers enabled."""

import importlib

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def rate_limited_client(api_client_context, monkeypatch):
    from src.config.auth_config import auth_settings
    from src.services.auth.jwt_service import JWTService
    from src.web.middleware import rate_limit

    modules = [
        importlib.import_module(f"src.web.routers.{name}")
        for name in ("prompts_crud_router", "skills_router")
    ]

    # Register fresh routes because the limiter wraps handlers at import time.
    try:
        with monkeypatch.context() as patch:
            patch.setenv("DISABLE_RATE_LIMITING", "false")
            patch.setattr(rate_limit, "create_redis_client", lambda: None)
            patch.setattr(rate_limit, "limiter", rate_limit.DynamicLimiter())
            app = FastAPI()
            app.state.limiter = rate_limit.limiter
            for module in modules:
                app.include_router(importlib.reload(module).router, prefix="/api")
            token = JWTService(auth_settings).generate_access_token(
                user_id="api-test-user-id",
                username="apiuser",
                email="api@example.com",
                role="editor",
            )
            yield TestClient(
                app,
                headers={"Authorization": f"Bearer {token}"},
                raise_server_exceptions=False,
            )
    finally:
        for module in modules:
            importlib.reload(module)


def _assert_rate_limited_success(response, status_code):
    assert response.status_code == status_code, response.text
    for name in ("X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"):
        assert name in response.headers


def test_prompt_creation_has_rate_limit_headers(rate_limited_client):
    response = rate_limited_client.post(
        "/api/prompts", data={"title": "Rate-limited prompt", "prompt": "Content"}
    )
    _assert_rate_limited_success(response, 201)
    assert response.json()["prompt_id"]


def test_prompt_deletion_has_rate_limit_headers(
    rate_limited_client, api_client_context
):
    client = api_client_context["client"]
    prompts = client.get("/api/prompts", headers=rate_limited_client.headers).json()[
        "prompts"
    ]
    prompt_id = next(iter(prompts))
    response = rate_limited_client.delete(f"/api/prompts/{prompt_id}")
    _assert_rate_limited_success(response, 200)
    assert response.json() == {"success": True}
    assert (
        prompt_id
        not in client.get("/api/prompts", headers=rate_limited_client.headers).json()[
            "prompts"
        ]
    )


def test_skill_import_and_replacement_have_rate_limit_headers(
    rate_limited_client, skill_zip_valid_wrapped
):
    files = {"archive": ("skill.zip", skill_zip_valid_wrapped, "application/zip")}
    imported = rate_limited_client.post("/api/skills/import", files=files)
    _assert_rate_limited_success(imported, 201)
    skill_id = imported.json()["skill"]["id"]

    replaced = rate_limited_client.put(f"/api/skills/{skill_id}/archive", files=files)
    _assert_rate_limited_success(replaced, 200)
    assert replaced.json()["skill"]["id"] == skill_id
