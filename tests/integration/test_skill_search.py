# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Skills in full-text search (FR-024), on SQLite always and PostgreSQL when available.

Only the ``SKILL.md`` text is indexed (it lives in ``prompts.prompt``); bundled
files never are.
"""

from types import SimpleNamespace

import pytest
from fixtures.skills import build_fixtures as bf
from sqlalchemy.orm import sessionmaker

from src.db.repositories.prompt_repository import PromptRepository
from src.services.skills.skill_service import SkillService

# A stand-in acting user (auth is on in tests, so the service needs an owner).
USER = SimpleNamespace(id="search-user", username="search_user", role="user")
BODY_TERM = "zebrafish"
SCRIPT_TERM = "narwhaltoken"


def _zip(body_word: str, script_word: str = SCRIPT_TERM) -> bytes:
    return bf.build_zip(
        [
            (
                "searchable/SKILL.md",
                f"---\nname: searchable\ndescription: d\n---\n# Doc\nAbout {body_word}.\n",
            ),
            ("searchable/scripts/run.py", f"# {script_word}\n"),
        ]
    )


@pytest.fixture
def env(fts_dialect_matrix, monkeypatch):
    """Point the app's session factory at the FTS-enabled database of the matrix."""
    from src.db import session as session_module
    from src.db.models import User

    engine = fts_dialect_matrix.get_bind()
    factory = sessionmaker(bind=engine)
    monkeypatch.setattr(session_module, "SessionLocal", factory)

    # PostgreSQL enforces the owner foreign key, so the acting user must exist.
    session = factory()
    session.add(
        User(
            id=USER.id,
            username=USER.username,
            email="search_user@example.com",
            password_hash="x",
            role="user",
        )
    )
    session.commit()
    session.close()
    return factory


def _search(factory, **kwargs):
    session = factory()
    try:
        return [
            (prompt.item_type, prompt.title, context)
            for prompt, context in PromptRepository(session).search(**kwargs)
        ]
    finally:
        session.close()


def _count(factory, **kwargs) -> int:
    session = factory()
    try:
        return PromptRepository(session).count(**kwargs)
    finally:
        session.close()


class TestSkillSearch:
    def test_body_term_matches_with_a_snippet_and_script_term_does_not(self, env):
        SkillService().import_skill(_zip(BODY_TERM), "searchable.zip", USER)

        hits = _search(env, query=BODY_TERM)
        assert [(t, title) for t, title, _ in hits] == [("skill", "searchable")]
        assert hits[0][2] is not None and "[[MATCH]]" in hits[0][2]
        assert _count(env, query=BODY_TERM) == 1

        assert _search(env, query=SCRIPT_TERM) == []
        assert _count(env, query=SCRIPT_TERM) == 0

    def test_title_matches_too(self, env):
        SkillService().import_skill(_zip("plain"), "searchable.zip", USER)
        assert [t for t, _, _ in _search(env, query="searchable")] == ["skill"]

    def test_type_filter_splits_a_shared_term(self, env):
        from src.db.models import Prompt

        SkillService().import_skill(_zip(BODY_TERM), "searchable.zip", USER)
        session = env()
        session.add(Prompt(title="A prompt", prompt=f"mentions {BODY_TERM} too"))
        session.commit()
        session.close()

        both = {t for t, _, _ in _search(env, query=BODY_TERM)}
        only_skill = [t for t, _, _ in _search(env, query=BODY_TERM, item_type="skill")]
        only_prompt = [
            t for t, _, _ in _search(env, query=BODY_TERM, item_type="prompt")
        ]
        assert both == {"skill", "prompt"}
        assert only_skill == ["skill"]
        assert only_prompt == ["prompt"]
        assert _count(env, query=BODY_TERM, item_type="skill") == 1
        assert _count(env, query=BODY_TERM) == 2

    def test_replacement_updates_the_index(self, env):
        service = SkillService()
        skill_id = service.import_skill(_zip(BODY_TERM), "searchable.zip", USER)["id"]

        service.replace_skill_archive(
            skill_id, _zip("pelicanword"), "searchable.zip", USER
        )
        assert _search(env, query=BODY_TERM) == []
        assert [t for t, _, _ in _search(env, query="pelicanword")] == ["skill"]

    def test_deleted_skill_leaves_the_index(self, env):
        service = SkillService()
        skill_id = service.import_skill(_zip(BODY_TERM), "searchable.zip", USER)["id"]
        service.delete_skill(skill_id, USER)
        assert _search(env, query=BODY_TERM) == []

    def test_substring_fallback_has_the_same_scope(self, env):
        SkillService().import_skill(_zip(BODY_TERM), "searchable.zip", USER)
        assert len(_search(env, query=BODY_TERM, ranked=False)) == 1
        assert _search(env, query=SCRIPT_TERM, ranked=False) == []
