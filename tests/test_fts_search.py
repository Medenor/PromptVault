# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Full-text search correctness tests (ranking, sort precedence, pagination).

Requires SQLite FTS5. If the interpreter's SQLite build lacks FTS5, the
whole module is skipped with a clear message rather than failing.
"""

import sqlite3
import uuid

import pytest
from sqlalchemy.orm import Session

from src.db.models import Category, Prompt, User
from src.db.repositories.prompt_repository import PromptRepository


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
        display_name="FTS Test User",
        email=f"{user_id[:8]}@example.com",
        password_hash="hashed_password_placeholder",
        role="user",
    )
    session.add(user)
    session.flush()
    return user


def _make_category(session: Session, name: str = "FTS Category") -> Category:
    category = Category(name=name, description="FTS test category")
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


class TestRankingCorrectness:
    """T010: title-weighted-above-body, all-words-above-partial, substring parity."""

    def test_title_match_ranks_above_body_match(self, fts_dialect_matrix: Session):
        session = fts_dialect_matrix
        user = _make_user(session)
        category = _make_category(session)

        title_hit = _make_prompt(
            session,
            user,
            category,
            title="Special Widget",
            prompt="unrelated body text",
        )
        body_hit = _make_prompt(
            session,
            user,
            category,
            title="Unrelated Title",
            prompt="contains widget in body",
        )
        session.commit()

        repo = PromptRepository(session)
        results = repo.search(query="widget")

        result_ids = [p.id for p, _ in results]
        assert title_hit.id in result_ids
        assert body_hit.id in result_ids
        assert result_ids.index(title_hit.id) < result_ids.index(body_hit.id)

    def test_all_words_match_ranks_above_partial_match(
        self, fts_dialect_matrix: Session
    ):
        session = fts_dialect_matrix
        user = _make_user(session)
        category = _make_category(session)

        # Matches both terms in the body.
        both_words = _make_prompt(
            session, user, category, title="Doc A", prompt="alpha bravo shared content"
        )
        # Matches only one of the two terms (still included: OR semantics).
        one_word = _make_prompt(
            session,
            user,
            category,
            title="Doc B",
            prompt="alpha only, no second term here",
        )
        session.commit()

        repo = PromptRepository(session)
        results = repo.search(query="alpha bravo")

        result_ids = [p.id for p, _ in results]
        # Partial match is still included (FR-002/FR-003 — OR, not AND).
        assert both_words.id in result_ids
        assert one_word.id in result_ids
        # All-words match ranks above the partial match.
        assert result_ids.index(both_words.id) < result_ids.index(one_word.id)

    def test_word_query_matches_same_prompts_as_substring(
        self, fts_dialect_matrix: Session
    ):
        session = fts_dialect_matrix
        user = _make_user(session)
        category = _make_category(session)

        matching = _make_prompt(
            session,
            user,
            category,
            title="Guide",
            prompt="this mentions gizmo explicitly",
        )
        non_matching = _make_prompt(
            session, user, category, title="Other", prompt="nothing relevant here"
        )
        session.commit()

        repo = PromptRepository(session)
        ranked_ids = {p.id for p, _ in repo.search(query="gizmo")}
        substring_ids = {p.id for p, _ in repo.search(query="gizmo", ranked=False)}

        assert ranked_ids == {matching.id}
        assert substring_ids == {matching.id}
        assert non_matching.id not in ranked_ids
        assert non_matching.id not in substring_ids


class TestSortPrecedenceAndPagination:
    """T011: explicit non-relevance ordering wins; pagination is stable; count() matches search()."""

    def test_ranked_false_restores_legacy_ordering(self, fts_dialect_matrix: Session):
        session = fts_dialect_matrix
        user = _make_user(session)
        category = _make_category(session)

        # Title match would rank first under FTS; body-only match would rank
        # second. With ranked=False, relevance must NOT determine order —
        # only that both are still returned via the substring path.
        title_hit = _make_prompt(
            session, user, category, title="Term", prompt="unrelated"
        )
        body_hit = _make_prompt(
            session, user, category, title="Unrelated", prompt="term body"
        )
        session.commit()

        repo = PromptRepository(session)
        ranked_ids = [p.id for p, _ in repo.search(query="term", ranked=True)]
        legacy_ids = [p.id for p, _ in repo.search(query="term", ranked=False)]

        # Ranked path puts the title match first (relevance).
        assert ranked_ids.index(title_hit.id) < ranked_ids.index(body_hit.id)
        # Legacy substring path returns the same set without relevance ranking.
        assert set(legacy_ids) == {title_hit.id, body_hit.id}
        assert all(
            context is None for _, context in repo.search(query="term", ranked=False)
        )

    def test_ranked_pagination_no_duplicates_or_skips(
        self, fts_dialect_matrix: Session
    ):
        session = fts_dialect_matrix
        user = _make_user(session)
        category = _make_category(session)

        created = [
            _make_prompt(
                session, user, category, title=f"Widget {i}", prompt="widget body"
            )
            for i in range(5)
        ]
        session.commit()

        repo = PromptRepository(session)
        page1 = repo.search(query="widget", limit=2, offset=0)
        page2 = repo.search(query="widget", limit=2, offset=2)
        page3 = repo.search(query="widget", limit=2, offset=4)

        all_ids = (
            [p.id for p, _ in page1]
            + [p.id for p, _ in page2]
            + [p.id for p, _ in page3]
        )
        assert len(all_ids) == len(set(all_ids)) == 5
        assert set(all_ids) == {p.id for p in created}

    def test_count_matches_ranked_search_len(self, fts_dialect_matrix: Session):
        session = fts_dialect_matrix
        user = _make_user(session)
        category = _make_category(session)

        for i in range(4):
            _make_prompt(
                session, user, category, title=f"Doohickey {i}", prompt="doohickey body"
            )
        _make_prompt(
            session, user, category, title="Unrelated", prompt="nothing to do with it"
        )
        session.commit()

        repo = PromptRepository(session)
        results = repo.search(query="doohickey")
        total = repo.count(query="doohickey")

        assert total == len(results) == 4


class TestFallbackSanitizationAndPhrases:
    """T024: case-sensitive behavior/pagination, operator-only fallback, quoted phrases."""

    def test_case_sensitive_matching_unchanged(self, fts_dialect_matrix: Session):
        session = fts_dialect_matrix
        user = _make_user(session)
        category = _make_category(session)

        exact_case = _make_prompt(
            session, user, category, title="Widget", prompt="Gadget content"
        )
        wrong_case = _make_prompt(
            session, user, category, title="widget", prompt="gadget content"
        )
        session.commit()

        repo = PromptRepository(session)
        results = repo.search(query="Gadget", case_sensitive=True)
        result_ids = {p.id for p, _ in results}

        assert result_ids == {exact_case.id}
        assert wrong_case.id not in result_ids
        assert all(context is None for _, context in results)

    def test_case_sensitive_pagination_no_duplicates_or_skips(
        self, fts_dialect_matrix: Session
    ):
        session = fts_dialect_matrix
        user = _make_user(session)
        category = _make_category(session)

        created = [
            _make_prompt(
                session, user, category, title=f"Sprocket {i}", prompt="Sprocket body"
            )
            for i in range(5)
        ]
        # Distractor with the wrong case: must never appear in case-sensitive results.
        _make_prompt(
            session, user, category, title="sprocket lower", prompt="sprocket body"
        )
        session.commit()

        repo = PromptRepository(session)
        page1 = repo.search(query="Sprocket", case_sensitive=True, limit=2, offset=0)
        page2 = repo.search(query="Sprocket", case_sensitive=True, limit=2, offset=2)
        page3 = repo.search(query="Sprocket", case_sensitive=True, limit=2, offset=4)

        all_ids = (
            [p.id for p, _ in page1]
            + [p.id for p, _ in page2]
            + [p.id for p, _ in page3]
        )
        assert len(all_ids) == len(set(all_ids)) == 5
        assert set(all_ids) == {p.id for p in created}

        total = repo.count(query="Sprocket", case_sensitive=True)
        assert total == 5

    def test_operator_only_query_falls_back_without_error(
        self, fts_dialect_matrix: Session
    ):
        session = fts_dialect_matrix
        user = _make_user(session)
        category = _make_category(session)

        _make_prompt(session, user, category, title="Anything", prompt="body text")
        session.commit()

        repo = PromptRepository(session)
        # Punctuation/operator-only input sanitizes to empty (FR-011); must not raise.
        results = repo.search(query='*** :: -- "" ()')
        total = repo.count(query='*** :: -- "" ()')

        assert results == []
        assert total == 0

    def test_embedded_operator_char_in_token_does_not_error(
        self, fts_dialect_matrix: Session
    ):
        session = fts_dialect_matrix
        user = _make_user(session)
        category = _make_category(session)

        _make_prompt(session, user, category, title="Foobar widget", prompt="body text")
        session.commit()

        repo = PromptRepository(session)
        # Operator characters embedded mid-token (not just at the edges) must be
        # stripped before reaching FTS5 MATCH / to_tsquery, per FR-011.
        results = repo.search(query="foo&bar")
        total = repo.count(query="foo&bar")

        assert total == len(results)

    def test_quoted_phrase_matches_as_a_unit(self, fts_dialect_matrix: Session):
        session = fts_dialect_matrix
        user = _make_user(session)
        category = _make_category(session)

        phrase_hit = _make_prompt(
            session, user, category, title="Doc", prompt="please quick brown fox jumps"
        )
        words_out_of_order = _make_prompt(
            session,
            user,
            category,
            title="Doc2",
            prompt="a fox that is brown and quick",
        )
        session.commit()

        repo = PromptRepository(session)
        results = repo.search(query='"quick brown fox"')
        result_ids = {p.id for p, _ in results}

        assert phrase_hit.id in result_ids
        assert words_out_of_order.id not in result_ids
