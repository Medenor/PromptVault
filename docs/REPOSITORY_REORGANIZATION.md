# PromptVault Repository Restructuring - Current-State Baseline and Migration Plan

Last verified against repository contents: 2026-01-21

## Executive Summary

This document updates the reorganization plan to reflect the **current, verified** structure of PromptVault. The repository is presently organized under `src/` with a production FastAPI app, Vite-built frontend, and database-backed services. The goal of this plan is to migrate to an `app/` layout **without losing parity** with the existing tooling, deployment, and docs.

This version replaces outdated assumptions with concrete, repo-specific details so the migration steps map cleanly to today’s structure.

---

## Current Repository State (Verified)

### Top-Level Layout

- `src/` - primary application code
- `tests/` - pytest + Vitest test suites
- `docs/` - documentation
- `scripts/` - operational scripts
- `alembic/` - DB migrations
- `data/` - SQLite DB, backups, logs
- `dist/` - Vite build output (static assets)
- `assets/` - static assets
- `run_web.py` - app entrypoint

### Application Code Structure

`src/` contains:

- `src/config/` - app and auth configuration
- `src/db/` - SQLAlchemy models, repositories, session management
- `src/scheduler/` - scheduled cleanup jobs
- `src/services/` - business logic (DB-backed + legacy)
- `src/utils/` - shared utilities (e.g., diff utils)
- `src/web/` - FastAPI app, routers, templates, static assets

`src/web/` contains:

- `app.py` - FastAPI app factory and lifecycle wiring
- `routers/`, `dependencies/`, `middleware/`, `validators/`, `monitoring/`, `models/`, `utils/`
- `templates/` - Jinja templates
- `static/` - frontend assets
  - `static/ts/` - TypeScript (active)
  - `static/js/` - legacy JS (read-only)
  - `static/css/` - Tailwind CSS v4 (utilities + globals)
  - `static/locales/` - i18n files

### Current Tooling & Build Paths

- **Python package discovery:** `pyproject.toml` uses `include = ["src*"]`
- **Coverage:** `pyproject.toml` and `.coveragerc` use `source = src`
- **Pytest:** `pytest.ini` uses `--cov=src` and omits legacy services by path
- **Alembic:** `alembic/env.py` imports from `src.db.*`
- **Entrypoint:** `run_web.py` imports `src.web.app`
- **Vite:** `vite.config.ts` uses root `src/web/static` and aliases pointing to `src/web/static/ts`
- **TypeScript:** `tsconfig.json` paths target `src/web/static/ts`
- **Vitest:** `vitest.config.ts` targets `src/web/static/ts`
- **ESLint:** `eslint.config.js` ignores `src/web/static/js/**`
- **Dockerfile:** copies `src/web/static/`, `src/web/templates/`, then `src/`
- **Docker Compose:** `PYTHONPATH=/app`, mounts `./data` and `./assets`, runs `run_web.py`

---

## Migration Target (Proposed)

**Target root:** `app/` replacing `src/`

Proposed target tree (mirror of current structure):

```
app/
  config/
  db/
  scheduler/
  services/
  utils/
  web/
    dependencies/
    middleware/
    models/
    monitoring/
    routers/
    static/
      css/
      js/
      locales/
      ts/
    templates/
    utils/
    validators/
```

---

## Migration Plan (Updated for Current Repo)

### Phase 1: Pre-Migration Snapshot

- [ ] **Verify Git state**
  - `git status`, `git diff --stat`, `git log --oneline -10`
- [ ] **Create safety branch**
  - `git checkout -b backup-pre-reorg`
- [ ] **Capture all `src` references (code + configs + docs)**
  - `rg -n "from src|import src|src/" pyproject.toml pytest.ini .coveragerc Dockerfile docker-compose.yml run_web.py alembic/env.py docs -g"*.md"`

### Phase 2: Create Target Structure

- [ ] **Create `app/` tree matching `src/`**
  - Include all current subfolders: `config/`, `db/`, `scheduler/`, `services/`, `utils/`, `web/`
  - Ensure `app/web/static/{ts,js,css,locales}` and `app/web/templates/` exist

### Phase 3: Code Migration (File Moves)

- [ ] **Move or copy `src/` into `app/`**
  - Maintain directory structure and `__init__.py` files
  - Do not move `dist/` (build output remains at repo root)
  - Keep `scripts/`, `tests/`, `docs/`, `alembic/` at top-level

### Phase 4: Update Python Imports and Entrypoints

- [ ] **Update imports from `src.*` to `app.*`**
  - Includes `alembic/env.py`, `run_web.py`, and all `src/**.py`
- [ ] **Update runtime entrypoint**
  - `run_web.py` should import `app.web.app`
  - Update uvicorn target string to `app.web.app:app`

### Phase 5: Update Tooling and Build Configs

**Python / Coverage**
- [ ] `pyproject.toml` `include = ["app*"]`
- [ ] `.coveragerc` `source = app`
- [ ] `pytest.ini` use `--cov=app`

**Vite / TypeScript / Vitest**
- [ ] `vite.config.ts` update:
  - `root: 'app/web/static'`
  - alias paths to `app/web/static/ts`
  - update `rollupOptions.input` entries
- [ ] `tsconfig.json` update paths and includes to `app/web/static/ts`
- [ ] `vitest.config.ts` update test include and alias paths
- [ ] `eslint.config.js` ignore `app/web/static/js/**`

**Docker**
- [ ] Update `Dockerfile` copy paths from `src/` to `app/`
  - `COPY app/web/static/ ./app/web/static/`
  - `COPY app/web/templates/ ./app/web/templates/`
  - `COPY app/ ./app/`
- [ ] Validate `docker-compose.yml` `PYTHONPATH` and volume expectations still match

### Phase 6: Docs and Scripts

- [ ] Update docs that reference `src/` paths:
  - `docs/DEPLOYMENT.md`
  - `docs/MIGRATION_GUIDE.md`
  - `docs/AUTH_DEPENDENCIES.md`
  - `docs/CHANGELOG.md` (path references in examples)
- [ ] Update any `scripts/` imports referencing `src.*`

### Phase 7: Vite Manifest + Static Assets

- [ ] Verify `app/web/utils/manifest.py` path assumptions
  - It currently resolves `dist/static/.vite/manifest.json` relative to file depth
  - Update path depth if directory nesting changes

### Phase 8: Validation

- [ ] `python run_web.py` (dev server)
- [ ] `python3 -m pytest`
- [ ] `npm run build`
- [ ] `npm run test:unit`
- [ ] `docker-compose up --build` (optional)

---

## Migration Risks (Realistic)

Low to moderate risk if done systematically, with the main risk coming from:

- Path-specific tooling (Vite + TS config paths)
- Alembic imports
- Dockerfile copy paths
- Docs and scripts referencing `src`

---

## Notes

This plan intentionally reflects **current reality** before proposing changes. If any new directories or tooling are added, update the “Current Repository State” section before proceeding with the migration.
