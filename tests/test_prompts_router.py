# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Characterization tests for src/web/routers/prompts.py write paths.

These lock in current black-box HTTP behavior of the direct db.add()/db.commit()
paths (create, update, delete, toggle-favorite, copy-with-version, ownership
checks) before Phase 1 moves those writes behind repository methods. The goal
is regression coverage, not new behavior.
"""

from datetime import UTC, datetime, timedelta

import pytest


@pytest.fixture
def api_client(api_client_context):
    return api_client_context["client"]


@pytest.fixture
def api_auth_headers(api_client_context) -> dict[str, str]:
    """Access token for the seeded owner user ('apiuser')."""
    from src.config import auth_config
    from src.services.auth.jwt_service import JWTService

    jwt_service = JWTService(auth_config.auth_settings)
    access_token = jwt_service.generate_access_token(
        user_id="api-test-user-id",
        username="apiuser",
        email="api@example.com",
        role="editor",
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def other_user_auth_headers(api_client_context) -> dict[str, str]:
    """Access token for a second, non-owner user created on the fly."""
    from src.config import auth_config
    from src.config.auth_config import auth_settings
    from src.db.models.user import User
    from src.db.models.user_session import UserSession
    from src.db.session import SessionLocal
    from src.services.auth.jwt_service import JWTService
    from src.services.auth.password_service import PasswordService

    password_service = PasswordService(auth_settings)
    password_hash = password_service.hash_password("OtherUserP@ssw0rd123")

    session = SessionLocal()
    try:
        other_user = session.query(User).filter_by(id="api-other-user-id").first()
        if not other_user:
            other_user = User(
                id="api-other-user-id",
                username="otheruser",
                email="other@example.com",
                password_hash=password_hash,
                role="editor",
                is_active=True,
                email_verified=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(other_user)
            session.flush()

            other_session = UserSession(
                user_id=other_user.id,
                family_id="api-other-test-family",
                refresh_token_jti="api-other-test-jti",
                ip_address="127.0.0.1",
                device_info="Test Agent",
                created_at=datetime.now(UTC),
                expires_at=datetime.now(UTC) + timedelta(days=30),
                is_revoked=False,
            )
            session.add(other_session)
            session.commit()
    finally:
        session.close()

    jwt_service = JWTService(auth_config.auth_settings)
    access_token = jwt_service.generate_access_token(
        user_id="api-other-user-id",
        username="otheruser",
        email="other@example.com",
        role="editor",
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def seeded_prompt_id(api_client):
    response = api_client.get("/api/prompts")
    assert response.status_code == 200
    prompts = response.json()["prompts"]
    for prompt_id, payload in prompts.items():
        if payload["title"] == "API Prompt 1":
            return prompt_id
    pytest.fail("Seeded prompt 'API Prompt 1' not found")


@pytest.fixture
def owned_prompt_id(api_client, api_auth_headers):
    """A prompt freshly created by the owner user, for ownership tests."""
    response = api_client.post(
        "/api/prompts",
        headers=api_auth_headers,
        data={
            "title": "Owner's Prompt",
            "prompt": "Owner content",
            "category": "Ownership",
            "tags": "",
        },
    )
    assert response.status_code == 201
    return response.json()["prompt_id"]


class TestOwnershipEnforcement:
    """check_prompt_ownership() 403 paths — currently zero coverage."""

    def test_update_by_non_owner_is_forbidden(
        self, api_client, other_user_auth_headers, owned_prompt_id
    ):
        response = api_client.put(
            f"/api/prompts/{owned_prompt_id}",
            headers=other_user_auth_headers,
            data={
                "title": "Hijacked",
                "prompt": "Hijacked body",
                "category": "",
                "tags": "",
                "commit_message": "hijack attempt",
            },
        )
        assert response.status_code == 403

    def test_delete_by_non_owner_is_forbidden(
        self, api_client, other_user_auth_headers, owned_prompt_id
    ):
        response = api_client.delete(
            f"/api/prompts/{owned_prompt_id}", headers=other_user_auth_headers
        )
        assert response.status_code == 403

    def test_toggle_favorite_by_non_owner_is_forbidden(
        self, api_client, other_user_auth_headers, owned_prompt_id
    ):
        response = api_client.put(
            f"/api/prompts/{owned_prompt_id}/favorite",
            headers=other_user_auth_headers,
        )
        assert response.status_code == 403

    def test_update_by_owner_succeeds(
        self, api_client, api_auth_headers, owned_prompt_id
    ):
        response = api_client.put(
            f"/api/prompts/{owned_prompt_id}",
            headers=api_auth_headers,
            data={
                "title": "Owner Edit",
                "prompt": "Edited by owner",
                "category": "",
                "tags": "",
                "commit_message": "owner edit",
            },
        )
        assert response.status_code == 200


class TestVersionDowngradeHeader:
    """update_prompt's X-Version-Downgrade response header behavior."""

    def test_version_upgrade_no_header(
        self, api_client, api_auth_headers, owned_prompt_id
    ):
        api_client.put(
            f"/api/prompts/{owned_prompt_id}",
            headers=api_auth_headers,
            data={
                "title": "v1",
                "prompt": "body",
                "category": "",
                "tags": "",
                "commit_message": "set v1",
                "semantic_version": "1.0.0",
            },
        )
        response = api_client.put(
            f"/api/prompts/{owned_prompt_id}",
            headers=api_auth_headers,
            data={
                "title": "v2",
                "prompt": "body",
                "category": "",
                "tags": "",
                "commit_message": "bump to v2",
                "semantic_version": "2.0.0",
            },
        )
        assert response.status_code == 200
        assert "X-Version-Downgrade" not in response.headers

    def test_version_downgrade_sets_header(
        self, api_client, api_auth_headers, owned_prompt_id
    ):
        api_client.put(
            f"/api/prompts/{owned_prompt_id}",
            headers=api_auth_headers,
            data={
                "title": "v2",
                "prompt": "body",
                "category": "",
                "tags": "",
                "commit_message": "set v2",
                "semantic_version": "2.0.0",
            },
        )
        response = api_client.put(
            f"/api/prompts/{owned_prompt_id}",
            headers=api_auth_headers,
            data={
                "title": "v1",
                "prompt": "body",
                "category": "",
                "tags": "",
                "commit_message": "downgrade to v1",
                "semantic_version": "1.0.0",
            },
        )
        assert response.status_code == 200
        assert response.headers.get("X-Version-Downgrade") == "true"


class TestCopyPromptWithVersion:
    """/api/prompts/{id}/copy-with-version — zero prior coverage."""

    def test_copy_with_version_success(
        self, api_client, api_auth_headers, owned_prompt_id
    ):
        api_client.put(
            f"/api/prompts/{owned_prompt_id}",
            headers=api_auth_headers,
            data={
                "title": "Versioned",
                "prompt": "Body to copy",
                "category": "",
                "tags": "",
                "commit_message": "set version",
                "semantic_version": "1.2.3",
            },
        )

        response = api_client.post(
            f"/api/prompts/{owned_prompt_id}/copy-with-version",
            headers=api_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["semantic_version"] == "1.2.3"
        assert "Body to copy" in data["content"]
        assert "prompt-version: 1.2.3" in data["content"]

    def test_copy_with_version_no_version_set(
        self, api_client, api_auth_headers, owned_prompt_id
    ):
        response = api_client.post(
            f"/api/prompts/{owned_prompt_id}/copy-with-version",
            headers=api_auth_headers,
        )
        assert response.status_code == 409
        assert response.json()["error"] == "no_version_set"

    def test_copy_with_version_not_found(self, api_client, api_auth_headers):
        response = api_client.post(
            "/api/prompts/999999/copy-with-version",
            headers=api_auth_headers,
        )
        assert response.status_code == 404

    def test_copy_with_version_unauthenticated_allowed(
        self, api_client, api_auth_headers, owned_prompt_id
    ):
        """Endpoint uses get_optional_user — anonymous access is allowed."""
        api_client.put(
            f"/api/prompts/{owned_prompt_id}",
            headers=api_auth_headers,
            data={
                "title": "Versioned",
                "prompt": "Body to copy",
                "category": "",
                "tags": "",
                "commit_message": "set version",
                "semantic_version": "1.0.0",
            },
        )
        response = api_client.post(f"/api/prompts/{owned_prompt_id}/copy-with-version")
        assert response.status_code == 200


class TestCreatePromptAnonymous:
    """create_prompt uses get_current_user_or_none — anonymous create is allowed."""

    def test_create_prompt_without_auth_succeeds(self, api_client):
        response = api_client.post(
            "/api/prompts",
            data={
                "title": "Anonymous Prompt",
                "prompt": "No auth needed",
                "category": "",
                "tags": "",
            },
        )
        assert response.status_code == 201
        prompt_id = response.json()["prompt_id"]

        # With AUTH_ENABLED=true, an anonymous-created prompt has no owner,
        # no grant, and is not legacy_public — it is invisible to everyone
        # (including a later anonymous request), per 007-prompt-sharing's
        # visibility scoping. The admin role always sees it (existence check).
        from datetime import datetime

        from src.config import auth_config
        from src.db.models.user import User
        from src.db.session import SessionLocal
        from src.services.auth.jwt_service import JWTService
        from src.services.auth.password_service import PasswordService

        session = SessionLocal()
        try:
            if not session.query(User).filter_by(id="anon-check-admin-id").first():
                password_service = PasswordService(auth_config.auth_settings)
                session.add(
                    User(
                        id="anon-check-admin-id",
                        username="anon_check_admin",
                        email="anon_check_admin@example.com",
                        password_hash=password_service.hash_password(
                            "AdminP@ssw0rd123"
                        ),
                        role="admin",
                        is_active=True,
                        email_verified=True,
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                    )
                )
                session.commit()
        finally:
            session.close()

        jwt_service = JWTService(auth_config.auth_settings)
        admin_token = jwt_service.generate_access_token(
            user_id="anon-check-admin-id",
            username="anon_check_admin",
            email="anon_check_admin@example.com",
            role="admin",
        )
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        retrieved_anon = api_client.get(f"/api/prompts/{prompt_id}")
        assert retrieved_anon.status_code == 404

        retrieved_admin = api_client.get(
            f"/api/prompts/{prompt_id}", headers=admin_headers
        )
        assert retrieved_admin.status_code == 200
        assert retrieved_admin.json()["title"] == "Anonymous Prompt"
