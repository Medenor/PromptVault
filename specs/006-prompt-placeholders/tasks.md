# Tasks: Dynamic Prompt Placeholders

**Input**: Design documents from `/specs/006-prompt-placeholders/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/placeholders-module.md, quickstart.md

**Tests**: Included — the plan's Constitution Check calls for unit tests before wiring the utility into call sites, and correctness of the detection/substitution regex logic is the core risk of this feature.

**Organization**: Tasks are grouped by user story (US1 = fill & copy, US2 = copy unfilled, US3 = non-regression across editing/versioning/search/filter/export).

## Path Conventions

Single web-app project, frontend-only change: `src/web/static/ts/` for source, `src/web/static/ts/utils/__tests__/` for Vitest unit tests (per `vitest.config.ts`), `tests/e2e/` for Playwright.

---

## Phase 1: Setup

**Purpose**: No new project scaffolding needed — reusing existing Vite/Vitest/Playwright setup and existing `createModal` component. Nothing to do here beyond confirming the branch is checked out.

- [ ] T001 Confirm branch `006-prompt-placeholders` is checked out and `npm install` / `npx playwright install` (if needed) succeed locally

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build and test the core detect/substitute utility that every user story depends on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [ ] T002 [P] Write failing Vitest unit tests for `detectPlaceholders()` in `src/web/static/ts/utils/__tests__/placeholders.test.ts`: distinct `[NAME]`/`{NAME}` tokens, repeated-token de-duplication, `[DURATION]` vs `{DURATION}` treated as distinct, malformed spans ignored (`[]`, unmatched `[abc`, nested `[[X]]`, multi-line span), first-seen order preserved, empty content returns empty array
- [ ] T003 [P] Write failing Vitest unit tests for `substitutePlaceholders()` in the same `src/web/static/ts/utils/__tests__/placeholders.test.ts`: filled tokens replaced everywhere they occur, unfilled tokens left byte-for-byte unchanged, a filled value containing placeholder-like text (`[NESTED]`) is not re-expanded (single-pass), empty `values` map returns content unchanged
- [ ] T004 Implement `PlaceholderToken` type, `detectPlaceholders()`, and `substitutePlaceholders()` in new file `src/web/static/ts/utils/placeholders.ts` per contracts/placeholders-module.md, making T002/T003 pass (depends on T002, T003)
- [ ] T005 Run `npx vitest run src/web/static/ts/utils/__tests__/placeholders.test.ts` and confirm all tests pass with no regressions to existing suites (depends on T004)

**Checkpoint**: Detection/substitution utility is correct and fully unit-tested — user story implementation can now begin.

---

## Phase 3: User Story 1 - Fill in placeholders and copy a ready-to-use prompt (Priority: P1) 🎯 MVP

**Goal**: Opening a prompt with placeholders shows a form with one field per distinct token; filling values and confirming copies the fully substituted text.

**Independent Test**: Open a prompt containing `[DURATION]`, `[TYPE OF PRESENTATION]`, `[INSERT PRESENTATION TITLE]`; confirm 3 fields appear; fill them in; confirm the copied text has all three substituted and everything else unchanged.

### Implementation for User Story 1

- [ ] T006 [US1] Add a placeholder-fill modal builder function (e.g. `openPlaceholderForm(tokens, onConfirm)`) in `src/web/static/ts/app.ts`, using the existing `createModal` helper from `@components` (same pattern as the keyboard-shortcuts-help modal around line 3653) with one labeled text input per `PlaceholderToken`
- [ ] T006a [US1] Add the modal's static chrome strings (title, confirm/cancel button labels, e.g. `placeholders.modalTitle`, `placeholders.copyButton`, `placeholders.cancelButton`) as new keys under a `placeholders` namespace in `src/web/static/locales/en.json`, mirror the same key paths in `de.json`, `fr.json`, `es.json`, and reference them via typed `t('placeholders.xxx')` calls in T006's modal builder — per constitution Principle IV (TypeScript-Only Frontend / typed i18n); per-field labels stay as the literal placeholder text (`PlaceholderToken.label`, e.g. `DURATION`), which is user-authored content, not translatable UI chrome, so it is NOT run through `t()` (depends on T006)
- [ ] T007 [US1] Wire `copyPrompt()` in `src/web/static/ts/app.ts` (~line 2179) to call `detectPlaceholders()` on the fetched/cached prompt content; if non-empty, open the modal from T006/T006a and, on confirm, call `substitutePlaceholders()` before passing the result to `copyTextToClipboard()` (depends on T004, T006, T006a)
- [ ] T008 [US1] Wire `copyPromptWithVersion()` in `src/web/static/ts/app.ts` (~line 2139) with the same detect → form → substitute flow before the `navigator.clipboard.writeText(data.content)` call (depends on T004, T006, T006a)
- [ ] T009 [P] [US1] Write Playwright e2e spec `tests/e2e/prompt-placeholders.spec.ts` covering: opening a prompt with 3 known placeholders shows 3 labeled fields, filling all 3 and confirming produces the exact expected substituted text on the clipboard (per quickstart.md scenario)

**Checkpoint**: User Story 1 fully functional and independently testable — this is the MVP.

---

## Phase 4: User Story 2 - Copy a prompt with placeholders left unfilled (Priority: P2)

**Goal**: Users can copy with some/all fields blank; unfilled placeholders remain as their original token; copying without ever opening the form is equivalent to raw copy.

**Independent Test**: Open a prompt with placeholders, leave all fields blank, confirm; copied text equals the original raw prompt content unchanged. Leave one of several fields blank; confirm only that one token remains literal in the output.

### Implementation for User Story 2

- [ ] T010 [US2] Confirm (and adjust if needed) that the modal built in T006 allows submitting with any subset of fields empty, and that `substitutePlaceholders()` is called with only the non-empty entries in the values map (depends on T004, T006, T007, T008)
- [ ] T011 [P] [US2] Extend `tests/e2e/prompt-placeholders.spec.ts` (from T009) with cases: all fields left blank → clipboard equals original raw content; one field left blank among several filled → only that token remains literal in the output
- [ ] T012 [P] [US2] Extend `src/web/static/ts/utils/__tests__/placeholders.test.ts` with a direct unit test asserting `substitutePlaceholders(content, new Map())` returns `content` unchanged (covers the "never opened the form" path at the utility level)

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Placeholders survive editing, versioning, search, filtering, and export (Priority: P2)

**Goal**: Non-regression — placeholder tokens are ordinary text everywhere except the new copy-time form; no backend behavior changes.

**Independent Test**: Edit a prompt's placeholders and confirm the form reflects the current content; confirm version history, search, filter, and export are byte-for-byte unaffected by placeholder tokens.

### Implementation for User Story 3

- [ ] T013 [US3] Confirm `copyPrompt()`/`copyPromptWithVersion()` (T007/T008) always re-run `detectPlaceholders()` against the latest fetched content rather than any cached token list, so edits are reflected on next open (depends on T007, T008)
- [ ] T013a [P] [US3] Confirm (per spec FR-004a) that no placeholder-form code is added to the version-history modal (`#version-history-modal`) or diff view (`displayDiff`/`renderCharacterDiff`) in `src/web/static/ts/app.ts` — those per-version "Revert" and "Select for diff" actions remain untouched and text-only; add a Playwright e2e case asserting the diff/history modal shows no placeholder input fields even when the prompt's current or historical content contains placeholder tokens
- [ ] T014 [P] [US3] Run existing backend suites unmodified to confirm no regression: `pytest tests/test_prompt_versioning_service.py tests/test_prompt_import_export_service.py tests/test_copy_with_version.py`
- [ ] T015 [P] [US3] Add a Playwright e2e case to `tests/e2e/prompt-placeholders.spec.ts`: edit a prompt to change its set of placeholders, reopen the copy form, and confirm the field set matches the new content (not the old one)
- [ ] T016 [P] [US3] Manually verify (or add a lightweight assertion in the e2e spec) that searching for placeholder-token substrings and exporting a prompt containing placeholders return the same results/content as before this feature, per quickstart.md's regression checks

**Checkpoint**: All three user stories independently functional; no regressions in existing features.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation across the whole feature.

- [ ] T017 Run `npm run typecheck` and `npm run lint` and fix any issues introduced by `placeholders.ts` or `app.ts` changes
- [ ] T018 Run full quickstart.md validation end-to-end (unit tests, e2e spec, backend regression suites) and confirm every step passes
- [ ] T019 [P] Update relevant user-facing docs (e.g. README feature list) to mention placeholder support, if the project's doc conventions call for it

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (the detect/substitute utility is shared by every story).
- **User Story 1 (Phase 3)**: Depends on Foundational. This is the MVP.
- **User Story 2 (Phase 4)**: Depends on Foundational and on the modal/wiring built in Phase 3 (T006-T008, including T006a) since it exercises the same UI path with different inputs.
- **User Story 3 (Phase 5)**: Depends on Foundational and Phase 3 wiring (T007/T008); mostly regression verification, can run in parallel with Phase 4 once Phase 3 lands. T013a has no dependency on Phase 3 wiring since it verifies the *absence* of new code in the version-history/diff view.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### Within Each User Story

- Tests before/alongside implementation where practical (unit tests for the utility are strictly first, per Phase 2).
- Utility (Phase 2) before UI wiring (Phase 3).
- Phase 3 wiring before Phase 4/5 verification, since both build on the same modal and call-site changes.

### Parallel Opportunities

- T002 and T003 (unit test files, same file but independent test blocks — write together, can be drafted in parallel by different people if desired).
- T009, T011, T012 can be worked in parallel once their preceding implementation tasks land.
- T013a, T014, T015, T016 in Phase 5 are independent of each other and can run in parallel.

---

## Parallel Example: Foundational Phase

```bash
# Draft both unit-test blocks together before implementation:
Task: "Write failing tests for detectPlaceholders() in src/web/static/ts/utils/__tests__/placeholders.test.ts"
Task: "Write failing tests for substitutePlaceholders() in src/web/static/ts/utils/__tests__/placeholders.test.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (trivial — confirm environment).
2. Complete Phase 2: Foundational — this is the bulk of the risk (regex correctness) and is fully unit-tested before any UI work.
3. Complete Phase 3: User Story 1 — wire the modal into both copy call sites.
4. **STOP and VALIDATE**: Run the Phase 3 e2e spec independently; this alone satisfies the ticket's core ask.
5. Demo if ready — Story 1 alone delivers the feature's primary value.

### Incremental Delivery

1. Setup + Foundational → utility ready and proven correct in isolation.
2. User Story 1 → fill-and-copy works end-to-end (MVP).
3. User Story 2 → confirms the "escape hatch" (blank fields, raw copy) doesn't regress.
4. User Story 3 → confirms zero blast radius on existing backend/versioning/search/export.
5. Polish → typecheck/lint/full quickstart pass, docs updated.

---

## Notes

- No backend changes anywhere in this feature — every task above touches only `src/web/static/ts/`, `src/web/static/locales/`, and test files.
- [P] tasks touch independent test blocks/files or are read-only verification steps; sequential tasks share `app.ts` edits (T007, T008) or build directly on one another.
- T006a touches locale JSON files (`en.json`, `de.json`, `fr.json`, `es.json`), not `app.ts` directly, so it can be drafted alongside T006 but must land before T007/T008 reference the new `t()` keys.
- Per-field labels (the placeholder's own name, e.g. `DURATION`) are user-authored prompt content and are never passed through `t()` — only the modal's static chrome (title, button labels) is translated (see T006a).
- Commit after each phase checkpoint, consistent with how prior features (e.g. `005-pagination-lazy-loading`) were merged via PR per feature branch.
