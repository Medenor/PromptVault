# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two audiences, equally first-class: solo self-hosters who keep a private library of prompts and skills, and small teams who run one shared instance and curate, version and share prompts and skills for daily AI work (content marketing, software development, general AI use). Users can be non-technical. Admins manage users and backups.

## Product Purpose

PromptVault is a self-hosted web app for organizing, versioning and retrieving AI prompts, and for storing skills (multi-file Agent Skills packages: a `SKILL.md` plus scripts, references and assets). It centralizes a prompt library so people reuse and improve prompts instead of rewriting them. Success: people find the right prompt or skill fast, change it without fear of losing history, and trust the instance with their data.

## Positioning

Self-hosted, you own the data. The instance runs on the user's own infrastructure (Docker, PostgreSQL or SQLite), with encrypted backups (Argon2id-derived AES-256-GCM), optional upload to S3-compatible storage, and an append-only backup audit log. Git-like versioning, prompts and skills side by side, and private-by-default sharing support this but are not the headline claim.

## Operating Context

- Runs as a FastAPI app with Jinja2 templates and a TypeScript frontend built with Vite, deployed with Docker; a Docusaurus documentation portal (`docs-portal/`) ships alongside.
- Multi-user with JWT (ES256) auth, roles, password reset, session management and rate limiting.
- Core workflows: browse and filter the prompt list (category, tags, favorites, All / Prompts / Skills, "Shared with me"); edit with commit messages; version history and diff with revert; import/export; backup management; share a prompt with a teammate; import, view and download a skill.
- UI languages: English, French, Spanish, German, switchable without a restart.

## Capabilities and Constraints

- Prompts default to private (owner, admins, explicit grantees). Grants are `read` or `edit`; grantees cannot delete, re-share, transfer ownership or toggle favorites. Pre-existing prompts were grandfathered as "Public (legacy)".
- Revert creates a new version; history is never lost.
- Skills: imported from `.zip`, read in memory only and never extracted or executed; searchable, tagged, included in backups. Not yet available for skills: version history, sharing, placeholders, bulk Import/Export.
- Frontend rules (see `docs/agents/frontend.md`): TypeScript only, Tailwind v4 utilities with no custom CSS, i18n keys for every UI string, dark mode via OS `prefers-color-scheme`, a component set in `src/web/static/ts/components/`, and a Service Worker `CACHE_VERSION` bump on any change under `src/web/static/`.

## Brand Commitments

Name: PromptVault. A logo exists at `docs/images/promptvault_logo.jpg`. No further brand commitments were stated; none are binding beyond the existing name.

## Evidence on Hand

- Screenshot gallery in `docs/images/gallery/` (login, main interface, editor, version history, import/export, backup, profile, admin).
- README feature descriptions and the specs under `specs/`.
- No testimonials, customer names, benchmarks or pricing exist; do not invent them.

## Product Principles

1. Ownership is the promise: the user's data stays on their own instance, and backups and exports make that tangible.
2. History is safe: changes are recorded and reversible, and destructive actions are guarded by backups.
3. Private by default: sharing is explicit and granular.
4. Equal footing for solo and team use: neither needs the other's complexity.
5. Prompts and skills are one library with one way to browse, search and organize.

## Accessibility & Inclusion

Existing repo commitment: focus states, keyboard navigation, ARIA labels and semantic HTML, with four-language i18n. No formal WCAG level was set; none is recorded as required.
