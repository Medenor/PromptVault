---
title: Import & Export
sidebar_position: 7
---

# Import & Export

Prompts can be exported to a file and later re-imported, either as a portable backup of your own library or to move prompts between instances.

## Export Formats

Prompts export to **CSV**, **Markdown**, or **JSON**. JSON export produces PromptVault's own envelope format, which is also the format the importer recognizes automatically when re-importing.

## Import Modes

When importing a file, you choose how it interacts with your existing prompts:

- **Append** — every prompt in the file is added, even if a prompt with the same title already exists (can create duplicates).
- **Merge** — a prompt in the file is only added if no existing prompt already has that exact title; otherwise it's skipped.
- **Replace** — your entire existing prompt library is cleared first, then every prompt in the file is added. PromptVault automatically creates a backup before a replace import runs, so the prior state isn't lost.

## Sharing State Is Not Portable

Export/import never includes prompt-sharing grants — see [Sharing](./sharing.md#exportimport-and-sharing) for why, and for the recommended alternative when you need that state preserved.

## Import/Export Statistics

An import/export stats view reports current usage figures for both operations, useful for confirming a large import or export actually completed as expected.
