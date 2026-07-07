# Data Model: Developer Workflow Makefile

**Feature**: `002-makefile-dev-workflows` | **Date**: 2026-07-03

This feature introduces no persistent data (no database, no schema, no files
emitted at rest — see `plan.md` "Storage: N/A"). Its "model" is the **Make
target graph**: the variables, targets, prerequisites, and recipes that form
the developer-facing surface area. This document enumerates them so
`contracts/make-targets.md` can reference them without duplication.

---

## Variables (recipe-time constants)

| Variable            | Value                               | Purpose                                                                   |
| ------------------- | ----------------------------------- | ------------------------------------------------------------------------- |
| `PYTHON`            | `.venv/bin/python`                  | Pinned project interpreter (created on `install`).                        |
| `PIP`               | `.venv/bin/pip`                     | Installer for the project interpreter.                                    |
| `BACKEND_PORT`      | `8003` (overridable via env `PORT`) | Backend dev port; matches `run_web.py` default and the Vite proxy target. |
| `FRONTEND_PORT`     | `5173`                              | Vite dev-server port; matches `vite.config.ts`.                           |
| `PYTEST`            | `python3 -m pytest`                 | Canonical, AGENTS-mandated test runner (never bare `pytest`).             |
| `BACKEND_TEST_CMD`  | `$(PYTEST)`                         | Backend test command; `--cov-fail-under=85` comes from `pytest.ini`.      |
| `FRONTEND_TEST_CMD` | `npm run test:unit:coverage`        | Frontend test + coverage command; thresholds from `vitest.config.ts`.     |
| `COMPOSE`           | `docker compose`                    | Docker Compose v2 plugin invocation.                                      |
| `VENV_DIR`          | `.venv`                             | Standardized virtualenv directory name.                                   |

**Validation rule**: `PYTHON`/`PIP` must resolve to a Python 3.14+ interpreter
(constitution §"Python runtime: 3.14+ minimum"). `install` creates it; other
Python targets fail fast with a human-readable message if `.venv` is absent.

---

## Targets (the public CLI surface)

Legend: **Phony** = always-run (no file artifact). **Prereqs** = dependencies.

### Core aggregate targets

| Target    | Phony | Prereqs                            | Recipe intent                                                          |
| --------- | ----- | ---------------------------------- | ---------------------------------------------------------------------- |
| `help`    | yes   | —                                  | Default goal. Prints every target + one-line description.              |
| `install` | yes   | `install-backend install-frontend` | Installs all deps in order: backend first, then frontend.              |
| `dev`     | yes   | `check-deps`                       | Starts backend + frontend concurrently; `trap` cleans up on interrupt. |
| `test`    | yes   | `test-backend test-frontend`       | Runs both suites + coverage; fails if either fails.                    |
| `lint`    | yes   | `lint-backend lint-frontend`       | Format-check + lint + typecheck across both stacks.                    |
| `build`   | yes   | `build-frontend build-image`       | Produces compiled frontend assets + production image.                  |

### Granular (single-stack) variants — required by FR-009

| Target             | Stack    | Recipe (canonical command)                                                    |
| ------------------ | -------- | ----------------------------------------------------------------------------- |
| `install-backend`  | backend  | Create `.venv` if missing → `pip install -e ".[test]"` → `pip install black`. |
| `install-frontend` | frontend | `npm ci`.                                                                     |
| `test-backend`     | backend  | `$(BACKEND_TEST_CMD)` (enforces 85% via `pytest.ini`).                        |
| `test-frontend`    | frontend | `$(FRONTEND_TEST_CMD)` (enforces `vitest.config.ts` thresholds).              |
| `lint-backend`     | backend  | `black --check src tests` + `$(PYTEST) --collect-only -q`.                    |
| `lint-frontend`    | frontend | `npm run lint` + `npm run typecheck` + `npm run format:check`.                |
| `build-frontend`   | frontend | `npm run build` → `dist/static/`.                                             |
| `build-image`      | infra    | `$(COMPOSE) build web`.                                                       |

### Auto-fix variant — FR (US3, scenario 3)

| Target     | Phony | Recipe                                                                |
| ---------- | ----- | --------------------------------------------------------------------- |
| `lint-fix` | yes   | `black src tests` (in place) + `npm run lint:fix` + `npm run format`. |

### Prerequisite / safety guard targets

| Target          | Phony | Behavior                                                                                                                                |
| --------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `check-deps`    | yes   | Verifies `.venv` and `node_modules` exist; else instructs to run `make install`. Used as `dev`/`test`/`lint`/`build` precondition hook. |
| `check-runtime` | yes   | Verifies `python3` (≥3.14) and `node` exist; fail-fast message otherwise.                                                               |

> **Note on `check-deps`**: it is invoked _inside_ the recipe of `dev` (not as a
> make prerequisite) so its failure message is printed in context. Targets like
> `test`/`lint`/`build` reference the corresponding already-installed toolchain;
> the canonical commands themselves already fail loudly on missing deps, so the
> explicit guard is light-touch (presence checks only).

---

## State transitions

The only meaningful state machine is the venv/node_modules provisioning:

```
[bare clone]
   │ make install
   ▼
[.venv created (Py3.14+) ─ deps installed ─ node_modules present]
   │ make dev | test | lint | build
   ▼
[dev environment running] / [artifacts produced]
```

- **Re-entrant**: `make install` is idempotent (venv created only if missing;
  `pip install -e .` and `npm ci` are safe to re-run).
- **No destructive transitions**: no target deletes state (additive-only,
  FR-011). Cleanup of orphaned _processes_ (not files) occurs in the `dev`
  trap handler.

---

## Relationships

```
help  ◄── default goal (.DEFAULT_GOAL)
install ─┬─ install-backend
         └─ install-frontend
dev ─────── check-deps (runtime guard)
test ─┬─ test-backend
      └─ test-frontend
lint ─┬─ lint-backend
      └─ lint-frontend
build ┬─ build-frontend
      └─ build-image
lint-fix (standalone)
```

All aggregate targets are `PHONY` (declared in `.PHONY:`), so they always run
and never collide with any real file in the repository.
