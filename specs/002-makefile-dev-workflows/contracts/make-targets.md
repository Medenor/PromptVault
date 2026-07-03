# Contract: `make` Targets (Developer CLI)

**Feature**: `002-makefile-dev-workflows` | **Date**: 2026-07-03

This is the **public interface contract** for the Developer Workflow Makefile.
It defines the exact command surface a contributor types, the behavior each
command guarantees, and the exit-code semantics. The Makefile is the
single entry point; it wraps (never replaces) the canonical commands listed in
`research.md`.

Reference for the underlying target graph and variables: [data-model.md](../data-model.md).

---

## Invocation

```sh
make [target]            # bare `make` == `make help` (default goal)
make <target>            # run a specific target
make help                # discover all targets
```

**Environment overrides**:
- `PORT` — override the backend dev port (default `8003`).
- `FRONTEND_PORT` — override the Vite dev port (default `5173`).

---

## Command surface

| Command | Variants | Guarantees |
|---------|----------|------------|
| `make help` | — | Lists every target with a one-line description; default action (FR-007). Exit 0. |
| `make install` | `install-backend`, `install-frontend` | Installs backend deps (`.venv` + `pip install -e ".[test]"` + `black`) **then** frontend deps (`npm ci`) (FR-001). Idempotent. Exit non-zero on failure. |
| `make dev` | — | Starts backend (port `PORT`, default 8003) **and** Vite frontend (port `FRONTEND_PORT`, default 5173) concurrently; on Ctrl-C/SIGTERM both are terminated with no orphan (FR-002, FR-010). Probes for port conflicts and prints guidance. |
| `make test` | `test-backend`, `test-frontend` | Runs `python3 -m pytest` (backend, enforces `--cov-fail-under=85`) **and** `npm run test:unit:coverage` (frontend, enforces `vitest.config.ts` thresholds) (FR-003, FR-004). Fails overall if either fails. |
| `make lint` | `lint-backend`, `lint-frontend` | Backend: `black --check` + `pytest --collect-only`. Frontend: `npm run lint` + `npm run typecheck` + `npm run format:check` (FR-005). Fails on first violation; clean tree is unmodified. |
| `make lint-fix` | — | Auto-fixes formatting + auto-fixable lint issues in place (Black, `eslint --fix`, `prettier --write`) (US3 scenario 3). |
| `make build` | `build-frontend`, `build-image` | Produces `dist/static/` (compiled assets) and builds the production `web` image via `docker compose build` (FR-006, FR-008). |

---

## Exit-code contract

| Outcome | Exit code |
|---------|-----------|
| Success (target completed) | `0` |
| A wrapped canonical command failed (test failure, lint violation, build error) | non-zero (propagated from the failing command) |
| Missing runtime (`python3`/`node` absent or wrong Python version) | non-zero, with a **named, human-readable** error identifying the missing prerequisite |
| Missing dependencies (`.venv` / `node_modules` absent) when running `dev` | non-zero, instructing the contributor to run `make install` first |
| Interrupt (Ctrl-C) during `dev` | exits after terminating all spawned processes (no orphan left) |

The aggregate targets (`test`, `lint`, `build`) are implemented so that a
sub-command failure is **surfaced** (not swallowed): the failing stack is named
in the summary before the non-zero exit, satisfying US2 scenario 2 and US3
scenario 1.

---

## Non-goals (out of contract)

- The Makefile does **not** run the production server (that is
  `docker compose up`, the documented deploy path) — `make build` only produces
  artifacts.
- The Makefile does **not** override or change the coverage threshold of either
  stack; it enforces whatever `pytest.ini` / `vitest.config.ts` mandate (see
  [research.md §4](../research.md)).
- The Makefile does **not** modify any existing file, command, or deployment
  definition (additive only, FR-011).

---

## Supported environments

POSIX-compatible systems with GNU/BSD `make`, Python ≥ 3.14, and Node 20+.
Native Windows requires a Unix-like shell (WSL / Git Bash). See
`docs/DEVELOPMENT.md` for prerequisites and failure-mode handling (FR-012).
