# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""T022: FTS performance benchmark (US3 — fast search on large vaults).

Builds a seeded vault of prompts and asserts:
- SC-001: a single-word ranked (FTS) query returns in < 1s at ~5,000 rows.
- SC-002: FTS wall-clock beats the substring (``ilike``) baseline on the
  same data, with both returning the same correct match set.
- FR-016: FTS latency scales sub-linearly (near-flat) from ~1,000 to ~5,000
  rows, while the substring baseline grows roughly linearly with row count.

Requires SQLite FTS5 (skipped module-wide otherwise, mirroring
tests/test_fts_search.py). Marked ``performance`` so it can be deselected
from routine runs via ``-m "not performance"``.
"""

import sqlite3
import time
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


pytestmark = [
    pytest.mark.performance,
    pytest.mark.skipif(
        not _sqlite_has_fts5(),
        reason="SQLite build does not have FTS5 compiled in (PRAGMA compile_options lacks ENABLE_FTS5)",
    ),
]

# The term seeded into a distinguishing fraction of rows so both the FTS and
# substring paths have a real, identical, and non-trivial match set to find.
_NEEDLE = "zzyzxneedle"
_HIT_STRIDE = 10  # 1 in 10 prompts contains the needle in its body.

# Padding text repeated into every prompt body so the substring scan has a
# realistic amount of text to walk per row (short in-memory rows make ilike
# look artificially fast and drown the timing signal in ORM/Python overhead).
_FILLER = (
    "the quick brown fox jumps over the lazy dog while pondering the "
    "nature of prompt engineering and large language model behavior "
) * 20

# Number of timed trials per measurement; the minimum is taken to cancel
# scheduling/GC noise (standard microbenchmark practice).
_TRIALS = 5


def _make_user(session: Session) -> User:
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        username=f"bench_{user_id[:8]}",
        display_name="Benchmark User",
        email=f"{user_id[:8]}@example.com",
        password_hash="hashed_password_placeholder",
        role="user",
    )
    session.add(user)
    session.flush()
    return user


def _make_category(session: Session) -> Category:
    category = Category(name="Benchmark Category", description="FTS benchmark")
    session.add(category)
    session.flush()
    return category


def _seed_prompts(
    session: Session,
    user: User,
    category: Category,
    count: int,
    *,
    offset: int = 0,
    hit_stride: int | None = _HIT_STRIDE,
) -> int:
    """Bulk-insert ``count`` prompts; every ``hit_stride``-th prompt contains the needle.

    ``offset`` shifts the numbering (and hit phase) so repeated calls that
    grow the same table don't all land hits on the same row indices.
    ``hit_stride=None`` seeds zero needle hits (pure corpus-size padding, used
    by the scaling test to grow the searched corpus without growing the
    match-set size).

    Returns the number of prompts in this batch that contain the needle.
    """
    hits = 0
    rows = []
    for i in range(offset, offset + count):
        is_hit = hit_stride is not None and i % hit_stride == 0
        if is_hit:
            hits += 1
        body = (
            f"lorem ipsum dolor sit amet {_NEEDLE} consectetur adipiscing elit number {i} {_FILLER}"
            if is_hit
            else f"lorem ipsum dolor sit amet consectetur adipiscing elit number {i} {_FILLER}"
        )
        rows.append(
            {
                "title": f"Benchmark Prompt {i}",
                "prompt": body,
                "note": None,
                "category_id": category.id,
                "user_id": user.id,
            }
        )
    session.bulk_insert_mappings(Prompt, rows)
    session.commit()
    return hits


def _time_search(repo: PromptRepository, *, ranked: bool) -> tuple[float, set[int]]:
    """Run the query _TRIALS times and return (min elapsed, match ids).

    Taking the minimum over several trials is standard microbenchmark
    practice for cancelling GC pauses/OS scheduling noise; the match set is
    identical across trials so any one trial's ids can be returned.
    """
    best = float("inf")
    matched_ids: set[int] = set()
    for _ in range(_TRIALS):
        start = time.perf_counter()
        results = repo.search(query=_NEEDLE, ranked=ranked, limit=None)
        elapsed = time.perf_counter() - start
        best = min(best, elapsed)
        matched_ids = {p.id for p, _ in results}
    return best, matched_ids


class TestFTSBenchmark:
    """T022: 5k-row benchmark — absolute latency, FTS-vs-ilike, and scaling."""

    def test_fts_query_under_one_second_at_5k(self, fts_db_session: Session):
        """SC-001: a single-word ranked query returns in < 1s at ~5,000 prompts."""
        session = fts_db_session
        user = _make_user(session)
        category = _make_category(session)
        expected_hits = _seed_prompts(session, user, category, 5000)

        repo = PromptRepository(session)
        elapsed, matched_ids = _time_search(repo, ranked=True)

        assert len(matched_ids) == expected_hits
        assert elapsed < 1.0, f"FTS query took {elapsed:.3f}s, expected < 1s at 5k rows"

    def test_fts_beats_substring_baseline_with_equal_matches(
        self, fts_db_session: Session
    ):
        """SC-002: FTS wall-clock beats ilike on the same data, same matches."""
        session = fts_db_session
        user = _make_user(session)
        category = _make_category(session)
        expected_hits = _seed_prompts(session, user, category, 5000)

        repo = PromptRepository(session)
        fts_elapsed, fts_ids = _time_search(repo, ranked=True)
        substring_elapsed, substring_ids = _time_search(repo, ranked=False)

        assert fts_ids == substring_ids
        assert len(fts_ids) == expected_hits

        assert fts_elapsed < substring_elapsed, (
            f"FTS ({fts_elapsed:.4f}s) did not beat substring baseline "
            f"({substring_elapsed:.4f}s) at 5k rows"
        )

    def test_fts_scales_sublinearly_vs_linear_substring_baseline(
        self, fts_db_session: Session
    ):
        """FR-016: FTS latency grows sub-linearly with corpus size; ilike grows ~linearly.

        Isolates *lookup* cost from *result-materialization* cost by holding
        the match-set size fixed (a handful of needle hits seeded once) while
        growing the surrounding no-match corpus 5x. If match count also grew
        with corpus size, result-row fetching/snippet cost would dominate
        both paths' timing and mask the underlying scan-cost difference.
        """
        session = fts_db_session
        user = _make_user(session)
        category = _make_category(session)

        repo = PromptRepository(session)

        # A fixed, small number of needle hits, seeded once.
        _FIXED_HITS = 5
        expected_hits = _seed_prompts(
            session, user, category, _FIXED_HITS, offset=0, hit_stride=1
        )
        assert expected_hits == _FIXED_HITS

        # Pad with ~1,000 non-matching rows and measure at ~1,000 total.
        _seed_prompts(session, user, category, 1000, offset=100_000, hit_stride=None)
        fts_small, ids_small = _time_search(repo, ranked=True)
        substring_small, _ = _time_search(repo, ranked=False)
        assert len(ids_small) == _FIXED_HITS

        # Pad to ~5,000 total (5x corpus) with more non-matching rows; the
        # match-set size is unchanged.
        _seed_prompts(session, user, category, 4000, offset=200_000, hit_stride=None)
        fts_large, ids_large = _time_search(repo, ranked=True)
        substring_large, _ = _time_search(repo, ranked=False)
        assert len(ids_large) == _FIXED_HITS

        # Guard against measurement noise on very fast queries.
        floor = 0.001
        fts_small = max(fts_small, floor)
        substring_small = max(substring_small, floor)

        fts_ratio = fts_large / fts_small
        substring_ratio = substring_large / substring_small

        # 5x the corpus should not come close to 5x the FTS time (near-flat,
        # index-backed). Allow generous headroom for test-environment noise.
        assert fts_ratio < 3.0, (
            f"FTS latency grew {fts_ratio:.2f}x for a 5x corpus increase "
            f"(small={fts_small:.4f}s, large={fts_large:.4f}s) — expected near-flat scaling"
        )
        # The FTS scaling factor should be meaningfully better than the
        # substring baseline's scaling factor, demonstrating the index is
        # doing real work rather than both paths coincidentally being fast.
        assert fts_ratio < substring_ratio, (
            f"FTS scaling ({fts_ratio:.2f}x) did not beat substring scaling "
            f"({substring_ratio:.2f}x) from 1k to 5k corpus rows"
        )
