# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Integration tests asserting semantic_version is present in prompt and version history responses."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import sessionmaker

from src.db.models.prompt import Prompt
from src.db.models.prompt_version import PromptVersion


def _insert_prompt(engine, semantic_version=None, user_id=None) -> int:
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        prompt = Prompt(
            title="E2E Test Prompt",
            prompt="E2E content",
            note="",
            favorite=False,
            semantic_version=semantic_version,
            user_id=user_id,
            created_at=datetime.now(UTC),
        )
        session.add(prompt)
        session.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version_id=f"e2e-v1-{prompt.id}",
            version_number=1,
            title=prompt.title,
            prompt=prompt.prompt,
            note=prompt.note,
            tags=[],
            favorite=prompt.favorite,
            semantic_version=semantic_version,
            author="e2e-test",
            message="Initial",
            created_at=datetime.now(UTC),
        )
        session.add(version)
        session.commit()
        return prompt.id
    finally:
        session.close()


@pytest.fixture
def client(api_client_context):
    return api_client_context["client"]


@pytest.fixture
def auth_headers(api_client_context) -> dict[str, str]:
    """Bearer token for a seeded user — GET /versions now enforces read-level
    access (contract §6), so anonymous requests against these ownerless test
    fixtures 404. The prompts here have no owner and aren't legacy_public,
    so any authenticated user works for the read-only assertions in this file."""
    from datetime import datetime as _dt

    from src.config import auth_config
    from src.db.models.user import User
    from src.db.session import SessionLocal
    from src.services.auth.jwt_service import JWTService

    session = SessionLocal()
    try:
        user = session.query(User).filter_by(id="e2e-history-user-id").first()
        if not user:
            user = User(
                id="e2e-history-user-id",
                username="e2e_history_user",
                email="e2e_history_user@example.com",
                password_hash="x",
                role="editor",
                is_active=True,
                email_verified=True,
                created_at=_dt.now(UTC),
                updated_at=_dt.now(UTC),
            )
            session.add(user)
            session.commit()
    finally:
        session.close()

    jwt_service = JWTService(auth_config.auth_settings)
    access_token = jwt_service.generate_access_token(
        user_id="e2e-history-user-id",
        username="e2e_history_user",
        email="e2e_history_user@example.com",
        role="editor",
    )
    return {"Authorization": f"Bearer {access_token}"}


class TestSemanticVersionInGetPrompt:
    def test_get_prompt_includes_semantic_version_when_set(
        self, client, test_db_engine, auth_headers
    ):
        pid = _insert_prompt(
            test_db_engine, semantic_version="3.2.1", user_id="e2e-history-user-id"
        )

        resp = client.get(f"/api/prompts/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "semantic_version" in data
        assert data["semantic_version"] == "3.2.1"

    def test_get_prompt_semantic_version_null_when_unset(
        self, client, test_db_engine, auth_headers
    ):
        pid = _insert_prompt(
            test_db_engine, semantic_version=None, user_id="e2e-history-user-id"
        )

        resp = client.get(f"/api/prompts/{pid}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "semantic_version" in data
        assert data["semantic_version"] is None


class TestSemanticVersionInVersionHistory:
    def test_version_history_includes_semantic_version(
        self, client, test_db_engine, auth_headers
    ):
        TestSession = sessionmaker(bind=test_db_engine)
        session = TestSession()
        try:
            prompt = Prompt(
                title="History E2E",
                prompt="Content v1",
                note="",
                favorite=False,
                semantic_version="1.0.0",
                user_id="e2e-history-user-id",
                created_at=datetime.now(UTC),
            )
            session.add(prompt)
            session.flush()

            v1 = PromptVersion(
                prompt_id=prompt.id,
                version_id=f"hist-v1-{prompt.id}",
                version_number=1,
                title=prompt.title,
                prompt=prompt.prompt,
                note="",
                tags=[],
                favorite=False,
                semantic_version="1.0.0",
                author="test",
                message="v1",
                created_at=datetime.now(UTC),
            )
            v2 = PromptVersion(
                prompt_id=prompt.id,
                version_id=f"hist-v2-{prompt.id}",
                version_number=2,
                title=prompt.title,
                prompt="Content v2",
                note="",
                tags=[],
                favorite=False,
                semantic_version="1.1.0",
                author="test",
                message="v2",
                created_at=datetime.now(UTC),
                parent_version_id=f"hist-v1-{prompt.id}",
            )
            session.add_all([v1, v2])
            session.commit()
            prompt_id = prompt.id
        finally:
            session.close()

        resp = client.get(f"/api/prompts/{prompt_id}/versions", headers=auth_headers)
        assert resp.status_code == 200
        versions = resp.json()["versions"]
        assert len(versions) == 2

        sem_versions = {v["semantic_version"] for v in versions}
        assert "1.0.0" in sem_versions
        assert "1.1.0" in sem_versions

    def test_version_history_null_for_old_entries(
        self, client, test_db_engine, auth_headers
    ):
        pid = _insert_prompt(
            test_db_engine, semantic_version=None, user_id="e2e-history-user-id"
        )

        resp = client.get(f"/api/prompts/{pid}/versions", headers=auth_headers)
        assert resp.status_code == 200
        versions = resp.json()["versions"]
        assert len(versions) >= 1
        for v in versions:
            assert "semantic_version" in v
            assert v["semantic_version"] is None
