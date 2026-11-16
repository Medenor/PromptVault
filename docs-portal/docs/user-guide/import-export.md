---
title: Import & Export
sidebar_position: 7
---

# Import & Export

Export prompts to move prompt content between instances or to keep a portable copy of your library. Export is not a full backup: it does not retain sharing permissions. Use a full backup when you must preserve access-control state.

## Export Formats {#export-formats}

Prompts export to **CSV**, **Markdown**, or **JSON**. JSON export produces PromptVault's own envelope format, which is also the format the importer recognizes automatically when re-importing.

## Import Modes {#import-modes}

Before importing, identify the mode that matches your intended result. Choose **Replace** only when you intend to replace the entire library.

- **Append** — every prompt in the file is added, even if a prompt with the same title already exists (can create duplicates).
- **Merge** — a prompt in the file is only added if no existing prompt already has that exact title; otherwise it's skipped.
- **Replace** — your entire existing prompt library is cleared first, then every prompt in the file is added. PromptVault creates a backup before the import. Confirm that the backup completed before relying on it to recover the prior library.

## Sharing State Is Not Portable {#sharing-state-is-not-portable}

Export/import never includes prompt-sharing grants — see [Sharing](./sharing.md#exportimport-and-sharing) for why, and for the recommended alternative when you need that state preserved.

## Import/Export Statistics {#importexport-statistics}

An import/export stats view reports current usage figures for both operations, useful for confirming a large import or export actually completed as expected.
