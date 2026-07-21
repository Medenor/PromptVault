# Refactor Opportunities Report

_Generated 2026-07-21. Scope: `src/`, `scripts/`. Behavior-preserving refactors only — no feature changes._

## Context: what's already been done — and what it left behind

PR #62 — "decompose god files into focused modules" (merged `e34e2c4`) — is **already on `main`**, so
everything measured below is the **current, post-merge state**. It did real work: extracted
`factory.py` / `middleware_setup.py` / `routing_setup.py` wiring out of `app.py`, split the auth /
prompts / tag_category routers, and broke up `backup_service_db.py` and several frontend god files.

But the decomposition was **incomplete**. Several files it claimed to "split" are still 1,000+ lines
because it extracted the *wiring* while leaving the *handlers* inline. These are not stale
observations to discount — they are live god files today (Tier 1.5 below).

The two highest-value tracks remain: **retiring dead parallel code** (ROADMAP §4, Tier 1) and
**finishing the god-file decomposition PR #62 started** (Tier 1.5).

---

## Tier 1 — Retire legacy / dead code (highest value, lowest risk)

This is ROADMAP §4 ("Retire Legacy JSON Services & Dead Code") and AGENTS.md's stated current
priority. The analysis below **verifies** the claim and corrects a couple of module names the roadmap
got wrong.

### 1a. Delete the legacy `src/web/static/js/` directory — ~7,674 lines

Every file there is headed `LEGACY JAVASCRIPT (HISTORICAL REFERENCE ONLY)`. The build pipeline is
Vite + TypeScript (`tsconfig.json` has `noEmit`, `include: src/web/static/ts/**`). The only place
these files load is a **fallback branch** in `templates/macros/scripts.html` that fires only when the
Vite manifest entry is missing:

```jinja
{% else %} {# Fallback to original JS during migration #}
<script src="/static/js/{{ legacy_entry }}.js" defer></script>
```

In a correctly-built deployment the manifest always resolves, so this branch is dead. Retiring it
removes a full duplicate frontend (two implementations of every page's logic to keep in sync).

- **One caveat — `telemetry.js`:** it is still referenced by a second fallback branch, **but it has
  already been ported** to `src/web/static/ts/telemetry.ts` (which also defines `window.FrontendLogger`).
  So it can go too; just remove the non-Vite `<script src="/static/js/telemetry.js">` fallback in the
  same macro, and fix the stale pointer at **`README.md:663`** that still names `static/js/telemetry.js`.

**To-do:** delete `src/web/static/js/`; delete both legacy-JS fallback branches in
`macros/scripts.html`; update `README.md` (lines ~174 and ~663) and `AGENTS.md` (§ "JavaScript",
line ~136) to drop the "kept for reference" language.

### 1b. Delete 5 dead service modules — ~2,267 lines

Verified via import analysis: these modules have **zero live (non-test) importers**, and zero
references anywhere in `src/` outside their own file:

| Module | Lines | Live importers | Note |
|---|--:|:--:|---|
| `src/services/prompt_data_service.py` | 823 | 0 | JSON data service; superseded by `prompt_data_service_db.py` |
| `src/services/backup_service.py` | 638 | 0 | superseded by `backup_service_db.py` + split modules |
| `src/services/version_compression_service.py` | 296 | 0 | superseded by `version_*` DB-era services |
| `src/services/version_export_service.py` | 291 | 0 | " |
| `src/services/version_tagging_service.py` | 219 | 0 | " |

> ⚠️ **Roadmap name correction:** ROADMAP §4 lists "compression/export/tagging services" — the actual
> dead files are the `version_*` ones above. The similarly-named **active** DB-era services
> (`prompt_versioning_service.py`, `prompt_import_export_service.py`, `version_compression_service` is
> dead but `backup_service_db.py`'s siblings are live) must **not** be deleted. Delete only the five
> rows in the table.

**Coupling to clean up first** (these modules are still referenced by tests, so deletion is not a
pure `rm`):

- `prompt_data_service.py` — 3 test files
- `backup_service.py` — 5 test files
- `version_compression_service.py` — 2 test files
- `version_export_service.py` — 1 test file
- `version_tagging_service.py` — 2 test files

Migrate or delete those tests, then remove the now-stale lines in **`.coveragerc`** (lines 5–6 omit
`prompt_data_service.py` and `backup_service.py` from coverage) and the AGENTS.md "Legacy JSON-based
service" notes.

**Combined Tier 1 payoff: ~9,900 lines of duplicate/dead code removed**, eliminating two parallel
data-service and backup implementations — a correctness and security liability, not just clutter.

---

## Tier 1.5 — God files still present post-merge (high value, moderate risk)

These are the files PR #62 reported as "split" but that remain 1,000+ lines because the handlers were
never moved out. Confirmed against current `main`.

### `src/web/app.py` — 1,060 lines, **17 route handlers still on `@app`**

The factory extraction moved middleware/routing *wiring* out, but the app module still directly
defines 17 endpoints — including `/api/import`, `/api/export`, `/api/prompts/{id}/versions*` (list,
compare, get, revert), `/api/categories`, `/api/tags`, and the `/import-export` and
`/backup-management` page routes. Dedicated routers for most of these **already exist**; these
handlers belong in them, not bolted onto the application object.

- **Split:** move version endpoints into a `prompts_versions_router` (alongside the existing
  `prompts_crud_router` / `prompts_search_router`); move import/export handlers into the existing
  import/export surface; move `/api/categories` + `/api/tags` GETs into `categories_router` /
  `tags_router`. `app.py` should end up as pure app assembly.
- **Longest handler:** `import_prompts` (137 lines) — extract validation + per-record ingestion.

### `src/web/routers/admin.py` — 1,105 lines, **two resources in one router**

Mixes user administration (`/users`, `/users/{id}`, `/users/{id}/sessions`) with global session/stats
administration (`/sessions`, `/stats`). Split into `admin_users_router` and `admin_sessions_router`.
Note the **frontend already separates these** (`admin-users.ts` vs `admin-sessions.ts`), so this
brings the backend back in step. Longest handler: `create_user` (110 lines).

### `src/services/auth/auth_service.py` — 1,017 lines, single class

Cohesive (one `AuthService` class) but carries two very long methods: `refresh_tokens` (185) and
`login` (143). These are **Extract Method** targets, not a file split — pull out the discrete steps
(lockout check, credential verify, token rotation, session persistence). Covered again in Tier 2.

### `src/web/dependencies/auth.py` — 1,023 lines — *cohesive, do NOT split*

Called out to pre-empt a wrong call: this file is large but genuinely single-responsibility (21
auth-dependency resolvers). The only smell is a **duplicated parallel family** of test/dev variants —
`get_current_user_or_none`, `get_current_user_or_default`, `require_role_or_bypass`,
`get_user_or_bypass`, `get_admin_or_bypass`, `get_editor_or_admin_or_bypass` (lines 854–1012) — that
shadow the real dependencies. Consolidate the bypass logic into one wrapper rather than six near-copies;
don't split the module.

---

## Tier 2 — Long methods (moderate value, low risk)

Individual functions still oversized (> ~120 lines) across active modules. Each is a straightforward
**Extract Method** target. (Some overlap Tier 1.5 files — do them as part of that split.)

| Lines | Location | Function | Suggested split |
|--:|---|---|---|
| 290 | `src/web/middleware_setup.py:55` | `configure_middleware` | one helper per concern: `add_security_headers`, `add_rate_limiting`, `add_cors`, `register_exception_handlers`, `mount_static` |
| 288 | `src/web/static/ts/app/index.ts:298` | `setupEventListeners` | group by feature area (filters, prompt actions, modal wiring) into named `setup*` helpers |
| 238 | `src/web/static/ts/tags/index.ts:410` | `init` | extract per-widget init (mirrors the `tags/a11y.ts` pattern already in place) |
| 210 | `src/web/static/ts/categories/index.ts:395` | `init` | same as tags — the two `init`s are near-parallel; consider a shared helper |
| 200 | `src/web/static/ts/app/prompt-list.ts:450` | `createPromptElement` | extract row sub-builders (badges, actions, version info) |
| 185 | `src/services/auth/auth_service.py:398` | `refresh_tokens` | extract validation, rotation, and persistence steps |
| 152 | `src/services/auth/password_service.py:454` | `check_password_strength` | table-drive the rule set instead of sequential `if`s |
| 143 | `src/services/auth/auth_service.py:253` | `login` | extract lockout check, credential verify, session issue |
| 140 | `src/web/routers/prompts_crud_router.py:297` | `update_prompt` | extract validation + diff-building from the handler |

**Note on the two near-duplicate `init`s:** `tags/index.ts` and `categories/index.ts` have
structurally parallel `init` functions (238 vs 210 lines) and parallel `a11y.ts` roving-tabindex
implementations (`tags/a11y.ts:63` and `categories/a11y.ts:49`, both ~115 lines). If they diverge
only in entity names, a shared generic module would remove real duplication — but confirm the
divergence is cosmetic before consolidating (over-abstraction risk).

---

## Tier 3 — Setup/deploy scripts (low priority)

`scripts/setup/` contains several long procedural `main`/`run_*` functions
(`setup_env.py:619 main` 177 lines, `setup.py:369 run_advanced_setup` 164, `deploy.py:168
run_preflight_checks` 131). These are one-shot operational scripts, not runtime code — lower blast
radius and lower payoff. Refactor opportunistically, only if you're already editing them.

---

## Recommended order

1. **Tier 1b** (dead services) — self-contained, biggest risk-reduction per line, unblocks the
   `.coveragerc`/AGENTS.md cleanup.
2. **Tier 1a** (legacy JS) — removes the largest single chunk; do after confirming the telemetry-TS
   port is live in production.
3. **Tier 1.5** (finish the god-file split) — `app.py` route extraction first (clearest win, existing
   routers to move into), then `admin.py` resource split. Each moved handler is behavior-preserving if
   the route path/signature is unchanged; the Playwright smoke tests PR #62 added guard these flows.
4. **Tier 2** — incremental Extract Method passes on the remaining long methods, one function per
   commit, tests green after each.

For Tier 1, follow ROADMAP §4's safety checklist: confirm coverage holds ≥ 85% after removing the
legacy modules and their tests (`pytest` + `vitest`), since deleting tested-but-dead code will change
the denominator.
