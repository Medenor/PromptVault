# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Prompt search and listing resume automatically after inactivity when the session can still be renewed. An expired access token no longer appears as an empty result set.
- Production update and rollback commands use the production environment file and verify database access from the web container. Docker Compose disables the Uvicorn file watcher by default.

## [1.17.1] - 2026-11-25

### Fixed

- **Successful rate-limited API requests return their expected status and rate-limit headers** (#134). Prompt creation and deletion, skill imports and archive replacement, and affected backup, sharing, and user search endpoints no longer return HTTP 500 when SlowAPI adds headers.

### Changed

- **Deployment guide, `.env.example` and documentation portal corrected for production**: Docker Compose passes `ENVIRONMENT`, `LOG_LEVEL`, `DISABLE_RATE_LIMITING` and `POSTGRES_PASSWORD` from the same `.env` you use for development, so a development `.env` could leave a production stack in debug mode with rate limiting off. The guide now recommends a separate `.env.production` (`COMPOSE_ENV_FILES` or `--env-file`), documents the `changeme` fallback and how to replace that password on an existing database, tags the running image for rollback instead of rebuilding old code, uses `-T` on the piped `pg_dump`, and shows the real `/api/health` response. The portal gets a new page, "Set up a production environment" (English, French, German, Spanish), and a rewritten "Return to the previous version" section in "Update PromptVault".

## [1.17.0] - 2026-11-24

### Security

- **PyJWT upgraded to 2.15.1** (from 2.13.0). A token with deeply nested JSON in its header or payload made PyJWT raise an uncaught `RecursionError`, so `/api/auth/refresh`, `/api/auth/logout` and the 2FA challenge exchange answered an unauthenticated request with a server error instead of a 401 (GHSA-8wjv-2p76-3863, GHSA-42vr-xj54-vc7v). The other PyJWT advisories fixed in these releases concern HMAC keys, `PyJWK` and `PyJWKClient`, which PromptVault does not use (it only accepts ES256 tokens).
- **Tokens sent in a request body are capped at 4096 characters** on those three endpoints, so oversized input is rejected with a 422 before it reaches the token parser.
- **Password reset hardening, follow-up to 1.16.0** (#120, #121): `PasswordResetService.request_password_reset` no longer returns the plain reset token to its caller, so it cannot leak through a future code path. The password-reset router now logs a masked email instead of the raw address when the account does not exist or the rate limit is hit, and the service no longer logs the address of an unknown account.

### Changed

- **Prompt cards put Copy first** (#129): Copy is the single blue primary action on each card and Edit is the secondary one. History, Copy+Version, Share and Delete moved into a keyboard-navigable "More actions" menu. Copying shows a toast that screen readers announce (polite on success, alert on failure).
- **Neutral header on every page** (#129): blue is now reserved for the primary "New" button and Logout is gray. Pages have a single `h1` with a fixed heading outline, the sidebar search input is 16px, and the list header wraps on narrow screens.
- **PostgreSQL driver moved from psycopg2 to psycopg v3** (#127): the image now installs `psycopg[binary]`, SQLAlchemy's default driver since 2.1. A `DATABASE_URL` that says `postgresql://` or the older `postgresql+psycopg2://` keeps working unchanged; both are loaded with psycopg v3. SQLite is unaffected.
- **CI now runs the PostgreSQL tests** against a real `postgres:15` server (`test-postgres` job, `make test-postgres`): full-text search, the migrations and the `pg_dump`/`psql` backup round trip, which previously only ran on SQLite. This is the check that would have caught #126.

### Fixed

- **PostgreSQL deployments crashed at startup with `No module named 'psycopg'`** (#126): since the SQLAlchemy 2.1 upgrade (#86) a plain `postgresql://` URL loads the psycopg v3 driver, but the image only shipped psycopg2, so the web server and Alembic failed at import. The image now ships psycopg v3 (see Changed), and `pg_dump` and `psql` always receive a plain `postgresql://` URI whichever driver the URL names, so backups keep working. No change to `DATABASE_URL` is needed. SQLite is unaffected.
- **Dark mode on the prompt library** (#129): badges, banners, skill buttons, the sidebar Manage buttons, Load More, footer links (about 2:1 contrast before) and the filled favorite star were low-contrast or nearly invisible in dark mode. They now have dark variants.
- **A failed first load of the prompt list no longer leaves a skeleton pulsing forever** (#129): it shows an announced error message with a "Try again" button. "Load More" and the new messages are translated in all four languages.

## [1.16.0] - 2026-11-24

### Changed

- **Build tooling now requires Node.js 26 or later** (#91). CI selects Node.js 26 through `.nvmrc`, and both Docker builds use digest-pinned `node:26-slim` images.
- **Setup wizard dependencies moved to the `setup` extra** (#114): `click`, `rich` and `httpx` are only used by `scripts/setup/` (and `httpx` by the test client), which runs on the host, so the Docker image no longer installs them. Install them with `pip install -e ".[setup]"` before running `scripts/setup/setup.py`; `make install` does this for you. The weekly security audit now also checks the `test` and `setup` extras.

### Removed

- **Unused dependencies** (#114): `aiofiles`, `greenlet` and `freezegun` (Python), `jiti` and `fake-indexeddb` (npm) were declared but never used. `dotenv` moved from npm `dependencies` to `devDependencies`, since only the Playwright config uses it.

### Fixed

- **Password reset hardening** (GHSA-prvq-q4c8-x9hr): the reset request response is now identical whether or not an account exists, and the reset link is no longer written to the application logs.
- **`setup_env.py --from-file` crashed on unquoted YAML values and dropped the template defaults** (#117): `DB_ECHO: true` or `DB_POOL_SIZE: 20` failed with `argument of type 'bool' is not a container`, and the written `.env` held only the keys present in the file. Values are now converted to strings (nested values are rejected with a clear message) and merged over the profile template, so missing keys keep their default. `DB_POOL_SIZE` is also validated as a positive integer instead of a port number (1-65535).
- **Edit prompt modal stayed open after a new search or filter** (#49): running a search, applying a filter or clearing filters now closes the prompt editor and restores the list, instead of leaving the editor for the previous prompt at the bottom of the page. Unsaved edits are discarded.
- **Export panel "Clear" button restored the wrong defaults** (#82, #111): it checked "favorites only" and set the filename to `promptvault_export.csv`, unlike the initial page. It now restores the page defaults. The client also now replaces a filename extension that does not match the selected format (`test.csv` with JSON gives `test.json`; Markdown gives `.md`), as the server does, and the export card markup (mismatched heading tags, invalid attribute, filename pattern) is fixed.
- **Update procedure in `docs/DEPLOYMENT.md` left the documentation portal on the old release**: the portal is compiled into the `docs` image, but the steps only recreated `web`. They now recreate `web docs`, check `http://localhost:7876/release-notes/` after the update, and the rollback restarts both, as the portal's own update guide already did.

## [1.15.0] - 2026-11-18

### Added

- **Release tooling** (#52): `make release-prepare VERSION=X.Y.Z` bumps the version in every file that carries it and prepares the changelog and the four release-notes pages; `make release-dry-run` and `make release` check, tag and publish the GitHub release from `main`. `make release-prepare-dry-run` shows the diff without writing. See `docs/DEVELOPMENT.md`.
- **API developer guides in the documentation portal** (#109): Added a Developer / API space in English, French, German and Spanish, with localized sidebar navigation and home-page links. It covers an overview, first calls (login with 2FA, read, create, search, history) and a reference for routes, permissions, pagination and errors. The portal now has 20 pages per locale instead of 17.
- **Documentation portal update guide and navigation** (#108): Added a four-language guide for updating and restoring a Docker Compose installation. The portal now has a “Back to PromptVault” navbar link, with its target configurable through `DOCS_APP_URL` when building the docs image.

### Changed

- **Repository moved from Codeberg to GitHub**: the project now lives at https://github.com/Medenor/PromptVault. CI runs on GitHub Actions as two parallel jobs (`lint` and `test`), issues were recreated there (old Codeberg numbers are mapped in PR #1), and the footer source link points to GitHub with a much lighter icon.
- **Template snapshot tests ignore asset hashes and the footer version**, so rebuilding assets or bumping the version no longer invalidates them.

## [1.14.1] - 2026-11-14

### 🐛 Fixed

- **Skill import and edit dialogs ignored dark mode**: the shared modal card, title and close button are light-only, so the dark-styled skill forms appeared on a white card in night mode. The dark styling is now scoped to the skill dialogs (`SKILL_MODAL_CLASS`); other dialogs are unchanged.

## [1.14.0] - 2026-11-14

### ✨ Added

- **Skills: a second content type next to prompts** (spec `011-skill-packages`): import, browse, download and manage multi-file skill packages (a `SKILL.md` with frontmatter plus optional scripts, references, templates and assets).
  - **Import** from a `.zip` through the new **Nouveau ▾ / New ▾ → Import skill** dialog (`POST /api/skills/import`), with an optional category (chosen from your existing categories) and tags (existing tags are offered as clickable chips). The archive is read in memory only, never extracted to disk or executed, with path, link, duplicate-entry, size and compression-ratio checks. Frontmatter is checked leniently against the Agent Skills format: problems are shown as warnings, not rejections.
  - **Browse**: skills appear in the prompt list with a "Skill" badge and an item-type filter (All / Prompts / Skills). The detail view shows the rendered `SKILL.md` instructions (sanitised Markdown), a file tree and a text/binary file viewer.
  - **Manage**: edit details, replace the files with a new archive, delete, and download the whole skill as a standard-layout `.zip` (`/api/skills/*`). Skills are full-text searchable through the existing search, and are included in database backup and restore.
  - **Not available for skills in this version**: version history, sharing, placeholders, bulk import/export and in-place text edits return `409 ITEM_IS_SKILL` (hidden in the UI). Replacing files overwrites the previous ones. Selective restore and restore diff skip skill rows.
  - **Limits** are configurable with `SKILL_MAX_UPLOAD_BYTES`, `SKILL_MAX_TOTAL_BYTES`, `SKILL_MAX_FILES`, `SKILL_MAX_DEPTH`, `SKILL_MAX_FILE_BYTES`, `SKILL_MAX_COMPRESSION_RATIO`, `SKILL_TEXT_PREVIEW_BYTES` and `SKILL_MAX_SKILL_MD_BYTES` (see `.env.example`). Oversized uploads are refused with `413`, including chunked uploads.
  - Backend: `SkillService` and the archive reader/writer in `src/services/skills/`, `SkillRepository`, `skills_router.py`. Migration `d4e5f6a7b8c9` adds `prompts.item_type` plus the `skill_packages` and `skill_files` tables, and works on SQLite and PostgreSQL without dropping the full-text sync triggers. New dependencies: `PyYAML`, `markdown-it-py`, `nh3`. User guide page added in all four languages.
- **Header menus**: "New prompt" and "Import skill" now share one **New ▾** menu, and between 768 and 1279 px wide Import/Export, Backup and Documentation move into a **More ▾** menu, so the navigation fits on one line. Both menus are keyboard accessible.

### ⚙️ Changed

- The service worker cache moved to `v7`; a reload may be needed once to pick up new translations.

### 🐛 Fixed

- **Documentation locale links could leak Docker's internal port**: Docusaurus emits canonical page URLs without a trailing slash. Nginx then redirected directory requests to its internal listening port (`8080`), sending visitors away from the published portal port (`7876`) and causing a 404/connection failure after switching languages. Directory redirects are now relative, so the browser retains the externally requested origin and port. The documentation container healthcheck now targets IPv4 loopback explicitly, avoiding an IPv6 `localhost` resolution failure when nginx listens only on IPv4.

**Upgrade note**: run the Alembic migration (`alembic upgrade head`) and reinstall dependencies (`PyYAML`, `markdown-it-py`, `nh3`). Existing prompts are unaffected and keep `item_type = 'prompt'`.

## [1.13.1] - 2026-11-13

### 🐛 Fixed

- **Docker rebuild crashed with `No module named 'psycopg'`** (Codeberg #94): `sqlalchemy` was unbounded (`>=2.0.25`), so a cache-less image rebuild installed SQLAlchemy 2.1, where a plain `postgresql://` URL selects the `psycopg` (v3) driver instead of `psycopg2`. Only `psycopg2-binary` is installed, so the web container failed at import. SQLAlchemy is now pinned to `>=2.0.25,<2.1`. Moving to psycopg v3 is left for a dedicated change.
- **In-app Documentation link unreachable in Docker deployments** (Codeberg #94): the link targeted `http://localhost:7876`, the Docusaurus dev server, which the Docker stack did not run. `docker-compose.yml` now includes a `docs` service (static portal served by non-root nginx on port 7876, built from `docs-portal/Dockerfile`), and `VITE_DOCS_PORTAL_URL` is passed to the `web` image as a build arg (default `http://localhost:7876`). **Upgrade note**: rebuild both images with `docker-compose build web docs && docker-compose up -d docs web`. To serve the portal from another URL, set `VITE_DOCS_PORTAL_URL` in `.env` and rebuild `web`.

## [1.13.0] - 2026-11-12

### ✨ Added

- **Optional TOTP two-factor authentication**: Users enroll an authenticator app from their profile page (QR code rendered server-side as inline SVG, with a manual-entry secret fallback), confirm with a 6-digit code, and receive 10 single-use recovery codes, shown once. Once enrolled, `POST /api/auth/login` returns a short-lived (2 min) signed challenge token instead of session tokens; it is exchanged at `POST /api/auth/login/2fa` for a TOTP or recovery code. Wrong, expired, or replayed codes are rejected (replay is blocked by a per-credential `last_used_step` counter), and failed attempts share the password-lockout counter.
  - `POST /api/auth/2fa/disable` and `POST /api/auth/2fa/recovery-codes/regenerate` require password and current code. Regenerating invalidates the previous recovery-code batch.
  - Admins can require 2FA per role (`GET`/`PUT /api/admin/2fa/policy`). Non-enrolled users in a required role are routed to a mandatory enrollment step after login and blocked from the rest of the app until they finish.
  - TOTP secrets are encrypted at rest with AES-256-GCM under a dedicated `TOTP_ENCRYPTION_KEY` (HKDF-derived). This is separate from the passphrase-gated backup scheme because the server must decrypt on every login. Recovery codes are Argon2id-hashed. No secret, code, or recovery code is logged.
  - Backend: `TotpService`, `TotpEncryptionService`, and `TotpPolicyService` in `src/services/auth/`, `TotpRepository`, and `auth_totp_router.py` / `admin_totp_policy_router.py`. A dialect-portable migration adds 4 tables/columns. The frontend (enrollment, login challenge, mandatory-enrollment step, admin policy screen) is translated into EN/FR/ES/DE. Coverage: 88%+ backend, 97%+ frontend.
- **Documentation portal with i18n (EN/FR/DE/ES)** (Codeberg #91): Docusaurus 3.x site in `docs-portal/` covering installation, configuration, user guide, troubleshooting, and release notes. Adds `npm run docs:check-parity` (compares page existence, frontmatter, and heading counts across locales), an untranslated-page banner for pages that fall back to English, a `docs-portal.yml` CI workflow scoped to `docs-portal/**`, a `make docs` target (`localhost:7876`), and an in-app link to the portal (configurable with `VITE_DOCS_PORTAL_URL`).
- **Full-text search with relevance ranking and highlighted snippets**: `GET /api/prompts/search` uses a real full-text index instead of a substring scan. SQLite uses an FTS5 external-content table (`prompts_fts`, kept in sync by triggers); PostgreSQL uses a generated, weighted `tsvector` column with a GIN index. Ranking is title > body > note (`bm25()` on SQLite, `ts_rank` on PostgreSQL, same 10/4/1 weights). Bare multi-word queries are OR-joined, with all-word matches ranked first. Operator characters are stripped anywhere in a token, so `foo&bar` cannot reach `MATCH`/`to_tsquery` as an operator. Hits carry an optional `match_context` snippet; the client renders matches as `<mark>` after HTML-escaping. `case_sensitive=true` and quoted phrases keep exact-match behavior. Unparseable queries and FTS engine errors fall back to substring search. Explicit `sort` options still override relevance. At 5,000 seeded prompts, queries return in well under 1s, with latency roughly flat as the corpus grows. **Upgrade note**: the migration backfills the search index from existing prompts. This may take a few seconds on large vaults; no manual action is needed.
- **App version in the site footer**: The footer shows `v{{ app_version }}`, read from `pyproject.toml` at request time (`src/web/utils/version.py`, with an `importlib.metadata` fallback) and exposed as a Jinja global on both template environments.

### 🔨 Refactored

- **Shared footer macro**: The footer, including a ~200-line inline Codeberg logo SVG, was duplicated across 8 auth and admin templates. All 8 now call `{{ page_footer.site_footer() }}`, removing ~1,650 lines.
- **Prompt list, search, and CRUD use the repository path only** (Codeberg #72): The list and search routers consulted the legacy `data_service` before the repository, which silently shadowed the FTS work. `get_prompt` and `toggle_favorite` had the same pattern. All of them now use `PromptRepository` exclusively. `set_legacy_public` still writes through `data_service` and is unchanged. `TestLegacyDataFallbacks` was removed, and `test_toggle_favorite_failure_returns_500` became a documented no-op, matching `test_update_prompt_failure_returns_500`.

### ⚙️ CI/Build

- **`ruff` gates `make lint-backend`** (Codeberg #79): Repo-wide `black` formatting was applied to 29 drifted files, and `ruff check` now runs alongside `black --check`. The rule set is pyflakes, pycodestyle, pyupgrade, isort, and bugbear, with five documented exclusions in `pyproject.toml`. All 2,360 initial findings were fixed, mostly mechanically. 59 bare `raise` statements inside `except` blocks now chain with `from e` / `from exc`, so the original exception stays visible.
- **`mypy` gates `make lint-backend` at zero errors** (Codeberg #82): Most of the 369 initial errors came from legacy SQLAlchemy `Column()` declarations. All 16 models moved to typed `Mapped[T]` / `mapped_column()`, which cut the count to 154. The remaining real issues were fixed (e.g. `dict[str, any]`, Pydantic v2 `example=`, implicit-Optional signatures, an `UndoService.pop()` signature mismatch). Where a type gap reflected a real runtime invariant, an `assert` or guard documents it instead of suppressing the check. `BaseRepository` now binds to a structural `_HasId` Protocol. Two narrowly scoped `# type: ignore[code]` remain, each with an inline reason. `mypy src` reports zero errors across 132 files.

### 🐛 Fixed

- **Non-hashed `/static/` assets could go stale in browsers indefinitely**: `StaticFiles` mounts sent no `Cache-Control`, so browsers cached locale files and images based only on `Last-Modified`/`ETag`. The new `RevalidatingStaticFiles` wrapper sends `Cache-Control: no-cache` on the un-hashed `/static` mount. `/static/dist` (content-hashed) is unchanged.
- **Service worker never refreshed cached locale files**: `CACHE_VERSION` in `src/web/static/ts/sw.ts` had stayed at `'v1'`. Returning visitors with an installed Service Worker kept serving cache-first copies of `/static/locales/*.json` and showed raw keys for newer strings. Bumped to `'v3'`, which evicts the older caches on activate. Users still stuck on stale content can hard-refresh.
- **`pytest` coverage HTML report crashed with `INTERNALERROR`** (Codeberg #86): `.coveragerc` measured `src/web/templates/*.html` and `src/web/static/*` as Python source, and the HTML report `ast.parse()`d them. coverage.py ignores `include` whenever `source` is set (as `pytest.ini`'s `--cov=src` does), so `.coveragerc` now uses `omit = */templates/*` and `*/static/*`.
- **Fresh SQLite install failed on the auth-fields migration**: `da013146c222_add_authentication_fields_to_users` ran PostgreSQL-only SQL (`DROP CONSTRAINT ... CASCADE`, `ADD COLUMN IF NOT EXISTS`) with no dialect branching, so `alembic upgrade head` failed on a new SQLite database. It now uses `op.batch_alter_table` on SQLite and keeps the raw SQL path for PostgreSQL.
- **Postgres test fixtures could not create the schema** (Codeberg #78): `PromptVersion.version_id` was `unique=True` at column level, so `create_all()` emitted the self-referential foreign key and the unique constraint in one `CREATE TABLE`, which PostgreSQL rejects. The Postgres leg of every cross-dialect FTS test was therefore always skipped. An explicit `UniqueConstraint("version_id")` fixes it; all 30 FTS tests pass against PostgreSQL 15.
- **Latent bugs found while triaging ruff/mypy output**: `UserNotFoundError` was raised in two `AuthService` paths without being imported, a `NameError` waiting to happen. `app.py`'s `data_service`, `import_export_service`, and `backup_service` globals were assigned via `global` without a module-level declaration.
- **Dead code removed**: `PromptDataService.get_tags_with_counts()` was defined twice, so the second definition shadowed the defensive `count or 0` fallback. `revoke_session()` had a duplicate `except SessionNotFoundError`, which made the logged branch unreachable (ruff B025). Both are merged into single handlers that keep the logged behavior.

## [1.12.0] - 2026-08-11

### ✨ Added

- **Prompt sharing & team collaboration**: Owners can now grant teammates `read` or `edit` access to individual prompts via a new Share modal (recipient typeahead over `GET /api/users/search`, matches active users by username/email prefix but never returns emails) and revoke access at any time; grantees get exactly the granted capability — `read` unlocks viewing and version history, `edit` additionally allows editing content/category/tags and reverting, but never delete, re-share, favorite-toggle, or ownership transfer, enforced server-side via a new `check_prompt_access()` authorization helper (`prompt_shares` table: `PromptShare` model with a unique `(prompt_id, grantee_id)` constraint, cascade-deletes with the prompt or grantee, `SET NULL` on grantor deletion). Grant/revoke failures never disclose whether a username exists, is inactive, or was a self-share attempt — all return the same generic `sharing.grant_failed` message — and both actions plus the endpoints power a "Shared with me" filter and a "Shared" badge distinguishing explicit grants from the pre-existing default-visible prompts. New endpoints: `POST/GET /api/prompts/{id}/shares`, `DELETE /api/prompts/{id}/shares/{user_id}`, `GET /api/users/search`; existing `GET/PUT /api/prompts/{id}` and the version-history/revert endpoints now resolve access through the same `read`/`edit`/`owner` matrix instead of owner-only or authenticated-only checks. All sharing mutations are audit-logged (`prompt.share.granted`/`prompt.share.revoked`) and rate-limited using the existing read/write budget tiers; i18n across all four locales (en/fr/es/de); disabled entirely (404) when `AUTH_ENABLED=false`. **Export/import is grant-blind by design**: CSV/Markdown/JSON export payloads never include `prompt_shares` grants or the `legacy_public` flag (they're runtime access-control state tied to this instance's user accounts, not portable prompt content), and re-importing an exported file recreates plain private prompts with no grants restored — full database backup/restore is the only path that preserves sharing state, and the Export Prompts UI now surfaces this directly.
  - **Visibility behavior change**: prompts created from now on default to **private** — visible only to their owner, admins, and users granted explicit access. Prompts that already existed before this release are grandfathered as **"Public (legacy)"** (`prompts.legacy_public=true`, set automatically by the migration) and remain visible to every authenticated user, badged distinctly from an explicit share, until their owner or an admin makes the prompt private via the new "Make private" (un-grandfather) action — a one-way transition with no re-publish path, so treat it as a deliberate policy checkpoint before shipping, not a display toggle.

### 🔨 Refactored

- **God-file decomposition, template & frontend/backend tiers**: Split the remaining oversized files — four Jinja2 templates, three TypeScript modules, two backend auth files — into focused modules, one behavior-preserving commit per phase. Templates (`index.html` 1745→361 lines, plus `manage_categories`/`manage_tags`/`backup_management`) extracted into shared `templates/macros/` partials, backed by a new snapshot-test harness (`tests/test_template_snapshots.py`) guaranteeing byte-identical rendered HTML. `prompt-list.ts`, `import-export.ts`, and `admin-users/index.ts` split into per-concern modules (`prompt-card.ts`/`prompt-filters.ts`, `validation.ts`/`preview.ts`/`operations.ts`, `user-actions.ts`/`create-user-form.ts`), each with new unit test coverage closing prior test gaps. `auth_service.py`'s lockout/session-cap logic promoted to dedicated `LockoutService`/`SessionService`; `dependencies/auth.py` (widest fan-in in the codebase) split into `token.py`/`roles.py`/`request_context.py`/`bypass.py` behind a compatibility re-export shim so none of its 12+ consumers needed an import-path change. No route paths, HTTP methods, public APIs, or rendered HTML changed. Full suite green throughout: 2149 backend tests (87% coverage), 400 frontend tests, `npm run typecheck`/`lint` clean.

### 🔒 Security

- **Extended rate limiting beyond auth to all state-changing and expensive endpoints**: Previously only three auth endpoints (login/register/password-reset) were throttled, so an authenticated (or token-stealing) client could hammer `/api/import`, `/api/export`, backup create/restore, bulk delete, or version revert without any limit — a DoS and data-churn vector in multi-user deployments. Added a four-bucket taxonomy in `src/config/auth_config.py` — **read** (300/min), **write** (60/min, prompt create/update/delete + version revert), **expensive** (10/min, import/export + backup create/restore/restore-preview/verify), **bulk** (5/min, bulk delete + delete-all backups + compress + retention cleanup) — each overridable per-window via env vars (`RATE_LIMIT_{READ,WRITE,EXPENSIVE,BULK}_{ATTEMPTS,WINDOW_SECONDS}`). Limits are now genuinely **per-user**: `get_rate_limit_key()` in `src/web/middleware/rate_limit.py` resolves the JWT `sub` claim statelessly from the `Authorization` header or `access_token` cookie (falling back to client IP for anonymous requests), so one user hitting a limit never throttles another — the prior implementation read `request.state.user`, which nothing populated, silently degrading every limit to per-IP. Applied `@limiter.limit(...)` decorators to 14 endpoints across `prompts_crud_router.py`, `import_export_router.py`, `prompts_versions_router.py`, and `backup.py` (each gained the `request: Request` param slowapi requires); health/static/page routes stay exempt by construction since limits are per-decorator, not global middleware. Every threshold breach now emits a `rate_limit.exceeded` audit event (actor key, endpoint, method, retry-after — no prompt/note bodies) via `logging_service`. On the client, `utils/api.ts` surfaces a warning toast on `429` (respecting `Retry-After`, i18n keys `messages.rateLimit`/`rateLimitGeneric` added to all four locales), auto-retries idempotent GETs once within a bounded 30s backoff, and never auto-retries writes (avoiding duplicate mutations); also fixed a latent bug where `handleApiError` referenced a non-existent `errors.rateLimit` key and returned the raw key string to users. **Also fixed a pre-existing hard `SyntaxError`**: `rate_limit.py` and `auth_config.py` contained Python-2 `except X, Y:` syntax (four sites) that made both modules fail to import under Python 3 — latent because rate limiting was disabled in dev/test. Verified end-to-end: with a tiny write budget, user A is throttled at the limit while user B (different JWT `sub`) is not; `429` carries `Retry-After` + `X-RateLimit-*`; health endpoints never throttle; the breach is audit-logged. Budgets documented in a new `docs/RATE_LIMITING.md` (the auth-specific limits stay in `docs/AUTHENTICATION_SECURITY.md`, which now cross-links it) and `.env.example`; the superseded `src/web/middleware/INTEGRATION.md` was folded into the new doc and removed
- **Eliminated stored-XSS risk from unsafe `innerHTML` usage**: Audited all 82 `innerHTML` call sites in `src/web/static/ts/` (prompt titles, tag names, and session/audit-log fields are user-controlled and get rendered back into the DOM) and found 8 real vulnerabilities, including two attribute-injection bugs in `profile.ts` and `admin-sessions.ts` where session/user IDs were interpolated raw into `onclick="window.revokeSession('${sessionId}')"`-style strings — a quote-breakout that gave arbitrary JS execution, not just HTML injection. Both rewritten to `data-*` attributes with `addEventListener`; the other 6 sites (unescaped prompt titles, tag names, audit-log `performed_by`/`operation` fields) fixed via `escapeHtml()` or DOM construction. Added `src/web/static/ts/utils/safe-html.ts`, an `html` tagged template that auto-escapes all interpolations by default (with a `raw()` opt-out for pre-built trusted fragments), and migrated 19+ sites to it so escaping is structural rather than a manual per-callsite `escapeHtml()` call that's easy to forget. Added an ESLint `no-restricted-properties` rule (error level) banning `innerHTML`/`outerHTML`/`insertAdjacentHTML` writes across the TS source, with justified inline disable comments on the 49 genuinely static-markup sites (no interpolation) so the ban is enforced with zero silent exceptions. Added CSP `object-src 'none'` (was missing) to `src/web/middleware/security_headers.py`; `script-src`'s remaining `'unsafe-inline'` is documented as a known gap in `docs/AUTHENTICATION_SECURITY.md` rather than fixed, since closing it requires auditing every remaining inline event handler project-wide. Verified live in a running instance: a prompt created with `<img src=x onerror=alert(...)>` in its title/tag and `<script>alert(...)</script>` in its body renders as inert escaped text with no DOM injection

### ⚙️ CI/Build

- **Added `make check-sw-cache-version`, wired into `make lint`/CI**: Manually remembering to bump `sw.ts`'s `CACHE_VERSION` on every `/static/` change proved unreliable in practice (see the `v1`→`v2`→`v3` Fixed entries above) — the failure mode is silent (no test/build error) and only surfaces as a stale-content bug report. The new Makefile target diffs the current branch against its merge-base with `main` and fails if any file under `src/web/static/` changed without a corresponding `CACHE_VERSION` line change in `src/web/static/ts/sw.ts`. CI now checks out full history (`fetch-depth: 0`) and passes the PR base ref so the check has a merge-base to diff against. Codeberg #74
- **Restricted CI trigger scope and reduced Forgejo Actions footprint** (Codeberg [PR #67](https://codeberg.org/Medenor/promptvault/pulls/67)): `ci.yml` and `accessibility.yml` previously ran `on: push` / `on: pull_request` with no branch filter, so every feature-branch push triggered a full run in addition to the run on the eventual PR. Both now scope to `branches: [main]`. The `accessibility.yml` workflow (Playwright/axe + Lighthouse, ~30 min timeout per job) has been removed from CI entirely — run manually via `tests/accessibility/RUN_TESTS.md` instead. The `security-audit` job (`pip-audit`, `npm audit`) was split out of `ci.yml` into its own `security-audit.yml`, now triggered weekly (Mondays 06:00 UTC) plus manual `workflow_dispatch` rather than on every push/PR, since dependency vulnerabilities don't change per-commit. `test-and-lint` (lint, unit tests, frontend build) is unchanged and still runs on every push/PR to `main`. Forgejo Actions is not currently enabled on this repository, so this is preventive housekeeping rather than a fix for actual resource consumption
- **Upgraded spec-kit tooling to v0.14.2**: `.specify/` templates and scripts, and the `claude`/`opencode`/`kilocode` agent integrations, were on a mix of v0.12.3 (claude, opencode — installed but never registered in `integration.json`'s tracked list) and v0.14.2 (kilocode, upgraded separately). Registered claude and opencode via `specify integration install` (opencode required `--force`, as it isn't declared multi-install-safe alongside the other two — a CLI heuristic, not an actual conflict), then refreshed the 5 shared templates (`spec-template.md`, `plan-template.md`, `tasks-template.md`, `checklist-template.md`, `constitution-template.md`) via `specify integration upgrade kilocode --force`. Changes are purely cosmetic (upstream's `__SPECKIT_COMMAND_*__` placeholder tokens replacing hardcoded command names, minor markdown reformatting) — no semantic or structural change to the constitution gates or template fields

### 🔧 Changed

- **Removed the still-live `PromptFilterService`/`PromptVersioningService` legacy globals and enforced zero `print()` in CI**: Both services were declared "retired" by AGENTS.md and the roadmap, but `src/web/app.py` still imported and instantiated them at startup; a grep confirmed no router actually consumed either global (`prompts_versions_router.py` already called `PromptDataServiceDB.get_prompt_versions()`/`.revert_prompt_to_version()` directly), so they were dead code. Deleted `prompt_filter_service.py`, `prompt_versioning_service.py`, `tests/test_prompt_versioning_service.py`, and the corresponding fixtures/save-restore tuples in `tests/conftest.py`. Separately, replaced the 14 remaining executable `print()` calls (`startup.py`, `middleware_setup.py`, `routing_setup.py`, `db/health.py`, `db/__init__.py`) with `logging_service` logger calls — most were redundant duplicates of an adjacent `logger.*` call and were simply removed — and rewrote `>>> print(...)` doctest examples across 8 files (`auth_service.py`, `jwt_service.py`, `password_service.py`, `password_reset_service.py`, `auth_config.py`, `undo_service.py`, `session_cleanup.py`, `user_agent_parser.py`) as plain doctest expressions. Added a `make lint-backend` gate failing on any `rg "print\(" src run_web.py` match, wired into the existing CI `Lint` step — the roadmap's own success metric for this, never previously enforced
- **Replaced the full-screen "Verifying session…" overlay with a server-side auth gate + inline skeleton**: Previously every page load hid the entire app shell (header, sidebar, layout) behind an opaque dark overlay until a client-side `GET /api/auth/me` round-trip resolved. `GET /` (`src/web/app.py`) now validates the `access_token` cookie's JWT signature/expiration statelessly before rendering (new `has_valid_auth_cookie()` in `src/web/dependencies/auth.py`, reused by `src/web/routers/pages.py`'s existing check), redirecting to `/auth/login` before any HTML is sent for missing/invalid/expired cookies — eliminating the flash for the common case. For valid sessions, the app shell now renders instantly; only the prompt grid (`src/web/templates/index.html`) shows a themed shimmer skeleton until the client-side `/api/auth/me` check confirms the session hasn't been revoked, preserving the existing privacy guarantee that an admin-revoked-but-unexpired session never displays prompt data. `checkAdminAccess()` (`src/web/static/ts/app/index.ts`) no longer toggles overlay/shell visibility — it just removes the skeleton on success or network failure

### 🐛 Fixed

- **"Per page" pagination label never translated, always showing English**: The `<label>` for the page-size selector on the prompts list (`#page-size-control` in `src/web/templates/index.html`) had no `data-i18n` attribute at all — a hardcoded `Per page:` string, so it ignored the active language and displayed in English regardless of locale (e.g. still "Per page:" under French). Added the `nav.perPage` key to all four locale files (en/fr/es/de) and wired the label with `data-i18n="nav.perPage"`
- **Shared modal component had no height cap or internal scroll, trapping the placeholder-fill Copy button off-screen on mobile**: `createModal()` (`src/web/static/ts/components/modal.ts`) rendered its panel with `overflow: visible` and no `max-height`, inside a `flex items-center justify-center` overlay, while `document.body.style.overflow` was set to `'hidden'` for the duration — so any modal whose content exceeded the viewport height (e.g. the placeholder-fill modal on a prompt with enough `[PLACEHOLDER]` tokens; see the regex-narrowing fix above, which reduced but didn't eliminate this) overflowed both the top and bottom of the screen with no scrollbar and no way to scroll the page underneath, making the header/close button and the action-row buttons (including "Copier") completely unreachable on mobile viewports — a soft lock. The modal panel is now a `max-h-[90vh]` flex column with the header and action footer pinned (`shrink-0`) and only the body scrolling internally (`overflow-y-auto min-h-0`), so long content scrolls in place while the title, close button, and action buttons stay reachable. Fix lives in the shared component, so it applies to every modal built on it (placeholder-fill, share, confirm/alert), not just the one that surfaced it. Reproduced and verified in Chrome DevTools mobile emulation (390×844) against a throwaway 12-placeholder test prompt
- **Service worker never invalidated cached locale files, leaving returning users stuck on stale translations**: `src/web/static/ts/sw.ts` names its caches `promptvault-static-${CACHE_VERSION}`/`promptvault-api-${CACHE_VERSION}` and its `activate` handler deletes any cache **not** in the current version's set — but `CACHE_VERSION` had stayed `'v1'` since the offline-cache feature (004-mobile-responsive-ui) shipped, so a browser that already had a Service Worker installed (any repeat visitor, most visibly on Firefox where SW/cache state persists more readily across restarts than in this project's other manually-tested browsers) kept serving its original `cache-first`-fetched `/static/locales/{en,fr,es,de}.json` forever, regardless of how many translation keys were added afterward — new keys like the `sharing.*` namespace from this release rendered as raw dotted keys (e.g. `sharing.legacy_public_badge` instead of "Public (legacy)"/"Public (ancien)") for anyone who'd visited before those keys existed. New installs and private/incognito sessions were unaffected (no persisted SW), which is why the bug looked browser-specific rather than cache-specific. Bumped `CACHE_VERSION` to `'v2'` so the next Service Worker update evicts the stale `v1` caches on `activate` and re-fetches current locale files — no user action required, but anyone still stuck should hard-refresh (bypasses the SW for that load) if the update doesn't reach them automatically. **Process note**: this cache key needs bumping on every release that changes anything under `/static/` (locale files, JS/CSS bundles) that a `cache-first`-strategy request could otherwise keep serving stale
- **Service worker `CACHE_VERSION` still hadn't been bumped for the `sharing.*` locale keys added after `v2`**: The process note above proved prescient the same day — `CACHE_VERSION` was last bumped `v1`→`v2` for the fix above, but the `sharing.*` locale keys landed on that same `v2` cache with no further bump, so browsers with an already-installed Service Worker kept serving pre-sharing locale files and showed raw keys like `importExport.sharingNotIncluded`. Bumped to `v3`. See Codeberg #74
- **Prompt revert silently dropped tags**: `VersionRepository.revert_to_version()` cleared `prompt.tags` when reverting to a prior version but never repopulated them from that version's denormalized tag snapshot (a `# Note: tag restoration would require tag lookup by name` admitted the gap directly in the code) — a revert to any version always left the prompt tag-less regardless of what tags existed at that point in history. Now restores tags via `TagRepository.get_or_create_many(target_version.tags)`. Not reachable from the API (the router's revert path uses `PromptDataServiceDB.revert_prompt_to_version()` → `update_prompt()` instead), but the method is public, tested, and documented as the git-like revert primitive, so the bug was real for any direct caller
- **"Remember Me" broke after server-side auth gate exposed a redirect loop**: The access_token cookie's `max_age` matches the refresh token's lifetime (7 or 30 days, or 30 with "Remember Me"), but the JWT inside still expires after 15 minutes — so the new server-side gate above correctly rejects it well before the cookie itself expires. The login page's bfcache guard (`redirectIfAuthenticated()` in `src/web/static/ts/auth.ts`) previously trusted a stored `access_token` in `localStorage` as proof of a valid session and bounced straight back to `/`, which the server rejected again, looping indefinitely. It now attempts a token refresh (`refreshTokens()`, newly exported from `src/web/static/ts/utils/api.ts`) before redirecting, and clears stale tokens instead of redirecting when refresh fails — restoring transparent "Remember Me" renewal across the 15-minute access-token boundary
- **`/api/auth/refresh` 500 error above the session limit**: `AuthService._enforce_refresh_session_limit()` (`src/services/auth/auth_service.py`) referenced an undefined `logger` when auto-revoking a user's oldest session past the 5-concurrent-session default, raising an unhandled `NameError` on every refresh attempt once a user was at/over the limit — silently breaking "Remember Me" renewal for users with several active sessions. Added the missing module-level `logger = logging.getLogger(__name__)`, consistent with the rest of the codebase
- **Placeholder false positives on prompts with bracket/brace content**: The placeholder detection regex (`detectPlaceholders()` in `src/web/static/ts/utils/placeholders.ts`) accepted any non-empty text between delimiters, so prompts containing YAML frontmatter, date formats (`[YYYY-MM-DD]`), lowercase references (`[bulletpoint]`, `[title]`), or short tokens (`[P]`, `[N]`) produced a flood of spurious placeholder fields in the copy modal — sometimes so many that the modal overflowed and the Copy button became unreachable. Detection now requires placeholder names to be 2+ characters of uppercase ASCII letters, digits, underscores, and spaces (`[A-Z0-9_ ]{2,}`), eliminating false positives while preserving the intended use case (`[DURATION]`, `[TYPE OF PRESENTATION]`, etc.)
- **Finished the god-file split PR #62 left incomplete (Tier 1.5 cleanup)**: Three files PR #62 reported as "split" still carried 1,000+ lines because handlers/logic were never actually moved out. `src/web/app.py` (1,060 lines) dropped to 434 — its 17 directly-defined route handlers moved into routers: new `prompts_versions_router.py` and `import_export_router.py`, plus existing `categories_router.py`/`tags_router.py` (GETs) and `pages.py` (`/import-export`, `/backup-management`); `import_prompts`'s validation/parsing/ingestion logic extracted into helpers. `src/web/routers/admin.py` (1,105 lines) split into `admin_users_router.py`, `admin_sessions_router.py`, and a shared `admin_shared.py`, bringing the backend back in step with the frontend's existing `admin-users.ts`/`admin-sessions.ts` split. `src/services/auth/auth_service.py`'s `login` and `refresh_tokens` methods (143 and 185 lines) got Extract Method treatment into named private helpers (lockout check, credential verify, session issuance, token rotation, reuse detection); `password_service.py`'s `check_password_strength` was table-driven as a bonus. `src/web/dependencies/auth.py` was deliberately left untouched (a prior analysis found it cohesive). No route paths, HTTP methods, schemas, or public interfaces changed. See [PR #65](https://codeberg.org/Medenor/promptvault/pulls/65)
- **Retired legacy `static/js/` and dead JSON-era services (Tier 1 cleanup)**: Deleted the 12-file legacy JavaScript tree (`src/web/static/js/`, ~7,674 lines) that was superseded by the TypeScript port, plus the two Jinja fallback branches in `scripts.html` that loaded it. Also deleted five JSON-era service modules with zero live importers — `prompt_data_service.py`, `backup_service.py`, `version_compression_service.py`, `version_export_service.py`, `version_tagging_service.py` (~2,267 lines) — all superseded by their DB-backed equivalents. `form_validation.js` turned out to still be live in production (loaded via a `form-validation.ts` bridge despite its "historical reference only" header); its DOM-wiring logic was ported to `form-validation.ts` rather than deleted, reusing the validators/constants already ported to TypeScript. `test_audit_logging.py` was migrated onto the live DB-backed services rather than deleted, preserving audit-log-emission coverage. Updated `.coveragerc`, `pytest.ini`, `tests/conftest.py`, `README.md`, `AGENTS.md`, `docs/TESTING.md`, and `eslint.config.js` to drop stale references. ~9,900 lines removed net. See [PR #63](https://codeberg.org/Medenor/promptvault/pulls/63)
- **God-file decomposition (backend)**: `src/web/app.py` split into a factory plus dedicated middleware/routing/startup modules; the auth, tag_category, and prompts routers split into focused modules; `backup_service_db.py` split into focused service modules
- **God-file decomposition (frontend)**: `manage-tags.ts`, `manage-categories.ts`, `admin-users.ts`, `backup-management.ts`, and `app.ts` split into per-concern modules under `tags/`, `categories/`, `admin-users/`, `backup/`, and `app/` respectively; extracted a shared `utils/debounce.ts` utility with errors routed through `handleApiError`
- **Consolidated write paths**: Prompt/tag/category write paths consolidated into repositories; duplicated auth dependency pipelines unified into a single pipeline
- **Duplicate scheduler router registration**: `src/web/app.py` registered `scheduler_router` twice under the same `/api` prefix — once via the module-level import (`from src.web.routers.scheduler import router as scheduler_router`) and again via a redundant `try`/`except ImportError` block later in the file that re-imported the same module and used its `.router` attribute. The second registration was dead code (FastAPI matches the first-registered route) left over from an incomplete refactor; removed as part of the `app.py` split
- **Duplicate user creation race**: A race in user creation could raise an untyped/unclear error on conflicting concurrent registrations; now raises a typed exception
- **Dev/prod backup data dir leak**: Test/isolated `data_dir` overrides could leak into the production backups directory when the override wasn't scoped per environment; backup directory resolution is now correctly isolated per environment
- **Roadmap link**: The "Roadmap" link in the `README.md` footer was broken (404) after the `ROADMAP.md` file was moved to `docs/ROADMAP.md`; fixed the link

### 📝 Documentation

- **Restructured AGENTS.md around progressive disclosure**: The root instructions file had grown to 975 lines with duplicated/contradictory content — four different, mutually inconsistent test-coverage snapshots (83.54%/1087 tests, 86.90%/509-of-514, 86.46%, 89.83% frontend), no mention of the `Makefile` that `docs/DEVELOPMENT.md` already documents as the canonical command surface (`make dev`/`make test`/`make lint`), and a dead "CSS File Consolidation" section referencing legacy stylesheets (`style.css`, `auth.css`, `admin.css`, `sessions.css`, `validation.css`) that no longer exist in the repo. Split into a minimal 44-line root `AGENTS.md` (project description, `make`-first command reference, and a pointer table) plus seven topic files under `docs/agents/` (`architecture.md`, `api.md`, `python-style.md`, `frontend.md`, `testing.md`, `git-and-docker-safety.md`, `workflow-and-pitfalls.md`), so an agent loads only what a given task needs instead of the full file on every turn. Stale coverage/test-count numbers were removed in favor of pointing at live test-runner output, matching the pattern `docs/TESTING.md` already used
- **Removed dead docs**: Deleted `docs/QUICK_START.md` (a content-free deprecation stub pointing to `docs/DEPLOYMENT.md`) and fixed dangling links to the already-removed `docs/REFACTOR_OPPORTUNITIES.md` and `docs/MIGRATION_GUIDE_JSON_TO_DB.md` across `docs/CHANGELOG.md`, `docs/ROADMAP.md`, `docs/DEPLOYMENT.md`, `docs/TROUBLESHOOTING.md`, and `README.md`
- **Marked `docs/ROADMAP.md` database migration item as done**: Item 5 ("Database Migration (SQLite/PostgreSQL)") was still phrased as pending work despite having shipped long ago; struck through and given a Resolution note, consistent with how other completed roadmap items are recorded
- **Synced `docs/SPECS/SPEC_APP.md` and `docs/SPECS/SPEC_DATABASE.md` with shipped features**: These living architecture specs (as opposed to the frozen per-feature specs under `specs/`) had drifted behind two shipped features — the `semantic_version` field on prompts/versions and the "copy with version metadata" UI action (001-prompt-versioning), and the full backup subsystem (003-enhanced-backup-restore): scheduled backups, AES-256-GCM encryption, S3-compatible cloud storage upload, incremental/delta backups with checksums, and an append-only audit log. Both specs bumped to v1.1.0

### 🧪 Tests

- **Phase 0 safety net**: Added Playwright smoke tests (admin-users, backup-management, category-management, prompt-management, tag-management) and expanded backend tests (DB services, prompts router, full backup roundtrip) to guard against behavioral regressions during refactoring works

## [1.11.0] - 2026-07-19

### 🔒 Security

- **Unpinned and patched vulnerable dependencies**: `fastapi`, `uvicorn`, `jinja2`, `python-multipart`, and `aiofiles` were pinned to exact versions frozen since ~2023; `pip-audit` found 24 known CVEs across them (notably a Jinja2 XSS/sandbox-escape family and a `python-multipart` parsing DoS family), invisible without running the audit manually. Floors bumped to patched versions; `starlette` (transitive via `fastapi`) now resolves to ≥1.3, closing those too
  - Updated all 14 `Jinja2Templates.TemplateResponse(...)` call sites to the `(request, name, context)` signature required by `starlette>=0.40` (the old `(name, {"request": request, ...})` form breaks Jinja2's internal template cache under the new Starlette)
- **Removed unused `codex` npm dependency**: A 2013-era documentation generator, present in `package.json` `dependencies` but referenced nowhere in the codebase, was dragging in 25 npm vulnerabilities (3 critical) via its `tea`/`orchid`/`ws` sub-dependencies
- **`vite` 5→8 and `vitest` 2→4 upgraded**: Closed the remaining transitive `esbuild`/`rollup`/`ws` vulnerabilities; 0 npm vulnerabilities remain (`npm audit`)
- **CI security-audit job**: New Forgejo Actions job runs `pip-audit` and `npm audit --audit-level=high` on every push/PR; `ecdsa` (transitive via `python-jose`, no fixed version available upstream) is explicitly ignored via `--ignore-vuln` with a comment rather than silently allowed

### ⚙️ CI/Build

- **New `ci.yml` Forgejo workflow**: Runs `make lint`, `make test`, and `make build-frontend` on every push/PR — previously only the `accessibility.yml` workflow existed, so lint/test regressions and dependency drift were only caught when a developer remembered to run them locally

### ✨ Added

- **Dynamic Prompt Placeholders** (spec 006, Codeberg #42): Prompt content can now contain `[NAME]`- or `{NAME}`-style placeholder tokens that get filled in at copy time
  - **Placeholder detection**: Clicking Copy on a prompt card whose content contains bracketed (`[DURATION]`) or braced (`{DURATION}`) tokens opens a form with one input per distinct token instead of copying immediately; prompts with no placeholders keep today's instant one-click copy unchanged
  - **Substitution**: Confirming the form replaces every occurrence of each filled placeholder with its value in the copied text; a repeated token (e.g. `[TITLE]` used twice) is filled once and substituted everywhere; unfilled fields are left as their original token, and confirming with all fields blank reproduces the raw content exactly
  - **Syntax rules**: `[NAME]` and `{NAME}` are distinct placeholder identities even with the same name; matching is exact and case-sensitive; only well-formed tokens (name is 2+ characters of uppercase ASCII letters, digits, underscores, and spaces — `[A-Z0-9_ ]{2,}`) are recognized — things like `array[0]`, `[point]`, `[YYYY-MM-DD]`, or unmatched `[abc` are left as plain text
  - **Non-recursive substitution**: A user-entered value is inserted as literal text and is not itself re-scanned for placeholder tokens
  - **No persistence, no schema change**: Placeholders are derived on the fly from prompt content; stored content, version history, search/filter matching, and CSV/Markdown/JSON export all continue to use the raw, unsubstituted text unchanged
  - **Version history untouched**: The placeholder-fill form only appears on the Copy-click action for a prompt's current content; the version-history/diff view stays read-only/text-only with no placeholder form (revert to an older version first to copy it with placeholders filled in)
  - **New module**: `src/web/static/ts/utils/placeholders.ts` (`detectPlaceholders`/`substitutePlaceholders`), covered by a dedicated unit test suite and a new Playwright e2e spec (`tests/e2e/prompt-placeholders.spec.ts`)
  - **i18n**: Placeholder modal chrome translated across EN/FR/ES/DE

### 🐛 Fixed

- **Placeholder copy error handling**: Clipboard write failures and substitution errors inside the placeholder-fill modal's confirm callback previously ran outside the enclosing try/catch and were silently dropped instead of surfacing a success or error notification

### 🧪 Tests

- **Backend/frontend coverage gaps closed**: Removed `src/services/tag_category_undo.py` (dead code superseded by the DB-backed undo system); added tests for `backup_scheduler.register_backup_jobs` and `BackupRepository` (both previously untested); added/extended frontend tests for `auth-nav.ts` (no prior test file), `dom.ts` scroll indicators, `notifications.ts` icon branches, and `secondary-nav.ts` auth-error handling
- **`docs/TESTING.md` rewritten**: Metrics sections now describe coverage gates and structure instead of point-in-time test counts/percentages that drifted out of date; added a "Known Accepted Gaps" section documenting intentionally-deferred low-value coverage (e.g. generic exception fallbacks in `auth.py`)
- **Frontend branch coverage restored after `vitest` 4 upgrade**: `@vitest/coverage-v8` 4.x computes branch coverage more strictly than 2.x, dropping the global figure from 91% to 79.55% with no functional regression; added targeted branch tests for `api.ts`, `i18n.ts`, `notifications.ts`, and `color-picker.ts` to bring it back to 86.57% (threshold: 85%) rather than lowering the gate

## [1.10.1] - 2026-07-15

### 🐛 Fixed

- **PostgreSQL migration failure in `enhanced_backup_tables`**: The v1.10.0 migration was written and tested against SQLite only and failed on PostgreSQL production deployments
  - Table/column existence checks used SQLite-only `sqlite_master`/`PRAGMA table_info` queries (`UndefinedTable: relation "sqlite_master" does not exist` on Postgres); replaced with dialect-agnostic `sa.inspect(conn)`
  - Boolean column defaults were declared as SQLite-style integer literals (`sa.text("1")`/`sa.text("0")`), which Postgres rejects (`DatatypeMismatch: column "enabled" is of type boolean but default expression is of type integer`); replaced with `sa.true()`/`sa.false()`
  - Raw `ALTER TABLE ... ADD COLUMN` SQL strings replaced with `op.add_column`/`op.drop_column` for portability
  - No schema or data changes beyond what v1.10.0 intended — this only fixes migration execution on PostgreSQL

## [1.10.0] - 2026-07-15

### ✨ Added

- **Server-side pagination for the prompt list**: `GET /api/prompts` and `GET /api/prompts/search` now return one page of results instead of the entire dataset
  - **Pagination envelope**: Responses include `page`, `limit`, `total_pages`, `total_count`, `has_next`, and `has_previous` alongside the `prompts` payload (additive, backward-compatible)
  - **Query params**: `page` (1-indexed, default 1) and `limit` (default 50, clamped to a max of 100); out-of-range values are normalized rather than rejected
  - **"Load More" UI**: New page-size selector (25/50/100) and a "Load More" control on the prompt list, backed by a new `utils/pagination.ts` state module with duplicate-click and past-last-page guards
  - **Test coverage**: New backend tests for the pagination envelope and repository `count()` method, plus a dedicated frontend test suite for the pagination state module

- **Enhanced Backup & Restore System** (spec 003): Encryption, cloud storage, scheduling, and audit logging for database backups
  - **Encryption**: Backups can be encrypted at creation with a user-supplied passphrase (AES-GCM); key rotation verifies the old passphrase via a stored sentinel before re-encrypting; scheduled backups fall back to unencrypted with a warning since no passphrase can be prompted for in a background job
  - **Cloud storage**: New S3-compatible provider configuration (with SSRF-safe endpoint URL validation) lets manual and scheduled backups upload to cloud storage; restore automatically falls back to downloading from cloud when the local backup file is missing
  - **Scheduling**: Configurable backup schedules with a single `retention_days` policy (replacing the earlier daily/weekly/monthly count design), persisted across restarts via `register_backup_jobs` at app startup, with misfire grace time to tolerate brief downtime
  - **Monitoring & audit**: New dashboard panel shows backup statistics (size, prompt count, creator) and a full audit log (create/restore/delete) backed by `BackupAuditService`
  - **Delete all backups**: New bulk-delete action with explicit confirmation modal
  - **Restore UX**: Restore modal prompts for a passphrase when the selected backup is encrypted and surfaces the specific restore error inline; backup list items show local/cloud/encrypted status badges independently (a backup can be both local and cloud)
  - **Storage efficiency**: SQLite backups now use `VACUUM INTO` instead of a raw file copy, excluding free/unused pages left behind by deletes (shrinks backups from ~11MB to ~320KB on a lightly-used dev DB)
  - **Access control**: All backup endpoints now require the admin role when auth is enabled (bypassed when `AUTH_ENABLED=false`, e.g. single-user/dev deployments)
  - **Database migration**: New tables `backup_audit_logs`, `backup_schedules`, `backup_storage_providers`, `encryption_key_configs`
  - **Test coverage**: 159 new tests across encryption, cloud, scheduler, audit, and restore-diff services

- **Global language selector**: Added to the header of every page (previously only reachable from the profile page, which is hidden when auth is disabled); language change is now centralized in `i18n.ts`

- **Developer Workflow Makefile**: Single `make` entry point for all common development tasks — no need to remember individual `npm`, `pytest`, or `pip` commands
  - **`make install`**: Creates the Python 3.14+ virtualenv if absent (or recreates if the existing one is too old), installs backend and frontend dependencies in one step
  - **`make dev`**: Starts the backend (FastAPI) and Vite frontend dev servers concurrently; loads local secrets/config from `.env`; Ctrl-C shuts both down cleanly; exits immediately with an error if either port is already in use
  - **`make test`**: Runs the full backend and frontend test suites and exits non-zero if either fails
  - **`make lint` / `make lint-fix`**: Runs Black, ESLint, TypeScript typecheck, and Prettier across both stacks; `lint-fix` applies auto-fixable issues in place
  - **`make build`**: Builds frontend assets (TypeScript + Vite) and the production Docker image
  - **`make help`**: Self-documenting target list (default when running bare `make`)
  - See `docs/DEVELOPMENT.md` for full prerequisites, port overrides, and failure mode guidance

- **Frontend Unit Tests**: Added unit test coverage for 7 previously untested TypeScript utility modules
  - `utils/a11y.ts`, `utils/color-picker.ts`, `utils/dialogs.ts`, `utils/focus-management.ts`, `utils/keyboard-nav.ts`, `utils/typeahead.ts`, `utils/button-keyboard-activation.ts`

- **Mobile-Responsive UI Enhancements** (spec 004, Codeberg #20): Touch-optimized navigation, layouts, gestures, offline support, and PWA installability
  - **Slide-out navigation drawer**: Hamburger-triggered drawer replaces the desktop sidebar below 768px, with sectioned Data/Manage/Account layout (for clearer screen-reader landmarks) shared across the homepage and all 9 secondary pages (admin users/sessions, backup, import/export, categories, tags, profile); shared `mobile_drawer` macro and `initMobileNav`/`utils/secondary-nav.ts` deduplicate logout and admin-visibility logic across pages
  - **Touch targets & layout**: 44x44px minimum touch targets, full-screen modals on mobile vs. centered dialogs on desktop, responsive breakpoints at 320/375/425/768px with no horizontal scrolling, keyboard-safe input focus, floating action button for new prompts, "Read More" truncation for long prompt text on mobile cards
  - **Full-screen mobile search overlay**: Replaces the desktop inline search bar; auto-closes shortly after results settle (1.2s idle timer, reset on each keystroke) rather than snapping shut mid-search; inline clear (×) buttons added to all search inputs (desktop, drawer, overlay)
  - **Touch gestures**: Swipe-left/right on prompt cards reveals delete/edit actions (with accessible on-screen equivalents), pull-to-refresh on the prompt list with a visible fallback control for non-touch input
  - **Offline support (read/copy-only)**: Service Worker precaches the app shell and all locale files (including languages never switched to while online) so previously-viewed prompts, their version history, and copy actions keep working offline; create/edit/delete/revert/bulk actions and navigation to connectivity-requiring pages (Import/Export, Manage Categories/Tags, Backup Management) are blocked client-side with a "reconnect to continue" message instead of being queued; cache and offline queue are purged on logout to prevent stale data leaking across users on shared devices
  - **PWA installability**: Web app manifest with icons at multiple resolutions for "Add to Home Screen"; `apple-touch-icon`/`apple-mobile-web-app-title` meta tags so iOS Safari shows the app icon and full name instead of a generic icon and truncated title
  - **Dark mode retrofit**: `prefers-color-scheme` dark theme extended from the homepage (its only prior scope) to every page, form, and shared component; required an explicit Tailwind v4 `@custom-variant dark` declaration since `darkMode: 'class'` in `tailwind.config.ts` is ignored, plus fixes for hardcoded light-only colors in form inputs, tables, validation banners, sidebar lists, session highlight rows, and the color picker
  - **Test coverage**: New Playwright mobile suites (navigation, touch targets, modals, keyboard, swipe/pull-to-refresh gestures + a11y, offline cache, PWA install, ARIA audit, tablet-landscape, performance) and Vitest unit tests for all new TypeScript modules (`gestures.ts`, `mobile-nav.ts`, `sw-register.ts`, `secondary-nav.ts`, `focus-management.ts`)

### 🔒 Security

- **Backup system path traversal**: `backup_id` is now format-validated and metadata file paths are confined within `backups_dir` via a realpath check
- **Backup system stored XSS**: All server-supplied values (backup list, cloud provider rows) are escaped before `innerHTML` assignment; IDs moved out of inline `onclick` strings into `data-` attributes
- **Backup system SSRF**: S3 endpoint URLs are validated before use
- **Backup system unauthenticated endpoints**: Schedule, encryption config, providers, monitoring, audit log, stats, and compress endpoints now require authentication; all backup operations now require the admin role when auth is enabled (bypassed when `AUTH_ENABLED=false`, e.g. single-user/dev deployments)
- **Cloud credentials passphrase**: No longer accepted from the client; sourced solely from the server-side `PROMPTVAULT_CLOUD_CREDS_PASSPHRASE` environment variable (documented in `.env.example`)

### 🐛 Fixed

- **Unbounded prompt list query**: `GET /api/prompts` and `GET /api/prompts/search` routed through `data_service.load_prompts()`, which fetched the entire prompts table unconditionally on every request rather than only as a rare legacy-JSON fallback; this path is now paginated too, and the previously unreachable `favorites=true` without-auth 401 check now actually fires
- **Backup restore on compressed backups**: `restore_backup`, `compute_restore_diff`, and `selective_restore` failed silently on gzip-compressed backups (read errors were swallowed, making restore-preview falsely report every prompt as "to be deleted" and selective restore silently restore nothing); backups are now decompressed before decryption in all three paths, and genuinely corrupt backups now fail loudly
- **Backup schedule schema drift**: A pre-existing `backup_schedules` table from an earlier prototype (with `retention_daily_count/weekly/monthly` columns) could slip past the migration's "if not exists" guard, breaking schedule saves with a missing-column error; the migration now reconciles existing tables into the new `retention_days` column
- **Backup ID collisions**: Scheduled and custom-named backups reused a fixed ID, colliding on the `backups.id` unique constraint after the first run; timestamps are now always appended
- **Backup live-database restore corruption**: SQLite restore used `shutil.copy2`, which could corrupt a live database with open connections; replaced with the `sqlite3.backup()` API
- **Backup encryption state desync**: A failed `_update_backup_encryption` call was previously swallowed, allowing a backup file to be encrypted on disk while the database recorded it as unencrypted; errors now propagate, and DB metadata is saved before encryption so salt/nonce are always recorded even if encryption fails partway
- **Backup key rotation error handling**: A wrong passphrase during key rotation surfaced as a generic 500; now returns 422 with the actual error message
- **Backup retention pooling**: Cleanup previously pooled all backups together when enforcing retention; now enforces per-kind quotas correctly
- **Dev/prod backup data dir isolation**: `BackupSchedulerService`'s lazily-loaded `BackupService` ignored `PROMPTVAULT_DATA_DIR`, causing scheduled backups to collide when dev and prod share a host; app startup now warns if `PROMPTVAULT_DATA_DIR` and `DATABASE_URL` point at different directories
- **Session cleanup undercounting**: Expired-but-revoked sessions were excluded from cleanup, letting 17k+ stale rows accumulate; cleanup now runs once synchronously at scheduler startup instead of waiting for the first hourly tick
- **Anonymous-mode prompt mutations**: Earlier 401 guards on `get_current_user_or_none` regressed single-user/anonymous deployments (`AUTH_ENABLED=false`) to read-only; a new `get_current_user_or_default` dependency falls back to a shared system user so update/delete/favorite/bulk-delete keep working when auth is disabled
- **Anonymous-mode category/tag pages**: `manage-categories` and `manage-tags` required a logged-in user unconditionally, unlike other data-facing routes; now bypass auth when disabled like the rest
- **Backup page i18n**: Backup list rows, cloud provider rows, status/progress messages, buttons, and audit/history table headers were hardcoded in English (in several cases due to duplicate `data-i18n` attributes silently dropping the second one); fully wired through `t()` across all locales, including a fix so the monitoring panel re-fetches after `changeLanguage()` completes instead of racing it
- **Backup page layout**: Long backup IDs overlapped the Restore/Delete buttons; titles are now truncated with an ellipsis and full ID shown via tooltip
- **`copy-with-version` metadata placement**: The portable metadata comment (`<!-- prompt-version: ... -->`) is now prepended to the copied content rather than appended, so consumers that detect it by reading the first line work correctly
- **Session cleanup double-open**: `SessionCleanupScheduler.run_cleanup_now()` was opening a DB session then calling `_cleanup_expired_sessions()` which opened a second concurrent session; it now delegates directly, eliminating the redundant connection and a potential SQLite lock
- **Session cleanup inflated count**: `run_cleanup_now` was counting expired sessions without the `is_revoked = false` filter used by the actual cleanup query, causing `expired_found` in the return value to be higher than sessions actually deleted
- **Mobile logo distortion**: A mobile media-query override in `@layer components` always lost to Tailwind's `@layer utilities`, causing inconsistent logo sizing on small viewports
- **Version history carousel listener leak**: Prev/next click handlers were re-attached on every reload without removing prior ones, so stacked stale-closure handlers drove the carousel index past its bounds after repeated opens
- **Pull-to-refresh listener leak**: Fixed a `pointerup`/`pointercancel` listener leak in `attachPullToRefresh`, and resolved a scroll-lock conflict with mouse-triggered pull-to-refresh
- **First-visit offline cache gap**: A page is never controlled by the Service Worker that installs it, so a first-ever visit previously left the offline cache empty until a second load

### 🔧 Changed

- **Backup retention policy simplified**: Replaced separate daily/weekly/monthly retention counts with a single `retention_days` field, moved into the Cleanup UI as a maintenance concern rather than a scheduling one
- **Backup datetime serialization**: Standardized datetime handling across backup audit/history logs
- **Black declared as a dev dependency**: `black` is now listed in `pyproject.toml` under `[project.optional-dependencies] dev` and installed via `pip install -e ".[test,dev]"`; it is no longer installed as a separate ad-hoc `pip install` step in the Makefile
- **Codebase reformatted with Black**: All Python source files and tests normalised to double-quoted strings and Black line-wrapping style (no logic changes)
- **ESLint config hardened**: Added `globals.browser` and `globals.es2022` to TypeScript file rules; excluded Python virtualenv, coverage, and accessibility test directories from linting; added `@typescript-eslint/no-unused-vars` rule with underscore-prefix ignore pattern

## [1.9.0] - 2026-07-02

### ✨ Added

- **Prompt Semantic Versioning**: Prompts can now be assigned an optional semantic version number (`MAJOR.MINOR.PATCH`) when creating or editing
  - **Version badge**: The current version is displayed as a `v1.2.0` badge on the prompt card and in the version history panel; prompts without a version show no badge
  - **Version history labels**: Each revision in the history panel now shows the semantic version that was active at save time; entries predating this feature are labeled "unversioned"
  - **Input validation**: Non-conforming version strings (e.g. `abc`, `1.0`) are rejected at both API and frontend levels with a clear error message
  - **Version downgrade warning**: Saving a version lower than the current one is allowed but triggers an `X-Version-Downgrade: true` response header
  - **Copy with version metadata**: New "Copy+Version" action on each prompt card calls `POST /api/prompts/{id}/copy-with-version` and places the prompt content plus a portable metadata line on the clipboard (e.g. `<!-- prompt-version: 1.2.0 | This line is metadata — ignore when processing this prompt. -->`), enabling users to detect outdated external copies
  - **Database migration**: `e1f2a3b4c5d6` adds a nullable `semantic_version` column to both `prompts` and `prompt_versions` tables; no action required for existing data

### 🔒 Security

- **Stored XSS in prompt cards**: `prompt.title`, `prompt.category`, tag names, and prompt preview text were interpolated directly into `innerHTML` without escaping; now wrapped with `escapeHtml()` (`src/web/static/ts/app.ts`)
- **Stored XSS in version history cards**: `version.author` and `version.message` were interpolated directly into `innerHTML` without escaping; now wrapped with `escapeHtml()` (`src/web/static/ts/app.ts`)
- **Unauthenticated prompt update**: `PUT /api/prompts/{id}` skipped the ownership check when no auth token was provided, allowing any caller to overwrite any prompt; now returns 401 when unauthenticated (`src/web/routers/prompts.py`)
- **Unauthenticated favorite toggle**: `PUT /api/prompts/{id}/favorite` had the same bypass; now returns 401 when unauthenticated (`src/web/routers/prompts.py`)
- **Unauthenticated backup deletion**: `DELETE /api/backups/{id}` had no authentication dependency, allowing any caller to delete any backup; now requires a valid session (`src/web/app.py`)

### 🐛 Fixed

- **Browser Back Navigation in Prompt Views**: Fixed bug where pressing the browser back button while editing a prompt or viewing version history navigated to a blank tab instead of returning to the prompt list
  - **Root cause**: The prompt editor and version history modal are shown/hidden by toggling CSS classes on the same page — no URL is pushed, so the browser has no `/` history entry to return to
  - **Fix**: `history.pushState()` is called when opening the editor or version history modal; a `popstate` listener closes the active view on back-navigation; close buttons and Escape key call `history.back()` so the pushed entry is always consumed
  - **Impact**: Back navigation now closes the editor/modal and keeps the user in the app, consistent with the behaviour of import/export, backup, profile, and admin pages
  - **Files Modified**: `src/web/static/ts/app.ts`, `src/web/templates/index.html`

- **Filter State Preservation**: Fixed bug where filter state was lost after editing or deleting prompts
  - **Root cause**: After saving/deleting, `loadPrompts()` was called instead of `performSearch()`, and sidebar lists were re-rendered without preserving active filter state
  - **Fix**: Updated `handlePromptSubmit()` and `deletePrompt()` to preserve filter state by calling `performSearch()` when filters are active; Modified `renderCategories()` and `renderTags()` to restore active filter state from `searchState` after re-rendering
  - **Impact**: Users can now edit/delete prompts while maintaining their current filtered view, improving workflow efficiency
  - **Files Modified**: Frontend logic in `src/web/static/ts/app.ts`

## [1.8.0] - 2026-03-27

### ♿ Accessibility

- **WCAG 2.1 AA Compliance**: Comprehensive accessibility improvements across all pages
  - **Color Contrast**: Fixed text and UI element contrast ratios to meet WCAG AA minimums across all templates
  - **Heading Hierarchy**: Corrected heading structure (h1→h2→h3) on all pages for proper document outline
  - **ARIA Attributes**: Added `aria-label`, `aria-describedby`, `aria-expanded`, and `aria-haspopup` to landmarks, buttons, form elements, and tables
  - **Focus Management**: Enhanced visible focus indicators for all interactive elements; focus trap in modals; focus fallback styles
  - **Keyboard Navigation**: Full keyboard support with tab order, button activation, and modal keyboard handling
  - **Skip Links**: Implemented skip-to-content link using clip-path technique for keyboard and screen reader users
  - **Landmark Regions**: Added `<header>`, `<nav>`, `<main>`, `<footer>` ARIA landmarks throughout
  - **Form Accessibility**: Inputs linked to help text via `aria-describedby`; explicit `type="button"` on all interactive elements
  - **Table Accessibility**: Table captions and ARIA labels on headers for screen readers
  - **i18n**: Added translation support for skip link navigation
  - **Lighthouse Scores** (Desktop): all pages score 95–100 (auth/login 96, main 95, manage-categories 95, manage-tags 95, import-export 100, profile 96, admin/users 100, admin/sessions 100, forgot-password 100, register 96)

## [1.7.0] - 2026-02-05

### ✨ Added

- **Turnkey Deployment System**: Complete deployment automation with pre-flight checks, five-phase deployment, and automatic rollback
  - **Deployment Orchestration Script**: `scripts/setup/deploy.py` provides comprehensive deployment automation
  - **Pre-flight Checks**: Validates Docker, ports, disk space, JWT keys, and configuration before deployment
  - **Five-Phase Deployment**:
    - **Preparation**: Database backup, container state preservation, image pulling/building
    - **Infrastructure**: PostgreSQL and Redis service startup with health verification
    - **Migrations**: Alembic database schema updates with validation
    - **Application**: PromptVault web service deployment with health monitoring
    - **Verification**: Smoke tests, deployment summary, and access information
  - **Automatic Rollback**: Full rollback capability on failure with database restoration
  - **Dry Run Mode**: Safe testing without making changes (`--dry-run`)
  - **CI/CD Integration**: Non-interactive mode for automated deployments (`--non-interactive`)
  - **Flexible Options**: Skip backup/migrations, force rebuild, and other configuration options
  - **Comprehensive Logging**: Detailed progress reporting and error handling
  - **Health Monitoring**: Service health checks with configurable timeouts
  - **Backup Management**: Automatic timestamped backups with verification
  - **Docker Integration**: Full Docker Compose orchestration with error handling
  - **Documentation**: Complete deployment guide in `scripts/setup/DEPLOY_README.md`

- **Enhanced Deployment Wizard**: Improved user experience with comprehensive information display
  - **Critical Information Display**: Highlights JWT keys, database backups, and configuration files that must be saved
  - **Visual Deployment Plan**: Step-by-step breakdown of the entire deployment process
  - **System Status Overview**: Shows current running services before deployment
  - **Change Preview**: Details what components will be modified during deployment
  - **Risky Operation Confirmations**: Explicit confirmation for database changes and container restarts
  - **Improved Console Methods**: Added `critical()` and `section()` methods for better information presentation

### 🔄 Changed

- **Deployment Process**: Replaced manual deployment steps with automated orchestration script
- **User Experience**: Enhanced deployment wizard provides comprehensive guidance and safety checks
- **Error Handling**: Improved error messages and rollback capabilities
- **Console Utilities**: Extended `SetupConsole` class with new methods for critical information display

### 🐛 Fixed

- **Live Tag Autocomplete**: Fixed tag autocomplete functionality in prompt editor
  - **Root Cause**: Tag autocomplete was not properly handling input events and tag selection
  - **Fix**: Improved event handling to prevent input blur on tag selection and ensure proper tag suggestions
  - **Impact**: Users can now seamlessly add tags during prompt creation/editing with live autocomplete suggestions
  - **Files Modified**: Frontend tag autocomplete logic in prompt editor components

### 📝 Documentation

- **Deployment Guide**: Added comprehensive `scripts/setup/DEPLOY_README.md` with usage examples, troubleshooting, and best practices
- **Changelog**: Updated to reflect new turnkey deployment features and improvements
- **Tag Autocomplete**: Updated documentation to include live autocomplete feature in prompt editor

## [1.6.0] - 2026-02-02

### ✨ Added

- **Tag and Category Management System**: Comprehensive management interface for tags and categories with CRUD operations, bulk actions, analytics, and undo support (see [SPEC_TAG_CATEGORY_MANAGEMENT](SPECS/SPEC_TAG_CATEGORY_MANAGEMENT.md))
  - **Management Pages**: Dedicated UI for managing tags and categories with search, filtering, and bulk selection
  - **CRUD Operations**: Create, read, update, and delete tags and categories with metadata (name, description, color)
  - **Merge Operations**: Merge multiple tags or categories into a single target with atomic transaction safety
  - **Bulk Operations**: Delete multiple tags/categories or apply/remove tags across multiple prompts in batch
  - **Find and Replace**: Replace tag/category names across all prompts in a single operation
  - **Undo System**: Full undo support for management operations with persistent storage and user-scoped history (50 operations per user per entity type, 30-day automatic expiration)
  - **Usage Analytics**: Track and display tag/category usage counts, most/least used items, and tag co-occurrence summaries
  - **Orphan Detection**: Identify unused tags, unused categories, and prompts lacking tags or categories
  - **Import/Export**: Import and export tag and category definitions in JSON format with validation
  - **Tag Hierarchy**: Optional parent-child relationships for tags to support hierarchical taxonomy
  - **Tag Suggestions**: Content-based tag suggestions from prompt text using deterministic keyword extraction
  - **Performance**: Optimized queries with no N+1 patterns, sub-100ms response times for typical operations
  - **Test Coverage**: 91+ tests for undo/merge operations, 1411+ total tests with 86.75% coverage

### 🔄 Changed

- **Version Comparison Enhancement**: Version diff modal now displays character-level changes with inline highlighting
  - **Character-level precision**: Insertions shown with green background and bold text, deletions with red background and strikethrough
  - **Improved granularity**: Easily identify punctuation fixes, typo corrections, and single character changes
  - **Backend**: Implemented `diff-match-patch` algorithm for computing character-level diffs in `src/utils/diff_utils.py`
  - **Frontend**: New `renderCharacterDiff` utility with Tailwind CSS styling for visual diff rendering
  - **Backward compatible**: Falls back to old/new box display if character diff is unavailable
  - **Test coverage**: 22 backend tests (95% coverage) + 13 frontend tests (100% coverage)
  - **Documentation**: Updated `docs/VERSION_CONTROL.md` with character-level diff feature guide

### 🔧 Fixed

- **Tags Not Persisting When Editing Prompts**: Fixed bug where modified tags were not saved during prompt updates
  - **Root cause**: `update_prompt` function in `src/web/routers/prompts.py` was missing tag update logic
  - **Fix**: Added tag parsing using `_parse_tags_field()`, created/retrieved tag objects with deduplication, and updated prompt tags
  - **Testing**: Tag modifications now persist correctly, filtering by new tags works properly, and tags persist through page refreshes

- **"undefined • undefined" Text Display in Tag Counter**: Fixed i18n initialization timing issue where translations were unavailable
  - **Root cause**: Tag counter in `src/web/static/js/form_validation.js` was calling `i18next.t()` before i18next was fully initialized
  - **Fix**: Added `safeTranslate()` helper function that checks i18next initialization status before translating, counter now only displays when valid translations are available
  - **Affected functions**: Updated `refreshValidationText()` and `initTagFieldValidation()` to use safe translation

- **Remember Me Token Persistence**: Fixed critical bug where users were logged out after 15 minutes despite checking "Remember Me"
  - **Root cause**: Access token cookie `max_age` was set to 15 minutes (matching JWT expiry), causing browser to delete cookie before refresh could occur
  - **Frontend fix**: Migrated all API calls in `app.ts`, `profile.ts`, `admin-sessions.ts`, `admin-users.ts`, `backup-management.ts`, and `import-export.ts` to use `apiFetch` utility with automatic token refresh
  - **Backend fix**: Extended access token cookie lifetime to match refresh token (7 days normal, 30 days with "Remember Me")
  - **Refresh endpoint**: Now properly updates HTTP-only cookies with new tokens after refresh
  - Users now stay logged in for full session duration (7 days or 30 days with "Remember Me")

## [1.5.0] - 2025-12-22

### 🔄 Changed

- **UI Design & Styling:** PromptVault's frontend has been modernized with Tailwind CSS v4 for consistent, responsive UI:
  - **Tailwind CSS v4**: Utility-first CSS framework with @theme directives for custom design system
  - **Responsive Design**: Mobile-first approach with breakpoints for all device sizes
  - **Dark Mode Ready**: Tailwind color palette supports light and dark themes
  - **Component Library**: Reusable button, card, form, input, and navigation components
  - **Accessibility**: Focus states, keyboard navigation, ARIA labels, and semantic HTML
  - **Performance**: CSS purging and optimization for minimal bundle size

## [1.4.0] - 2025-12-21

### ✨ New Features

- **Frontend TypeScript Migration**: All frontend scripts migrated to TypeScript with strict type checking and Vite build pipeline.
- **Frontend Unit Tests**: Added Vitest test suite with coverage reporting (v8).
- **Type-safe i18n**: Translation keys are now type-checked against `src/web/static/locales/en.json`.
- **Remember me**: Implemented login "Remember me" option with persisted token storage preference and i18n labels across EN/FR/ES/DE

### Changed

- **Frontend Tooling**: Added ESLint + Prettier and associated scripts for linting/formatting.
- **Docs**: Updated README and testing docs to reflect the TypeScript migration and frontend workflow.
- **Container security strenghtening**:
  - All containers now run as non-root users (`appuser`, `postgres`, `redis`) to enforce a least-privilege security model.
  - Docker Compose configuration updated with `no-new-privileges:true` and `cap_drop: ALL` for all services.
  - Improved security defaults for PostgreSQL and Redis deployments.

### Fixed

#### Version Control & History

- **Duplicate Version Entries**: Fixed critical bug where each prompt update created 2 versions instead of 1
  - Removed legacy data_service compatibility code creating duplicate versions in update_prompt router endpoint
  - Root cause: Update endpoint was calling both legacy service method and new version repository create method

- **Incorrect Author Tracking in Versions**: Fixed version history showing "anonymous" or "system" instead of actual authenticated user
  - Changed create_prompt and update_prompt endpoints to use `get_current_active_user` instead of `get_optional_user`
  - Updated prompt_data_service_db to accept optional author parameter for flexible service usage

- **Missing Initial Versions**: Fixed new prompts having empty version history
  - Added automatic creation of initial version (v1) with "Initial commit" message when prompt is created
  - Ensures all prompts have at least one version entry in their history

#### Authentication & API

- **Create Prompt Authentication Error**: Fixed AttributeError crash on POST /api/prompts
  - Endpoint was using get_optional_user (returning None) then accessing user.id without validation
  - Now enforces authentication via get_current_active_user dependency

#### Docker & Deployment

- **Volume Permission Issues**: Resolved permission issues caused by legacy volumes created when containers ran as root
  - Ensured correct UID/GID ownership inside data volumes (PostgreSQL UID 70, Redis UID 999)
  - ⚠️ **Action required if upgrading from a version where containers ran as root.** See [DEPLOYMENT.md](DEPLOYMENT.md). Fresh installations do not require any action.

## [1.3.0] - 2025-12-06

### ✨ New Features

- **Authentication & Authorization System**: Complete multi-user authentication with JWT tokens and role-based access control
  - **User Management**: Registration, login, logout, profile management, password changes
  - **Security Features**:
    - Argon2id password hashing (OWASP recommended, winner of Password Hashing Competition)
    - ES256 (ECDSA) JWT tokens with access and refresh token rotation
    - Account lockout after 5 failed attempts (15-minute duration)
    - Password reset flow with email-based tokens (1-hour expiry)
    - Rate limiting on authentication endpoints (slowapi + Redis)
    - Session management with max 5 concurrent sessions per user
    - Token family tracking for reuse detection and automatic revocation
  - **Role-Based Access Control (RBAC)**:
    - **Viewer**: Read-only access to own prompts
    - **Editor**: Full CRUD on own prompts, version control, import/export
    - **Admin**: All editor permissions + user management + system-wide access
  - **API Layer** (20 endpoints):
    - 8 public auth endpoints (register, login, refresh, logout, password reset)
    - 5 protected user endpoints (profile, change password, sessions)
    - 7 admin endpoints (user management, role assignment, session monitoring)
  - **Frontend Components**:
    - 7 HTML templates (login, register, forgot password, reset password, profile, admin users, admin sessions)
    - 5 JavaScript files (1,917 lines) with auth logic, password strength, session management
    - 2 CSS files (1,105 lines) with responsive authentication UI
    - 156 i18n keys in English (ready for FR, ES, DE translations)
    - **Logout Button**: [Added logout button to main navigation header for easier access](http://localhost:8003/auth/login)
  - **Database Schema**:
    - Enhanced `users` table with authentication fields (password_hash, email_verified, is_active, failed_login_attempts, locked_until)
    - `user_sessions` table for token family tracking and session management
    - `refresh_token_families` table for token rotation and reuse detection
    - `password_reset_tokens` table for secure password reset flow
  - **Comprehensive Testing**: 481 passing tests (99.8% coverage)
    - 440 existing tests (backend, services, repositories, API)
    - 41 new security integration tests covering all critical security features
  - **Production-Ready**:
    - OWASP compliance (Top 10 coverage, cheat sheet alignment)
    - Defense-in-depth security (password policies, token security, rate limiting)
    - Session cleanup job for expired tokens
    - Audit logging integration
  - **Documentation**: 3,000+ lines of comprehensive guides
    - Deployment guide with JWT key generation (`docs/AUTHENTICATION_DEPLOYMENT.md`)
    - API documentation for all 20 authentication endpoints (`docs/AUTHENTICATION_API.md`)
    - Security documentation covering OWASP compliance and threat mitigation (`docs/AUTHENTICATION_SECURITY.md`)
    - Admin setup script for creating first admin user (`scripts/create_admin_user.py`)

### 📚 Documentation

- **Authentication Deployment Guide** (`docs/AUTHENTICATION_DEPLOYMENT.md`): Complete setup instructions with JWT key generation and environment configuration
- **Authentication API Guide** (`docs/AUTHENTICATION_API.md`): All 20 endpoints documented with request/response examples
- **Authentication Security Guide** (`docs/AUTHENTICATION_SECURITY.md`): OWASP compliance, security features, threat mitigation, audit checklist
- **Authentication Specification** (`docs/SPECS/SPEC_AUTHENTICATION.md`): Updated status from DRAFT to IMPLEMENTED with completion date
- **Testing Checklist** (`docs/AUTHENTICATION_TEST_CHECKLIST.md`): Comprehensive manual testing checklist with 123 test cases
- **README.md**: Added Authentication section documenting user roles, security features, first-time setup, and authentication endpoints

### 🔧 Fixed

- **Pytest Warnings**: Eliminated all 80 pytest warnings for clean test output
  - Updated Pydantic V2 configuration in `src/db/config.py` - replaced deprecated class-based `Config` with `model_config = ConfigDict()`
  - Removed 10 deprecated `save_prompts()` calls (7 in `src/web/app.py`, 3 in tests) - no longer needed with database backend as transactions auto-persist
  - Fixed `data_file_path` deprecation in `src/web/app.py` - database now uses `DATABASE_URL` environment variable exclusively
  - Test results: 514/514 passing (100% pass rate), 86.12% coverage, 0 warnings

### 📚 Documentation

- **Testing Documentation**: Updated all documentation to reflect correct pytest usage
  - Updated `docs/TESTING.md` with `python3 -m pytest` commands and comprehensive troubleshooting section
  - Updated `docs/SPECS/SPEC_APP.md` with testing framework requirements
  - Updated `README.md` with correct test commands and metrics (514 tests, 86.46% coverage)
  - Updated `docs/AGENTS.md` with testing quick reference and explanation
  - Added troubleshooting for version conflicts and dependency issues

## [1.2.0]

### ✨ New Features

- **Database Migration (Phases 1-11)**: Complete transition from JSON file storage to relational database backend
  - **SQLAlchemy ORM**: Type-safe database operations with declarative models for Prompt, PromptVersion, Category, Tag, User, and Backup
  - **Repository Pattern**: Clean data access layer with specialized repositories (PromptRepository, VersionRepository, CategoryRepository, TagRepository)
  - **Database Support**: Production-ready PostgreSQL and development-friendly SQLite backends
  - **Alembic Migrations**: Version-controlled database schema evolution with `alembic upgrade/downgrade`
  - **Transaction Safety**: Context managers with automatic commit/rollback for data consistency
  - **Session Management**: Connection pooling for PostgreSQL with configurable pool size and timeout
  - **Migration Script**: Automated JSON to database migration with dry-run mode and verbose logging (`scripts/migrate_json_to_db.py`)
  - **Backward Compatibility**: 100% API compatibility maintained - existing endpoints return identical responses
  - **Database Backups**: SQLite file copy and PostgreSQL pg_dump integration with metadata tracking
  - **Comprehensive Testing**: 509 passing tests (86.90% coverage) for repositories, services, and integration workflows using in-memory SQLite
  - **Docker Integration**: Production-ready Docker Compose setup with PostgreSQL service and health checks
  - **Complete Documentation**: Deployment guide and technical specification (see `docs/DEPLOYMENT.md`, `docs/SPECS/SPEC_DATABASE.md`)
  - **Performance**: Indexed queries, eager loading to prevent N+1, pagination support for large datasets
  - **Security**: Parameterized queries (SQL injection prevention), SSL/TLS support, environment-based credentials

- **Test Suite Rewrite**: Complete rewrite of backend pytest suite from scratch for database-backed architecture
  - **Coverage**: 86.90% (exceeds 85% requirement by 1.9%)
  - **Test Count**: 509 passing tests out of 514 total (99% pass rate)
  - **Execution Time**: ~8 seconds for full suite (13x faster than before)
  - **New Test Files**:
    - `tests/test_db_repositories.py` (78 tests) - Repository layer with 89-100% coverage
    - `tests/test_db_services.py` (88 tests) - Service layer with 75-82% coverage
    - `tests/test_version_system.py` (48 tests) - Version control with 95-100% coverage
  - **Test Infrastructure**: Complete rewrite of `tests/conftest.py` with 30 comprehensive fixtures
  - **Database Testing**: In-memory SQLite with thread-safe handling for FastAPI TestClient
  - **Modern Patterns**: Repository pattern testing, service isolation, integration testing
  - **Coverage Configuration**: `.coveragerc` excludes legacy JSON services for accurate metrics
  - **Documentation**: Comprehensive test suite documentation in `docs/TESTING.md`
  - **Cleanup**: Removed 11 obsolete test files (1,800+ lines of outdated code)
  - **CI/CD Ready**: Fast, deterministic tests with no external dependencies
- **Bulk Prompt Deletion**: Multi-select prompts with checkboxes and delete multiple prompts in a single operation
  - **Multi-select UI**: Checkboxes on each prompt card with "Select All" functionality
  - **Bulk Actions Toolbar**: Shows selection count and delete button when prompts are selected
  - **Bulk Delete API**: `DELETE /api/prompts/bulk` endpoint accepting 1-1000 unique prompt IDs
  - **Automatic Backups**: Pre-deletion backup created automatically before bulk operations
  - **Validation**: Pydantic validation prevents duplicate IDs and enforces limits
  - **Confirmation Dialog**: Shows count of prompts to be deleted with safety warning
  - **Success Feedback**: Displays statistics on successful and failed deletions
  - **Internationalization**: Full translation support in English, French, Spanish, and German
  - **Comprehensive Testing**: 10 tests covering API endpoints, service layer, and validation
- **Input Sanitization & Validation**: comprehensive input validation and sanitization across all user-facing forms and API endpoints to prevent injection attacks, ensure data integrity, and improve user experience with clear validation feedback.
- **Frontend Telemetry Reporting**: `telemetry.js` now captures browser errors via `window.FrontendLogger`, pipes them into the `/api/logs/frontend` endpoint with rate limiting/sanitization, and exposes opt-out controls plus helper wrappers across the UI.

### 🔧 Fixed

- **Version Revert Category Loss**: Fixed bug where reverting a prompt to a previous version would lose the category, setting it to "categories.noCategory" - `_version_to_dict` now properly looks up category name from stored `category_id` in version snapshots
- **Version Timestamp Display**: Fixed "Invalid Date" display in production (PostgreSQL/Docker) by properly converting timezone-aware datetimes to UTC with ISO 8601 format
- **Bulk Delete Checkbox Position**: Moved bulk deletion checkbox to appear next to favorite button in prompt actions for better visual grouping
- **Route Ordering**: Fixed bulk delete endpoint route ordering - moved `/api/prompts/bulk` before `/api/prompts/{prompt_id}` to prevent "bulk" being interpreted as a prompt ID

### 📚 Documentation

- **Deployment Guide** (`docs/DEPLOYMENT.md`): Complete guide for Docker Compose, Docker, and manual deployment with PostgreSQL/SQLite setup
- **Migration Guide** (`docs/MIGRATION_GUIDE.md`): Step-by-step instructions for migrating from JSON to database storage with rollback procedures
- **Database Specification** (`docs/SPECS/SPEC_DATABASE.md`): Technical specification with requirements, architecture, schema, and acceptance criteria
- **Phase Documentation**: Detailed implementation reports for Phases 1-11 covering dependencies, models, configuration, migrations, repositories, services, backups, testing, and deployment

### 🔄 Changed

- **Python Version**: Minimum required Python version updated to 3.11+ (was 3.8+)
- **Data Storage**: Database backend (PostgreSQL/SQLite) is now the recommended storage method; JSON file storage marked as deprecated
- **Docker Configuration**: Enhanced Dockerfile with PostgreSQL client, non-root user, and integrated health checks
- **Docker Compose**: Complete rewrite with PostgreSQL service, health checks, and environment-based configuration

## [1.1.0] - 2025-10-30

### ✨ New Features

- **Search & Filter UI improved**: Moving search/filter block on top of windows to ease the use of this feature - [`01a40cf`]
- **Tags autocompletion**: Added tag autocomplete with usage counts for prompt tags in the web UI, leveraging the new get_tags_with_counts() service method - [`62644ec`]

### 🔧 Fixed

- **Tag normalization**: Trim tag whitespace during save to avoid duplicate entries with leading spaces - [`dd53bc3`]
- **Category sorting**: Preserve category order from configuration when saving prompts - [`b8ef70e`]
- **Search localization**: Replaced hardcoded English text in the search/filter experience, added matching translation keys in all locales, and stopped HTML entities from showing up in filter summaries.

## [1.0.0] - 2025-10-22

### Added

- **🚀 Web Application Architecture**: Complete transformation from PyQt6 desktop application to modern web-based application
  - **FastAPI Backend**: High-performance ASGI web framework replacing PyQt6 GUI
  - **REST API**: Full CRUD operations via RESTful endpoints (`/api/prompts`, `/api/categories`, `/api/tags`)
  - **Web UI**: Responsive HTML interface with Jinja2 templating
  - **Interactive Frontend**: JavaScript-based client-side functionality for seamless user experience
  - **Real-time Updates**: Dynamic prompt list updates without page refreshes

- **🐳 Docker Containerization**: Production-ready deployment with Docker
  - **Dockerfile**: Multi-stage build with Python slim image and GCC for dependencies
  - **Docker Compose**: One-command deployment with volume mounting for data persistence
  - **Volume Management**: Secure data storage outside container (`./data:/app/data`)
  - **Health Checks**: Built-in container health monitoring

- **🔒 Security Enhancements**: Enterprise-grade security practices
  - **Data Isolation**: Personal data excluded from Docker images (no sensitive data in containers)
  - **Volume Mounting**: Data stored on host filesystem with proper access controls
  - **Clean Builds**: `--no-cache` builds ensure no residual data in images

- **📱 Responsive Web Design**: Modern, accessible user interface
  - **Mobile-First**: Works seamlessly on desktop, tablet, and mobile devices
  - **CSS Framework**: Clean, maintainable stylesheets with theming support
  - **Progressive Enhancement**: Graceful degradation for older browsers

- **🔧 Developer Experience**: Improved development workflow
  - **Hot Reload**: Development server with automatic code reloading
  - **Debug Logging**: Comprehensive client and server-side logging for troubleshooting
  - **Modular Architecture**: Clean separation between web, services, and legacy components

### Changed

- **Breaking Change**: Desktop application moved to legacy status
  - Original PyQt6 application preserved in `src/main.py` and `src/ui/`
  - Desktop version marked as deprecated, web version now primary
  - Data format remains compatible between versions

- **Project Structure**: Web-first architecture with clear separation
  - `src/web/` promoted to primary application module
  - `src/services/` shared between web and desktop versions
  - Legacy desktop components moved to `src/ui/` and `src/main.py`

- **Dependencies**: Complete technology stack modernization
  - **Removed**: PyQt6, Qt dependencies (desktop GUI framework)
  - **Added**: FastAPI, Uvicorn, Jinja2, python-multipart (web framework)
  - **Updated**: Python packaging to modern `pyproject.toml` standards

### Removed

- **PyQt6 Dependencies**: Desktop GUI framework completely removed from web deployment
- **Legacy UI Components**: Desktop-specific widgets and dialogs deprecated
- **Personal Data in Images**: Sensitive data no longer included in Docker containers

### Fixed

- **Data Persistence**: Fixed critical bug where prompt changes weren't saved to disk
- **API Endpoints**: Resolved type conversion issues between string URLs and integer IDs
- **Template Rendering**: Fixed Jinja2 template errors with incorrect field references
- **Form Validation**: Improved client-side validation and error handling

### Dependencies

- **Added**:
  - `fastapi` - Modern web framework
  - `uvicorn[standard]` - ASGI server with hot reload
  - `jinja2` - Template engine
  - `python-multipart` - Form data handling
  - `aiofiles` - Async file operations
- **Removed**:
  - `PyQt6` and all Qt-related packages
  - `PyQt6-Qt6` system dependencies

### Migration Guide

**For Existing Users:**

1. **Data Preservation**: Your existing `data/prompts_data.json` file is fully compatible
2. **Web Migration**: Use `docker-compose up --build` for new web deployment
3. **Legacy Access**: Desktop version still available via `PYTHONPATH=. python -m src.main`

**For Developers:**

- Web application runs on `http://localhost:8001` (Docker) or `http://localhost:8003` (development)
- API endpoints available at `/api/*` routes
- All original functionality preserved with improved performance

## [0.4.0] - 2025-10-17

### Added

- **Comprehensive Data Backup System**: Implemented a robust backup and restoration system to prevent data loss
  - **BackupService**: New service class providing complete backup functionality with metadata tracking
  - **Automatic Backups**: Pre-operation backups created before risky operations (import, bulk delete, bulk update)
  - **Manual Backups**: User-initiated backups available through File menu ("Create Backup", "Backup & Restore")
  - **Backup Management Dialog**: Full-featured interface for viewing, restoring, and managing all backups
  - **Smart Retention**: Configurable cleanup policies to automatically remove old backups (default: 30 days)
  - **Compression**: Automatic gzip compression of older backups (default: after 7 days) to save disk space
  - **Safety Features**: Pre-restore backups ensure no data loss during restoration operations
  - **Complete Metadata**: Every backup includes comprehensive information (timestamp, size, prompt count, author)
  - **Backup Statistics**: Real-time monitoring of backup status and storage usage
  - **Cross-Platform**: Works seamlessly on Windows, macOS, and Linux

### Dependencies

- Added `humanize` library for user-friendly timestamp formatting in backup dialogs

### Changed

- Migrated packaging to `pyproject.toml` with PEP 621 metadata and setuptools backend.
- Updated installation instructions to use `pip install .` and removed the redundant `requirements.txt`.

## [0.3.0] - 2025-09-16

### Added

- **Customizable Layout**: Implemented resizable panels and layout persistence.
  - The main application window now features a flexible layout with three resizable panels: Categories/Tags, Prompt List, and Prompt Editor.
  - Utilized `QSplitter` for dynamic resizing of these panels.
  - Integrated `QSettings` to save and restore the user's preferred panel sizes and window state across sessions.

## [0.2.0] - 2025-09-12

### Added

- Internationalization support: Added translation files for multiple languages (French, German, Spanish, English) and a build script for generating translation binaries.

## [0.1.1] - 2025-09-12

### Changed

- **Project Structure Reorganization**: Restructured the codebase for better organization and maintainability
  - Created `src/` directory as main source code container
  - Moved UI components to `src/ui/` (dialogs, widgets)
  - Moved business logic to `src/services/` (data, filter, versioning, import/export services)
  - Consolidated assets in `assets/` directory (images, themes)
  - Moved data files to `data/` directory
  - Added `__init__.py` files to create proper Python packages
  - Updated all import statements to use relative imports
  - Updated README.md with new project structure and run instructions
- Changed application launch command to `PYTHONPATH=. python -m src.main`
- Extracted duplicate prompt handling logic into `_handle_duplicate_prompt` method for improved clarity and maintainability.
- **Asset Path Fixes**:
  - Corrected image paths in `assets/themes/dark.qss` and `assets/themes/light.qss` to use `assets:images/` aliases.
  - Added `assets` as a search path in `src/main.py` to ensure proper loading of resources referenced in QSS files.
- **Bug Fix: Revert Functionality**:
  - Addressed a `NameError` in `src/ui/version_history_dialog.py` by adding `QLineEdit` to its imports.
  - Fixed an issue where the `prompt_id` was not correctly passed to `VersionHistoryDialog` from `src/ui/prompt_manager_widget.py`, resolving the "Could not find prompt with ID XXXXX to revert" error.

## [0.1.0] - 2025-09-11

### Added

- Dedicated service classes for improved modularity:
  - `PromptDataService` for data operations
  - `PromptFilterService` for filtering/searching
  - `PromptVersioningService` for version control
  - `PromptImportExportService` for import/export functionality
- Comprehensive test suite for verifying refactored code functionality
- Documentation of new architecture in README.md

### Changed

- Refactored `PromptManager` to use new service classes
- Made data file path configurable
- Improved code maintainability and extensibility through modular design
- Updated version identifier description in README.md

### Notes

- Initial release with refactored architecture
- Published app on various platforms
