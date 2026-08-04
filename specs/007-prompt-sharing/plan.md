# Implementation Plan: Prompt Sharing & Team Collaboration

**Branch**: `007-prompt-sharing` | **Date**: 2026-08-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-prompt-sharing/spec.md`

## Summary

Add per-prompt sharing grants between users with two permission levels (`read`, `edit`), a "shared with me" listing/filter with badges, owner-managed grant review/revocation, and full audit coverage. Technically: a new `prompt_shares` table (Alembic migration, SQLite+Postgres portable), a `SharingRepository`, authorization extensions in `PromptDataServiceDB` and the prompt routers, visibility-scoped list/search queries (owned ∪ shared, admin sees all), four new API endpoints plus a user-typeahead endpoint, and a share modal + badge + filter chip in the TypeScript frontend.

**Critical architectural note**: today `PromptRepository.search()` is not user-scoped — any authenticated user sees all prompts; ownership only gates mutations (`check_prompt_ownership` in `src/web/routers/prompts_shared.py:33`). This feature introduces read-visibility scoping (own + shared-with-me + admin-all) when `AUTH_ENABLED=true`. See research.md §1 for the migration/behavior decision.

## Technical Context

**Language/Version**: Python 3.14+ (backend), TypeScript strict / ES2020 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x ORM, Alembic, Pydantic, slowapi (rate limiting), i18next; Vite + Vitest frontend toolchain

**Storage**: SQLite (dev/default) and PostgreSQL (production) via SQLAlchemy; new `prompt_shares` table

**Testing**: `python3 -m pytest` (backend, ≥85% coverage gate), Vitest (frontend, ≥85%); both dialects exercised for the migration

**Target Platform**: Self-hosted web app (Docker, linux/amd64+arm64); browsers per existing support matrix

**Project Type**: Web application — FastAPI backend + TypeScript SPA-ish frontend in one repo

**Performance Goals**: Combined owned+shared listing within existing listing latency envelope (SC-004: no perceptible slowdown; single query, no N+1 — target: one extra indexed join/EXISTS, <10% latency delta on 5k-prompt vault)

**Constraints**: Alembic migration must be dialect-portable (no PRAGMA/sqlite_master, `sa.Enum(native_enum=False)`, `sa.true()/sa.false()`); no user enumeration in error paths; rate limiting consistent with auth endpoints; i18n in all 4 locales; MPL 2.0 headers on new files

**Scale/Scope**: Team-internal deployments — tens of users, thousands of prompts, ≤ hundreds of grants per prompt in practice

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|-----------|------|--------|
| I. Layered Service Architecture | New routes call `PromptDataServiceDB` / sharing service methods only; `SharingRepository` owns all `prompt_shares` SQL; no route→DB shortcuts | ✅ Design follows existing router→service→repository chain |
| II. Test Coverage Gate (≥85%) | Repository, service authz matrix, API integration, migration up/down (both dialects), Vitest for modal/badge — written alongside code | ✅ Test plan defined in quickstart.md; tasks will pair tests with each layer |
| III. Security-First Authentication | All share-mutating endpoints require auth when enabled; rate-limited via existing `src/web/middleware/rate_limit.py`; no enumeration (mirrors password-reset); grantee privilege ceiling enforced server-side | ✅ Explicit authz matrix in spec FR-001..FR-007; anonymous mode: sharing disabled (research §2) |
| IV. TypeScript-Only Frontend | Share modal, badge, filter chip all under `src/web/static/ts/`; typed `t('key.path')` i18n; no `innerHTML` with untrusted input (usernames rendered via `textContent`/safe-html helper) | ✅ Reuses `components/modal.ts`, `utils/typeahead.ts` |
| V. Database-Backed Persistence | `prompt_shares` via SQLAlchemy model + Alembic migration; repository pattern; session context managers | ✅ No file/JSON storage involved |

**Initial gate**: PASS — no violations, Complexity Tracking not needed.

**Post-Phase-1 re-check**: PASS — design artifacts introduce no new layers, no raw SQL, no JS edits, no coverage exemptions.

## Project Structure

### Documentation (this feature)

```text
specs/007-prompt-sharing/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── sharing-api.md   # Phase 1 output
├── checklists/
│   └── requirements.md  # Spec quality checklist (complete)
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
alembic/versions/
└── <rev>_add_prompt_shares_table.py     # NEW — portable migration

src/db/
├── models/
│   ├── prompt_share.py                  # NEW — PromptShare ORM model
│   ├── prompt.py                        # MODIFIED — shares relationship (cascade delete-orphan)
│   ├── user.py                          # MODIFIED — received_shares relationship
│   └── __init__.py                      # MODIFIED — export PromptShare
└── repositories/
    ├── sharing_repository.py            # NEW — create/upsert, revoke, list_for_prompt, list_for_grantee, permission_for
    ├── prompt_repository.py             # MODIFIED — visibility-scoped search()/count (owned ∪ shared, admin all)
    └── user_repository.py               # MODIFIED — search_active_by_prefix() for typeahead

src/services/
└── prompt_data_service_db.py            # MODIFIED — share-aware authorization + share CRUD passthrough + audit events

src/web/
├── models/
│   ├── sharing_requests.py              # NEW — ShareGrantRequest (identifier, permission)
│   └── sharing_responses.py             # NEW — ShareResponse, ShareListResponse, UserSuggestion
├── routers/
│   ├── prompts_sharing_router.py        # NEW — POST/GET /api/prompts/{id}/shares, DELETE /api/prompts/{id}/shares/{user_id}
│   ├── prompts_search_router.py         # MODIFIED — ?filter=shared-with-me + visibility scoping + shared flags in payload
│   ├── prompts_shared.py                # MODIFIED — check_prompt_access(prompt, user, level) alongside check_prompt_ownership
│   ├── prompts_crud_router.py           # MODIFIED — edit path honors edit-grants; favorite/delete stay owner/admin
│   ├── prompts_versions_router.py       # MODIFIED — history readable with read-grant, revert requires edit-grant
│   ├── users_router.py                  # NEW — GET /api/users/search (typeahead, auth-required, rate-limited)
│   └── __init__.py                      # MODIFIED — register new routers
└── static/
    ├── ts/
    │   ├── components/share-modal.ts    # NEW — grant form + current-grants list + revoke
    │   ├── components/__tests__/share-modal.test.ts  # NEW
    │   ├── app/                         # MODIFIED — card badge, sidebar "Shared with me" chip, share action wiring
    │   └── utils/api.ts                 # MODIFIED — share API client functions + types
    └── locales/{en,fr,es,de}.json       # MODIFIED — sharing.* keys

tests/
├── test_sharing_repository.py           # NEW
├── test_sharing_service.py              # NEW — authz matrix (5 actors × 4 actions)
├── test_sharing_api.py                  # NEW — API integration incl. enumeration + rate limits
├── test_users_api.py                    # NEW — user typeahead endpoint tests
└── test_migration_prompt_shares.py      # NEW — up/down on SQLite + Postgres (skip if PG unavailable)
```

**Structure Decision**: Single-repo web application following the existing layered layout. New code lands in the established directories (`src/db/models/` one-file-per-model, `src/db/repositories/`, focused routers under `src/web/routers/` mirroring the prompts_* router decomposition, components under `src/web/static/ts/components/`). No new top-level structure.

## Complexity Tracking

No constitution violations — table intentionally left empty.
