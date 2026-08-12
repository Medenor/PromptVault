# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Snippet/match_context tests for ranked full-text search (US2).

Requires SQLite FTS5. If the interpreter's SQLite build lacks FTS5, the
whole module is skipped with a clear message rather than failing.
"""

import sqlite3
import uuid

import pytest
from sqlalchemy.orm import Session

from src.db.models import Category, Prompt, User
from src.db.repositories.prompt_repository import PromptRepository
from src.db.search.fts import MATCH_END, MATCH_START


def _sqlite_has_fts5() -> bool:
    conn = sqlite3.connect(":memory:")
    try:
        options = {row[0] for row in conn.execute("PRAGMA compile_options")}
        return any(opt.startswith("ENABLE_FTS5") for opt in options)
    finally:
        conn.close()


pytestmark = pytest.mark.skipif(
    not _sqlite_has_fts5(),
    reason="SQLite build does not have FTS5 compiled in (PRAGMA compile_options lacks ENABLE_FTS5)",
)


def _make_user(session: Session) -> User:
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        username=f"user_{user_id[:8]}",
        display_name="FTS Snippet Test User",
        email=f"{user_id[:8]}@example.com",
        password_hash="hashed_password_placeholder",
        role="user",
    )
    session.add(user)
    session.flush()
    return user


def _make_category(session: Session, name: str = "FTS Snippet Category") -> Category:
    category = Category(name=name, description="FTS snippet test category")
    session.add(category)
    session.flush()
    return category


def _make_prompt(
    session: Session,
    user: User,
    category: Category,
    title: str,
    prompt: str = "content",
    note: str | None = None,
) -> Prompt:
    p = Prompt(
        title=title,
        prompt=prompt,
        note=note,
        category_id=category.id,
        user_id=user.id,
    )
    session.add(p)
    session.flush()
    return p


class TestMatchContextSnippets:
    """T016: search() returns match_context with sentinels for body hits, None for title-only."""

    def test_body_match_returns_sentinel_wrapped_snippet(self, fts_dialect_matrix: Session):
        session = fts_dialect_matrix
        user = _make_user(session)
        category = _make_category(session)

        _make_prompt(
            session,
            user,
            category,
            title="Unrelated Title",
            prompt="this body clearly contains the word gizmo buried inside it",
        )
        session.commit()

        repo = PromptRepository(session)
        results = repo.search(query="gizmo")

        assert len(results) == 1
        _, match_context = results[0]
        assert match_context is not None
        assert MATCH_START in match_context
        assert MATCH_END in match_context
        assert "gizmo" in match_context.lower()

    def test_title_only_match_returns_none_context(self, fts_dialect_matrix: Session):
        session = fts_dialect_matrix
        user = _make_user(session)
        category = _make_category(session)

        _make_prompt(
            session,
            user,
            category,
            title="Special Widget",
            prompt="totally unrelated body text with no hit",
        )
        session.commit()

        repo = PromptRepository(session)
        results = repo.search(query="widget")

        assert len(results) == 1
        _, match_context = results[0]
        assert match_context is None

    def test_case_sensitive_search_has_no_match_context(self, fts_dialect_matrix: Session):
        session = fts_dialect_matrix
        user = _make_user(session)
        category = _make_category(session)

        _make_prompt(
            session,
            user,
            category,
            title="Unrelated",
            prompt="body containing thingamajig here",
        )
        session.commit()

        repo = PromptRepository(session)
        results = repo.search(query="thingamajig", case_sensitive=True)

        assert len(results) == 1
        _, match_context = results[0]
        assert match_context is None
