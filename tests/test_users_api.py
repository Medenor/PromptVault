# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""API integration tests for the user-search (typeahead) endpoint.

GET /api/users/search — recipient picker for the share modal (US1).
"""

from datetime import datetime, timezone
from typing import Dict

import pytest


@pytest.fixture
def api_client(api_client_context):
    return api_client_context["client"]


def _seed_user(user_id: str, username: str, email: str, is_active: bool = True):
    from src.services.auth.password_service import PasswordService
    from src.config.auth_config import auth_settings
    from src.db.models.user import User
    from src.db.session import SessionLocal

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
                role="editor",
                is_active=is_active,
                email_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(user)
            session.commit()
    finally:
        session.close()


@pytest.fixture
def searcher_auth_headers(api_client_context) -> Dict[str, str]:
    from src.services.auth.jwt_service import JWTService
    from src.config import auth_config

    _seed_user("search-user-id", "searcher", "searcher@example.com")
    jwt_service = JWTService(auth_config.auth_settings)
    access_token = jwt_service.generate_access_token(
        user_id="search-user-id",
        username="searcher",
        email="searcher@example.com",
        role="editor",
    )
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def seeded_search_candidates():
    _seed_user("search-alice-id", "alice_search", "alice_search@example.com")
    _seed_user("search-alicia-id", "alicia_search", "alicia_search@example.com")
    _seed_user("search-bob-id", "bob_search", "aliasbob@example.com")
    _seed_user(
        "search-inactive-id",
        "alice_inactive_search",
        "alice_inactive_search@example.com",
        is_active=False,
    )


class TestUserSearch:
    def test_unauthenticated_returns_401(self, api_client):
        response = api_client.get("/api/users/search?q=al")

        assert response.status_code == 401

    def test_query_too_short_returns_400(self, api_client, searcher_auth_headers):
        response = api_client.get(
            "/api/users/search?q=a", headers=searcher_auth_headers
        )

        assert response.status_code == 400

    def test_matches_username_prefix(
        self, api_client, searcher_auth_headers, seeded_search_candidates
    ):
        response = api_client.get(
            "/api/users/search?q=alice_s", headers=searcher_auth_headers
        )

        assert response.status_code == 200
        usernames = {u["username"] for u in response.json()["users"]}
        assert "alice_search" in usernames
        assert "alicia_search" not in usernames

    def test_matches_email_prefix(
        self, api_client, searcher_auth_headers, seeded_search_candidates
    ):
        response = api_client.get(
            "/api/users/search?q=aliasbob", headers=searcher_auth_headers
        )

        assert response.status_code == 200
        usernames = {u["username"] for u in response.json()["users"]}
        assert "bob_search" in usernames

    def test_excludes_inactive_users(
        self, api_client, searcher_auth_headers, seeded_search_candidates
    ):
        response = api_client.get(
            "/api/users/search?q=alice_inactive", headers=searcher_auth_headers
        )

        assert response.status_code == 200
        usernames = {u["username"] for u in response.json()["users"]}
        assert "alice_inactive_search" not in usernames

    def test_response_contains_no_email_field(
        self, api_client, searcher_auth_headers, seeded_search_candidates
    ):
        response = api_client.get(
            "/api/users/search?q=alice_s", headers=searcher_auth_headers
        )

        assert response.status_code == 200
        for user in response.json()["users"]:
            assert set(user.keys()) == {"id", "username"}

    def test_results_capped_at_ten(self, api_client, searcher_auth_headers):
        for i in range(15):
            _seed_user(f"search-many-{i}", f"manymatch_{i}", f"manymatch_{i}@example.com")

        response = api_client.get(
            "/api/users/search?q=manymatch", headers=searcher_auth_headers
        )

        assert response.status_code == 200
        assert len(response.json()["users"]) <= 10
