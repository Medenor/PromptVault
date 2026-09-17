---
title: Release Notes
sidebar_position: 1
---

# Release Notes

Highlights from recent PromptVault releases. For the complete, unabridged history, see `docs/CHANGELOG.md` in the repository.

## Unreleased

- **Full-text search with relevance ranking**: search now runs against a real full-text index instead of a plain substring scan, with results ranked by relevance and highlighted match snippets.
- **App version shown in the footer**.
- Various backend reliability fixes (coverage report crash on templates, migration portability, dead-code cleanup).

## 1.12.0

- **Prompt sharing & team collaboration**: prompt owners can grant teammates read or edit access to individual prompts, with a "Shared with me" filter and clear badging between an explicit share and a legacy-visible prompt. Sharing state is intentionally not included in export/import — use a full backup/restore if you need it preserved.
- **Visibility change**: new prompts default to private; prompts that existed before this release were grandfathered as "Public (legacy)" and can be made private (one-way) by their owner or an admin.
- Large internal refactor of oversized templates and TypeScript modules — no user-visible behavior change.
- **Security**: extended rate limiting from auth endpoints to all state-changing and expensive endpoints (import/export, backups, bulk actions), now genuinely per-user rather than accidentally global. Fixed several stored-XSS risks from unsafe `innerHTML` usage.

## 1.11.0

- Dependency security patches (Jinja2, python-multipart, and others) closing 24 known CVEs.
- New CI security-audit job running dependency vulnerability scans on every push/PR.
- **Dynamic Prompt Placeholders**: prompt content can contain `[NAME]`/`{NAME}`-style tokens filled in at copy time.

## 1.10.0

- Server-side pagination for the prompt list, so large libraries load a page at a time instead of the entire dataset.
- **Enhanced Backup & Restore System**: encryption, cloud storage (S3-compatible, Google Drive, Dropbox), scheduling, and audit logging for backups, plus several backup-related security fixes (path traversal, stored XSS, unauthenticated endpoints).
- Global language selector added to every page's header.
- New Developer Workflow Makefile (`make install`, `make dev`, `make test`, `make lint`, `make build`) as a single entry point for common tasks.
- Mobile-responsive UI enhancements: touch-optimized navigation, offline support, and installability as a Progressive Web App.

## 1.9.0

- **Prompt Semantic Versioning**: prompts can be assigned an optional `MAJOR.MINOR.PATCH` version number when creating or editing.
