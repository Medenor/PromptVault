# Implementation Plan: Developer Workflow Makefile

**Branch**: `002-makefile-dev-workflows` | **Date**: 2026-07-03 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-makefile-dev-workflows/spec.md`

## Summary

Provide a single `Makefile` at the repository root that wraps the project's
already-approved canonical commands into five core developer workflows
(`install`, `dev`, `test`, `lint`, `build`) plus a self-documenting `help`
target. Each core target has granular backend-only / frontend-only variants
(FR-009). The Makefile is **additive only** (FR-011): it introduces no new
source code and modifies no existing script, configuration, or deployment
definition — it orchestrates the existing toolchain (`python run_web.py`,
`python3 -m pytest`, the `npm` scripts, and `docker compose`).

The `dev` target runs the backend (port 8003) and the Vite frontend dev server
(port 5173) concurrently and tears both down cleanly on interrupt (FR-010). The
`test` target runs both suites and surfaces each stack's configured coverage
gate as a hard failure (FR-004): `pytest.ini`'s `--cov-fail-under=85` for the
backend and `vitest.config.ts` thresholds for the frontend.

## Technical Context

**Language/Version**: GNU Make (POSIX `/bin/sh` recipes) wrapping Python 3.14+
(backend) and Node 20+ / TypeScript 5 (frontend). `make` is a prerequisite
(POSIX systems).

**Primary Dependencies**: GNU Make 3.81+; the project's existing toolchain only
— `uvicorn` (via `run_web.py`), `pytest` + `pytest-cov`, Vite/Vitest, ESLint,
Prettier, `tsc`, and `docker compose` (v2 plugin). No new third-party
dependency is introduced (additive constraint, FR-008/FR-011).

**Storage**: N/A — pure build/dev orchestration. No persistence, schema, or
migration impact.

**Testing**: Validation is manual smoke-testing of targets (see `quickstart.md`)
plus optional `shellcheck` on the Makefile recipes. The suites the Makefile
*runs* (`python3 -m pytest`, `npm run test:unit:coverage`) are not part of this
feature's deliverable.

**Target Platform**: POSIX-compatible systems (macOS / Linux) with `make`
available. Native Windows users require a Unix-like shell (WSL, Git Bash) —
documented as a known limitation (FR-012).

**Project Type**: Build / developer-automation tooling (a `Makefile` plus a
documentation page). No application/library source changes.

**Performance Goals**: `dev` target brings both services up within a few
seconds of the underlying tools; interrupt terminates all spawned processes
within one signal cycle (no orphans). `help` returns instantly.

**Constraints**: Additive only (FR-011); must reuse canonical commands without
duplication or divergence (FR-008); POSIX `make`-portable recipes (no GNU-only
constructs that break BSD `make` where avoidable); default action is `help`
(FR-007).

**Scale/Scope**: One `Makefile` (≈ 12 targets, ≈ 6 recipe variables) plus one
documentation page (`docs/DEVELOPMENT.md`) and a short README pointer.
Estimated effort: small.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Layered Service Architecture** | ✅ PASS | No source layer touched. The Makefile calls the approved entry script and npm scripts; it introduces no web/service/data code and bypasses no layer. |
| **II. Test Coverage Gate (NON-NEGOTIABLE)** | ✅ PASS (strengthens) | `make test` runs `python3 -m pytest`, which enforces `--cov-fail-under=85` (pytest.ini). The frontend gate is enforced by `vitest.config.ts`. The Makefile surfaces each gate as a hard pass/fail — directly serving this principle. See `research.md` for the backend(85)/frontend(configured) discrepancy note. |
| **III. Security-First Authentication** | ✅ PASS | No endpoint, auth, or rate-limiting code is added or changed. The dev server is started via the existing approved script. |
| **IV. TypeScript-Only Frontend** | ✅ PASS | The Makefile does not edit `src/web/static/ts/` or `js/`. It only invokes the existing `npm` scripts (`typecheck`, `lint`, `build`, `test:unit:coverage`). |
| **V. Database-Backed Persistence** | ✅ PASS | No storage, ORM, or migration impact. Pure orchestration. |

**Result**: No violations. No complexity-tracking entries required.

**Post-Design Re-check (after Phase 1)**: The design — a `Makefile` that *only*
invokes existing approved commands plus one additive doc page — touches no
service/data/auth/TS layer and changes no tracked config. All five principles
remain **PASS**. The feature *strengthens* Principle II by making the 85% backend
coverage gate one command away (`make test`). The frontend coverage-gap note
(research.md §4) is a documented follow-up, not a violation introduced by this
feature.

## Project Structure

### Documentation (this feature)

```text
specs/002-makefile-dev-workflows/
├── plan.md              # This file
├── research.md          # Phase 0 — resolves tooling/cleanup/venv/coverage questions
├── data-model.md        # Phase 1 — Make target model (targets, variables, prerequisites)
├── contracts/
│   └── make-targets.md  # Phase 1 — public CLI contract (commands, variants, exit codes)
└── quickstart.md        # Phase 1 — runnable validation guide
```

### Source Code (repository root)

```text
.
├── Makefile                 # NEW — dev workflow targets (additive)
├── docs/
│   └── DEVELOPMENT.md       # NEW — documented commands, prerequisites, failure modes (FR-012)
├── README.md                # EDITED — one-line pointer to `make help` / DEVELOPMENT.md
└── (all existing files unchanged)
```

**Structure Decision**: The feature is a single additive build file at the repo
root (standard Make convention, discoverable by `make help` as the default
target) plus a dedicated documentation page under `docs/` to satisfy FR-012
without bloating the README. No `src/`, `backend/`, or `frontend/` tree changes
are in scope — the existing `src/` (Python) and `src/web/static/` (TypeScript)
layouts are merely *invoked* by the recipes.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

None — no constitution violations.
