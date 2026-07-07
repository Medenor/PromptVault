# Implementation Plan: Prompt Semantic Versioning

**Branch**: `001-prompt-versioning` | **Date**: 2026-07-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-prompt-versioning/spec.md`

## Summary

Add optional `MAJOR.MINOR.PATCH` semantic version labels to prompts, displaying the current version on the detail view and snapshotting it into each version history entry. A new "Copy with version metadata" action embeds the version in an HTML comment line for cross-platform tracking.

The approach is purely additive: two nullable `semantic_version` columns (one on `prompts`, one on `prompt_versions`), one new API endpoint, and UI additions to the edit form, prompt detail badge, and version history list. No existing behaviour changes.

## Technical Context

**Language/Version**: Python 3.14+ (backend), TypeScript (frontend, `tsc` strict)

**Primary Dependencies**: FastAPI 0.104.1, SQLAlchemy 2.0+, Alembic, Pydantic v2, Jinja2 3.1.2, Tailwind CSS, Vitest (frontend tests), pytest (backend tests)

**Storage**: PostgreSQL (prod) / SQLite (dev/test) via SQLAlchemy ORM + Alembic migrations

**Testing**: pytest + pytest-asyncio (backend, ≥ 85% coverage gate); Vitest + v8 (frontend, ≥ 85% coverage gate); Playwright (E2E, optional for this feature)

**Target Platform**: Linux server (Docker); also runs locally via `python run_web.py`

**Project Type**: Web service (FastAPI backend + Jinja2 + TypeScript SPA-style frontend)

**Performance Goals**: No new performance requirements; the new column is nullable and zero-cost for read paths that don't request it.

**Constraints**: All schema changes via Alembic; no raw SQL; TypeScript only for new frontend logic; all new endpoints protected by existing auth middleware when `AUTH_ENABLED=true`.

**Scale/Scope**: Single-user to small-team self-hosted deployment; no pagination or batching concerns for this feature.

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle                              | Status | Notes                                                                                                                                                                                                               |
| -------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **I. Layered Service Architecture**    | PASS   | New `semantic_version` field flows: Route → Service → Repository → DB. No route handler touches the DB directly.                                                                                                    |
| **II. Test Coverage Gate (≥ 85%)**     | PASS   | New service logic, validators, and endpoint will have unit tests. Frontend component has Vitest coverage. Gate enforced pre-merge.                                                                                  |
| **III. Security-First Authentication** | PASS   | The new `POST /api/prompts/{id}/copy-with-version` endpoint is read-only (no mutation) but must still be protected from unauthenticated access when `AUTH_ENABLED=true`, consistent with all prompt-read endpoints. |
| **IV. TypeScript-Only Frontend**       | PASS   | Version field UI, badge, and copy action all written in `src/web/static/ts/`. No edits to legacy `src/web/static/js/`.                                                                                              |
| **V. Database-Backed Persistence**     | PASS   | `semantic_version` stored in PostgreSQL/SQLite via SQLAlchemy ORM columns. No JSON-file storage. Alembic migration required.                                                                                        |

**Constitution Check Result**: PASS — no violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-prompt-versioning/
├── plan.md              # This file
├── research.md          # Research decisions (Phase 0)
├── data-model.md        # Schema changes (Phase 1)
├── quickstart.md        # Validation guide (Phase 1)
├── contracts/
│   └── api.md           # API contract changes (Phase 1)
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
alembic/versions/
└── <hash>_add_semantic_version_to_prompts.py   # NEW migration

src/
├── db/
│   ├── models/
│   │   ├── prompt.py              # ADD: semantic_version column
│   │   └── prompt_version.py      # ADD: semantic_version column (snapshot)
│   └── repositories/
│       ├── version_repository.py  # UPDATE: include semantic_version in create_version()
│       └── prompt_repository.py   # UPDATE: set/get semantic_version on Prompt
├── services/
│   └── (no new service file; changes absorbed into existing prompt_data_service_db.py)
└── web/
    ├── models/
    │   ├── requests.py            # UPDATE: add semantic_version to PromptCreateRequest, PromptUpdateRequest
    │   └── prompt_responses.py    # UPDATE: add semantic_version to PromptResponse, VersionSummary
    ├── routers/
    │   └── prompts.py             # UPDATE: pass semantic_version through create/update; ADD copy-with-version endpoint
    ├── app.py                     # UPDATE: version history response includes semantic_version
    └── static/ts/
        └── app.ts                 # UPDATE: version form field, detail badge, history entries, copy action

tests/
├── unit/
│   ├── test_semantic_version_validation.py   # NEW: Pydantic validator unit tests
│   └── test_copy_with_version.py             # NEW: copy-with-version endpoint unit tests
└── integration/
    └── test_prompt_versioning_e2e.py          # UPDATE: add semantic_version assertions to existing tests
```

**Structure Decision**: Single-project web service. Changes span the full vertical (migration → model → repository → service → router → frontend). No new module or package is warranted — all changes slot into existing files/patterns.

## Complexity Tracking

No Constitution violations to justify.
