# Quickstart: Validate the Developer Workflow Makefile

**Feature**: `002-makefile-dev-workflows` | **Date**: 2026-07-03

This is a runnable validation guide. Run these scenarios after implementation to
prove the feature works end-to-end. Each scenario is mapped to the spec's
acceptance criteria and uses **only** the documented `make` targets.

For the exact command behavior and exit codes, see
[contracts/make-targets.md](./contracts/make-targets.md). For the target graph,
see [data-model.md](./data-model.md).

---

## Prerequisites

- POSIX system with `make` (macOS / Linux, or WSL / Git Bash on Windows).
- Python **3.14+** (`python3 --version`) — the constitution's mandated runtime.
- Node **20+** and `npm` (`node --version`).
- Docker with the **Compose v2** plugin (`docker compose version`) — only for
  the build-image scenario.

> If a prerequisite is missing, `make` targets must fail fast with a clear,
> named message (covers the "Missing runtime" edge case).

---

## Scenario 1 — Discover commands (US1 scenario 3, FR-007)

```sh
make            # same as `make help`
```

**Expected**: a human-readable list of every target (`help`, `install`,
`install-backend`, `install-frontend`, `dev`, `test`, `test-backend`,
`test-frontend`, `lint`, `lint-backend`, `lint-frontend`, `lint-fix`, `build`,
`build-frontend`, `build-image`) each with a one-line description. Exit code 0.

---

## Scenario 2 — Install everything (US1 scenario 1, FR-001)

```sh
make install
```

**Expected**:

- A `.venv` directory created with Python 3.14+ (`./.venv/bin/python --version`
  prints ≥ 3.14).
- Backend deps installed via `pip install -e ".[test]"`; `black` available.
- Frontend deps installed via `npm ci`; `node_modules/` present.
- Exit code 0. Re-running is safe and idempotent.

**Granular check**: `make install-backend` then `make install-frontend` produce
the same end state (FR-009).

---

## Scenario 3 — Run the dev environment (US1 scenario 2, FR-002, FR-010)

```sh
make dev
```

**Expected**:

- Backend available at `http://localhost:8003` (or `$PORT`).
- Vite dev server at `http://localhost:5173` proxying `/api`, `/auth`, and
  `/static/locales` to the backend — the app loads in a browser.
- Press **Ctrl-C**: both processes terminate. Verify no orphan remains:

```sh
# should print nothing (no uvicorn / vite left behind)
pgrep -fl "run_web.py|vite" || echo "clean"
```

---

## Scenario 4 — Run the full test suite (US2, FR-003, FR-004)

```sh
make test
```

**Expected**:

- Backend `pytest` runs with coverage; the `--cov-fail-under=85` gate
  (from `pytest.ini`) is reported.
- Frontend `vitest` runs with coverage; `vitest.config.ts` thresholds are
  reported.
- Exit 0 only if both pass.

**Failure simulation (independent test for US2 scenario 2)**: temporarily lower
coverage or break a test, run `make test`, and confirm the summary names the
failing stack and the command exits non-zero. Then revert.

**Granular check**: `make test-backend` and `make test-frontend` run only their
own stack (FR-009).

---

## Scenario 5 — Lint across both stacks (US3, FR-005)

```sh
make lint
```

**Expected**: backend (`black --check` + `pytest --collect-only`) and frontend
(`eslint` + `tsc --noEmit` + `prettier --check`) all pass; clean tree is left
unmodified. Exit 0.

**Auto-fix check (US3 scenario 3)**:

```sh
make lint-fix
```

**Expected**: Black, `eslint --fix`, and `prettier --write` correct
auto-fixable issues in place; review the diff afterward.

---

## Scenario 6 — Production build (US4, FR-006)

```sh
make build
```

**Expected**:

- `dist/static/` contains compiled assets (manifest + hashed JS/CSS).
- The production `web` image is built (`docker compose build web`).

**Smoke test the image (US4 scenario 2)**:

```sh
docker compose up -d web   # start the built image
curl -sf http://localhost:8001/api/health   # expect a healthy response
docker compose down
```

**Granular check**: `make build-frontend` and `make build-image` each produce
only their own artifact (FR-009).

---

## Edge-case spot checks

| Edge case       | How to validate                                                                                              |
| --------------- | ------------------------------------------------------------------------------------------------------------ |
| Missing runtime | Unset/disable `python3` or `node` in a subshell; run a target; expect a **named** fail-fast message.         |
| Missing deps    | Delete `.venv`/`node_modules` (in a throwaway clone); run `make dev`; expect guidance to run `make install`. |
| Port in use     | Start something on 8003, then `make dev`; expect a clear port-conflict message.                              |
| Clean interrupt | Scenario 3's `pgrep` check.                                                                                  |

---

## Done criteria for this feature

- [ ] All six scenarios pass using only `make` targets.
- [ ] No existing documented command/script/deployment path is altered or broken.
- [ ] `docs/DEVELOPMENT.md` documents prerequisites, supported environments, and
      the failure modes above (FR-012).
