---
title: Pagination
sidebar_position: 8
---

# Pagination

The main prompt grid loads results a page at a time rather than fetching your entire library at once, keeping the initial load fast even with a large collection.

## Loading More

When more prompts are available than the current page shows, a "Load More" control fetches the next page and appends it to what's already displayed, without losing your place. Once every prompt has been loaded, the control disappears.

## Page Size

You can choose a page size of 25, 50, or 100 prompts; if you don't choose one, PromptVault loads 50 at a time by default. Requesting a page size above 100 is clamped down to 100 rather than rejected.

## Pagination and Filters

Applying a [category](./categories.md) or [tag](./tags.md) filter, or a [search](./search.md) query, paginates the filtered result set, not your full library — and changing any filter resets you back to the first page.
