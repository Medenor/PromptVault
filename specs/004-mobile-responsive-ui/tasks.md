---
description: 'Task list for Mobile-Responsive UI Enhancements'
---

# Tasks: Mobile-Responsive UI Enhancements

**Input**: Design documents from `/specs/004-mobile-responsive-ui/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/offline-sync.md, quickstart.md

**Tests**: Included per task, per Constitution Principle II (Test Coverage Gate, NON-NEGOTIABLE — ≥85% coverage, tests alongside implementation, not after).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

Single project, existing structure: `src/web/templates/`, `src/web/static/ts/`, `src/web/routers/`, `tests/` (pytest), Vitest specs co-located under `src/web/static/ts/__tests__/`, Playwright specs under the project's existing e2e location per `playwright.config.ts`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Base assets and scaffolding shared by all user stories

- [ ] T001 Create icon assets (192x192, 512x512, maskable) under `src/web/static/images/icons/`
- [ ] T002 [P] Create `src/web/static/manifest.json` per contract in `specs/004-mobile-responsive-ui/contracts/offline-sync.md` (name, icons, start_url, display: standalone, theme_color/background_color matching `tailwind.config.ts`)
- [ ] T003 [P] Add `<link rel="manifest">` and theme-color meta tag to the shared base template (locate the layout included by `src/web/templates/index.html` and `src/web/templates/import_export.html`)
- [ ] T004 [P] Configure Tailwind `darkMode: 'class'` in `tailwind.config.ts` if not already set

**Checkpoint**: Manifest and icons installable-ready; base template wired for later dark-mode/gesture/nav work

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Add Tailwind responsive breakpoint audit pass: identify current tap-target, overflow, and layout issues in `src/web/templates/index.html` and `src/web/templates/import_export.html` (audit output feeds US1 tasks; no code changes yet)
- [ ] T006 [P] Add a Vite build entry for the Service Worker so `src/web/static/ts/sw.ts` compiles to a standalone `src/web/static/sw.js` (not bundled into the main app chunk), per `research.md` decision on SW build output
- [ ] T007 [P] Create `src/web/static/ts/utils/dom-a11y-helpers.ts` (or extend existing `src/web/static/ts/utils/a11y.ts`) with a shared focus-trap helper for use by the nav drawer and full-screen modals/search overlay
- [ ] T008 Create Playwright mobile device projects (`iPhone 14`, `Pixel 7`) in `playwright.config.ts` if not already present, so all US test files below can target `--project=mobile`

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Navigate and manage prompts on a phone (Priority: P1) 🎯 MVP

**Goal**: Replace the desktop-only layout with a mobile navigation drawer, 44px touch targets, full-screen modals, and keyboard-safe editing on viewports 320px-768px.

**Independent Test**: Load the app at 375px width, open the drawer via hamburger, navigate, tap into a prompt, and edit it — no horizontal scroll, no mis-taps, keyboard doesn't obscure the active field.

### Tests for User Story 1

- [ ] T009 [P] [US1] Vitest unit test for drawer open/close/focus-trap logic in `src/web/static/ts/__tests__/mobile-nav.test.ts`
- [ ] T010 [P] [US1] Playwright test: hamburger opens drawer, outside-tap closes it, no horizontal scroll at 320/375/425/768px in `tests/e2e/mobile-nav.spec.ts`
- [ ] T011 [P] [US1] Playwright test: touch targets ≥44x44px on primary mobile screens (prompt list, prompt editor) in `tests/e2e/mobile-touch-targets.spec.ts`
- [ ] T012 [P] [US1] Playwright test: full-screen modal on mobile vs. centered dialog on desktop for the prompt editor in `tests/e2e/mobile-modals.spec.ts`
- [ ] T013 [P] [US1] Playwright test: virtual keyboard does not obscure the focused input on mobile in `tests/e2e/mobile-keyboard.spec.ts`

### Implementation for User Story 1

- [ ] T014 [US1] Implement `src/web/static/ts/mobile-nav.ts`: hamburger toggle, slide-out drawer, focus trap (using T007 helper), outside-tap/Escape close, ARIA roles/labels (`role="dialog"`, `aria-expanded`) (depends on T007)
- [ ] T015 [US1] Wire `mobile-nav.ts` into `src/web/static/ts/app.ts` entry point
- [ ] T016 [US1] Update `src/web/templates/index.html` (and the shared base layout) to replace the current `hidden md:block` sidebar pattern with a drawer container + hamburger trigger markup, removing horizontal-scroll-prone layout at narrow widths
- [ ] T017 [US1] [P] Update Tailwind utility classes across `src/web/templates/index.html` interactive elements (buttons, menu items, prompt card actions) to guarantee 44x44px minimum touch targets on mobile breakpoints
- [ ] T018 [US1] [P] Update `src/web/templates/import_export.html` modal markup to use full-screen layout on mobile (`sm:` breakpoint container swap) and centered dialog on desktop
- [ ] T019 [US1] Implement responsive font sizing using `clamp()` in the relevant Tailwind/CSS layer for prompt titles/body text (mobile-readability requirement)
- [ ] T020 [US1] Implement virtual-keyboard-safe scroll behavior (e.g., `scrollIntoView` on focus, or `interactive-widget=resizes-content` viewport meta) in `src/web/static/ts/mobile-nav.ts` or a small dedicated module, applied to the prompt editor's text inputs
- [ ] T021 [US1] Implement a full-screen search overlay component (`src/web/static/ts/mobile-nav.ts` or new `search-overlay.ts`) replacing the desktop inline search bar on mobile viewports, with the shared focus-trap helper
- [ ] T022 [US1] Implement "Read More" smart truncation for long prompt text on mobile card/list views in `src/web/templates/index.html` + a small TS helper for expand/collapse state
- [ ] T023 [US1] Run `npm run typecheck && npm run lint` and fix any issues introduced by T014-T022
- [ ] T024 [US1] Run `npm run test:unit:coverage` and confirm new TS modules keep the suite ≥85% coverage

**Checkpoint**: User Story 1 fully functional and independently testable — mobile nav, touch targets, modals, keyboard handling, search overlay all working without touching offline/gesture code.

---

## Phase 4: User Story 2 - Work with prompts offline and sync seamlessly (Priority: P2)

**Goal**: Cache previously-viewed prompts and static assets via a Service Worker, queue offline edits in IndexedDB, and auto-sync with conflict detection when connectivity returns.

**Independent Test**: Load online, go offline, confirm cached prompts remain viewable with an offline indicator, edit a prompt, go back online, confirm the edit syncs automatically within 10s; verify a conflicting concurrent edit surfaces a notification instead of silently overwriting.

### Tests for User Story 2

- [ ] T025 [P] [US2] Vitest unit test for `OfflineQueueEntry` CRUD + status transitions in `src/web/static/ts/__tests__/offline-queue.test.ts` (mocking `indexedDB`)
- [ ] T026 [P] [US2] Vitest unit test for Service Worker registration + offline-indicator wiring in `src/web/static/ts/__tests__/sw-register.test.ts`
- [ ] T027 [P] [US2] pytest test for `expected_version` conflict detection on `PUT /prompts/{prompt_id}` (200 on match, 409 on mismatch) in `tests/unit/test_prompts_router.py` (or existing equivalent test file for `src/web/routers/prompts.py`)
- [ ] T028 [P] [US2] Playwright test: cached prompts remain viewable offline with visible offline indicator in `tests/e2e/offline-cache.spec.ts` (using `context.setOffline(true)`)
- [ ] T029 [P] [US2] Playwright test: offline edit queues, then auto-syncs within 10s of reconnect, in `tests/e2e/offline-sync.spec.ts`
- [ ] T030 [P] [US2] Playwright test: conflicting concurrent offline edits from two contexts surface a conflict notification instead of silent overwrite, in `tests/e2e/offline-conflict.spec.ts`

### Implementation for User Story 2

- [ ] T031 [US2] Implement `src/web/static/ts/sw.ts`: cache static assets (CSS/JS/manifest/icons) and previously-fetched prompt API responses using the Cache API, with a cache-versioning/invalidation strategy (depends on T006 build entry)
- [ ] T032 [US2] Implement `src/web/static/ts/sw-register.ts`: register the compiled `sw.js`, listen for `online`/`offline` events, render the persistent offline indicator (depends on T031)
- [ ] T033 [US2] [P] [US2] Implement `src/web/static/ts/utils/offline-queue.ts`: IndexedDB-backed `OfflineQueueEntry` store per `data-model.md` (add/list/update-status operations, `pending → syncing → (synced|conflict)` transitions)
- [ ] T034 [US2] Implement sync replay logic (in `sw-register.ts` or a new `offline-sync.ts`) that, on reconnect, replays `pending` queue entries via the existing prompt create/update endpoints with `expected_version`, per the contract in `specs/004-mobile-responsive-ui/contracts/offline-sync.md` (depends on T033)
- [ ] T035 [US2] Implement conflict notification UI (reusing `src/web/static/ts/utils/notifications.ts` if present) triggered when a queued entry's sync returns 409 (depends on T034)
- [ ] T036 [US2] Add `expected_version` optional form field handling to `update_prompt` in `src/web/routers/prompts.py:654`, comparing against the prompt's current version (via existing `VersionRepository`/`PromptVersion` data) and returning `409` with `{"error": "version_conflict", "current_version": ..., "current_prompt": {...}}` on mismatch — implemented in the service layer per Constitution Principle I, not directly in the router
- [ ] T037 [US2] Wire `sw-register.ts` and `offline-queue.ts` into `src/web/static/ts/app.ts`, hooking prompt edit/create UI actions to queue when offline instead of failing
- [ ] T038 [US2] Run `python3 -m pytest` and confirm the updated router/service logic keeps backend coverage ≥85%
- [ ] T039 [US2] Run `npm run typecheck && npm run lint && npm run test:unit:coverage` for the new TS modules

**Checkpoint**: User Stories 1 AND 2 both work independently — offline browsing, queuing, and conflict-aware sync all functional on top of the P1 mobile layout.

---

## Phase 5: User Story 3 - Use touch gestures and an installable app shortcut (Priority: P3)

**Goal**: Add swipe-to-edit/delete on prompt cards, pull-to-refresh on the prompt list, a FAB for new prompts, a swipeable version-history carousel, pinch-to-zoom/horizontal-scroll for long content, and confirm PWA installability.

**Independent Test**: Swipe a card left/right to reveal delete/edit actions (each with an accessible button fallback), pull down to refresh the list, and use "Add to Home Screen" to install the app with its own icon/name.

### Tests for User Story 3

- [ ] T040 [P] [US3] Vitest unit test for swipe-reveal and pull-to-refresh Pointer Event handling in `src/web/static/ts/__tests__/gestures.test.ts`
- [ ] T041 [P] [US3] Playwright test: swipe-left reveals delete action requiring confirmation, swipe-right reveals edit action, in `tests/e2e/gestures-swipe.spec.ts`
- [ ] T042 [P] [US3] Playwright test: pull-to-refresh reloads the prompt list with a loading affordance, in `tests/e2e/gestures-pull-refresh.spec.ts`
- [ ] T043 [P] [US3] Playwright test: every gesture action has a visible, keyboard/screen-reader-reachable equivalent control (FR-020) in `tests/e2e/gestures-a11y.spec.ts`
- [ ] T044 [P] [US3] Playwright test: PWA installability (manifest fields present, "Add to Home Screen" affordance available) in `tests/e2e/pwa-install.spec.ts`

### Implementation for User Story 3

- [ ] T045 [US3] Implement `src/web/static/ts/gestures.ts`: Pointer-Event-based swipe-reveal (left → delete action, right → edit action) with a confirming tap step for delete, per `research.md` gesture decision
- [ ] T046 [US3] [P] [US3] Extend `gestures.ts` (or add a sibling module) with pull-to-refresh handling on the prompt list container, including a loading affordance
- [ ] T047 [US3] Add visible, accessible fallback buttons (edit/delete/refresh) alongside every gesture-driven action in `src/web/templates/index.html`, wired to the same handlers as the gestures (depends on T045, T046)
- [ ] T048 [US3] Implement a floating action button (FAB) for "New Prompt" in `src/web/templates/index.html` + supporting styles, visible only on mobile breakpoints
- [ ] T049 [US3] [P] [US3] Implement a touch-friendly swipeable carousel for version history in the prompt detail/version view template, using `gestures.ts` primitives
- [ ] T050 [US3] [P] [US3] Enable pinch-to-zoom and horizontal-scroll containment for long prompt content and the diff viewer on mobile (viewport meta + CSS `overflow-x`/`touch-action` adjustments), without affecting desktop layout
- [ ] T051 [US3] Implement `prefers-color-scheme` dark mode bootstrap script (adds/removes `dark` class on `<html>`) per `research.md` decision, loaded from the base template before first paint to avoid flash-of-wrong-theme
- [ ] T052 [US3] Apply `dark:` Tailwind variants across `src/web/templates/index.html` and `src/web/templates/import_export.html` primary UI surfaces
- [ ] T053 [US3] Implement lazy-loading for non-critical images/assets (`loading="lazy"` + any needed TS intersection-observer helper) across mobile views
- [ ] T054 [US3] Wire `gestures.ts` and the dark-mode bootstrap into `src/web/static/ts/app.ts`
- [ ] T055 [US3] Run `npm run typecheck && npm run lint && npm run test:unit:coverage` for gesture/dark-mode modules

**Checkpoint**: All user stories independently functional — full mobile experience (nav, offline, gestures, install, dark mode) complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that span multiple user stories, and final validation

- [ ] T056 [P] Add mobile-specific ARIA audit pass across drawer, FAB, swipe actions, and search overlay (FR-020) — extend or add to existing accessibility test coverage (`@axe-core/playwright` is already a dependency)
- [ ] T057 [P] Add landscape-tablet layout check (≥768px width uses desktop layout per FR-021) as a Playwright test in `tests/e2e/tablet-landscape.spec.ts`
- [ ] T058 Performance check: verify prompt list is interactive within 3s on simulated 4G on a mid-tier emulated device (SC-007), using Playwright's network throttling
- [ ] T059 Docker parity check: validate the feature under `docker-compose up --build` per constitution Development Workflow item 6
- [ ] T060 Run full `specs/004-mobile-responsive-ui/quickstart.md` validation sweep (pytest, typecheck, lint, unit coverage, Playwright mobile suite) and record results
- [ ] T061 Update project documentation (README mobile/PWA section) reflecting the new capabilities

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — no dependency on US2/US3
- **User Story 2 (Phase 4)**: Depends on Foundational — functionally independent of US1, but benefits from US1's mobile shell existing first (recommended sequential order: US1 → US2)
- **User Story 3 (Phase 5)**: Depends on Foundational — gesture/FAB/dark-mode work touches the same templates as US1, so implementing after US1 avoids merge friction; PWA install (T044) only depends on Phase 1's manifest/icon work
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: No dependencies on other stories — MVP slice
- **User Story 2 (P2)**: Independently testable; the offline queue's conflict detection reuses versioning data already in the backend, not anything from US1
- **User Story 3 (P3)**: Independently testable; touch-target/template groundwork from US1 makes gesture wiring cleaner but is not a hard blocker

### Within Each User Story

- Tests written first, confirmed failing before implementation
- TS modules before template wiring where a module is a prerequisite (e.g., T014 before T016)
- Story complete (tests passing, coverage gate met) before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] (T002-T004) run in parallel after T001
- Foundational [P] tasks (T006, T007) run in parallel; T005 (audit) and T008 (Playwright config) can also run alongside them
- Once Foundational completes, US1/US2/US3 test-writing tasks within each phase (all marked [P]) can run in parallel
- Different user story phases can be staffed in parallel by different developers, though the recommended default is sequential P1 → P2 → P3 for a single implementer

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together:
Task: "Vitest unit test for drawer logic in src/web/static/ts/__tests__/mobile-nav.test.ts"
Task: "Playwright test: hamburger/drawer/no-horizontal-scroll in tests/e2e/mobile-nav.spec.ts"
Task: "Playwright test: touch targets >=44px in tests/e2e/mobile-touch-targets.spec.ts"
Task: "Playwright test: full-screen modal vs desktop dialog in tests/e2e/mobile-modals.spec.ts"
Task: "Playwright test: keyboard-safe input in tests/e2e/mobile-keyboard.spec.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Run `tests/e2e/mobile-nav.spec.ts` + touch-target/modal/keyboard suites, confirm quickstart.md US1 walkthrough passes
5. Deploy/demo if ready — this alone resolves the ticket's core "mobile usage is frustrating" complaint

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP)
3. Add User Story 2 → Test independently → Deploy/Demo (offline resilience)
4. Add User Story 3 → Test independently → Deploy/Demo (gestures + installability + dark mode)
5. Polish phase → final cross-cutting validation

---

## Notes

- [P] tasks touch different files with no unmet dependencies
- [Story] label maps every user-story-phase task to US1/US2/US3 for traceability
- Constitution's ≥85% coverage gate applies per story, not just at the end — run coverage checks at each story's checkpoint (T023-T024, T038-T039, T055) rather than deferring to Phase 6
- Constitution Principle IV (TypeScript-only frontend): all new client code goes under `src/web/static/ts/`; `src/web/static/js/app.js` is never edited
- Constitution Principle I (Layered Service Architecture): the only backend change (T036) implements conflict detection in the service layer, not directly in the router
- Avoid: vague tasks, same-file conflicts, cross-story hard dependencies that would break independent testability
