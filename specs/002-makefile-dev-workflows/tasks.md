# Tasks: Developer Workflow Makefile

**Input**: Design documents from `/specs/002-makefile-dev-workflows/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: No automated test tasks. This feature is a build/automation file; validation is manual smoke-testing of `make` targets per `quickstart.md`, plus optional `shellcheck` on recipes. The suites the Makefile *runs* (`python3 -m pytest`, `npm run test:unit:coverage`) are out of scope.

**Organization**: Tasks are grouped by user story to enable independent validation of each story. Because the primary deliverable is a single `Makefile`, most implementation tasks edit the same file and are therefore sequential within a phase; the `[P]` marker is reserved for genuinely independent files (e.g. documentation).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g. US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Build/automation file**: `Makefile` at repository root (NEW, additive — FR-011)
- **Documentation**: `docs/DEVELOPMENT.md` (NEW), `README.md` (EDITED — one-line pointer)
- **Canonical commands referenced (NOT modified)**: `run_web.py`, `package.json`, `pytest.ini`, `vitest.config.ts`, `docker-compose.yml`, `Dockerfile`

## Design References

- Variables, target graph, prerequisites: `data-model.md`
- Public CLI contract (commands, variants, exit codes): `contracts/make-targets.md`
- Resolved decisions (venv, trap cleanup, Black, coverage parity, build): `research.md`
- Runnable validation scenarios: `quickstart.md`
- Constitution: `.specify/memory/constitution.md` (all 5 principles PASS)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the single additive `Makefile` skeleton that all subsequent targets extend.

- [ ] T001 Create `Makefile` at repository root with the file header comment, the recipe-time variables block (`PYTHON`, `PIP`, `VENV_DIR`, `BACKEND_PORT`, `FRONTEND_PORT`, `PYTEST`, `BACKEND_TEST_CMD`, `FRONTEND_TEST_CMD`, `COMPOSE` per `data-model.md`), the `.PHONY:` declaration listing every phony target, and `.DEFAULT_GOAL := help` in `Makefile`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared self-documentation + safety-guard infrastructure that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 Implement the `help` target in `Makefile`: a self-documenting recipe (e.g. `awk`/`sed` over `$(MAKEFILE_LIST)`) that prints every `## `-annotated target with a one-line description, so listing grows automatically as later targets are added (FR-007)
- [ ] T003 Implement the `check-runtime` guard target in `Makefile`: verifies `python3` resolves to ≥ 3.14 and `node` exists via `command -v`, emitting a named, human-readable fail-fast message and exiting non-zero on a missing/wrong prerequisite (edge case: Missing runtime)
- [ ] T004 Implement the `check-deps` guard target in `Makefile`: verifies `.venv` and `node_modules` exist, else prints guidance to run `make install` and exits non-zero (edge case: Dependencies not yet installed)

**Checkpoint**: Foundation ready — `make help` prints usage, and guards fail fast on missing runtime/deps. User story implementation can now begin.

---

## Phase 3: User Story 1 - Fast Onboarding for a New Contributor (Priority: P1) 🎯 MVP

**Goal**: A new contributor goes from a clean clone to a running app (backend + frontend) and can discover all commands, using only `make install`, `make dev`, and `make help`.

**Independent Test**: In a fresh clone, run `make install` then `make dev` and confirm the app loads in a browser; run `make help` and confirm every command is listed (quickstart scenarios 1–3).

### Implementation for User Story 1

- [ ] T005 [US1] Implement the `install-backend` target in `Makefile`: create `.venv` with Python 3.14+ if missing, run `$(PIP) install -e ".[test]"`, then `$(PIP) install black`; idempotent (venv created only if absent) (FR-001)
- [ ] T006 [US1] Implement the `install-frontend` target in `Makefile`: run `npm ci` (reproducible install matching the Docker build) (FR-001)
- [ ] T007 [US1] Implement the aggregate `install` target in `Makefile` depending on `install-backend install-frontend` so backend deps install before frontend (FR-001, FR-008)
- [ ] T008 [US1] Implement the `dev` target in `Makefile`: invoke `check-deps` in-recipe, probe ports `BACKEND_PORT`/`FRONTEND_PORT` for conflicts with an advisory `lsof`/`nc` check (non-fatal if the tool is absent), start `$(PYTHON) run_web.py` and `npm run dev` concurrently in the background, and install a `trap` on `INT TERM EXIT` that kills the process group then `wait`s for a clean, orphan-free shutdown (FR-002, FR-010; edge cases: Port already in use, Interrupted long-running target)
- [ ] T009 [US1] Validate US1 by running quickstart scenarios 1–3 (`make help`, `make install`, `make dev` + Ctrl-C), confirming the app is reachable and `pgrep -fl "run_web.py|vite"` prints nothing after interrupt

**Checkpoint**: US1 fully functional and independently testable — the MVP is shippable.

---

## Phase 4: User Story 2 - Run the Full Test Suite With One Command (Priority: P1)

**Goal**: A developer runs the complete backend + frontend test suites with their configured coverage gates via a single command, with granular per-stack variants.

**Independent Test**: Temporarily drop coverage or break a test, run `make test`, confirm a non-zero exit naming the failing stack; revert and confirm success; confirm `make test-backend`/`make test-frontend` run only their stack (quickstart scenario 4).

### Implementation for User Story 2

- [ ] T010 [US2] Implement the `test-backend` target in `Makefile`: run `$(BACKEND_TEST_CMD)` (i.e. `python3 -m pytest`), delegating the 85% floor to `pytest.ini`'s `--cov-fail-under=85` (FR-003, FR-004)
- [ ] T011 [US2] Implement the `test-frontend` target in `Makefile`: run `$(FRONTEND_TEST_CMD)` (i.e. `npm run test:unit:coverage`), delegating thresholds to `vitest.config.ts` (FR-003, FR-004)
- [ ] T012 [US2] Implement the aggregate `test` target in `Makefile` depending on `test-backend test-frontend`, surfacing a per-suite pass/fail summary and failing overall if either suite fails (FR-003, FR-004, FR-009; edge case: Coverage threshold edge)
- [ ] T013 [US2] Validate US2 by running quickstart scenario 4 (`make test`, plus `make test-backend` and `make test-frontend` granular checks)

**Checkpoint**: US1 AND US2 both work independently.

---

## Phase 5: User Story 3 - Lint and Format Before Committing (Priority: P2)

**Goal**: A developer checks formatting, linting, and type-safety across both stacks with one command (leaving a clean tree unmodified), and can auto-fix issues in place.

**Independent Test**: Introduce a style/type violation, run `make lint`, confirm it fails reporting the offending file/rule; fix via `make lint-fix`; confirm a clean tree passes `make lint` unmodified (quickstart scenario 5).

### Implementation for User Story 3

- [ ] T014 [US3] Implement the `lint-backend` target in `Makefile`: run `black --check src tests` followed by `$(PYTEST) --collect-only -q` (fast import/syntax sanity check) (FR-005)
- [ ] T015 [US3] Implement the `lint-frontend` target in `Makefile`: run `npm run lint`, `npm run typecheck`, and `npm run format:check` (FR-005)
- [ ] T016 [US3] Implement the aggregate `lint` target in `Makefile` depending on `lint-backend lint-frontend`; it must not modify files on a clean tree and must fail on the first violation (FR-005, FR-009)
- [ ] T017 [US3] Implement the `lint-fix` target in `Makefile`: run `black src tests`, `npm run lint:fix`, and `npm run format` to correct auto-fixable issues in place (US3 scenario 3)
- [ ] T018 [US3] Validate US3 by running quickstart scenario 5 (`make lint` on a clean tree, inject a violation, run `make lint-fix`, re-run `make lint`)

**Checkpoint**: US1, US2, AND US3 all work independently.

---

## Phase 6: User Story 4 - Build the Project for Production (Priority: P2)

**Goal**: A maintainer produces compiled frontend assets and a production container image consistent with the documented deployment, with granular single-artifact variants.

**Independent Test**: Run `make build`, confirm `dist/static/` contains compiled assets and `docker compose build web` produces the image; smoke-test the image serves the app; confirm `make build-frontend`/`make build-image` produce only their own artifact (quickstart scenario 6).

### Implementation for User Story 4

- [ ] T019 [US4] Implement the `build-frontend` target in `Makefile`: run `npm run build` producing `dist/static/` (compiled assets) (FR-006)
- [ ] T020 [US4] Implement the `build-image` target in `Makefile`: run `$(COMPOSE) build web` (Docker Compose v2) reproducing the production image from the root `Dockerfile` (FR-006, FR-008)
- [ ] T021 [US4] Implement the aggregate `build` target in `Makefile` depending on `build-frontend build-image`, with clean interrupt handling for spawned processes (FR-006, FR-009, FR-010)
- [ ] T022 [US4] Validate US4 by running quickstart scenario 6 (`make build`, smoke-test the image via `docker compose up -d web` + `/api/health`, plus `make build-frontend` and `make build-image` granular checks)

**Checkpoint**: All four user stories are independently functional.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, portability hardening, and end-to-end validation across all stories.

- [ ] T023 [P] Create `docs/DEVELOPMENT.md` documenting: every `make` target, supported environments (POSIX; Windows via WSL/Git Bash), prerequisites (Python 3.14+, Node 20+, Docker Compose v2), and common failure modes (missing runtime, missing deps, port conflicts, non-POSIX limitation) (FR-012)
- [ ] T024 [P] Add a one-line pointer in `README.md` directing contributors to `make help` and `docs/DEVELOPMENT.md`
- [ ] T025 [P] Add `docs/DEVELOPMENT.md` and the `Makefile` to the "Development Commands" / contribution notes in `docs/TESTING.md` or relevant docs if a canonical entry point exists (additive cross-reference only — do not alter existing content)
- [ ] T026 Optionally validate `Makefile` recipes with `shellcheck` (extract recipes) and fix any POSIX-`/bin/sh` portability issues (GNU-isms avoided where a portable form exists)
- [ ] T027 Verify the `.PHONY:` list includes every phony target and that `make help` lists all targets with descriptions (FR-007, FR-009)
- [ ] T028 Run all six `quickstart.md` scenarios end-to-end and the edge-case spot checks (missing runtime, missing deps, port in use, clean interrupt), confirming each passes using only `make` targets and that no existing documented command/script/deployment path is altered (additive-only, FR-011)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately. Creates the `Makefile` skeleton all targets extend.
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories (`help` is the discovery surface; guards are shared preconditions).
- **User Stories (Phases 3–6)**: All depend on Foundational completion.
  - Recommended order: US1 → US2 → US3 → US4 (priority P1 → P2).
  - All recipes edit the same `Makefile`, so implement sequentially to avoid conflicts even though the stories are logically independent.
- **Polish (Phase 7)**: Documentation tasks (T023–T025) can start once the target set is stable (after Phase 6); validation tasks (T026–T028) depend on all stories being complete.

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependencies on other stories. (MVP)
- **US2 (P1)**: Can start after Foundational — independent of US1 (test recipes do not call install/dev).
- **US3 (P2)**: Can start after Foundational — independent; depends on Black being installed by `make install`, but the recipe itself is self-contained.
- **US4 (P2)**: Can start after Foundational — independent; `build-image` reuses the existing Dockerfile/compose, not US1–US3.

### Within Each User Story

- Implement the granular (single-stack) variants first, then the aggregate target that depends on them.
- Validate the story against its `quickstart.md` scenario before moving to the next priority.

### Parallel Opportunities

- **Limited by single-file scope**: The core `Makefile` edits are sequential (same file). Most implementation tasks are therefore NOT marked `[P]`.
- **Parallelizable**: T023 (`docs/DEVELOPMENT.md`), T024 (`README.md`), T025 (docs cross-reference) edit independent files and can run together once the target set is stable.
- **Per story**: within a story, the backend-variant and frontend-variant targets are logically independent and may be authored in either order, but since they land in the same `Makefile`, sequence them to prevent edit conflicts.

---

## Parallel Example: Polish Phase

```bash
# These three touch independent files and can run together once targets are stable:
Task: "Create docs/DEVELOPMENT.md (FR-012)"
Task: "Add one-line pointer in README.md"
Task: "Add additive cross-reference in docs/"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (`Makefile` skeleton + variables).
2. Complete Phase 2: Foundational (`help`, `check-runtime`, `check-deps`) — CRITICAL, blocks all stories.
3. Complete Phase 3: User Story 1 (`install` + `dev`).
4. **STOP and VALIDATE**: clone-fresh `make install` → `make dev` → app loads; `make help` lists commands; Ctrl-C leaves no orphan.
5. Demo / onboard a contributor if ready.

### Incremental Delivery

1. Setup + Foundational → discoverable, guarded CLI surface.
2. Add US1 → validate (MVP: onboard + run app).
3. Add US2 → validate (one-command full test + coverage gate).
4. Add US3 → validate (one-command lint + auto-fix).
5. Add US4 → validate (production build + image smoke test).
6. Polish → docs, portability, full quickstart + edge cases.
7. Each story adds value without breaking previous stories (additive-only, FR-011).

### Parallel Team Strategy

With multiple contributors:

1. Team completes Setup + Foundational together (the shared `Makefile`).
2. Once Foundational is done, stories are logically independent but share one file — coordinate via short-lived sequential PRs per story, or branch on different sections and merge carefully.
3. Documentation (T023–T025) can be done in parallel with late story work.

---

## Notes

- **Additive only (FR-011)**: create `Makefile` and `docs/DEVELOPMENT.md`; edit `README.md` with a one-line pointer only. Do not modify `run_web.py`, `package.json`, `pytest.ini`, `vitest.config.ts`, `docker-compose.yml`, or `Dockerfile`.
- **Reuse canonical commands (FR-008)**: every recipe must wrap the approved command (`python run_web.py`, `python3 -m pytest`, `npm` scripts, `docker compose`), never duplicate or diverge.
- **Coverage parity (FR-004)**: delegate thresholds to each tool's config; do not hardcode or override `pytest.ini` (85%) or `vitest.config.ts`. The frontend 85% alignment is a documented follow-up, out of scope here.
- **No automated test tasks**: validation is manual per `quickstart.md`; optional `shellcheck` only.
- `[P]` tasks = different files, no dependencies. `[Story]` label maps to a user story for traceability.
- Commit after each task or logical group; stop at any checkpoint to validate a story independently.
