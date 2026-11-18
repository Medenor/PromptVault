# Developer Workflow Guide

This page documents the `Makefile` at the repository root, which provides a
unified command surface for common development tasks.

---

## Prerequisites

| Tool               | Version                                 | Check                    |
| ------------------ | --------------------------------------- | ------------------------ |
| **GNU/BSD Make**   | 3.81+                                   | `make --version`         |
| **Python**         | 3.14+                                   | `python3 --version`      |
| **Node.js**        | 20+                                     | `node --version`         |
| **npm**            | 10+                                     | `npm --version`          |
| **Docker Compose** | v2 plugin (optional, for `build-image`) | `docker compose version` |

Native Windows is **not supported** directly. Use WSL or Git Bash.

---

## Quick Reference

```sh
make              # show all targets (same as `make help`)
make install      # install all dependencies (backend + frontend)
make dev          # start backend + frontend dev servers
make test         # run full test suite with coverage gates
make lint         # check formatting, lint, and types across both stacks
make lint-fix     # auto-fix formatting and lint issues
make build        # produce production artifacts (frontend + Docker image)
```

---

## All Targets

### Discovery & Guards

| Target          | Description                                          |
| --------------- | ---------------------------------------------------- |
| `help`          | List all targets with descriptions (default action). |
| `check-runtime` | Verify `python3` (>= 3.14) and `node` are available. |
| `check-deps`    | Verify `.venv/` and `node_modules/` exist.           |

### Installation (US1)

| Target             | Description                                                             |
| ------------------ | ----------------------------------------------------------------------- |
| `install`          | Install all dependencies (backend first, then frontend).                |
| `install-backend`  | Create `.venv/` (Python 3.14+) if needed, install project deps + Black. |
| `install-frontend` | Run `npm ci` for reproducible frontend deps.                            |

### Development Server (US1)

| Target | Description                                                                                    |
| ------ | ---------------------------------------------------------------------------------------------- |
| `dev`  | Start backend (port 7870) + Vite frontend (port 7873) concurrently. Ctrl-C stops both cleanly. |

Override ports: `BACKEND_PORT=9000 make dev` or `FRONTEND_PORT=3000 make dev`.

**Access the app at `http://localhost:7870/`** — the Vite server at port 7873 is an asset dev server only (hot-reload for static files), not the application itself.

### Testing (US2)

| Target          | Description                                                           |
| --------------- | --------------------------------------------------------------------- |
| `test`          | Run backend + frontend test suites. Fails if either fails.            |
| `test-backend`  | Run `python3 -m pytest` (coverage gate: 85% via `pytest.ini`).        |
| `test-frontend` | Run `npm run test:unit:coverage` (thresholds via `vitest.config.ts`). |

### Linting & Formatting (US3)

| Target          | Description                                                                                         |
| --------------- | --------------------------------------------------------------------------------------------------- |
| `lint`          | Check backend (Black + ruff + import sanity) and frontend (ESLint + tsc + Prettier). Read-only.     |
| `lint-backend`  | `black --check src tests` + `ruff check src tests` + `pytest --collect-only -q`.                    |
| `lint-frontend` | `npm run lint` + `npm run typecheck` + `npm run format:check`.                                      |
| `lint-fix`      | Auto-fix: `black src tests` + `ruff check --fix src tests` + `npm run lint:fix` + `npm run format`. |

### Production Build (US4)

| Target           | Description                                              |
| ---------------- | -------------------------------------------------------- |
| `build`          | Build frontend assets + Docker production image.         |
| `build-frontend` | `npm run build` (compiled assets in `dist/static/`).     |
| `build-image`    | `docker compose build web` (production container image). |

---

## Documentation Portal

`docs-portal/` is a standalone Docusaurus 3.x site (installation, configuration, user guide, troubleshooting, release notes) published in English, French, German, and Spanish. It has its own `package.json`/lockfile — fully isolated from the root `npm install`/`make install` and from the main app's build/test/lint pipeline.

| Command                                       | Description                                                                                                    |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `make docs`                                   | Install deps and start the docs-portal dev server (`localhost:7876`).                                          |
| `cd docs-portal && npm run docs:build`        | Build the static site (`docs-portal/build/`).                                                                  |
| `cd docs-portal && npm run docs:check-parity` | Verify every non-English locale has the same pages and section structure as English; fails the build on drift. |

**i18n parity**: every English page under `docs-portal/docs/` must have a mirrored translation at the same relative path under `docs-portal/i18n/{fr,de,es}/docusaurus-plugin-content-docs/current/`, with a matching `##`/`###` heading count. A page can opt out via `translation_exempt: true` in its frontmatter. `.github/workflows/docs-portal.yml` (triggered only on `docs-portal/**` changes) runs this check plus a full build on pushes and PRs to `main` that touch that folder. Its `build-and-check` job is deliberately **not** a required status check on `main`: because of the path filter it never reports on other PRs, and a required check that never reports would block every non-docs merge. Look at its result before merging a PR that changes `docs-portal/**`. Only `test-and-lint` (the `CI` workflow) is required.

Set `VITE_DOCS_PORTAL_URL` when building the application to point its Documentation links at a deployed portal. Without it, development links use `http://localhost:7876`.

---

## Writing Alembic Migrations

Migrations are authored and tested against **SQLite** in dev, but run against **PostgreSQL** in production (see [DEPLOYMENT.md](DEPLOYMENT.md)). A migration that only works on one dialect will pass local testing and then break the production upgrade — this happened in `f1a2b3c4d5e6_enhanced_backup_tables` (fixed in v1.10.1). When writing or reviewing a migration:

- **Existence checks**: Use `sa.inspect(conn).get_table_names()` / `.get_columns(table)`. Never query dialect-specific catalogs directly — `sqlite_master` and `PRAGMA table_info(...)` don't exist on PostgreSQL (`UndefinedTable: relation "sqlite_master" does not exist`).
- **Boolean defaults**: Use `sa.true()` / `sa.false()` for `server_default` on Boolean columns. `sa.text("1")` / `sa.text("0")` works on SQLite (booleans are ints there) but PostgreSQL rejects it (`DatatypeMismatch: column "enabled" is of type boolean but default expression is of type integer`).
- **Column changes**: Prefer `op.add_column` / `op.drop_column` (or `op.batch_alter_table` when SQLite needs a table rebuild) over raw `ALTER TABLE ... ADD COLUMN` strings — raw DDL tends to smuggle in dialect-specific types (`DATETIME`, `JSON`, `BOOLEAN ... DEFAULT 0`) that don't parse identically on both engines.
- **Before merging**: Run the migration against a local PostgreSQL container in addition to the default SQLite dev setup — dev-only testing is exactly what let the above bug ship.

---

## Environment Variables

| Variable        | Default | Purpose                  |
| --------------- | ------- | ------------------------ |
| `BACKEND_PORT`  | `7870`  | Backend dev server port. |
| `FRONTEND_PORT` | `7873`  | Vite dev server port.    |

---

## Common Failure Modes

| Symptom                                | Cause                      | Resolution                                            |
| -------------------------------------- | -------------------------- | ----------------------------------------------------- |
| `ERROR: python3 is not installed`      | Missing Python             | Install Python 3.14+                                  |
| `ERROR: Python >= 3.14 is required`    | Wrong Python version       | Upgrade Python                                        |
| `ERROR: node is not installed`         | Missing Node.js            | Install Node.js 20+                                   |
| `ERROR: Virtual environment not found` | Dependencies not installed | Run `make install`                                    |
| `ERROR: node_modules/ not found`       | Dependencies not installed | Run `make install`                                    |
| `WARNING: Port 7870 is already in use` | Port conflict              | Stop other process or `BACKEND_PORT=<port> make dev`  |
| `WARNING: Port 7873 is already in use` | Port conflict              | Stop other process or `FRONTEND_PORT=<port> make dev` |

---

## Design Notes

- **Additive only**: the `Makefile` wraps existing canonical commands without
  modifying any source file, script, or deployment definition.
- **POSIX-portable recipes**: no GNU-only constructs where avoidable.
- **Coverage gates** are delegated to each tool's own config (`pytest.ini`,
  `vitest.config.ts`) — the Makefile does not override them.
