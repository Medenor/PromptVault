---
title: Search
sidebar_position: 4
---

# Search

PromptVault's search runs against a real full-text index rather than a plain substring scan, so results are ranked by relevance and stay fast as your prompt library grows.

## How Ranking Works {#how-ranking-works}

Matches in a prompt's **title** are weighted highest, then its **body**, then its **note** — so a prompt whose title matches your query surfaces above one that only mentions the term in passing. Plain multi-word queries are OR-joined: prompts matching only some of the words still appear, just ranked below prompts matching all of them.

If you explicitly choose a sort option (e.g. sort by date), that overrides relevance ranking, since you've asked for a specific order.

## Matched-Term Highlighting {#matched-term-highlighting}

Search results include a highlighted snippet showing the matched term(s) in context, so you can tell at a glance why a given prompt matched without opening it.

## Exact and Phrase Matching {#exact-and-phrase-matching}

- `case_sensitive=true` searches preserve exact-case matching.
- Quoting a query (`"exact phrase"`) searches for that exact phrase rather than treating it as separate OR-joined words.

## Reliability {#reliability}

Any query PromptVault can't parse as a structured search (for example, one made up entirely of search operators with no actual search terms) transparently falls back to a plain substring search rather than returning an error — a search should never fail outright just because of how it was phrased.

## Performance {#performance}

Search stays fast as your library grows: query latency stays roughly flat rather than degrading linearly with the number of stored prompts, since the underlying index (not a full scan) does the matching work.
