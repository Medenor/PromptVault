# Plan: Facultative Authentication (`AUTH_ENABLED`)

## Goal
Make authentication optional via the `AUTH_ENABLED` environment variable (default `true`). When set to `false`, the application runs in **anonymous mode**: no login required, all data endpoints are publicly accessible, and auth/admin API routes are unmounted (return 404).

## Key Decisions
- **Env var**: `AUTH_ENABLED`
- **Default**: `true` (backward compatible; existing deployments unchanged)
- **Scope**: Backend config, app bootstrap, auth dependencies, affected routers, main frontend shell, tests
- **Out of scope (for now)**: Secondary frontend pages UX polish beyond the main app shell and backup-management; legacy `app.js`; deployment docs and spec updates

## Implementation Tasks

### 1. Add `auth_enabled` to config
- **File**: `src/config/auth_config.py`
- Add `auth_enabled: bool = Field(default=True, description="Enable authentication subsystem. Set to false for anonymous/local mode.")`
- Pydantic handles `AUTH_ENABLED` env var automatically (case-insensitive). Invalid values raise `ValidationError` at startup.

### 2. Conditional router mounting + startup warning + home route
- **File**: `src/web/app.py`
- Wrap `auth_router` and `admin_router` inclusion in `if auth_settings.auth_enabled: ...`
- If disabled, log `WARNING`: `AUTH_ENABLED=false — Authentication is DISABLED. All endpoints are publicly accessible. Do NOT use this mode in a multi-user or network-exposed deployment.`
- In `home()`: skip the 302 redirect to `/auth/login` when `auth_settings.auth_enabled` is `False`; pass `auth_enabled` into the template context.

### 3. Bypass auth dependencies
- **File**: `src/web/dependencies/auth.py`
- Add factory helpers that return `None`-returning deps in anonymous mode:
  - `get_current_user_or_none`
  - `get_editor_or_admin_or_bypass`
  - `get_admin_or_bypass`

### 4. Update routers to use bypass deps
- **Files**: `src/web/routers/prompts.py`, `src/web/routers/tag_category.py`, `src/web/routers/pages.py`, `src/web/routers/scheduler.py`
- Replace `get_current_active_user` with `get_current_user_or_none` on endpoints that must remain open.
- Replace `get_admin_user` with `get_admin_or_bypass` on admin-only endpoints.
- Guard all `user.id`, `user.username`, and ownership checks with `if user:` / `user.id if user else None` / `"anonymous"` fallbacks.
- In `pages.py`, pass `auth_enabled = auth_settings.auth_enabled` into every `TemplateResponse` context.

### 5. Frontend anonymous-mode support
- **File**: `src/web/templates/index.html`
  - Inject `<script>window.__AUTH_ENABLED__ = {{ 'true' if auth_enabled else 'false' }};</script>` before app scripts.
- **File**: `src/web/static/ts/app.ts`
  - In `checkAdminAccess()`: if `window.__AUTH_ENABLED__ === false`, show app, hide auth-only buttons (`profile-btn`, `logout-btn`, `logout-btn-mobile`, profile links), and return early.
  - In `logout()`: if anonymous, skip the `/api/auth/logout` call and redirect to `/` instead of `/auth/login`.

### 6. Fix backup-management redirect in anonymous mode
- **File**: `src/web/static/ts/backup-management.ts`
  - In `checkAdminAccess()`: if `window.__AUTH_ENABLED__ === false`, return early without redirecting.

### 7. Update `.env.example`
- **File**: `.env.example`
- Add `AUTH_ENABLED=true` with a warning comment under Authentication & Security Configuration.

### 8. Tests
- **Update** `tests/test_history_navigation_auth.py`: skip classes/methods that assume mandatory auth when `AUTH_ENABLED=false`.
- **Add** `tests/test_auth_optional.py` covering:
  - Startup warning logged at `WARNING` when `AUTH_ENABLED=false`
  - `GET /api/prompts` returns `200` without credentials
  - `POST /api/auth/login` returns `404` when disabled
  - `GET /api/admin/users` returns `404` when disabled
  - `AUTH_ENABLED=invalid` raises `ValidationError` and prevents startup
  - Default value is `true`

## Risks & Mitigations
- **Operator accidentally disables auth in production**: Default is `true`; startup warning is loud.
- **`user=None` causes `AttributeError`**: Audit all `user.*` accesses in affected routers (prompts, tag_category, pages, scheduler).
- **Existing tests break**: Tests that assert unauthenticated redirects must be guarded with `pytest.skip` when `AUTH_ENABLED=false`.
- **Frontend redirect loops in secondary pages**: Fix `backup-management.ts` and `logout()` as specified above.

## Validation
1. Run full test suite with default settings (`AUTH_ENABLED=true`) — must pass unchanged.
2. Run new `tests/test_auth_optional.py` with `AUTH_ENABLED=false` — must pass.
3. Manual smoke test: start app with `AUTH_ENABLED=false`, verify `/` loads, create/edit prompts, verify `/api/auth/*` and `/api/admin/*` return 404.
