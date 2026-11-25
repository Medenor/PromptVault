---
title: Release Notes
sidebar_position: 1
---

# Release Notes

Highlights from recent PromptVault releases. For the complete, unabridged history, see `docs/CHANGELOG.md` in the repository.

For upgrade steps, see [Update PromptVault](../installation/update.md).

## 1.17.1

- **API fix**. Creating or deleting prompts and importing or replacing skill archives now return the expected status and rate-limit headers when rate limiting is enabled.
- **Deployment**. The production guide now explains how to use a separate `.env.production`, replace the default database password, and roll back using the previous image.

## 1.17.0

- **Fix**: PostgreSQL installations running 1.16.0 failed to start with `No module named 'psycopg'`. PromptVault now ships the psycopg v3 driver. Your `DATABASE_URL` does not need to change: both `postgresql://` and `postgresql+psycopg2://` work. SQLite is not affected.
- **Security fix**: PyJWT was upgraded to 2.15.1. A token with deeply nested JSON made the refresh, logout and 2FA endpoints answer with a server error instead of a 401. Tokens sent in a request body are now limited to 4096 characters. PromptVault only accepts ES256 tokens, so the other PyJWT advisories do not apply.
- **Hardening**: the password reset flow no longer hands the plain reset token back to its caller, and it logs a masked email address instead of the raw one.
- **Interface**: on each prompt card, Copy is now the main blue action and Edit is secondary. History, Copy+Version, Share and Delete are in a "More actions" menu. The header is neutral on every page. Dark mode is fixed for badges, banners, buttons, footer links and the favorite star. A failed first load of the prompt list now shows an error with a "Try again" button.
- **Upgrade**: rebuild the images and restart. No database migration is needed.

## 1.16.0

- **Security fix**: the password reset request now gives the same answer whether or not an account exists, and the reset link is no longer written to the application logs. Reset links expire after one hour, but you may want to purge older log lines containing `reset-password?token=`.
- **Fix**: `setup_env.py --from-file` now accepts unquoted YAML values (`true`, `20`) and keeps the default for any key missing from the file. `DB_POOL_SIZE` is checked as a positive number instead of a port.
- **Setup wizard**: its dependencies (`click`, `rich`, `httpx`) moved to the `setup` extra, and the Docker image no longer installs them. Run `pip install -e ".[setup]"` (or `make install`) before `scripts/setup/setup.py`.
- **Build**: building the frontend now requires Node.js 26 or later.
- **Upgrade**: rebuild the images and restart. No database migration is needed.

## 1.15.0

- **API developer guides**: a new Developer / API space explains how to call the PromptVault API: first calls (login with 2FA, read, create, search, history) and a reference for routes, permissions, pagination and errors. See [Developer / API](../developer-api/index.md).
- **Update guide**: the portal now has a guide for backing up, updating, verifying, and restoring a Docker Compose installation. See [Update PromptVault](../installation/update.md).
- **Back to PromptVault**: each page has a link back to the app. Set `DOCS_APP_URL` when building the docs image to point it to your instance.
- **Now on GitHub**: the source code, issues and releases moved from Codeberg to https://github.com/Medenor/PromptVault, and the footer link follows.

## 1.14.1

- **Fix**: the skill import and edit dialogs now follow dark mode instead of showing on a white background.

## 1.14.0

- **Skills**: PromptVault now stores skills (a `SKILL.md` plus scripts, references and other files) next to your prompts. Import a skill from a `.zip` with **New ▾ → Import skill**, browse its rendered instructions and file tree, edit its details, replace its files, download it as a `.zip`, or delete it. Skills are searchable, filterable by type, and included in database backups. Version history, sharing, placeholders and bulk import/export do not apply to skills yet. See the new Skills page in the user guide.
- **Header menus**: "New prompt" and "Import skill" now share a **New ▾** menu, and secondary links move into a **More ▾** menu on medium-width screens, so the navigation fits on one line.
- **Security fix**: bulk tag updates now check that you own (or administer) every selected item.
- **Upgrade**: apply the database migration and rebuild the images. A reload may be needed once to pick up new translations.

## 1.13.1

- **Fix**: rebuilding the Docker image without cache no longer fails with `No module named 'psycopg'` (the SQLAlchemy dependency is now capped below 2.1).
- **Fix**: the Documentation link in the application menu now works in Docker deployments. The Docker stack includes a `docs` service serving the portal on port 7876. After upgrading, rebuild both images: `docker-compose build web docs && docker-compose up -d docs web`.

## 1.13.0

- **Optional two-factor authentication (time-based one-time password, TOTP)**: users can enroll an authenticator app from their profile and get single-use recovery codes. Admins can require 2FA per role.
- **Documentation portal link**: the application menu now links to the documentation portal. The deployment URL is configured with `VITE_DOCS_PORTAL_URL`; local development uses `http://localhost:7876`.
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
