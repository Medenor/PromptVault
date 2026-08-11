# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Dialect detection, query sanitization, and snippet helpers for full-text search.

Shared by ``PromptRepository.search()``/``count()`` so both SQLite (FTS5)
and PostgreSQL (tsvector) branches build their queries from the same safe,
pre-sanitized representation. See research.md Decisions 3-5.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

# Snippet highlight sentinels (research.md Decision 5). Neutral markers
# instead of raw <mark> so the frontend can escapeHtml() the whole string
# first and only then turn these into markup (FR-007/SC-006).
MATCH_START = "[[MATCH]]"
MATCH_END = "[[/MATCH]]"

# Characters that are FTS5/tsquery operators or punctuation with no
# standalone meaning as search text. A token made up only of these is
# dropped rather than passed to the query engine (FR-011).
_OPERATOR_CHARS = set('"*^:()-+~|&!<>@')

_QUOTED_PHRASE_RE = re.compile(r'"([^"]+)"')
_TOKEN_RE = re.compile(r"[^\s]+")


@dataclass
class SafeQuery:
    """A sanitized search query, dialect-agnostic.

    ``terms`` are bare (unquoted) words to be OR-joined; ``phrases`` are
    quoted substrings to be matched as phrases and OR'd in alongside the
    bare terms (research.md Decision 4 — OR semantics, not AND).
    """

    terms: list[str] = field(default_factory=list)
    phrases: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not self.terms and not self.phrases

    def to_fts5_match(self) -> str:
        """Build a SQLite FTS5 MATCH expression: OR-joined terms/phrases."""
        clauses = [f'"{phrase}"' for phrase in self.phrases]
        clauses += [f'"{term}"' for term in self.terms]
        return " OR ".join(clauses)

    def to_tsquery(self) -> str:
        """Build a Postgres to_tsquery expression: OR-joined terms/phrases.

        Phrases become sequential (<->) joins of their words so they match
        as a unit; the whole thing is OR'd with the bare terms.
        """
        clauses = []
        for phrase in self.phrases:
            words = phrase.split()
            if words:
                clauses.append(" <-> ".join(words))
        clauses += list(self.terms)
        return " | ".join(clauses)


def active_dialect(session: Session) -> str:
    """Return the active SQLAlchemy dialect name: 'sqlite' or 'postgresql'."""
    return session.get_bind().dialect.name


def _clean_token(token: str) -> str:
    return token.strip(''.join(_OPERATOR_CHARS))


def sanitize_fts_query(raw: str | None) -> SafeQuery | None:
    """Sanitize raw user input into a SafeQuery, or None to signal fallback.

    - Extracts "quoted phrases" first.
    - Splits the remainder on whitespace into bare tokens.
    - Strips operator-only punctuation from each token; drops empty results.
    - Returns None when nothing usable remains (caller falls back to the
      substring/ilike path per FR-010/FR-011).
    """
    if not raw:
        return None

    phrases: list[str] = []

    def _capture_phrase(m: re.Match) -> str:
        phrase = m.group(1).strip()
        if phrase:
            phrases.append(phrase)
        return " "

    remainder = _QUOTED_PHRASE_RE.sub(_capture_phrase, raw)

    terms: list[str] = []
    for token in _TOKEN_RE.findall(remainder):
        cleaned = _clean_token(token)
        if cleaned:
            terms.append(cleaned)

    query = SafeQuery(terms=terms, phrases=phrases)
    if query.is_empty():
        return None
    return query


# --- Snippet helpers (research.md Decision 5) --------------------------

# Ellipsis inserted between non-adjacent excerpt fragments.
_SNIPPET_ELLIPSIS = "..."

# Approximate number of tokens of context to keep around a match.
_SNIPPET_TOKENS = 32


def fts5_snippet_args(column_index: int) -> tuple:
    """Positional args for SQLite's snippet(), after the table name.

    Usage: ``snippet(prompts_fts, <column_index>, ?, ?, ?, ?)`` bound with
    these four values (start sentinel, end sentinel, ellipsis, token count).
    """
    return (column_index, MATCH_START, MATCH_END, _SNIPPET_ELLIPSIS, _SNIPPET_TOKENS)


def ts_headline_options() -> str:
    """The options string for Postgres ts_headline(), using our sentinels."""
    return f"StartSel={MATCH_START}, StopSel={MATCH_END}, MaxFragments=1, MaxWords=35, MinWords=15"
