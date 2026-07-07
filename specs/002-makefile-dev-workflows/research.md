# Research: Developer Workflow Makefile

**Feature**: `002-makefile-dev-workflows` | **Date**: 2026-07-03

This document resolves every technical unknown surfaced in the Technical Context
of [plan.md](./plan.md). Findings are based on direct inspection of the
repository's canonical commands, configurations, and runtimes.

---

## 1. Running backend + frontend concurrently with clean shutdown (FR-002, FR-010)

**Decision**: Implement a single shared-recipe shell fragment that launches both
processes in the background and uses a `trap` on `INT TERM EXIT` to kill the
whole process group, then `wait`s. Both the backend (`python run_web.py`,
port 8003) and the frontend (`npm run dev`, port 5173) are started under one
recipe.

**Rationale**: Pure POSIX `sh` needs no new dependency, satisfying the
additive-only constraint (FR-011) and the "reuse canonical commands" rule
(FR-008). The `trap … kill … wait` idiom is the standard, portable way to
guarantee no orphaned server/watcher survives a Ctrl-C: the trap fires on
interrupt and kills the process group, and `wait` returns the failure so make
exits non-zero appropriately.

**Alternatives considered**:

- **`concurrently` / `npm-run-all` (npm tooling)** — rejected: introduces a new
  dev dependency, violating the additive/zero-new-deps intent.
- **`honcho` / `foreman` with a Procfile** — rejected: adds a Python dev
  dependency and a new file format for no gain over a `trap`.
- **GNU Make `--jobserver` with two `&` recipes** — rejected: harder to guarantee
  joint cleanup; the explicit `trap` is clearer and portable.

**Port-conflict handling**: Before starting, the recipe probes whether ports
8003/5173 are already bound (using a best-effort `lsof`/`nc` check guarded by
`command -v`) and prints a human-readable message directing the contributor to
free the port or set `PORT` (backend) — satisfying the "Port already in use"
edge case. The probe is advisory (non-fatal if the detection tool is absent) so
it never breaks startup on a minimal system.

---

## 2. Python virtualenv handling (FR-001)

**Decision**: Standardize on a **`.venv`** directory created with the project's
current interpreter (Python 3.14+). The `install` target creates `.venv` only if
absent, then runs `pip install -e ".[test]"` (editable install + test extras,
matching `docs/TESTING.md` and the now-removed `requirements.txt` workflow).
Subsequent Python recipes invoke `.venv/bin/python` (or `.venv/bin/activate`)
so the correct, isolated interpreter is always used.

**Rationale**: `docs/TESTING.md`, `docs/DEPLOYMENT.md`, and
`docs/TROUBLESHOOTING.md` all document `pip install -e .[test]`; there is no
`requirements.txt` (removed per `docs/CHANGELOG.md`). The editable install is
the single approved backend dependency path. Pinning the interpreter via
`.venv/bin/python` removes ambiguity between the two pre-existing virtualenvs
in this checkout (see "Current state" below).

**Current state observed**: The checkout contains both a `.venv` (Python 3.11)
and a `venv` (Python 3.14). The constitution mandates Python 3.14+, so the
**3.11 `.venv` is non-compliant**. The Makefile will recreate `.venv` against
the system Python 3.14 on first `make install`, correcting this silently.

**Alternatives considered**:

- **Reuse `venv/`** — rejected: `.venv` is the broader community/`python -m venv`
  default and the one covered by the in-repo `.gitignore` pattern.
- **Detect and use whichever venv exists** — rejected: too magical; a single
  deterministic name is easier to document and reason about (FR-012).
- **Skip venv, install globally** — rejected: unsafe and not reproducible.

---

## 3. Backend formatting / lint tooling (FR-005)

**Decision**: The Makefile invokes **Black** as the canonical Python formatter
(per the constitution's "Code style: Black formatter (Python)" and
`AGENTS.md`'s "Format Code: Use black code formatter"). Because Black is not
currently declared in `pyproject.toml`, the `install` target additionally runs
`pip install black` into the project venv (a single additive dev-tool install
that does not alter any existing source or config). The `lint` target then runs
`black --check` (fail on diff) plus `python3 -m pytest --collect-only -q` as a
fast import/syntax sanity check; the `lint-fix` variant runs `black` in place.

**Rationale**: The constitution names Black explicitly, so wrapping it keeps
the Makefile aligned with project standards rather than inventing a new lint
surface. Adding Black to the venv (not to `pyproject.toml`) avoids changing a
tracked config file while still making the formatter available. `pytest
--collect-only` is a zero-cost import check that catches broken imports without
running the suite.

**Alternatives considered**:

- **Add Black to `pyproject.toml [test]`/`[dev]`** — preferred long-term, but it
  edits a tracked dependency manifest; deferred to keep this feature strictly
  additive. Flagged as a recommended follow-up.
- **`ruff`/`flake8`/`mypy`** — rejected for now: none are declared as the
  project standard, and introducing a new analyzer widens scope. Black alone
  matches the documented canonical tool.
- **Omit backend formatting entirely** — rejected: contradicts the
  "single lint command across both stacks" requirement (FR-005).

> **NEEDS CLARIFICATION (resolved):** None outstanding. The approach is
> self-contained and additive.

---

## 4. Coverage gate parity (FR-004)

**Decision**: `make test` enforces coverage by delegating to **each stack's own
configured threshold**:

- Backend: `python3 -m pytest` — `pytest.ini` already sets
  `--cov-fail-under=85`, exactly the constitution's non-negotiable floor. ✅
- Frontend: `npm run test:unit:coverage` — `vitest.config.ts` sets thresholds
  (lines 70 / branches 60 / functions 70 / statements 70) and fails the run if
  violated.

The Makefile does **not** inject or override either threshold, because doing so
for the frontend would require editing `vitest.config.ts` (a tracked config —
violates additive-only FR-011). The aggregate `test` target fails overall if
either suite fails.

**Documented discrepancy**: The constitution states frontend ≥ 85%, but the
_configured_ Vitest gate is lower (70/60/70/70). The Makefile faithfully
enforces whatever each tool's config mandates and surfaces a clear per-suite
pass/fail summary. **Aligning `vitest.config.ts` to 85% is recommended as a
separate follow-up task** (out of scope here — it is a config change, not a
workflow change).

**Alternatives considered**:

- **Hardcode `--cov-fail-under=85` in the Makefile for both** — rejected:
  impossible for Vitest without a plugin/flag it doesn't expose, and overriding
  pytest's value would duplicate/diverge from `pytest.ini`.
- **Modify `vitest.config.ts` to 85% inside this feature** — rejected: violates
  FR-011 (additive only) and changes a tracked config.

---

## 5. Production build artifacts (FR-006)

**Decision**: `make build` runs `npm run build` (compiles TypeScript + Vite →
`dist/static/`) and then `docker compose build` (builds the `web` image from the
root `Dockerfile`, consistent with the documented `docker-compose up --build`
production path). Granular variants: `build-frontend` (`npm run build`) and
`build-image` (`docker compose build web`).

**Rationale**: The Dockerfile is a two-stage build that itself runs
`npm run build` internally; producing the host-side `dist/static` first lets a
contributor inspect the compiled assets, and `docker compose build` reproduces
the exact production image. Docker Compose **v2** (`docker compose` plugin) is
present (confirmed: Compose v5.1.4) and is the modern invocation; the legacy
`docker-compose` (hyphen, v1) is not assumed.

**Alternatives considered**:

- **`docker compose up --build`** — that's a _run_ (server), not a _build_;
  reserved for deploy. `build` produces artifacts only, per the spec wording
  ("produces … artifacts").
- **`docker build .`** (raw) — rejected: bypasses the compose service
  definition (env, healthcheck) and the documented production path (FR-008).

---

## 6. Frontend install determinism (FR-001)

**Decision**: `install-frontend` uses **`npm ci`** (a `package-lock.json` is
committed and the Dockerfile already uses `npm ci --ignore-scripts`).

**Rationale**: `npm ci` is reproducible and faster than `npm install` for CI
and onboarding, and matches the production Docker build.

**Alternatives considered**:

- **`npm install`** — rejected unless no lockfile; mutates the lockfile and is
  less reproducible.

---

## 7. POSIX `make` portability & default action (FR-007, edge cases)

**Decision**: The first real target in the file is `help`, and `.DEFAULT_GOAL`
is set to `help` so bare `make` prints usage. Recipes use `/bin/sh` idioms;
GNU-isms are avoided where a portable form exists. Prerequisite checks
(`command -v python3`, `command -v node`, presence of `.venv`, `node_modules`)
emit clear human-readable messages and exit non-zero on missing prerequisites
("Missing runtime" / "Dependencies not yet installed" edge cases).

**Rationale**: Failing fast with an actionable message is explicitly required
by the spec's edge cases. `.DEFAULT_GOAL := help` is universally supported by
modern GNU/BSD make.

**Non-POSIX limitation**: Native Windows without a Unix-like shell is
unsupported and documented in `docs/DEVELOPMENT.md` (recommended workaround:
WSL / Git Bash), per the "Non-POSIX environment" edge case.

**Alternatives considered**:

- **`just` / `task` (modern runners)** — rejected: `make` is what the spec asks
  for and is preinstalled on macOS/Linux.

---

## Summary of resolutions

| Unknown                         | Resolution                                                                   |
| ------------------------------- | ---------------------------------------------------------------------------- |
| Concurrent dev + clean shutdown | `trap INT/TERM/EXIT` + `kill` group + `wait` (pure POSIX)                    |
| Python venv name & install      | `.venv` via `pip install -e ".[test]"`, interpreter 3.14+                    |
| Backend formatting tool         | Black (installed into venv by `make install`)                                |
| Coverage gate parity            | Delegate to each tool's own config; flag frontend 85% alignment as follow-up |
| Production build artifacts      | `npm run build` + `docker compose build`                                     |
| Frontend install determinism    | `npm ci`                                                                     |
| Portability / default action    | `.DEFAULT_GOAL := help`; `/bin/sh` recipes; documented POSIX-only            |

All NEEDS CLARIFICATION items are resolved. No blocking unknowns remain.
