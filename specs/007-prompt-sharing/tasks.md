# Tasks: Prompt Sharing & Team Collaboration

**Input**: Design documents from `/specs/007-prompt-sharing/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/sharing-api.md, quickstart.md

**Tests**: INCLUDED — the project constitution (Principle II) makes tests-alongside-code non-negotiable with an 85% coverage gate on both backend and frontend.

**Organization**: Tasks are grouped by user story. US1 (grant shares) is the MVP; US2 (shared-with-me experience) and US3 (review & revoke) build on the same foundation and are independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1 / US2 / US3 from spec.md
- All new Python/TS files get the MPL 2.0 header

## Phase 1: Setup

**Purpose**: Confirm a green baseline so regressions are attributable to this feature.

- [ ] T001 Verify baseline: run `python3 -m pytest` and `npm run typecheck && npm run lint && npm run test:unit` on branch `007-prompt-sharing`; record baseline coverage numbers in the PR description draft

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema, ORM model, repository, and the authorization helper every story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 Create `PromptShare` ORM model in `src/db/models/prompt_share.py` per data-model.md (columns, `sa.Enum(native_enum=False, validate_strings=True)`, unique constraint `uq_prompt_shares_prompt_grantee`, index `idx_prompt_shares_grantee`, FK ondelete rules: prompt CASCADE, grantee CASCADE, granted_by SET NULL)
- [ ] T003 Wire relationships: add `shares` (cascade `all, delete-orphan`) to `src/db/models/prompt.py`, `received_shares` to `src/db/models/user.py`, export `PromptShare` from `src/db/models/__init__.py`
- [ ] T004 Create Alembic migration `alembic/versions/<rev>_add_prompt_shares_table.py` (dialect-portable: plain `op.create_table`/`op.drop_table`, no PRAGMA/sqlite_master, no native enum) — depends on T002
- [ ] T005 [P] Write migration round-trip test in `tests/test_migration_prompt_shares.py` (upgrade→downgrade→upgrade on SQLite; Postgres cases skip without `DATABASE_URL`; assert table/constraint/index presence and absence)
- [ ] T006 Implement `SharingRepository` in `src/db/repositories/sharing_repository.py` extending `BaseRepository`: `upsert()`, `revoke()`, `list_for_prompt()`, `list_for_grantee()`, `permission_for()` per data-model.md; export from `src/db/repositories/__init__.py`
- [ ] T007 [P] Write repository tests in `tests/test_sharing_repository.py`: upsert create + update-in-place (no duplicate), revoke, both list directions, permission_for hit/miss, cascade on prompt delete, cascade on grantee delete, granted_by SET NULL on grantor delete, and grantee deactivation leaves share rows untouched (FR-014 no-op case)
- [ ] T008 Add `check_prompt_access(prompt, user, level)` to `src/web/routers/prompts_shared.py` implementing the effective-permission resolution table from data-model.md (admin→owner, owner→owner, grant→its level, else no access; `AUTH_ENABLED=false` → legacy pass-through); keep `check_prompt_ownership` delegating to it at `owner` level
- [ ] T009 Add sharing test fixtures to `tests/conftest.py`: `sharing_repo`, `second_user`, `third_user`, and a `shared_prompt` factory (prompt + grant at a given permission)

**Checkpoint**: `prompt_shares` migrates cleanly on both dialects; repository and access helper fully tested — user stories can start (in parallel if staffed).

---

## Phase 3: User Story 1 — Share a prompt with a teammate (Priority: P1) 🎯 MVP

**Goal**: An owner can grant a teammate read or edit access; the grantee's capabilities are enforced exactly (view/history at read; edit/revert at edit; never delete/re-share/favorite/ownership). Recipient picking works via typeahead with no user enumeration on failure.

**Independent Test**: Two-user flow — create users A and B, A grants B read then edit on one prompt, verify B's access at each level and that stranger C has none (quickstart.md §3 steps 1, 3, 5).

### Tests for User Story 1 (write first, ensure they fail)

- [ ] T010 [P] [US1] Write service authz-matrix tests in `tests/test_sharing_service.py`: parametrize 5 actors (owner, grantee-read, grantee-edit, stranger, admin) × actions (view, edit content/category/tags, toggle favorite, delete, revert, grant share) asserting the data-model.md matrix; plus grant validations (self-share refused, owner-as-grantee refused, inactive/unknown grantee refused, upsert semantics)
- [ ] T011 [P] [US1] Write API tests for granting in `tests/test_sharing_api.py`: `POST /api/prompts/{id}/shares` 201/200-upsert/403-nonowner/404-invisible-prompt/422; identical generic 400 bodies for unknown-user vs inactive-user vs self-share (SC-006); 404 when `AUTH_ENABLED=false`; audit event `prompt.share.granted` emitted with actor/grantee/permission/resource_id
- [ ] T012 [P] [US1] Write typeahead API tests in `tests/test_users_api.py` (own file — avoids write conflicts with T011): `GET /api/users/search` — 401 unauthenticated, 400 for q<2 chars, ≤10 results, active users only, matches username and email prefixes, usernames only in payload (no email field)

### Implementation for User Story 1

- [ ] T013 [P] [US1] Create Pydantic models `ShareGrantRequest` in `src/web/models/sharing_requests.py` and `ShareResponse`/`ShareListResponse`/`UserSuggestion` in `src/web/models/sharing_responses.py` per contracts/sharing-api.md; export from `src/web/models/__init__.py`
- [ ] T014 [US1] Add `grant_share(prompt_id, identifier, permission, acting_user)` to `src/services/prompt_data_service_db.py`: resolve identifier (username or email, active only), validate (no self-share, not owner, prompt exists), call `SharingRepository.upsert()`, emit `prompt.share.granted` via `logging_service.log_audit_event` — depends on T013
- [ ] T015 [US1] Add `search_active_by_prefix(prefix, limit=10)` to `src/db/repositories/user_repository.py` (active accounts, matches username OR email prefix, returns User objects but callers expose usernames only, ordered)
- [ ] T016 [US1] Create `src/web/routers/prompts_sharing_router.py` with `POST /api/prompts/{id}/shares` (owner/admin via `check_prompt_access` at `owner` level; generic 400 on grant failure; 404 when auth disabled; `@limiter.limit` — resolve the final values from the improvement-plan item-3 taxonomy NOW, at implementation time, so T043 is verification only); register in `src/web/routers/__init__.py` and `src/web/app.py` — depends on T014
- [ ] T017 [US1] Create `src/web/routers/users_router.py` with `GET /api/users/search` (auth-required, min length 2, ≤10 active usernames, rate-limited); register router — depends on T015
- [ ] T018 [US1] Enforce grant-aware authorization in `src/web/routers/prompts_crud_router.py`: `PUT /api/prompts/{id}` uses `check_prompt_access(edit)` (content/category/tags editable; favorite field rejected for non-owners), `GET /api/prompts/{id}` uses `read` level returning 404 when invisible and its response payload gains the `shared` and `permission` fields (contracts §4 — the frontend gates edit controls on them when opening a prompt directly); `DELETE` and `PUT .../favorite` stay `owner` level — depends on T008
- [ ] T019 [US1] Enforce grant-aware authorization in `src/web/routers/prompts_versions_router.py`: history/compare/get-version at `read` level, revert at `edit` level (version author = acting grantee) — depends on T008
- [ ] T020 [P] [US1] Add share API client functions + TS types (`grantShare`, `searchUsers`, `ShareResponse`, `UserSuggestion`) to `src/web/static/ts/utils/api.ts`
- [ ] T021 [US1] Create share modal (grant form only at this stage) in `src/web/static/ts/components/share-modal.ts`: composes `components/modal.ts`, user picker via `utils/typeahead.ts` + `utils/debounce.ts`, read/edit `<select>`, typed `t('sharing.*')` strings, no `innerHTML` with user data — depends on T020
- [ ] T022 [US1] Wire a Share action (owner/admin only) onto prompt cards in `src/web/static/ts/app/` opening the share modal — depends on T021
- [ ] T023 [P] [US1] Add `sharing.*` i18n keys (grant flow subset: title, grant, permission.read, permission.edit, grant_failed, picker_placeholder) to all four `src/web/static/locales/{en,fr,es,de}.json`
- [ ] T024 [P] [US1] Write Vitest specs for the share modal grant flow in `src/web/static/ts/components/__tests__/share-modal.test.ts` (open, typeahead select, permission choice, submit, generic error rendering)
- [ ] T025 [US1] Run `npm run build` + full backend/frontend suites; fix until green with coverage ≥85% on new modules

**Checkpoint**: Grants work end-to-end with exact permission enforcement — MVP demonstrable with two users (recipient reaches shared prompts by direct URL until US2 lands).

---

## Phase 4: User Story 2 — Find and work with prompts shared with me (Priority: P2)

**Goal**: Visibility-scoped listings (owned ∪ shared; admin all), a "shared with me" filter, "Shared" badges, and permission-gated UI controls.

**Independent Test**: With grants from fixtures, log in as recipient: list shows own + shared (badged, deduplicated), `filter=shared-with-me` narrows correctly, search/filters/pagination span both sets, read-grantees see no edit controls (quickstart.md §3 steps 2, 4).

### Tests for User Story 2 (write first, ensure they fail)

- [ ] T026 [P] [US2] Write repository visibility tests in `tests/test_sharing_repository.py`: `search(visible_to_user_id=...)` returns owned ∪ shared with no duplicates, honors query/category/tags filters and pagination; favorites filter returns owned prompts only (shared excluded, spec Edge Cases); `shared_only` variant; `search_count` consistency; `None` (admin) unscoped
- [ ] T027 [P] [US2] Write API visibility tests in `tests/test_sharing_api.py`: default list scoping per actor (owner/grantee/stranger/admin), `?filter=shared-with-me`, `shared`/`permission` fields in payloads, 404 on invisible prompt detail, legacy all-visible behavior when `AUTH_ENABLED=false`, seeded ~1k-prompt/100-share correctness + advisory timing log (SC-004, research §11)

### Implementation for User Story 2

- [ ] T028 [US2] Extend `PromptRepository.search()` and `search_count()` in `src/db/repositories/prompt_repository.py` with `visible_to_user_id: Optional[str]` and `shared_only: bool` using the OR + IN-subquery from research §4 (no outer join, ordering/pagination unchanged); when `favorite=True` is combined with `visible_to_user_id`, restrict to owned prompts only (spec Edge Cases)
- [ ] T029 [US2] Apply scoping in `src/web/routers/prompts_search_router.py` and list endpoints: non-admin authenticated users get `visible_to_user_id=user.id`; `?filter=shared-with-me` maps to `shared_only`; each payload item gains `shared` and `permission` fields (via `check_prompt_access` resolution); anonymous mode unscoped — depends on T028
- [ ] T030 [US2] Update service-layer list/search passthroughs in `src/services/prompt_data_service_db.py` to accept and forward the acting user id — depends on T028
- [ ] T031 [P] [US2] Render "Shared" badge on prompt cards in `src/web/static/ts/app/` when `shared: true` (safe rendering, `t('sharing.badge')`), and gate edit/delete/favorite/share controls on the payload `permission` field
- [ ] T032 [P] [US2] Add "Shared with me" sidebar filter chip in `src/web/static/ts/app/` driving `filter=shared-with-me`, following the existing favorites-filter wiring
- [ ] T033 [P] [US2] Add remaining `sharing.*` i18n keys (badge, shared_with_me) to all four `src/web/static/locales/{en,fr,es,de}.json`
- [ ] T034 [P] [US2] Write Vitest specs for badge rendering + permission-gated controls in `src/web/static/ts/app/__tests__/` (or extend existing card spec file)
- [ ] T035 [US2] Run `npm run build` + full suites; fix until green, coverage ≥85%

**Checkpoint**: Recipients discover and use shared prompts entirely through the UI; visibility change verified in both auth modes.

---

## Phase 5: User Story 3 — Review and revoke access (Priority: P3)

**Goal**: Owners/admins see each prompt's grant list and revoke grants; revocation is immediate and audited.

**Independent Test**: With existing grants, open the share modal as owner → grant list matches; revoke one → recipient loses access on next request; `prompt.share.revoked` audit line present; grantee's attempt to list grants → 403 (quickstart.md §3 step 6).

### Tests for User Story 3 (write first, ensure they fail)

- [ ] T036 [P] [US3] Write API tests in `tests/test_sharing_api.py`: `GET /api/prompts/{id}/shares` 200 owner/admin with full list, 403 grantee (both levels), 404 stranger; `DELETE /api/prompts/{id}/shares/{user_id}` 200 + immediate access loss, 404 for absent grant, 403 non-owner; audit event `prompt.share.revoked`; rate-limit 429 on both endpoints

### Implementation for User Story 3

- [ ] T037 [US3] Add `list_shares(prompt_id, acting_user)` and `revoke_share(prompt_id, grantee_user_id, acting_user)` to `src/services/prompt_data_service_db.py` (owner/admin only; audit `prompt.share.revoked` including the revoked grant's permission level)
- [ ] T038 [US3] Add `GET /api/prompts/{id}/shares` and `DELETE /api/prompts/{id}/shares/{user_id}` to `src/web/routers/prompts_sharing_router.py` (rate-limited, contracts §2–3) — depends on T037
- [ ] T039 [US3] Extend `src/web/static/ts/components/share-modal.ts` with the current-grants list (grantee, permission, granted-by) and per-row revoke buttons; add `listShares`/`revokeShare` client functions to `src/web/static/ts/utils/api.ts`
- [ ] T040 [P] [US3] Add revoke-flow i18n keys (revoke, revoked, no_shares) to all four `src/web/static/locales/{en,fr,es,de}.json`
- [ ] T041 [P] [US3] Extend Vitest specs in `src/web/static/ts/components/__tests__/share-modal.test.ts` for grant listing and revoke flow
- [ ] T042 [US3] Run `npm run build` + full suites; fix until green, coverage ≥85%

**Checkpoint**: All three stories independently functional — full share lifecycle (grant → use → review → revoke) works end-to-end.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T043 [P] Verify the rate-limit values chosen in T016/T017/T038 against the improvement-plan item-3 taxonomy and run the quickstart §4 spot-check (verification only — values were resolved at implementation time)
- [ ] T044 [P] Execute the full quickstart.md §3 manual two-user walkthrough (all 9 steps, including fr/es/de locale check and anonymous-mode step) and fix any gaps
- [ ] T045 [P] Update `CHANGELOG.md`: feature entry plus the **highlighted visibility behavior change** note (authenticated users now see only owned + shared prompts — research §1)
- [ ] T046 [P] Update `AGENTS.md` API endpoint list and database schema section with `prompt_shares` and the new endpoints
- [ ] T047 Final gates: `python3 -m pytest` ≥85% coverage, `npm run typecheck && npm run lint && npm run test:unit:coverage` ≥85%, `alembic downgrade -1 && alembic upgrade head` round-trip, `docker-compose up --build` smoke check (constitution Workflow §6)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: none
- **Phase 2 (Foundational)**: after T001 — internal order: T002 → T003 → T004; T006 → T007; T008 needs T006; T005/T009 parallel after T004/T006
- **Phase 3 (US1)**: after Phase 2 complete
- **Phase 4 (US2)**: after Phase 2; independent of US1 on the backend (T028–T030 touch different files), but the UI permission-gating (T031) reads the same payload fields — deliver after US1 for a coherent demo
- **Phase 5 (US3)**: after US1 (extends `prompts_sharing_router.py`, share modal, and service from Phase 3)
- **Phase 6 (Polish)**: after all desired stories

### Story completion order

```text
Setup → Foundational → US1 (MVP) → US2 → US3 → Polish
                          └── US2 backend (T026–T030) may proceed in parallel with US1 if staffed
```

### Parallel Opportunities

- Phase 2: T005 ∥ T007 ∥ T009 once their prerequisites exist
- US1 tests first: T010 ∥ T011 ∥ T012; then T013 ∥ T015 ∥ T020 ∥ T023; T024 ∥ backend tasks
- US2: T026 ∥ T027; then T031 ∥ T032 ∥ T033 ∥ T034 after T029
- US3: T040 ∥ T041 after T039
- Polish: T043 ∥ T044 ∥ T045 ∥ T046

## Parallel Example: User Story 1

```bash
# Write all US1 tests together (must fail before implementation):
Task: "Service authz-matrix tests in tests/test_sharing_service.py"          # T010
Task: "Grant API + enumeration tests in tests/test_sharing_api.py"           # T011
Task: "Typeahead API tests in tests/test_users_api.py"                       # T012

# Then start independent implementation files in parallel:
Task: "Pydantic sharing models in src/web/models/sharing_*.py"               # T013
Task: "search_active_by_prefix in src/db/repositories/user_repository.py"    # T015
Task: "Share API client functions in src/web/static/ts/utils/api.ts"         # T020
Task: "sharing.* i18n keys in src/web/static/locales/*.json"                 # T023
```

## Implementation Strategy

**MVP first**: Phases 1–3 deliver the flagship capability (grants with enforced permissions). Stop, run the US1 independent test, demo with two users.

**Incremental delivery**: US2 makes sharing discoverable (badges, filter, visibility scoping — the user-facing behavior change ships here, with its CHANGELOG note). US3 completes the lifecycle with review/revoke. Each checkpoint leaves the suite green at ≥85% coverage, so any phase boundary is a mergeable state.

**Notes**:

- Tests within each story are written before implementation and must fail first (constitution Principle II)
- `tests/test_sharing_api.py` is shared across T011 (US1, creates it), T027 (US2), and T036 (US3) — they append distinct test classes and stories run sequentially, so no write conflicts in practice; typeahead tests live in their own `tests/test_users_api.py` (T012) so US1's two [P] test tasks touch different files
- Commit after each task or logical group; never below the coverage gate at a checkpoint
