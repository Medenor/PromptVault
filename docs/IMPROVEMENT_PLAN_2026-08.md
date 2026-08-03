# Feature Improvement Report — July 2026

_Global analysis performed 2026-07-31 against the current `main` codebase. Complements (and cross-references) the 2026 report in `docs/ROADMAP.md`. Every finding below was verified against the code, not just the docs. Items are ranked by combined user value, technical complexity, and integration ease. Each To-Do list is written to be delegable as-is to an agent or contributor._

## Verified Baseline (evidence)

| Claim | Reality in code |
| --- | --- |
| "Structured logging shipped, zero `print()`" | ✅ Done 2026-08-02: zero executable `print()` calls in `src/`/`run_web.py`; CI gate (`make lint` → `rg "print\(" src run_web.py`) enforces it |
| "Legacy JSON services retired (PR #63)" | ✅ Done 2026-08-02: `PromptFilterService` + `PromptVersioningService` deleted along with their tests/fixtures |
| "Don't use `innerHTML`" (AGENTS.md) | 85 `innerHTML` sites in `static/ts/`; mostly escaped, no lint enforcement |
| Search | `LIKE`/`ilike` only; FTS explicitly deferred (`prompt_repository.py:23`) |
| Rate limiting | ✅ Done 2026-08-03: extended beyond auth to prompt CRUD/import/export/backup/revert via a per-user four-bucket taxonomy (`security/rate-limiting-beyond-auth`) |
| 2FA / sharing | Absent (grep-confirmed) |
| Largest files | `auth_service.py` 1148 · `dependencies/auth.py` 1054 · `index.html` 1745 · `prompt-list.ts` 871 |

---

## Priority List (High to Low)

### 1. XSS Hardening: `innerHTML` Elimination & Lint Enforcement (Security) - ✅ Done 2026-08-01 on branch `security/innerhtml-hardening`

- **Description**: Audit and remediate the 85 `innerHTML` call sites, replace unsafe patterns with DOM-construction or a small sanctioned `html`-tagged-template helper, and add an ESLint rule so the AGENTS.md "no `innerHTML`" policy is machine-enforced rather than aspirational.
- **Rationale**: Highest-severity class of vulnerability in a prompt manager: prompt bodies, tags, and commit messages are user-controlled and rendered back into the DOM. Most sites use `escapeHtml`, but the guarantee is manual and per-call-site — one missed interpolation (e.g. banner builders in `form-validation.ts:578`, `app/prompt-form.ts:152`, chip rendering in `app/tag-autocomplete.ts:93`) is a stored XSS. CSP (`self`-only scripts) is a good second layer but inline event-handler and HTML-injection vectors remain. Low complexity, very high value, purely additive.
- **To-Do List**:
  - Inventory all 85 sites: `rg -n "innerHTML" src/web/static/ts --glob '!*test*'`; classify each as (a) static markup, (b) escaped interpolation, (c) unescaped interpolation.
  - Fix every category-(c) site immediately (convert to `document.createElement` + `textContent`, or route through `escapeHtml`).
  - Create `src/web/static/ts/utils/safe-html.ts`: a tiny `html` tagged template that auto-escapes all interpolations (opt-out via explicit `raw()` wrapper); unit-test it (escaping, nesting, raw passthrough).
  - Migrate category-(b) sites to the helper so escaping is structural, not per-callsite.
  - Allow category-(a) static markup only via a named constant with an `// static-markup` justification, or convert to `<template>` elements in the Jinja templates and clone them.
  - Add ESLint `no-restricted-properties` rule banning `innerHTML`/`outerHTML`/`insertAdjacentHTML` assignments (error level); grandfather nothing — the migration above should get to zero.
  - Add a Vitest DOM test that renders a prompt titled `<img src=x onerror=alert(1)>` through the prompt card, version list, tag chip, and diff renderer, asserting no element injection.
  - Verify CSP in `middleware/security_headers.py` includes `object-src 'none'` and no `unsafe-inline` for scripts; document the final policy in `docs/AUTHENTICATION_SECURITY.md`.
  - CI: `npm run lint` must fail on any new `innerHTML`.

### 2. Finish What's Declared Done: Legacy Service Removal + `print()` Eradication (Refactoring / Integrity) - ✅ Done 2026-08-02 on branch `refactor/legacy-service-removal-print-eradication`

- **Description**: Delete the still-live `PromptFilterService` and `PromptVersioningService` (superseded by `PromptRepository`/DB versioning), and complete the `print()` → structured-logger migration (34 remaining calls), then enforce both in CI.
- **Rationale**: The roadmap and AGENTS.md declare both migrations complete; the code disagrees. This gap is worse than ordinary tech debt because docs are the contract agents and contributors rely on. The roadmap's own success metric — "`rg "print(" src run_web.py` must return zero matches in CI" — was never wired up. Small, safe, immediately verifiable.
- **To-Do List**:
  - Trace all consumers of `filter_service` / `versioning_service` globals in `src/web/app.py` (lines 15-16, 227, 241-242) and any router using them; port any residual call to `PromptRepository` / `PromptDataServiceDB` equivalents.
  - Delete `src/services/prompt_filter_service.py`, `src/services/prompt_versioning_service.py`, `tests/test_prompt_versioning_service.py`; strip related fixtures from `tests/conftest.py` (`empty_data_service`, `populated_data_service` legacy fixtures too, if now unused).
  - Replace each of the 34 `print()` calls with the appropriate `logging_service` logger call (`src/config/auth_config.py`, `src/web/startup.py`, `src/web/routing_setup.py`, `src/web/middleware_setup.py`, `src/scheduler/session_cleanup.py`, `src/db/health.py`, `src/db/__init__.py`, `src/services/undo_service.py`, `src/services/auth/*.py`). Startup banners become `logger.info` with `ENVIRONMENT=development` console formatting.
  - Add the CI gate from the roadmap: a lint step failing on `rg "print\(" src run_web.py` matches (allowlist: none).
  - Update AGENTS.md (remove the "legacy services" sections and the "Use direct `print()` only as a short-lived fallback" clause) and mark the roadmap metric satisfied.
  - Run full suite; coverage must stay ≥ 85%.

### 3. Rate Limiting & Abuse Controls Beyond Auth (Security) - ✅ Done 2026-08-03 on branch `security/rate-limiting-beyond-auth`

- **Description**: Extend slowapi rate limiting from auth endpoints to all state-changing and expensive endpoints — prompt CRUD, bulk delete, import, export, backup create/restore, version revert — with per-user (not just per-IP) keys and sane, configurable budgets.
- **Rationale**: Auth is well-defended, but an authenticated (or token-stealing) client can hammer `/api/import`, `/api/backups`, or bulk delete without any throttle — a DoS and data-churn vector in a multi-user deployment. The slowapi infrastructure already exists in `src/web/middleware/rate_limit.py` (568 lines), so this is configuration + wiring, not new architecture.
- **To-Do List**:
  - Define a limit taxonomy in `src/config/`: reads (e.g. 300/min), writes (60/min), expensive ops (import/export/backup/restore: 10/min), bulk ops (5/min) — all overridable via env vars.
  - Add a per-user key function (JWT subject, falling back to IP for anonymous) alongside the existing IP-based limiter.
  - Apply decorators/dependencies to `prompts_crud_router.py`, `backup.py`, import/export router, versions revert endpoint.
  - Return `429` with `Retry-After` and the standard `X-RateLimit-*` headers; add i18n-ready client handling (toast + backoff) in `utils/api.ts`.
  - Audit-log threshold breaches (actor, endpoint, count) — no prompt bodies.
  - Tests: per-user isolation (user A throttled ≠ user B), header correctness, env-var overrides, exemption of health/static routes.
  - Document the budgets in `docs/AUTHENTICATION_SECURITY.md` and `.env.example`.

### 4. Prompt Sharing & Team Collaboration (Feature — flagship)

- **Description**: Per-prompt (and per-collection) sharing grants between users with read/edit permission levels, "shared with me" listing, and share badges — the middle ground between "own" and "admin-sees-all" that RBAC currently lacks.
- **Rationale**: Confirmed absent (no share concept in `src/db/models/`). This remains the single biggest gap between the README's "ready for team deployments" claim and the implementation. Builds directly on existing RBAC, `User`, and the repository pattern. Carried from ROADMAP 2026 item #1 (Codeberg issues #23, #17) — still the top feature priority; plan refined below.
- **To-Do List**:
  - Schema: `prompt_shares` (id, prompt_id FK, grantee_user_id FK, permission ENUM('read','edit'), granted_by, created_at; unique(prompt_id, grantee_user_id)). Alembic migration portable across SQLite/Postgres — use `sa.Enum` with native_enum=False, `sa.true()/sa.false()`, no PRAGMA introspection.
  - `SharingRepository` under `src/db/repositories/` following existing pattern (create, revoke, list_for_prompt, list_for_grantee, permission_for).
  - Service layer: extend `PromptDataServiceDB` authorization checks — owner OR admin OR (grantee with sufficient permission); grantees cannot delete, re-share, or change ownership; version history readable with `read`, revert requires `edit`.
  - Extend `PromptRepository.search()` and list queries to union owned + shared-with-me (single query with outer join on `prompt_shares`, deduplicated), preserving pagination and filters.
  - API: `POST /api/prompts/{id}/shares` (body: username/email + permission), `DELETE /api/prompts/{id}/shares/{user_id}`, `GET /api/prompts/{id}/shares` (owner only), `GET /api/prompts?filter=shared-with-me`. Pydantic request/response models in `src/web/models/`; no user enumeration in error responses (mirror the password-reset pattern).
  - Frontend: share modal component (user picker with typeahead reusing `utils/typeahead.ts`, permission select, current-grants list with revoke); "Shared" badge on cards; sidebar filter chip. Vitest coverage for the modal and badge logic.
  - Audit events: `prompt.share.granted` / `revoked` with actor, grantee, permission, prompt_id (Issue #10 fields).
  - Rate-limit share endpoints (item 3 taxonomy); i18n keys in all 4 locales.
  - Tests: repository, service authz matrix (owner/grantee-read/grantee-edit/stranger/admin × view/edit/delete/share), API integration, migration up/down on both dialects.

### 5. Full-Text Search (SQLite FTS5 / PostgreSQL tsvector) (Feature)

- **Description**: Replace `ilike '%term%'` scans with real full-text search — FTS5 virtual table on SQLite, `tsvector` GIN column on Postgres — with relevance ranking and result snippets/highlighting; keep LIKE as fallback.
- **Rationale**: Confirmed: `prompt_repository.py` comments say "FTS deferred to future phase". `LIKE '%x%'` can't use indexes, has no ranking, and degrades linearly with vault size. Native FTS in both backends means zero new dependencies. Carried from ROADMAP 2026 #3 (issue #15).
- **To-Do List**:
  - Alembic migration, dialect-branched via `op.get_bind().dialect.name`: SQLite — `prompts_fts` FTS5 virtual table (title, prompt, note) + triggers (AFTER INSERT/UPDATE/DELETE) keeping it in sync; Postgres — generated `search_vector tsvector` column (weighted: title A, prompt B, note C) + GIN index.
  - `PromptRepository.search()`: detect dialect; use `MATCH`/`bm25()` on SQLite, `@@ plainto_tsquery` + `ts_rank` on Postgres; sanitize user input into a safe FTS query (strip operators, or support quoted phrases explicitly); fall back to current LIKE path on FTS syntax errors and for the `case_sensitive` mode.
  - Snippets: `snippet()` (SQLite) / `ts_headline` (Postgres) returned as a `match_context` field; escape before rendering, highlight via `<mark>` in the safe-html helper (item 1).
  - Keep `search_count()` consistent with the ranked query.
  - API: add `?ranked=true` (default) to `/api/prompts/search`; response gains `match_context`.
  - Frontend: render snippets under card titles; ranked default ordering with existing sort options preserved.
  - Seed-data benchmark (5k prompts) in `tests/`, asserting FTS beats LIKE and results stay correct; full test matrix on both dialects.
  - Migration guide note in CHANGELOG (FTS table build on upgrade may take seconds on large vaults).

### 6. Template & Frontend God-File Decomposition (Refactoring)

- **Description**: Break up the outsized frontend and backend units: `index.html` (1,745 lines) into Jinja2 partials/`{% include %}` blocks; `app/prompt-list.ts` (871), `import-export.ts` (847), `admin-users/index.ts` (786) into focused modules; split `auth_service.py` (1,148) and `dependencies/auth.py` (1,054) along their natural seams.
- **Rationale**: These files are where every future feature (sharing modal, FTS snippets, analytics) must land; their size is the main drag on velocity and review quality. The `app/` directory already shows the target pattern (`prompt-crud.ts`, `versions.ts`, `keyboard-nav.ts` split) — this extends it. Behavior-preserving, test-protected, incremental.
- **To-Do List**:
  - `index.html`: extract modals (version history, prompt editor, placeholder fill-in, delete confirm), sidebar, card grid, and mobile drawer into `templates/partials/*.html` with `{% include %}`; verify byte-identical rendered output via a snapshot test (render route, compare normalized DOM).
  - Repeat for `manage_tags.html` (930), `backup_management.html` (921), `manage_categories.html` (903): share common partials (page header, confirm dialog, pagination controls).
  - `prompt-list.ts`: split into `prompt-card.ts` (rendering), `prompt-filters.ts` (filter state), `prompt-selection.ts` (bulk select) with explicit exported interfaces; keep `prompt-list.ts` as the orchestrator.
  - `auth_service.py`: extract lockout logic, session-cap logic, and login-flow orchestration into separate modules under `src/services/auth/`; public API unchanged (re-export from `auth_service.py`).
  - `dependencies/auth.py`: split token-extraction, role-check dependencies, and CSRF into three modules under `src/web/dependencies/`.
  - Each split lands as its own small PR with `npm run typecheck && npm run test:unit` and `python3 -m pytest` green; coverage thresholds unchanged.
  - Add a soft CI warning (not gate) for source files > 600 lines to prevent regrowth.

### 7. Two-Factor Authentication (TOTP) (Security)

- **Description**: Optional TOTP 2FA with QR enrollment, single-use recovery codes, and an admin policy to require 2FA per role.
- **Rationale**: Confirmed absent (zero TOTP references). The auth stack (Argon2id, ES256, rotation, lockout, session cap) makes this the natural next hardening step and a common team-deployment compliance ask. Well-bounded extension of the existing login flow. Carried from ROADMAP 2026 #5; plan refined.
- **To-Do List**:
  - Add `pyotp` dependency; columns on `users`: `totp_secret` (encrypted at rest with the backup-encryption key-derivation pattern), `totp_enabled` (bool, `sa.false()` default), `recovery_codes` (JSON of Argon2 hashes). Portable Alembic migration.
  - `TotpService` in `src/services/auth/`: enroll (generate secret + provisioning URI), verify (±1 time-step window, replay protection on last-used counter), recovery-code consume (single use), disable (requires password + current code).
  - Endpoints: `POST /api/auth/2fa/enroll`, `POST /api/auth/2fa/verify` (activates), `POST /api/auth/2fa/disable`, `POST /api/auth/2fa/recovery-codes/regenerate` — all authenticated + rate-limited (5/min).
  - Login flow: on valid password with `totp_enabled`, return an intermediate short-lived (2 min) challenge token instead of access/refresh; `POST /api/auth/login/2fa` exchanges challenge + code for the real tokens. Lockout counter shared with password attempts.
  - Admin policy: `require_2fa_roles` setting; enforcement = users in those roles get a mandatory enrollment interstitial after login.
  - Frontend: profile-page enrollment card (QR via client-side `qrcode` lib or server-rendered SVG — keep CSP-clean), challenge step on login page, recovery-code download prompt.
  - Audit events: enable/disable/challenge-success/challenge-failure/recovery-used.
  - Tests: enrollment happy path, wrong/expired/replayed codes, recovery single-use, challenge-token expiry, admin enforcement, migration on both dialects. i18n note: auth UI is English-only today — keep parity.

### 8. AI-Native Prompt Tooling: Token Counter & Test-Run Panel (Feature)

- **Description**: Live token estimation in the editor, per-prompt target-model/provider metadata, and an optional "Test Run" panel that substitutes placeholders and executes the prompt against an LLM using a user-supplied (BYO) API key.
- **Rationale**: PromptVault stores prompts but does nothing AI-aware with them. This is the feature that turns storage into workflow, and it composes with the shipped placeholder system. BYO-key keeps the server stateless about billing and secrets minimal. Carried from ROADMAP 2026 #2; plan refined.
- **To-Do List**:
  - Migration: nullable prompt columns `target_model`, `provider`, `model_params` (JSON: temperature, max_tokens); Pydantic + client validation; editor UI fields.
  - Client-side token estimator module (`utils/token-estimate.ts`): heuristic (chars/words-based per model family) with clearly-labeled "≈" UI; live counter in editor footer; unit tests against known reference counts.
  - Per-user provider key storage: `user_api_keys` table (provider, encrypted key — AES-GCM with server key, never returned after write, last-4 display); profile-page management UI; audit add/remove.
  - `POST /api/prompts/{id}/test-run`: substitutes provided placeholder values server-side, calls the provider (Anthropic first, OpenAI-compatible second) with the user's key, streams or returns the completion. Never log the key or prompt/response bodies (existing rule); redact in error paths.
  - Strict rate limit (item 3: expensive tier) + per-request timeout + response size cap; graceful "no key configured" state linking to profile.
  - Frontend Test panel: reuse the placeholder fill-in form; show substituted prompt, run button, output pane (rendered as text, not HTML), token usage echo from the provider response.
  - Tests: substitution parity with the copy flow, key encryption round-trip, provider client mocked (success/timeout/401), rate-limit behavior; Vitest for panel state machine. i18n for all 4 locales.

### 9. Pagination Completion & List Virtualization (UI/UX + Performance)

- **Description**: Ensure every list surface (main prompt grid, version history, backups, admin users — the latter already paginated) uses bounded server-side pagination end-to-end, and add incremental rendering ("Load more" / infinite scroll) on the main grid.
- **Rationale**: `prompts_shared.py` normalizes page/limit params and admin users paginate, but the main `GET /api/prompts` list and version history flows should be verified bounded by default — an unbounded default is both a performance and memory issue as vaults grow, and it interacts with FTS (item 5) and sharing unions (item 4). Mostly wiring, low risk.
- **To-Do List**:
  - Audit every list endpoint for an enforced default `limit` (e.g. 50) and max cap (e.g. 200) via the existing `prompts_shared.py` normalizer; fix any endpoint returning unbounded results.
  - Standardize the response envelope (`items`, `page`, `page_size`, `total`, `has_next`) across prompts, versions, backups.
  - Frontend: "Load more" button + IntersectionObserver auto-load on the prompt grid; preserve scroll position on detail-return; reset to page 1 on filter/search change; sync page state to URL query params.
  - Version-history modal: lazy-load pages of 20.
  - Tests: boundary pages, cap enforcement, filter-reset behavior; Vitest for the loader state.
  - i18n: "Showing X of Y" strings, 4 locales.

### 10. Dark Mode Completion & Theme Toggle (UI/UX)

- **Description**: Audit all templates/components for missing `dark:` variants, fix WCAG AA contrast in the dark palette, and add a persisted system/light/dark toggle in the profile page.
- **Rationale**: README says dark mode is automatic; AGENTS.md says it's "ready for future implementation" — the docs contradict each other, which means the experience is likely partial. Cheap, visible quality win; good interleave item. Carried from ROADMAP 2026 #7.
- **To-Do List**:
  - Grep-driven audit: every `bg-*`/`text-*`/`border-*` utility without a `dark:` sibling in `templates/` and `ts/components/`; fix systematically per component.
  - Add theme toggle (system/light/dark) to profile: stores preference (user preference API + localStorage for pre-auth pages), applies via `class="dark"` on `<html>` with a no-flash inline bootstrap snippet (CSP-compliant — nonce or move to the bundled entry).
  - Contrast check the dark palette (4.5:1 normal text) with an automated axe/Lighthouse pass in CI or a one-off script; fix failures in `tailwind.config.ts` tokens.
  - Update README/AGENTS to a single consistent statement; refresh screenshots.
  - Vitest for toggle persistence logic; visual spot-check on all 9 pages including auth (English-only) pages.

### 11. Prompt Analytics & Usage Dashboard (Feature)

- **Description**: Owner-scoped dashboard: most-copied prompts, recently edited, tag/category distribution, version churn, vault growth — built on the existing audit log plus a lightweight `copy` event.
- **Rationale**: Surfaces value from telemetry that already exists; strictly additive and read-only. Lowest priority because it's discretionary polish, but cheap after items 4/5 stabilize the query layer. Carried from ROADMAP 2026 #8 (issue #22).
- **To-Do List**:
  - Add a `prompt.copied` audit event (client fires `POST /api/prompts/{id}/events/copy`, debounced; metadata only).
  - Aggregation queries in a read-only `AnalyticsRepository` (top-copied, edits/week, tag distribution, growth series) — owner-scoped, admin gets system-wide.
  - `GET /api/analytics/summary` + `GET /api/analytics/series/{metric}` with date-range params, rate-limited (reads tier).
  - Dashboard page: accessible, theme-aware charts (SVG, no external CDN — CSP), stat tiles, empty states.
  - Guarantee no prompt bodies in any analytics payload; tests for scoping (user A cannot see user B), aggregation correctness, and both dialects.
  - i18n, 4 locales; nav entry under "Data".

---

## Implementation Priority Matrix

| # | Item | Type | User Value | Complexity | Depends on |
| - | ---- | ---- | ---------- | ---------- | ---------- |
| 1 | XSS hardening + lint | Security | High | Low | — |
| 2 | Legacy removal + print() | Refactor | Med (integrity) | Low | — |
| 3 | Rate limiting everywhere | Security | High | Low | — |
| 4 | Sharing & collaboration | Feature | Very High | High | 2, 3 |
| 5 | Full-text search | Feature | High | Medium | 2 |
| 6 | God-file decomposition | Refactor | Med | Medium | 2 |
| 7 | 2FA (TOTP) | Security | High | Medium | 3 |
| 8 | AI-native tooling | Feature | High | Medium | 3 |
| 9 | Pagination completion | UX/Perf | Med | Low | — |
| 10 | Dark mode + toggle | UX | Med | Low | — |
| 11 | Analytics dashboard | Feature | Med | Medium | 5 (soft) |

## Suggested Execution Order

1. **Sprint A (hygiene, 1–2 weeks)**: items 1, 2 — small, independent, restore doc/code integrity and close the cheapest security gaps.
2. **Sprint B (hardening, 2 weeks)**: items 3 → 7, with 10 interleaved as polish.
3. **Sprint C (flagship, 4–6 weeks)**: item 4 (sharing), then 5 (FTS), with 9 folded into whichever list surface each touches.
4. **Sprint D (differentiation)**: items 8, 11, continuing 6 opportunistically (one split-PR per week).
