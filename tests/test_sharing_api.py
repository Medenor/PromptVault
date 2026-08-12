# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""API integration tests for the prompt sharing endpoints.

US1 (this file, initial classes): POST /api/prompts/{id}/shares — grant/
update, generic-400 enumeration resistance, audit event, 404 on invisible
prompt, 404 when AUTH_ENABLED=false.

US2 and US3 classes are appended in later phases (visibility scoping,
list/revoke grants, un-grandfathering) — see tasks.md T031/T040/T041.
"""

from datetime import UTC, datetime

import pytest


@pytest.fixture
def api_client(api_client_context):
    return api_client_context["client"]


def _make_auth_headers(user_id: str, username: str, email: str, role: str = "editor"):
    from src.config import auth_config
    from src.services.auth.jwt_service import JWTService

    jwt_service = JWTService(auth_config.auth_settings)
    access_token = jwt_service.generate_access_token(
        user_id=user_id, username=username, email=email, role=role
    )
    return {"Authorization": f"Bearer {access_token}"}


def _seed_user(user_id: str, username: str, email: str, role: str = "editor"):
    from src.config.auth_config import auth_settings
    from src.db.models.user import User
    from src.db.session import SessionLocal
    from src.services.auth.password_service import PasswordService

    password_service = PasswordService(auth_settings)
    password_hash = password_service.hash_password("SeedUserP@ssw0rd123")

    session = SessionLocal()
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            user = User(
                id=user_id,
                username=username,
                email=email,
                password_hash=password_hash,
                role=role,
                is_active=True,
                email_verified=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(user)
            session.commit()
    finally:
        session.close()


@pytest.fixture
def owner_auth_headers(api_client_context) -> dict[str, str]:
    _seed_user("share-owner-id", "share_owner", "share_owner@example.com")
    return _make_auth_headers(
        "share-owner-id", "share_owner", "share_owner@example.com"
    )


@pytest.fixture
def grantee_auth_headers(api_client_context) -> dict[str, str]:
    _seed_user("share-grantee-id", "share_grantee", "share_grantee@example.com")
    return _make_auth_headers(
        "share-grantee-id", "share_grantee", "share_grantee@example.com"
    )


@pytest.fixture
def stranger_auth_headers(api_client_context) -> dict[str, str]:
    _seed_user("share-stranger-id", "share_stranger", "share_stranger@example.com")
    return _make_auth_headers(
        "share-stranger-id", "share_stranger", "share_stranger@example.com"
    )


@pytest.fixture
def owned_prompt_id(api_client, owner_auth_headers):
    """A prompt freshly created by owner_auth_headers's user."""
    response = api_client.post(
        "/api/prompts",
        headers=owner_auth_headers,
        data={
            "title": "Owner's Shareable Prompt",
            "prompt": "Shareable content",
            "category": "Sharing",
            "tags": "",
        },
    )
    assert response.status_code == 201
    return response.json()["prompt_id"]


class TestGrantShare:
    def test_grant_new_share_returns_201(
        self, api_client, owner_auth_headers, grantee_auth_headers, owned_prompt_id
    ):
        response = api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "read"},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["prompt_id"] == owned_prompt_id
        assert body["grantee"]["username"] == "share_grantee"
        assert body["permission"] == "read"
        assert body["granted_by"] == "share_owner"

    def test_grant_by_email_identifier(
        self, api_client, owner_auth_headers, grantee_auth_headers, owned_prompt_id
    ):
        response = api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee@example.com", "permission": "edit"},
        )

        assert response.status_code == 201
        assert response.json()["permission"] == "edit"

    def test_regrant_updates_permission_returns_200(
        self, api_client, owner_auth_headers, grantee_auth_headers, owned_prompt_id
    ):
        first = api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "read"},
        )
        assert first.status_code == 201

        second = api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "edit"},
        )

        assert second.status_code == 200
        assert second.json()["permission"] == "edit"

    def test_grant_by_non_owner_forbidden(
        self,
        api_client,
        stranger_auth_headers,
        grantee_auth_headers,
        owned_prompt_id,
    ):
        # Prompt is private (freshly created, no grant/legacy_public), so a
        # stranger with zero visibility gets 404 (existence hiding) rather
        # than 403 — matching get_prompt/list_shares elsewhere in the API.
        response = api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=stranger_auth_headers,
            json={"identifier": "share_grantee", "permission": "read"},
        )

        assert response.status_code == 404

    def test_grant_on_invisible_prompt_returns_404(
        self, api_client, owner_auth_headers
    ):
        response = api_client.post(
            "/api/prompts/999999/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "read"},
        )

        assert response.status_code == 404

    def test_grant_malformed_body_returns_422(
        self, api_client, owner_auth_headers, owned_prompt_id
    ):
        response = api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "not-a-level"},
        )

        assert response.status_code == 422

    @pytest.mark.parametrize(
        "body",
        [
            {"identifier": "no_such_user", "permission": "read"},
            {"identifier": "share_owner", "permission": "read"},  # owner-as-grantee
        ],
    )
    def test_grant_failure_cases_share_generic_400(
        self, api_client, owner_auth_headers, owned_prompt_id, body
    ):
        response = api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json=body,
        )

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_self_share_returns_generic_400(
        self, api_client, owner_auth_headers, owned_prompt_id
    ):
        response = api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_owner", "permission": "read"},
        )

        assert response.status_code == 400

    def test_inactive_grantee_returns_generic_400(
        self, api_client, owner_auth_headers, owned_prompt_id
    ):
        from src.db.models.user import User
        from src.db.session import SessionLocal

        _seed_user("share-inactive-id", "share_inactive", "share_inactive@example.com")
        session = SessionLocal()
        try:
            inactive = session.query(User).filter_by(id="share-inactive-id").first()
            inactive.is_active = False
            session.commit()
        finally:
            session.close()

        response = api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_inactive", "permission": "read"},
        )

        assert response.status_code == 400

    def test_all_grant_failures_share_identical_body_shape(
        self, api_client, owner_auth_headers, owned_prompt_id
    ):
        unknown = api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "no_such_user_xyz", "permission": "read"},
        )
        self_share = api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_owner", "permission": "read"},
        )

        assert unknown.status_code == self_share.status_code == 400
        assert set(unknown.json().keys()) == set(self_share.json().keys())

    def test_grant_on_legacy_public_prompt_behaves_identically(
        self, api_client, owner_auth_headers, grantee_auth_headers
    ):
        from src.db.models.prompt import Prompt
        from src.db.session import SessionLocal

        session = SessionLocal()
        try:
            prompt = Prompt(
                title="Legacy Public API Prompt",
                prompt="Grandfathered content",
                favorite=False,
                legacy_public=True,
                user_id="share-owner-id",
            )
            session.add(prompt)
            session.commit()
            prompt_id = prompt.id
        finally:
            session.close()

        response = api_client.post(
            f"/api/prompts/{prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "edit"},
        )

        assert response.status_code == 201
        assert response.json()["permission"] == "edit"


@pytest.fixture
def admin_auth_headers(api_client_context) -> dict[str, str]:
    _seed_user("share-admin-id", "share_admin", "share_admin@example.com", role="admin")
    return _make_auth_headers(
        "share-admin-id", "share_admin", "share_admin@example.com", role="admin"
    )


class TestVisibilityScoping:
    """GET /api/prompts and /api/prompts/search default scoping (US2, T031)."""

    def test_owner_sees_own_prompt(
        self, api_client, owner_auth_headers, owned_prompt_id
    ):
        response = api_client.get("/api/prompts", headers=owner_auth_headers)
        assert response.status_code == 200
        assert str(owned_prompt_id) in response.json()["prompts"]

    def test_grantee_sees_shared_prompt(
        self, api_client, owner_auth_headers, grantee_auth_headers, owned_prompt_id
    ):
        grant = api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "read"},
        )
        assert grant.status_code == 201

        response = api_client.get("/api/prompts", headers=grantee_auth_headers)
        assert response.status_code == 200
        assert str(owned_prompt_id) in response.json()["prompts"]

    def test_stranger_does_not_see_private_prompt(
        self, api_client, stranger_auth_headers, owned_prompt_id
    ):
        response = api_client.get("/api/prompts", headers=stranger_auth_headers)
        assert response.status_code == 200
        assert str(owned_prompt_id) not in response.json()["prompts"]

    def test_stranger_direct_access_404(
        self, api_client, stranger_auth_headers, owned_prompt_id
    ):
        response = api_client.get(
            f"/api/prompts/{owned_prompt_id}", headers=stranger_auth_headers
        )
        assert response.status_code == 404

    def test_admin_sees_private_prompt(
        self, api_client, admin_auth_headers, owned_prompt_id
    ):
        response = api_client.get("/api/prompts", headers=admin_auth_headers)
        assert response.status_code == 200
        assert str(owned_prompt_id) in response.json()["prompts"]

    def test_legacy_public_prompt_visible_to_any_authenticated_user(
        self, api_client, owner_auth_headers, stranger_auth_headers
    ):
        from src.db.models.prompt import Prompt
        from src.db.session import SessionLocal

        session = SessionLocal()
        try:
            prompt = Prompt(
                title="Legacy Public Visibility",
                prompt="Grandfathered",
                favorite=False,
                legacy_public=True,
                user_id="share-owner-id",
            )
            session.add(prompt)
            session.commit()
            prompt_id = prompt.id
        finally:
            session.close()

        response = api_client.get("/api/prompts", headers=stranger_auth_headers)
        assert response.status_code == 200
        assert str(prompt_id) in response.json()["prompts"]

    def test_shared_with_me_filter_excludes_legacy_public(
        self, api_client, owner_auth_headers, grantee_auth_headers, owned_prompt_id
    ):
        from src.db.models.prompt import Prompt
        from src.db.session import SessionLocal

        session = SessionLocal()
        try:
            legacy = Prompt(
                title="Legacy for filter test",
                prompt="Grandfathered",
                favorite=False,
                legacy_public=True,
                user_id="share-owner-id",
            )
            session.add(legacy)
            session.commit()
            legacy_id = legacy.id
        finally:
            session.close()

        grant = api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "read"},
        )
        assert grant.status_code == 201

        response = api_client.get(
            "/api/prompts",
            params={"filter": "shared-with-me"},
            headers=grantee_auth_headers,
        )
        assert response.status_code == 200
        prompts = response.json()["prompts"]
        assert str(owned_prompt_id) in prompts
        assert str(legacy_id) not in prompts

    def test_payload_includes_shared_legacy_public_permission_fields(
        self, api_client, owner_auth_headers, grantee_auth_headers, owned_prompt_id
    ):
        grant = api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "edit"},
        )
        assert grant.status_code == 201

        response = api_client.get("/api/prompts", headers=grantee_auth_headers)
        assert response.status_code == 200
        payload = response.json()["prompts"][str(owned_prompt_id)]
        assert payload["shared"] is True
        assert payload["legacy_public"] is False
        assert payload["permission"] == "edit"

    def test_search_endpoint_visibility_scoping(
        self, api_client, owner_auth_headers, stranger_auth_headers, owned_prompt_id
    ):
        response = api_client.get(
            "/api/prompts/search",
            params={"search": "Shareable"},
            headers=stranger_auth_headers,
        )
        assert response.status_code == 200
        assert str(owned_prompt_id) not in response.json()["prompts"]

        response_owner = api_client.get(
            "/api/prompts/search",
            params={"search": "Shareable"},
            headers=owner_auth_headers,
        )
        assert response_owner.status_code == 200
        assert str(owned_prompt_id) in response_owner.json()["prompts"]


class TestListAndRevokeShares:
    """US3: GET .../shares (list) and DELETE .../shares/{user_id} (revoke)."""

    def test_list_shares_owner_sees_full_list(
        self, api_client, owner_auth_headers, grantee_auth_headers, owned_prompt_id
    ):
        grant = api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "edit"},
        )
        assert grant.status_code == 201

        response = api_client.get(
            f"/api/prompts/{owned_prompt_id}/shares", headers=owner_auth_headers
        )
        assert response.status_code == 200
        body = response.json()
        assert body["prompt_id"] == owned_prompt_id
        assert len(body["shares"]) == 1
        assert body["shares"][0]["grantee"]["username"] == "share_grantee"
        assert body["shares"][0]["permission"] == "edit"

    def test_list_shares_grantee_forbidden(
        self, api_client, owner_auth_headers, grantee_auth_headers, owned_prompt_id
    ):
        api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "read"},
        )

        response = api_client.get(
            f"/api/prompts/{owned_prompt_id}/shares", headers=grantee_auth_headers
        )
        assert response.status_code == 403

    def test_list_shares_edit_grantee_also_forbidden(
        self, api_client, owner_auth_headers, grantee_auth_headers, owned_prompt_id
    ):
        api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "edit"},
        )

        response = api_client.get(
            f"/api/prompts/{owned_prompt_id}/shares", headers=grantee_auth_headers
        )
        assert response.status_code == 403

    def test_list_shares_stranger_gets_404(
        self, api_client, stranger_auth_headers, owned_prompt_id
    ):
        response = api_client.get(
            f"/api/prompts/{owned_prompt_id}/shares", headers=stranger_auth_headers
        )
        assert response.status_code == 404

    def test_revoke_share_returns_200_and_ends_access(
        self, api_client, owner_auth_headers, grantee_auth_headers, owned_prompt_id
    ):
        api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "read"},
        )
        visible = api_client.get(
            f"/api/prompts/{owned_prompt_id}", headers=grantee_auth_headers
        )
        assert visible.status_code == 200

        response = api_client.delete(
            f"/api/prompts/{owned_prompt_id}/shares/share-grantee-id",
            headers=owner_auth_headers,
        )
        assert response.status_code == 200

        after = api_client.get(
            f"/api/prompts/{owned_prompt_id}", headers=grantee_auth_headers
        )
        assert after.status_code == 404

    def test_revoke_absent_grant_returns_404(
        self, api_client, owner_auth_headers, owned_prompt_id
    ):
        response = api_client.delete(
            f"/api/prompts/{owned_prompt_id}/shares/no-such-user-id",
            headers=owner_auth_headers,
        )
        assert response.status_code == 404

    def test_revoke_by_non_owner_forbidden(
        self, api_client, owner_auth_headers, grantee_auth_headers, owned_prompt_id
    ):
        api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "read"},
        )

        response = api_client.delete(
            f"/api/prompts/{owned_prompt_id}/shares/share-grantee-id",
            headers=grantee_auth_headers,
        )
        assert response.status_code == 403

    def test_revoke_emits_audit_event_with_permission(
        self,
        api_client,
        owner_auth_headers,
        grantee_auth_headers,
        owned_prompt_id,
        monkeypatch,
    ):
        from src.services.logging_service import logging_service

        captured = []
        original = logging_service.log_audit_event

        def _spy(*args, **kwargs):
            captured.append(kwargs)
            return original(*args, **kwargs)

        monkeypatch.setattr(logging_service, "log_audit_event", _spy)

        api_client.post(
            f"/api/prompts/{owned_prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "edit"},
        )
        response = api_client.delete(
            f"/api/prompts/{owned_prompt_id}/shares/share-grantee-id",
            headers=owner_auth_headers,
        )
        assert response.status_code == 200

        revoke_events = [
            c for c in captured if c.get("action") == "prompt.share.revoked"
        ]
        assert len(revoke_events) == 1
        assert revoke_events[0]["permission"] == "edit"


class TestUnGrandfather:
    """US3: PATCH /api/prompts/{id} with {"legacy_public": false}."""

    def test_owner_can_ungrandfather(
        self, api_client, owner_auth_headers, api_client_context
    ):
        from src.db.repositories.prompt_repository import PromptRepository
        from src.db.session import SessionLocal

        session = SessionLocal()
        try:
            prompt_repo = PromptRepository(session)
            prompt = prompt_repo.create(
                title="Legacy prompt",
                prompt="Legacy content",
                user_id="share-owner-id",
                legacy_public=True,
            )
            session.commit()
            prompt_id = prompt.id
        finally:
            session.close()

        response = api_client.patch(
            f"/api/prompts/{prompt_id}",
            headers=owner_auth_headers,
            json={"legacy_public": False},
        )
        assert response.status_code == 200
        assert response.json()["legacy_public"] is False

    def test_ungrandfather_hides_prompt_from_others_immediately(
        self, api_client, owner_auth_headers, stranger_auth_headers
    ):
        from src.db.repositories.prompt_repository import PromptRepository
        from src.db.session import SessionLocal

        session = SessionLocal()
        try:
            prompt_repo = PromptRepository(session)
            prompt = prompt_repo.create(
                title="Legacy prompt 2",
                prompt="Legacy content 2",
                user_id="share-owner-id",
                legacy_public=True,
            )
            session.commit()
            prompt_id = prompt.id
        finally:
            session.close()

        visible_before = api_client.get(
            f"/api/prompts/{prompt_id}", headers=stranger_auth_headers
        )
        assert visible_before.status_code == 200

        patch_resp = api_client.patch(
            f"/api/prompts/{prompt_id}",
            headers=owner_auth_headers,
            json={"legacy_public": False},
        )
        assert patch_resp.status_code == 200

        visible_after = api_client.get(
            f"/api/prompts/{prompt_id}", headers=stranger_auth_headers
        )
        assert visible_after.status_code == 404

    def test_non_owner_forbidden(
        self, api_client, owner_auth_headers, grantee_auth_headers
    ):
        from src.db.repositories.prompt_repository import PromptRepository
        from src.db.session import SessionLocal

        session = SessionLocal()
        try:
            prompt_repo = PromptRepository(session)
            prompt = prompt_repo.create(
                title="Legacy prompt 3",
                prompt="Legacy content 3",
                user_id="share-owner-id",
                legacy_public=True,
            )
            session.commit()
            prompt_id = prompt.id
        finally:
            session.close()

        # Even with an edit grant, a non-owner cannot un-grandfather.
        api_client.post(
            f"/api/prompts/{prompt_id}/shares",
            headers=owner_auth_headers,
            json={"identifier": "share_grantee", "permission": "edit"},
        )

        response = api_client.patch(
            f"/api/prompts/{prompt_id}",
            headers=grantee_auth_headers,
            json={"legacy_public": False},
        )
        assert response.status_code == 403

    def test_setting_legacy_public_true_rejected(
        self, api_client, owner_auth_headers, owned_prompt_id
    ):
        response = api_client.patch(
            f"/api/prompts/{owned_prompt_id}",
            headers=owner_auth_headers,
            json={"legacy_public": True},
        )
        assert response.status_code == 400

    def test_ungrandfather_creates_no_share_rows(
        self, api_client, owner_auth_headers, stranger_auth_headers
    ):
        from src.db.repositories.prompt_repository import PromptRepository
        from src.db.repositories.sharing_repository import SharingRepository
        from src.db.session import SessionLocal

        session = SessionLocal()
        try:
            prompt_repo = PromptRepository(session)
            prompt = prompt_repo.create(
                title="Legacy prompt 4",
                prompt="Legacy content 4",
                user_id="share-owner-id",
                legacy_public=True,
            )
            session.commit()
            prompt_id = prompt.id
        finally:
            session.close()

        response = api_client.patch(
            f"/api/prompts/{prompt_id}",
            headers=owner_auth_headers,
            json={"legacy_public": False},
        )
        assert response.status_code == 200

        session = SessionLocal()
        try:
            shares = SharingRepository(session).list_for_prompt(prompt_id)
            assert shares == []
        finally:
            session.close()


# Auth-disabled (anonymous mode) coverage for the sharing/typeahead routes'
# unmounting lives in tests/test_auth_optional.py::TestAnonymousMode — that
# file's api_client fixture builds the app with AUTH_ENABLED=false baked in
# at construction time (route mounting happens once, at startup, per
# routing_setup.configure_routing), which api_client_context here cannot
# replicate by toggling auth_settings after the fact.
