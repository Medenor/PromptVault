# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Lightweight tag suggestion service."""

from collections import Counter
import re
from typing import Iterable, List, Tuple

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "into", "your", "you",
    "are", "was", "were", "have", "has", "had", "not", "but", "use", "using",
    "how", "what", "why", "when", "where", "who", "will", "can", "could",
    "should", "would", "about", "above", "below", "under", "over", "than",
    "then", "them", "they", "their", "there", "here", "also", "such", "these",
    "those", "only", "each", "more", "most", "some", "any", "all", "one",
    "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
}


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

    tokens = [token.lower() for token in _TOKEN_PATTERN.findall(content)]
    tokens = [token for token in tokens if len(token) >= 3 and token not in _STOPWORDS]
    if not tokens:
        return []

    token_counts = Counter(tokens)
    suggestions: List[Tuple[str, float]] = []

    for tag in existing_tags:
        if not tag:
            continue
        tag_lower = tag.lower()
        if tag_lower in token_counts:
            suggestions.append((tag, float(token_counts[tag_lower])))

    suggestions.sort(key=lambda item: (-item[1], item[0].lower()))
    return suggestions[:limit]
