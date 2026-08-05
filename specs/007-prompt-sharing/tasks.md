# Tasks: Prompt Sharing & Team Collaboration

**Input**: Design documents from `/specs/007-prompt-sharing/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/sharing-api.md, quickstart.md

**Tests**: INCLUDED — the project constitution (Principle II) makes tests-alongside-code non-negotiable with an 85% coverage gate on both backend and frontend.

**Organization**: Tasks are grouped by user story. US1 (grant shares) is the MVP; US2 (shared-with-me experience, including the new default-private + grandfathered-public visibility model) and US3 (review, revoke, and un-grandfather) build on the same foundation and are independently testable.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1 / US2 / US3 from spec.md
- All new Python/TS files get the MPL 2.0 header

## Phase 1: Setup

**Purpose**: Confirm a green baseline so regressions are attributable to this feature.

- [ ] T001 Verify baseline: run `python3 -m pytest` and `npm run typecheck && npm run lint && npm run test:unit` on branch `007-prompt-sharing`; record baseline coverage numbers in the PR description draft

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schema, ORM models, repository, and the authorization helper every story depends on — including the `legacy_public` grandfathering column, since visibility resolution (Phase 2's `check_prompt_access`) needs it from the start.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 Create `PromptShare` ORM model in `src/db/models/prompt_share.py` per data-model.md (columns, `sa.Enum(native_enum=False, validate_strings=True)`, unique constraint `uq_prompt_shares_prompt_grantee`, index `idx_prompt_shares_grantee`, FK ondelete rules: prompt CASCADE, grantee CASCADE, granted_by SET NULL)
- [ ] T003 Wire relationships: add `shares` (cascade `all, delete-orphan`) to `src/db/models/prompt.py`, `received_shares` to `src/db/models/user.py`, export `PromptShare` from `src/db/models/__init__.py`
- [ ] T004 Create Alembic migration `alembic/versions/<rev>_add_prompt_shares_table.py` (dialect-portable: plain `op.create_table`/`op.drop_table`, no PRAGMA/sqlite_master, no native enum) — depends on T002
- [ ] T005 [P] Write migration round-trip test in `tests/test_migration_prompt_shares.py` (upgrade→downgrade→upgrade on SQLite; Postgres cases skip without `DATABASE_URL`; assert table/constraint/index presence and absence)
- [ ] T006 Add `legacy_public: Boolean NOT NULL default=False` column to the `Prompt` model in `src/db/models/prompt.py` per data-model.md and research.md §1/§3
- [ ] T007 Create Alembic migration `alembic/versions/<rev>_add_prompt_legacy_public.py`: add the column with dialect-portable `server_default=sa.false()`, then a scoped data migration (`op.execute`) that sets `legacy_public=True` on every row that existed before this migration ran (grandfathering, FR-017); downgrade drops the column — depends on T006
- [ ] T008 [P] Write migration round-trip test in `tests/test_migration_prompt_legacy_public.py`: seed rows before "upgrade", assert they land `legacy_public=True` after upgrade; assert a row inserted after upgrade defaults `False`; upgrade→downgrade→upgrade on SQLite, Postgres skip without `DATABASE_URL`
- [ ] T009 Implement `SharingRepository` in `src/db/repositories/sharing_repository.py` extending `BaseRepository`: `upsert()`, `revoke()`, `list_for_prompt()`, `list_for_grantee()`, `permission_for()` per data-model.md; export from `src/db/repositories/__init__.py`
- [ ] T010 [P] Write repository tests in `tests/test_sharing_repository.py`: upsert create + update-in-place (no duplicate), revoke, both list directions, permission_for hit/miss, cascade on prompt delete, cascade on grantee delete, granted_by SET NULL on grantor delete, and grantee deactivation leaves share rows untouched (FR-014 no-op case)
- [ ] T011 Add `check_prompt_access(prompt, user, level)` to `src/web/routers/prompts_shared.py` implementing the full effective-permission resolution table from data-model.md (admin→owner, owner→owner, grant→its level, `legacy_public=True`→`read` only, else no access; `AUTH_ENABLED=false` → legacy pass-through); keep `check_prompt_ownership` delegating to it at `owner` level — depends on T006, T009
- [ ] T012 [P] Write authz-helper unit tests in `tests/test_prompt_access.py` covering the six-branch resolution table directly (admin, owner, read-grant, edit-grant, legacy_public-only, no-access), including that `legacy_public=True` never yields `edit` level — depends on T011
- [ ] T013 Add sharing test fixtures to `tests/conftest.py`: `sharing_repo`, `second_user`, `third_user`, a `shared_prompt` factory (prompt + grant at a given permission), and a `legacy_public_prompt` factory (prompt with `legacy_public=True`, no grants)

**Checkpoint**: `prompt_shares` and `prompts.legacy_public` migrate cleanly on both dialects; repository and access helper (including grandfathering) fully tested — user stories can start (in parallel if staffed).

---

## Phase 3: User Story 1 — Share a prompt with a teammate (Priority: P1) 🎯 MVP

**Goal**: An owner can grant a teammate read or edit access; the grantee's capabilities are enforced exactly (view/history at read; edit/revert at edit; never delete/re-share/favorite/ownership/un-grandfather). Recipient picking works via typeahead with no user enumeration on failure.

**Independent Test**: Two-user flow — create users A and B, A grants B read then edit on one prompt, verify B's access at each level and that stranger C has none (quickstart.md §3 steps 1, 3, 5).

### Tests for User Story 1 (write first, ensure they fail)

- [ ] T014 [P] [US1] Write service authz-matrix tests in `tests/test_sharing_service.py`: parametrize 5 actors (owner, grantee-read, grantee-edit, stranger, admin) × actions (view, edit content/category/tags, toggle favorite, delete, revert, grant share, un-grandfather) asserting the data-model.md matrix; plus grant validations (self-share refused, owner-as-grantee refused, inactive/unknown grantee refused, upsert semantics)
- [ ] T015 [P] [US1] Write API tests for granting in `tests/test_sharing_api.py`: `POST /api/prompts/{id}/shares` 201/200-upsert/403-nonowner/404-invisible-prompt/422; identical generic 400 bodies for unknown-user vs inactive-user vs self-share (SC-006); 404 when `AUTH_ENABLED=false`; audit event `prompt.share.granted` emitted with actor/grantee/permission/resource_id; granting on a `legacy_public` prompt behaves identically to any other prompt
- [ ] T016 [P] [US1] Write typeahead API tests in `tests/test_users_api.py` (own file — avoids write conflicts with T015): `GET /api/users/search` — 401 unauthenticated, 400 for q<2 chars, ≤10 results, active users only, matches username and email prefixes, usernames only in payload (no email field)

### Implementation for User Story 1

- [ ] T017 [P] [US1] Create Pydantic models `ShareGrantRequest` in `src/web/models/sharing_requests.py` and `ShareResponse`/`ShareListResponse`/`UserSuggestion` in `src/web/models/sharing_responses.py` per contracts/sharing-api.md; export from `src/web/models/__init__.py`
- [ ] T018 [US1] Add `grant_share(prompt_id, identifier, permission, acting_user)` to `src/services/prompt_data_service_db.py`: resolve identifier (username or email, active only), validate (no self-share, not owner, prompt exists — visible via any path including `legacy_public`), call `SharingRepository.upsert()`, emit `prompt.share.granted` via `logging_service.log_audit_event` — depends on T017
- [ ] T019 [US1] Add `search_active_by_prefix(prefix, limit=10)` to `src/db/repositories/user_repository.py` (active accounts, matches username OR email prefix, returns User objects but callers expose usernames only, ordered)
- [ ] T020 [US1] Create `src/web/routers/prompts_sharing_router.py` with `POST /api/prompts/{id}/shares` (owner/admin via `check_prompt_access` at `owner` level; generic 400 on grant failure; 404 when auth disabled; `@limiter.limit` — resolve the final values from the improvement-plan item-3 taxonomy NOW, at implementation time, so T053 is verification only); register in `src/web/routers/__init__.py` and `src/web/app.py` — depends on T018
- [ ] T021 [US1] Create `src/web/routers/users_router.py` with `GET /api/users/search` (auth-required, min length 2, ≤10 active usernames, rate-limited); register router — depends on T019
- [ ] T022 [US1] Enforce grant-aware authorization in `src/web/routers/prompts_crud_router.py`: `PUT /api/prompts/{id}` uses `check_prompt_access(edit)` (content/category/tags editable; favorite and `legacy_public` fields rejected for non-owners), `GET /api/prompts/{id}` uses `read` level (satisfied by ownership, a grant, or `legacy_public=True`) returning 404 when invisible, and its response payload gains the `shared`, `legacy_public`, and `permission` fields (contracts §4 — the frontend gates edit controls on `permission`); `DELETE` and `PUT .../favorite` stay `owner` level — depends on T011
- [ ] T023 [US1] Enforce grant-aware authorization in `src/web/routers/prompts_versions_router.py`: history/compare/get-version at `read` level (including `legacy_public`), revert at `edit` level (version author = acting grantee; `legacy_public` alone never permits revert) — depends on T011
- [ ] T024 [P] [US1] Add share API client functions + TS types (`grantShare`, `searchUsers`, `ShareResponse`, `UserSuggestion`) to `src/web/static/ts/utils/api.ts`
- [ ] T025 [US1] Create share modal (grant form only at this stage) in `src/web/static/ts/components/share-modal.ts`: composes `components/modal.ts`, user picker via `utils/typeahead.ts` + `utils/debounce.ts`, read/edit `<select>`, typed `t('sharing.*')` strings, no `innerHTML` with user data — depends on T024
- [ ] T026 [US1] Wire a Share action (owner/admin only) onto prompt cards in `src/web/static/ts/app/` opening the share modal — depends on T025
- [ ] T027 [P] [US1] Add `sharing.*` i18n keys (grant flow subset: title, grant, permission.read, permission.edit, grant_failed, picker_placeholder) to all four `src/web/static/locales/{en,fr,es,de}.json`
- [ ] T028 [P] [US1] Write Vitest specs for the share modal grant flow in `src/web/static/ts/components/__tests__/share-modal.test.ts` (open, typeahead select, permission choice, submit, generic error rendering)
- [ ] T029 [US1] Run `npm run build` + full backend/frontend suites; fix until green with coverage ≥85% on new modules

**Checkpoint**: Grants work end-to-end with exact permission enforcement — MVP demonstrable with two users (recipient reaches shared prompts by direct URL until US2 lands).

---

## Phase 4: User Story 2 — Find and work with prompts shared with me (Priority: P2)

**Goal**: Visibility-scoped listings (owned ∪ shared ∪ legacy-public; admin sees all including private prompts), a "shared with me" filter that excludes grandfathered-public prompts, distinguishable "Shared" vs "Public (legacy)" badges, and permission-gated UI controls.

**Independent Test**: With grants and a grandfathered prompt from fixtures, log in as recipient: list shows own + shared + legacy-public prompts (correctly badged, deduplicated), `filter=shared-with-me` narrows to explicit grants only (excludes legacy-public), search/filters/pagination span the combined set, read-grantees and legacy-public viewers see no edit controls (quickstart.md §3 steps 2, 4).

### Tests for User Story 2 (write first, ensure they fail)

- [ ] T030 [P] [US2] Write repository visibility tests in `tests/test_sharing_repository.py`: `search(visible_to_user_id=...)` returns owned ∪ shared ∪ legacy-public with no duplicates, honors query/category/tags filters and pagination; favorites filter returns owned prompts only (shared and legacy-public excluded, spec Edge Cases); `shared_only` variant excludes legacy-public rows; `search_count` consistency; `None` (admin) unscoped, sees private (non-legacy-public, non-shared) prompts too
- [ ] T031 [P] [US2] Write API visibility tests in `tests/test_sharing_api.py`: default list scoping per actor (owner/grantee/legacy-public-viewer/stranger-on-private-prompt/admin), `?filter=shared-with-me` excludes legacy-public prompts, `shared`/`legacy_public`/`permission` fields in payloads, 404 on invisible (private, unshared, non-legacy-public) prompt detail for a stranger, legacy all-visible behavior when `AUTH_ENABLED=false`, seeded ~1k-prompt/100-share/100-legacy-public correctness + advisory timing log (SC-004, research §11)

### Implementation for User Story 2

- [ ] T032 [US2] Extend `PromptRepository.search()` and `search_count()` in `src/db/repositories/prompt_repository.py` with `visible_to_user_id: Optional[str]` and `shared_only: bool` using the OR + IN-subquery from research §4 (`Prompt.user_id == user_id OR Prompt.legacy_public.is_(True) OR Prompt.id.in_(shared subquery)`; `shared_only=True` narrows to the grant-only branch, excluding `legacy_public`; no outer join, ordering/pagination unchanged); when `favorite=True` is combined with `visible_to_user_id`, restrict to owned prompts only (spec Edge Cases)
- [ ] T033 [US2] Apply scoping in `src/web/routers/prompts_search_router.py` and list endpoints: non-admin authenticated users get `visible_to_user_id=user.id`; `?filter=shared-with-me` maps to `shared_only`; each payload item gains `shared`, `legacy_public`, and `permission` fields (via `check_prompt_access` resolution; `shared` is `true` only for an explicit grant, never for `legacy_public`-only visibility); anonymous mode unscoped — depends on T032
- [ ] T034 [US2] Update service-layer list/search passthroughs in `src/services/prompt_data_service_db.py` to accept and forward the acting user id — depends on T032
- [ ] T035 [P] [US2] Render distinct "Shared" and "Public (legacy)" badges on prompt cards in `src/web/static/ts/app/` from the `shared`/`legacy_public` payload fields respectively (safe rendering, `t('sharing.badge')` / `t('sharing.legacy_public_badge')`), and gate edit/delete/favorite/share/un-grandfather controls on the payload `permission` field
- [ ] T036 [P] [US2] Add "Shared with me" sidebar filter chip in `src/web/static/ts/app/` driving `filter=shared-with-me`, following the existing favorites-filter wiring
- [ ] T037 [P] [US2] Add remaining `sharing.*` i18n keys (badge, legacy_public_badge, shared_with_me) to all four `src/web/static/locales/{en,fr,es,de}.json`
- [ ] T038 [P] [US2] Write Vitest specs for badge rendering (both badge kinds, mutually exclusive) + permission-gated controls in `src/web/static/ts/app/__tests__/` (or extend existing card spec file)
- [ ] T039 [US2] Run `npm run build` + full suites; fix until green, coverage ≥85%

**Checkpoint**: Recipients discover and use shared and legacy-public prompts entirely through the UI; visibility change (including grandfathering) verified in both auth modes.

---

## Phase 5: User Story 3 — Review and revoke access (Priority: P3)

**Goal**: Owners/admins see each prompt's grant list, revoke grants, and can un-grandfather a legacy-public prompt to bring it under the private-plus-explicit-grants model; every action is immediate and audited.

**Independent Test**: With existing grants, open the share modal as owner → grant list matches; revoke one → recipient loses access on next request; `prompt.share.revoked` audit line present; grantee's attempt to list grants → 403; owner un-grandfathers a legacy-public prompt → it disappears from other users' listings immediately, and attempting to re-set `legacy_public: true` is rejected (quickstart.md §3 step 6 and the un-grandfather scenario).

### Tests for User Story 3 (write first, ensure they fail)

- [ ] T040 [P] [US3] Write API tests in `tests/test_sharing_api.py`: `GET /api/prompts/{id}/shares` 200 owner/admin with full list, 403 grantee (both levels), 404 stranger; `DELETE /api/prompts/{id}/shares/{user_id}` 200 + immediate access loss, 404 for absent grant, 403 non-owner; audit event `prompt.share.revoked`; rate-limit 429 on both endpoints
- [ ] T041 [P] [US3] Write API tests for un-grandfathering in `tests/test_sharing_api.py`: `PATCH /api/prompts/{id}` with `{"legacy_public": false}` → 200 owner/admin, immediate loss of implicit visibility for other users on next request, 403 for non-owner/grantee, 400 when submitting `{"legacy_public": true}` (one-way, FR-018), no `PromptShare` row is created as a side effect (spec Edge Cases)

### Implementation for User Story 3

- [ ] T042 [US3] Add `list_shares(prompt_id, acting_user)` and `revoke_share(prompt_id, grantee_user_id, acting_user)` to `src/services/prompt_data_service_db.py` (owner/admin only; audit `prompt.share.revoked` including the revoked grant's permission level)
- [ ] T043 [US3] Add `GET /api/prompts/{id}/shares` and `DELETE /api/prompts/{id}/shares/{user_id}` to `src/web/routers/prompts_sharing_router.py` (rate-limited, contracts §2–3) — depends on T042
- [ ] T044 [US3] Add `set_legacy_public(prompt_id, acting_user)` to `src/services/prompt_data_service_db.py` (owner/admin only; rejects if already `False`; flips `True→False`; audit event `prompt.legacy_public.revoked` or equivalent per logging_service conventions; creates no `PromptShare` rows) — depends on T006
- [ ] T045 [US3] Extend `PUT /api/prompts/{id}` in `src/web/routers/prompts_crud_router.py` (or add dedicated handling) to accept `legacy_public: false` in the request body per contracts §4b, routing to `set_legacy_public`; reject `legacy_public: true` with 400 — depends on T022, T044
- [ ] T046 [US3] Extend `src/web/static/ts/components/share-modal.ts` with the current-grants list (grantee, permission, granted-by) and per-row revoke buttons; add `listShares`/`revokeShare` client functions to `src/web/static/ts/utils/api.ts`
- [ ] T047 [US3] Add an "Make private" / un-grandfather action (owner/admin only) to the share modal or prompt card for `legacy_public` prompts in `src/web/static/ts/components/share-modal.ts` and/or `src/web/static/ts/app/`; add `unGrandfatherPrompt` client function to `src/web/static/ts/utils/api.ts` — depends on T045
- [ ] T048 [P] [US3] Add revoke-flow and un-grandfather i18n keys (revoke, revoked, no_shares, make_private, make_private_confirm) to all four `src/web/static/locales/{en,fr,es,de}.json`
- [ ] T049 [P] [US3] Extend Vitest specs in `src/web/static/ts/components/__tests__/share-modal.test.ts` for grant listing, revoke flow, and the un-grandfather action
- [ ] T050 [US3] Run `npm run build` + full suites; fix until green, coverage ≥85%

**Checkpoint**: All three stories independently functional — full share lifecycle (grant → use → review → revoke) works end-to-end, and the grandfathering transition has a real exit path (un-grandfather).

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T051 [P] Verify the rate-limit values chosen in T020/T021/T043 against the improvement-plan item-3 taxonomy and run the quickstart §4 spot-check (verification only — values were resolved at implementation time)
- [ ] T052 [P] Execute the full quickstart.md §3 manual two-user walkthrough (all steps, including fr/es/de locale check, anonymous-mode step, and the legacy-public/un-grandfather scenario) and fix any gaps
- [ ] T053 [P] Update `CHANGELOG.md`: feature entry plus the **highlighted visibility behavior change** note — prompts created from now on are private by default (owner + admin + explicit grants only); prompts that existed before this release remain visible to all authenticated users ("legacy public") until their owner or an admin makes them private (research §1)
- [ ] T054 [P] Update `AGENTS.md` API endpoint list and database schema section with `prompt_shares`, `prompts.legacy_public`, and the new/modified endpoints (including the `PATCH .../legacy_public` behavior)
- [ ] T055 Final gates: `python3 -m pytest` ≥85% coverage, `npm run typecheck && npm run lint && npm run test:unit:coverage` ≥85%, `alembic downgrade -1 && alembic downgrade -1 && alembic upgrade head` round-trip (both new migrations), `docker-compose up --build` smoke check (constitution Workflow §6)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: none
- **Phase 2 (Foundational)**: after T001 — internal order: T002 → T003 → T004; T006 → T007; T009 → T010; T011 needs T006 + T009; T005/T008/T012/T013 parallel after their prerequisites
- **Phase 3 (US1)**: after Phase 2 complete
- **Phase 4 (US2)**: after Phase 2; independent of US1 on the backend (T032–T034 touch different files), but the UI permission-gating (T035) reads the same payload fields — deliver after US1 for a coherent demo
- **Phase 5 (US3)**: after US1 (extends `prompts_sharing_router.py`, share modal, and service from Phase 3); the un-grandfather sub-thread (T044–T047) only needs T006/T022 from Phase 2/3, so it could ship independently of the revoke sub-thread (T042–T043) if staffed separately
- **Phase 6 (Polish)**: after all desired stories

### Story completion order

```text
Setup → Foundational (shares table + legacy_public column) → US1 (MVP) → US2 → US3 → Polish
                                                                └── US2 backend (T030–T034) may proceed in parallel with US1 if staffed
                                                                └── US3's un-grandfather sub-thread (T044–T047) may proceed in parallel with its revoke sub-thread (T042–T043)
```

### Parallel Opportunities

- Phase 2: T005 ∥ T008 ∥ T010 ∥ T012 ∥ T013 once their prerequisites exist
- US1 tests first: T014 ∥ T015 ∥ T016; then T017 ∥ T019 ∥ T024 ∥ T027; T028 ∥ backend tasks
- US2: T030 ∥ T031; then T035 ∥ T036 ∥ T037 ∥ T038 after T033
- US3: T040 ∥ T041; then T048 ∥ T049 after T046/T047
- Polish: T051 ∥ T052 ∥ T053 ∥ T054

## Parallel Example: User Story 1

```bash
# Write all US1 tests together (must fail before implementation):
Task: "Service authz-matrix tests in tests/test_sharing_service.py"          # T014
Task: "Grant API + enumeration tests in tests/test_sharing_api.py"           # T015
Task: "Typeahead API tests in tests/test_users_api.py"                      # T016

# Then start independent implementation files in parallel:
Task: "Pydantic sharing models in src/web/models/sharing_*.py"               # T017
Task: "search_active_by_prefix in src/db/repositories/user_repository.py"    # T019
Task: "Share API client functions in src/web/static/ts/utils/api.ts"         # T024
Task: "sharing.* i18n keys in src/web/static/locales/*.json"                 # T027
```

## Implementation Strategy

**MVP first**: Phases 1–3 deliver the flagship capability (grants with enforced permissions) plus the foundational grandfathering column. Stop, run the US1 independent test, demo with two users.

**Incremental delivery**: US2 makes sharing discoverable and lands the default-visibility change (badges, filter, visibility scoping including legacy-public — the user-facing behavior change ships here, with its CHANGELOG note). US3 completes the lifecycle with review/revoke and gives owners an exit from the grandfathered state. Each checkpoint leaves the suite green at ≥85% coverage, so any phase boundary is a mergeable state.

**Notes**:

- Tests within each story are written before implementation and must fail first (constitution Principle II)
- `tests/test_sharing_api.py` is shared across T015 (US1, creates it), T031 (US2), and T040/T041 (US3) — they append distinct test classes and stories run sequentially, so no write conflicts in practice; typeahead tests live in their own `tests/test_users_api.py` (T016) so US1's test tasks touch different files
- The `legacy_public` column and its migration (T006–T008) live in Phase 2, not US2, because `check_prompt_access` (T011, also Phase 2) needs the column to implement the full resolution table from the start — US2 only adds the *query-level* and *UI-level* consumption of it
- Commit after each task or logical group; never below the coverage gate at a checkpoint
