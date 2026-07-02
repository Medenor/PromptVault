# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for POST /api/prompts/{id}/copy-with-version endpoint."""

import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session, sessionmaker

from src.db.models.prompt import Prompt
from src.db.models.prompt_version import PromptVersion


def _insert_prompt(engine, semantic_version=None) -> int:
    """Insert a minimal prompt directly into the test DB; return its ID."""
    TestSession = sessionmaker(bind=engine)
    session = TestSession()
    try:
        prompt = Prompt(
            title="Test Prompt",
            prompt="Hello world",
            note="",
            favorite=False,
            semantic_version=semantic_version,
            created_at=datetime.now(timezone.utc),
        )
        session.add(prompt)
        session.flush()

        version = PromptVersion(
            prompt_id=prompt.id,
            version_id=f"cv-test-{prompt.id}",
            version_number=1,
            title=prompt.title,
            prompt=prompt.prompt,
            note=prompt.note,
            tags=[],
            favorite=prompt.favorite,
            semantic_version=semantic_version,
            author="test",
            message="Initial commit",
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


class TestCopyWithVersionEndpoint:
    def test_200_with_version(self, client, test_db_engine):
        prompt_id = _insert_prompt(test_db_engine, semantic_version="1.1.0")

        response = client.post(f"/api/prompts/{prompt_id}/copy-with-version")
        assert response.status_code == 200

        data = response.json()
        assert data["semantic_version"] == "1.1.0"
        assert "Hello world" in data["content"]
        assert "<!-- prompt-version: 1.1.0" in data["content"]
        assert "This line is metadata" in data["content"]

    def test_409_without_version(self, client, test_db_engine):
        prompt_id = _insert_prompt(test_db_engine, semantic_version=None)

        response = client.post(f"/api/prompts/{prompt_id}/copy-with-version")
        assert response.status_code == 409

        data = response.json()
        assert data["error"] == "no_version_set"
        assert "semantic version" in data["message"].lower()

    def test_404_unknown_prompt(self, client):
        response = client.post("/api/prompts/999999/copy-with-version")
        assert response.status_code == 404

    def test_metadata_format(self, client, test_db_engine):
        prompt_id = _insert_prompt(test_db_engine, semantic_version="2.0.1")

        response = client.post(f"/api/prompts/{prompt_id}/copy-with-version")
        assert response.status_code == 200

        content = response.json()["content"]
        lines = content.split("\n")
        last_line = lines[-1]
        assert last_line.startswith("<!-- prompt-version: 2.0.1 |")
        assert last_line.endswith("-->")
