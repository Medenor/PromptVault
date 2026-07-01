# Tasks: Prompt Semantic Versioning

**Input**: Design documents from `specs/001-prompt-versioning/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/api.md ✅ | quickstart.md ✅

**Organization**: Tasks grouped by user story (P1 → P2 → P3) for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no shared dependencies)
- **[Story]**: Which user story this task belongs to
- Exact file paths included in every task

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Alembic migration — the one structural prerequisite all stories share.

- [ ] T001 Create Alembic migration adding `semantic_version VARCHAR(20) NULL` to `prompts` and `prompt_versions` tables in `alembic/versions/<hash>_add_semantic_version_to_prompts.py`
- [ ] T002 Run migration locally and verify schema: `alembic upgrade head`

**Checkpoint**: Both tables have the `semantic_version` column; existing data is unaffected.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Model and Pydantic changes that all three user stories depend on. Must complete before any story work begins.

- [ ] T003 Add `semantic_version = Column(String(20), nullable=True)` to `Prompt` model in `src/db/models/prompt.py`
- [ ] T004 Add `semantic_version = Column(String(20), nullable=True)` to `PromptVersion` model in `src/db/models/prompt_version.py`
- [ ] T005 Add `semantic_version: Optional[str] = None` with `field_validator` (regex `^\d+\.\d+\.\d+$`, strip whitespace, normalize `""` → `None`) to `PromptCreateRequest` in `src/web/models/requests.py`
- [ ] T006 Add same `semantic_version` field and validator to `PromptUpdateRequest` in `src/web/models/requests.py`
- [ ] T007 Add `semantic_version: Optional[str] = None` to `PromptResponse` in `src/web/models/prompt_responses.py`
- [ ] T008 Update `VersionSummary` TypeScript interface to add `semantic_version: string | null` in `src/web/static/ts/app.ts`

**Checkpoint**: Models compile, Pydantic validators reject invalid formats (verify with `python -c "from src.web.models.requests import PromptUpdateRequest; PromptUpdateRequest(title='x',prompt='x',semantic_version='abc')"` — should raise `ValidationError`). TypeScript compiles (`npm run typecheck`).

---

## Phase 3: User Story 1 — Assign and Display Version Number (Priority: P1) 🎯 MVP

**Goal**: Users can set a `MAJOR.MINOR.PATCH` version on a prompt during create/edit, and see it as a badge on the prompt detail view.

**Independent Test**: Edit a prompt, set version `1.0.0`, save, and confirm the detail view shows `v1.0.0`. Enter `abc` and confirm save is blocked. See `quickstart.md` Scenarios 1 & 2.

### Implementation for User Story 1

- [ ] T009 [US1] Update `create_version()` in `src/db/repositories/version_repository.py` to accept and store `semantic_version` parameter into the new `PromptVersion` column
- [ ] T010 [US1] Update `create_prompt` route handler in `src/web/routers/prompts.py` to read `semantic_version` from `PromptCreateRequest`, write it to `Prompt.semantic_version`, and pass it to `version_repo.create_version()`
- [ ] T011 [US1] Update `update_prompt` route handler in `src/web/routers/prompts.py` to read `semantic_version` from `PromptUpdateRequest`, update `Prompt.semantic_version`, pass it to `version_repo.create_version()`, and add `X-Version-Downgrade: true` header when new version is lower than current
- [ ] T012 [US1] Update `_prompt_to_dict()` helper in `src/web/routers/prompts.py` to include `semantic_version` in the returned dict
- [ ] T013 [US1] Update the `GET /api/prompts/{prompt_id}` handler in `src/web/routers/prompts.py` (or `src/web/app.py`) to return `semantic_version` in the response
- [ ] T014 [US1] Add version input field to the create/edit prompt form in `src/web/templates/index.html` (label "Semantic Version", placeholder `e.g. 1.0.0`, optional field)
- [ ] T015 [US1] Add frontend validation for the version field in `src/web/static/ts/app.ts`: on form submit, validate against `^\d+\.\d+\.\d+$` and show inline error if invalid, blocking submission
- [ ] T016 [US1] Add version badge to the prompt detail view in `src/web/templates/index.html` (displays `v{semantic_version}` or hidden when null)
- [ ] T017 [US1] Update the TypeScript prompt detail rendering in `src/web/static/ts/app.ts` to read `semantic_version` from the API response and show/hide the badge

**Checkpoint**: Scenarios 1 & 2 from `quickstart.md` pass. `npm run typecheck && npm run lint` pass.

---

## Phase 4: User Story 2 — Version History Shows Numbered Versions (Priority: P2)

**Goal**: Each entry in the version history modal shows the semantic version label that was active at save time. Pre-existing entries without a label show "Unversioned".

**Independent Test**: Create a prompt at `1.0.0`, bump to `1.1.0`, open version history — both entries show correct labels. Open history of a pre-existing unversioned prompt — entries show "Unversioned" not blank. See `quickstart.md` Scenarios 3 & 4.

### Implementation for User Story 2

- [ ] T018 [US2] Update `get_version_history` endpoint in `src/web/app.py` (lines ~1411–1442) to include `semantic_version` in each version dict appended to `version_list`
- [ ] T019 [US2] Update version history modal rendering in `src/web/static/ts/app.ts`: in the function that builds version history list items, display `v{semantic_version}` badge if non-null, else display "Unversioned" label
- [ ] T020 [US2] Update the version history modal HTML in `src/web/templates/index.html` to include a placeholder element for the version badge in each history row (if not already rendered purely from JS)

**Checkpoint**: Scenarios 3 & 4 from `quickstart.md` pass. Version history shows correct labels for all entries, no blank fields.

---

## Phase 5: User Story 3 — Copy with Version Metadata (Priority: P3)

**Goal**: A "Copy with version metadata" button copies the prompt content plus an HTML comment metadata line to the clipboard. Blocked gracefully when no version is set.

**Independent Test**: On a `1.1.0` prompt, click the button, paste into a text editor — last line is `<!-- prompt-version: 1.1.0 | ... -->`. On an unversioned prompt, clicking shows an error toast. See `quickstart.md` Scenarios 5 & 6.

### Implementation for User Story 3

- [ ] T021 [US3] Add `POST /api/prompts/{prompt_id}/copy-with-version` endpoint in `src/web/routers/prompts.py`: return `{"content": "<prompt_content>\n<!-- prompt-version: X.Y.Z | This line is metadata — ignore when processing this prompt. -->", "semantic_version": "X.Y.Z"}`; return `409` with `{"error": "no_version_set", ...}` when `semantic_version` is null
- [ ] T022 [US3] Add "Copy with version metadata" button to prompt detail view in `src/web/templates/index.html` (visible only when `semantic_version` is set, or always visible but shows error on click when unset)
- [ ] T023 [US3] Implement click handler in `src/web/static/ts/app.ts`: call `POST /api/prompts/{id}/copy-with-version`, on success write `response.content` to `navigator.clipboard.writeText()` and show success toast; on `409` show error toast "Assign a semantic version before copying with metadata."

**Checkpoint**: Scenarios 5 & 6 from `quickstart.md` pass. Clipboard contains correct content with metadata line. Error case shows toast without clipboard write.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Test coverage, i18n keys, and final integration validation.

- [ ] T024 [P] Write unit tests for `semantic_version` Pydantic validator (valid formats, invalid formats, empty string normalization) in `tests/unit/test_semantic_version_validation.py`
- [ ] T025 [P] Write unit tests for `POST /api/prompts/{id}/copy-with-version` endpoint (200 with version, 409 without version, 404 unknown prompt) in `tests/unit/test_copy_with_version.py`
- [ ] T026 [P] Update existing integration tests in `tests/integration/test_prompt_versioning_e2e.py` to assert `semantic_version` is present/null in prompt and version history responses
- [ ] T027 Add i18n translation keys for new UI strings (version field label, badge, copy button, error messages, "Unversioned" label) in the i18n JSON files used by `src/web/static/ts/app.ts`
- [ ] T028 Run full validation suite: `python -m pytest tests/ -v --cov=src --cov-report=term-missing && npm run typecheck && npm run lint && npm run test:unit:coverage`
- [ ] T029 Run quickstart.md validation scenarios manually against `python run_web.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Migration)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 (migration must exist before models reference columns)
- **Phase 3 (US1)**: Depends on Phase 2 — BLOCKS until foundational models/validators are done
- **Phase 4 (US2)**: Depends on Phase 2; independently testable from US1 (reads `PromptVersion.semantic_version` set by Phase 2 + US1 write path)
- **Phase 5 (US3)**: Depends on Phase 2 + US1 (needs `Prompt.semantic_version` to be writable)
- **Phase 6 (Polish)**: Depends on Phases 3–5 being complete

### User Story Dependencies

- **US1 (P1)**: No story dependencies — starts after Phase 2
- **US2 (P2)**: No hard dependency on US1, but version labels in history are only meaningful once US1 can write them. Can implement and test independently (will show "Unversioned" on all entries until US1 is done)
- **US3 (P3)**: Requires US1 (needs `Prompt.semantic_version` to be populated by the update path)

### Parallel Opportunities

- T003 and T004 (model column additions) can run in parallel — different files
- T005 and T006 (Pydantic validators) can run in parallel — same file, adjacent additions, merge carefully
- T007 and T008 (response model + TS interface) can run in parallel — different files/languages
- T009, T014, T015 (repository + form UI + frontend validation) can run in parallel within US1
- T024, T025, T026 (all test files) can run in parallel in Phase 6

---

## Parallel Example: Phase 2 (Foundational)

```text
# These four tasks touch different files and can proceed simultaneously:
T003: src/db/models/prompt.py           → add semantic_version column
T004: src/db/models/prompt_version.py   → add semantic_version column
T007: src/web/models/prompt_responses.py → add semantic_version field
T008: src/web/static/ts/app.ts          → extend VersionSummary interface
```

## Parallel Example: Phase 6 (Tests)

```text
# All three test files are independent:
T024: tests/unit/test_semantic_version_validation.py
T025: tests/unit/test_copy_with_version.py
T026: tests/integration/test_prompt_versioning_e2e.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (migration) + Phase 2 (foundational)
2. Complete Phase 3 (US1: form field, badge, write/read path)
3. **STOP and VALIDATE**: Run quickstart Scenarios 1 & 2
4. Ship or demo version display — immediately useful

### Incremental Delivery

1. Phase 1 + Phase 2 → foundation ready
2. Phase 3 (US1) → users can set and see version — MVP ✅
3. Phase 4 (US2) → version history labeled — useful for changelog audit
4. Phase 5 (US3) → copy-with-metadata — cross-platform comparison workflow complete
5. Phase 6 → coverage gate, i18n, final validation

---

## Notes

- [P] = different files, no shared incomplete dependencies — safe to parallelize
- All new frontend logic in `src/web/static/ts/` only — no edits to `src/web/static/js/`
- Pydantic validation covers the backend; frontend validation (T015) is a UX layer, not a security gate
- `X-Version-Downgrade` warning header (T011) is informational only — the write proceeds regardless
- i18n keys (T027) should use the existing translation key pattern in the project (e.g., `version.semanticVersion`, `version.copyWithMetadata`, `version.unversioned`)
- Coverage gate ≥ 85% is non-negotiable (Constitution Principle II) — do not skip T024–T026
