# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Integration tests asserting semantic_version is present in prompt and version history responses."""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session, sessionmaker

from src.db.models.prompt import Prompt
from src.db.models.prompt_version import PromptVersion


def _insert_prompt(engine, semantic_version=None) -> int:
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        prompt = Prompt(
            title="E2E Test Prompt",
            prompt="E2E content",
            note="",
            favorite=False,
            semantic_version=semantic_version,
            created_at=datetime.now(timezone.utc),
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
            created_at=datetime.now(timezone.utc),
        )
        session.add(version)
        session.commit()
        return prompt.id
    finally:
        session.close()


@pytest.fixture
def client(api_client_context):
    return api_client_context["client"]


class TestSemanticVersionInGetPrompt:
    def test_get_prompt_includes_semantic_version_when_set(
        self, client, test_db_engine
    ):
        pid = _insert_prompt(test_db_engine, semantic_version="3.2.1")

        resp = client.get(f"/api/prompts/{pid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "semantic_version" in data
        assert data["semantic_version"] == "3.2.1"

    def test_get_prompt_semantic_version_null_when_unset(self, client, test_db_engine):
        pid = _insert_prompt(test_db_engine, semantic_version=None)

        resp = client.get(f"/api/prompts/{pid}")
        assert resp.status_code == 200
        data = resp.json()
        assert "semantic_version" in data
        assert data["semantic_version"] is None


class TestSemanticVersionInVersionHistory:
    def test_version_history_includes_semantic_version(self, client, test_db_engine):
        TestSession = sessionmaker(bind=test_db_engine)
        session = TestSession()
        try:
            prompt = Prompt(
                title="History E2E",
                prompt="Content v1",
                note="",
                favorite=False,
                semantic_version="1.0.0",
                created_at=datetime.now(timezone.utc),
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
                created_at=datetime.now(timezone.utc),
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
                created_at=datetime.now(timezone.utc),
                parent_version_id=f"hist-v1-{prompt.id}",
            )
            session.add_all([v1, v2])
            session.commit()
            prompt_id = prompt.id
        finally:
            session.close()

        resp = client.get(f"/api/prompts/{prompt_id}/versions")
        assert resp.status_code == 200
        versions = resp.json()["versions"]
        assert len(versions) == 2

        sem_versions = {v["semantic_version"] for v in versions}
        assert "1.0.0" in sem_versions
        assert "1.1.0" in sem_versions

    def test_version_history_null_for_old_entries(self, client, test_db_engine):
        pid = _insert_prompt(test_db_engine, semantic_version=None)

        resp = client.get(f"/api/prompts/{pid}/versions")
        assert resp.status_code == 200
        versions = resp.json()["versions"]
        assert len(versions) >= 1
        for v in versions:
            assert "semantic_version" in v
            assert v["semantic_version"] is None
