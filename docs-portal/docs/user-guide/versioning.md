---
title: Prompt Versioning
sidebar_position: 1
---

# Prompt Versioning

PromptVault keeps a full, Git-like history of every prompt, so you never lose track of how a prompt evolved and can always revert to an earlier version.

## Automatic Versioning {#automatic-versioning}

Every time you save a change to a prompt, PromptVault automatically creates a new version recording:

- A unique version ID
- A timestamp
- The author of the change
- A commit message describing what changed
- A complete snapshot of the prompt at that point in time

You don't need to do anything to enable this — it happens on every update.

## Viewing Version History {#viewing-version-history}

Open the version history for any prompt via:

- The keyboard shortcut `Cmd+H` (Mac) or `Ctrl+H` (Windows/Linux)
- The "Version History" button in the prompt editor

The history modal lists every version newest-first, with its commit message and metadata, a search box to find a specific version, and quick actions to compare or revert.

## Comparing Versions {#comparing-versions}

From the version history modal, select any two versions to see a detailed diff across all prompt fields (title, content, category, tags, notes).

Text fields use character-level diff highlighting rather than line-level diffs, so small edits — a typo fix, a punctuation change, a single added word — are easy to spot instead of being buried in a wall of "changed line" noise. Insertions appear with a green highlight, deletions with a red strikethrough, and unchanged text stays neutral.

## Reverting to a Previous Version {#reverting-to-a-previous-version}

From the comparison or history view, you can revert a prompt to any prior version. Reverting creates a **new** version containing the old content — it doesn't delete history, so the revert itself is also tracked and can be undone by reverting again.

## Why This Matters {#why-this-matters}

If you're iterating on a prompt and a new variant performs worse, you can always get back to what worked without having to remember or manually re-type the previous wording.
