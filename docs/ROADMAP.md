# PromptVault Roadmap

_Rebuilt 2026-11-13 from the current `main` (v1.13.1). Replaces the 2025 and 2026-07 reports, whose completed items are recorded in `docs/CHANGELOG.md` and in git history. Detailed to-do lists for the items below live in `docs/archives/IMPROVEMENT_PLAN_2026-08.md` and in the linked Codeberg issues._

## Shipped

| Area                                                                        | Delivered                                                         | Where                                              |
| --------------------------------------------------------------------------- | ----------------------------------------------------------------- | -------------------------------------------------- |
| Input validation                                                            | Pydantic request models, field limits, tag rules                  | `src/web/models/`                                  |
| Structured logging and audit                                                | No `print()` in `src/`, request IDs, audit events                 | `src/services/logging_service.py`                  |
| Authentication and RBAC                                                     | Argon2id, ES256 tokens with rotation, lockout, session cap, roles | `docs/AUTHENTICATION_SECURITY.md`                  |
| Database                                                                    | SQLAlchemy and Alembic, SQLite and PostgreSQL                     | `docs/SPECS/SPEC_DATABASE.md`                      |
| Legacy JSON services removed                                                | Retired in PR #63                                                 | `docs/CHANGELOG.md`                                |
| XSS hardening                                                               | `innerHTML` elimination, lint enforcement                         | `docs/archives/IMPROVEMENT_PLAN_2026-08.md` item 1 |
| Rate limiting beyond auth                                                   | Per-user buckets on prompt, import, export and backup routes      | `docs/RATE_LIMITING.md`                            |
| Prompt sharing                                                              | Read and edit grants, shared-with-me filter                       | `specs/007-prompt-sharing/`                        |
| Full-text search                                                            | FTS5 on SQLite, tsvector on PostgreSQL                            | `specs/008-full-text-search/`                      |
| God-file decomposition                                                      | Frontend and backend splits                                       | `docs/archives/IMPROVEMENT_PLAN_2026-08.md` item 6 |
| Two-factor authentication                                                   | TOTP, recovery codes, admin-enforced policy                       | `specs/009-totp-2fa/`                              |
| Documentation portal                                                        | Docusaurus, EN/FR/DE/ES, served from Docker                       | `docs-portal/`                                     |
| Tag and category management, bulk delete, mobile layout, accessibility pass | Shipped in the 2025 cycle (issues #16, #24, #25, #21)             | `docs/CHANGELOG.md`                                |

## Now

These items are planned for the next implementation cycle.

- **AI-native prompt tooling** — live token estimate, per-prompt target model and parameters, optional Test Run panel with a user-supplied key. Codeberg [#98](https://codeberg.org/medenor/promptvault/issues/98).
- **Pagination completion** — bounded defaults on every list endpoint, "Load more" on the prompt grid. Codeberg [#99](https://codeberg.org/medenor/promptvault/issues/99).

## Next

Start once the "Now" items are in review.

- **Dark mode completion and theme toggle** — audit `dark:` variants, WCAG AA contrast, system/light/dark preference. Codeberg [#100](https://codeberg.org/medenor/promptvault/issues/100).
- **Prompt analytics dashboard** — owner-scoped usage stats built on the audit log and a `copy` event. Codeberg [#101](https://codeberg.org/medenor/promptvault/issues/101), related to [#22](https://codeberg.org/Medenor/promptvault/issues/22).

## Later

- **Team collaboration beyond sharing** — real-time updates, presence and edit locks. Codeberg [#17](https://codeberg.org/Medenor/promptvault/issues/17). Sharing grants already exist, so this only covers live behavior.
- **Export and integrations** — PDF and HTML export, public links, and the other items in Codeberg [#23](https://codeberg.org/Medenor/promptvault/issues/23).
- **Public API and developer docs** — versioned API, OpenAPI tags, API keys. Codeberg [#19](https://codeberg.org/Medenor/promptvault/issues/19).
- **Skill packages** — multi-file skills stored alongside prompts. Codeberg [#73](https://codeberg.org/Medenor/promptvault/issues/73). On hold; branch `011-skill-packages` exists and should wait until the 2FA and docs-portal work is finalized.
- **HTTPS and TLS support** — Codeberg [#31](https://codeberg.org/Medenor/promptvault/issues/31).

## Open bugs and hygiene

These are not roadmap items, but they block or affect trust in the build.

- [#88](https://codeberg.org/medenor/promptvault/issues/88) — four stale snapshot tests fail on `main`.
- [#90](https://codeberg.org/medenor/promptvault/issues/90) — edit modal stays open after a new search or filter.
- [#61](https://codeberg.org/Medenor/promptvault/issues/61) — password-reset email is stubbed; the link is only logged.
- [#93](https://codeberg.org/medenor/promptvault/issues/93) — admin cannot disable 2FA for a locked-out user.
- [#95](https://codeberg.org/medenor/promptvault/issues/95) — "Update PromptVault" page for the documentation portal.
- [#97](https://codeberg.org/medenor/promptvault/issues/97) — `make release` and `make release-dry-run` targets.

## Principles for ordering

- Close security and integrity gaps before adding features that widen the attack surface.
- Prefer additive changes that reuse existing repositories and the dual-backend migration pattern.
- Keep every item behind a Codeberg issue so progress can be tracked in one place.

## Relationship to other documents

- `docs/archives/IMPROVEMENT_PLAN_2026-08.md` holds the detailed to-do lists and per-item status for the August 2026 plan.
- `docs/CHANGELOG.md` records what shipped in each release.
- This roadmap is the single prioritized view. When an item moves, update this file and the linked issue together.
