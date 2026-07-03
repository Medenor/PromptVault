# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Lightweight tag suggestion service."""

from collections import Counter
import re
import unicodedata
from typing import Iterable, List, Tuple

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")

_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "your",
    "you",
    "are",
    "was",
    "were",
    "have",
    "has",
    "had",
    "not",
    "but",
    "use",
    "using",
    "how",
    "what",
    "why",
    "when",
    "where",
    "who",
    "will",
    "can",
    "could",
    "should",
    "would",
    "about",
    "above",
    "below",
    "under",
    "over",
    "than",
    "then",
    "them",
    "they",
    "their",
    "there",
    "here",
    "also",
    "such",
    "these",
    "those",
    "only",
    "each",
    "more",
    "most",
    "some",
    "any",
    "all",
    "one",
    "two",
    "three",
    "four",
    "five",
    "six",
    "seven",
    "eight",
    "nine",
    "ten",
}

_SYNONYMS = {
    "database": {"basedonnees", "basededonnees", "donnees", "data"},
    "review": {"revue"},
    "security": {"securite"},
    "testing": {"test", "tests"},
    "verified": {"verifie", "verifiee", "validation"},
    "bug": {"bug"},
    "fixed": {"corrige", "corrigee", "corrigees"},
    "final": {"finale"},
}

_REVERSE_SYNONYMS = {}
for key, values in _SYNONYMS.items():
    for value in values:
        _REVERSE_SYNONYMS.setdefault(value, set()).add(key)


def _normalize(text: str) -> str:
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _tokenize(text: str) -> List[str]:
    normalized = _normalize(text)
    return [token for token in _TOKEN_PATTERN.findall(normalized)]


def _equivalent_tokens(token: str) -> List[str]:
    equivalents = {token}
    if token in _SYNONYMS:
        equivalents.update(_SYNONYMS[token])
    if token in _REVERSE_SYNONYMS:
        equivalents.update(_REVERSE_SYNONYMS[token])
    return list(equivalents)


def suggest_tags(
    content: str,
    existing_tags: Iterable[str],
    limit: int = 10,
) -> List[Tuple[str, float]]:
    """Suggest tags based on existing taxonomy and content.

    Args:
        content: Prompt content to analyze
        existing_tags: List of tag names to consider
        limit: Maximum number of suggestions

    Returns:
        List of (tag_name, score) tuples, ordered by score desc.
    """
    if not content:
        return []

    tokens = _tokenize(content)
    tokens = [token for token in tokens if len(token) >= 3 and token not in _STOPWORDS]
    if not tokens:
        return []

    token_counts = Counter(tokens)
    suggestions: List[Tuple[str, float]] = []

    for tag in existing_tags:
        if not tag:
            continue
        tag_tokens = _tokenize(tag)
        if not tag_tokens:
            continue
        matched = 0
        score = 0.0
        for tag_token in tag_tokens:
            best_count = 0
            for candidate in _equivalent_tokens(tag_token):
                best_count = max(best_count, token_counts.get(candidate, 0))
            if best_count > 0:
                matched += 1
                score += float(best_count)
        if matched == 0:
            continue
        required = max(1, (len(tag_tokens) + 1) // 2)
        if matched >= required:
            score *= matched / len(tag_tokens)
            suggestions.append((tag, score))

    suggestions.sort(key=lambda item: (-item[1], item[0].lower()))
    return suggestions[:limit]
