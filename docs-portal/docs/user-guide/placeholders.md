---
title: Placeholders
sidebar_position: 4
---

# Placeholders

Placeholders turn a static prompt into a reusable template: write a bracketed token like `[DURATION]` or a braced token like `{DURATION}` anywhere in a prompt's content, and PromptVault will ask you to fill it in when you copy the prompt.

## Recognized Syntax

A placeholder name must be 2 or more characters made up of uppercase letters, digits, underscores, or spaces — for example `[DURATION]`, `[TYPE OF PRESENTATION]`, or `{MAX_RETRIES}`. Lowercase, mixed-case, and hyphenated tokens (like `[Duration]` or `[YYYY-MM-DD]`) are **not** recognized as placeholders and are left as plain text, as are stray brackets that don't form a well-matched pair.

`[DURATION]` and `{DURATION}` are treated as two distinct placeholders, even though they share a name — the bracket and brace syntaxes don't merge.

## Filling In Values on Copy

Clicking Copy on a prompt that contains placeholders opens a form with one input field per distinct placeholder, rather than copying immediately. If the same placeholder appears multiple times in the prompt, it still gets a single field — the value you enter replaces every occurrence. Confirming with some or all fields left blank still copies successfully; a blank field's placeholder token is copied unchanged in its original form.

Prompts with no placeholders copy instantly, exactly as before — the form only appears when there's something to fill in.

## Placeholders Elsewhere in PromptVault

Outside of the Copy-click flow, a placeholder token is treated as ordinary text everywhere: [version history](./versioning.md) stores each version's raw content with tokens intact, [search](./search.md) and category/tag filtering match placeholder text like any other text, and [exported](./import-export.md) content contains the original, unsubstituted tokens. The version-history and diff views are read-only and never show the placeholder-fill form — to copy an older version with values filled in, revert to it first, then use the regular Copy action.
