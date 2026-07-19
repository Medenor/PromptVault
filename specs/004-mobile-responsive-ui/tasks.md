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

- [x] T001 Create icon assets (192x192, 512x512, maskable) under `src/web/static/images/icons/`
- [x] T002 [P] Create `src/web/static/manifest.json` per contract in `specs/004-mobile-responsive-ui/contracts/offline-sync.md` (name, icons, start_url, display: standalone, theme_color/background_color matching `tailwind.config.ts`)
- [x] T003 [P] Add `<link rel="manifest">` and theme-color meta tag to the shared base template (locate the layout included by `src/web/templates/index.html` and `src/web/templates/import_export.html`)
- [x] T004 [P] Configure Tailwind `darkMode: 'class'` in `tailwind.config.ts` if not already set

**Checkpoint**: Manifest and icons installable-ready; base template wired for later dark-mode/gesture/nav work

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T005 Add Tailwind responsive breakpoint audit pass: identify current tap-target, overflow, and layout issues in `src/web/templates/index.html` and `src/web/templates/import_export.html` (audit output feeds US1 tasks; no code changes yet)
- [x] T006 [P] Add a Vite build entry for the Service Worker so `src/web/static/ts/sw.ts` compiles to a standalone `src/web/static/sw.js` (not bundled into the main app chunk), per `research.md` decision on SW build output
- [x] T007 [P] Create `src/web/static/ts/utils/dom-a11y-helpers.ts` (or extend existing `src/web/static/ts/utils/a11y.ts`) with a shared focus-trap helper for use by the nav drawer and full-screen modals/search overlay
- [x] T008 Create Playwright mobile device projects (`iPhone 14`, `Pixel 7`) in `playwright.config.ts` if not already present, so all US test files below can target `--project=mobile`

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Navigate and manage prompts on a phone (Priority: P1) 🎯 MVP

**Goal**: Replace the desktop-only layout with a mobile navigation drawer, 44px touch targets, full-screen modals, and keyboard-safe editing on viewports 320px-768px.

**Independent Test**: Load the app at 375px width, open the drawer via hamburger, navigate, tap into a prompt, and edit it — no horizontal scroll, no mis-taps, keyboard doesn't obscure the active field.

### Tests for User Story 1

- [x] T009 [P] [US1] Vitest unit test for drawer open/close/focus-trap logic in `src/web/static/ts/__tests__/mobile-nav.test.ts`
- [x] T010 [P] [US1] Playwright test: hamburger opens drawer, outside-tap closes it, no horizontal scroll at 320/375/425/768px in `tests/e2e/mobile-nav.spec.ts`
- [x] T011 [P] [US1] Playwright test: touch targets ≥44x44px on primary mobile screens (prompt list, prompt editor) in `tests/e2e/mobile-touch-targets.spec.ts`
- [x] T012 [P] [US1] Playwright test: full-screen modal on mobile vs. centered dialog on desktop for the prompt editor in `tests/e2e/mobile-modals.spec.ts`
- [x] T013 [P] [US1] Playwright test: virtual keyboard does not obscure the focused input on mobile in `tests/e2e/mobile-keyboard.spec.ts`

### Implementation for User Story 1

- [x] T014 [US1] Implement `src/web/static/ts/mobile-nav.ts`: hamburger toggle, slide-out drawer, focus trap (using T007 helper), outside-tap/Escape close, ARIA roles/labels (`role="dialog"`, `aria-expanded`) (depends on T007)
- [x] T015 [US1] Wire `mobile-nav.ts` into `src/web/static/ts/app.ts` entry point
- [x] T016 [US1] Update `src/web/templates/index.html` (and the shared base layout) to replace the current `hidden md:block` sidebar pattern with a drawer container + hamburger trigger markup, removing horizontal-scroll-prone layout at narrow widths (unified the pre-existing filters drawer + separate mobile-menu dropdown into one `#mobile-sidebar` drawer per user decision)
- [x] T017 [US1] [P] Update Tailwind utility classes across `src/web/templates/index.html` interactive elements (buttons, menu items, prompt card actions) to guarantee 44x44px minimum touch targets on mobile breakpoints (applied to both the Jinja fallback markup and the real JS-rendered card template in `app.ts`)
- [x] T018 [US1] [P] Update modal markup to use full-screen layout on mobile (`sm:` breakpoint container swap) and centered dialog on desktop (scope corrected: applied to the actual `role="dialog"` modals in `index.html` — version-history and diff — since `import_export.html` has no modals)
- [x] T019 [US1] Implement responsive font sizing using `clamp()` in the relevant Tailwind/CSS layer for prompt titles/body text (mobile-readability requirement)
- [x] T020 [US1] Implement virtual-keyboard-safe scroll behavior (e.g., `scrollIntoView` on focus, or `interactive-widget=resizes-content` viewport meta) in `src/web/static/ts/mobile-nav.ts` or a small dedicated module, applied to the prompt editor's text inputs
- [x] T021 [US1] Implement a full-screen search overlay component (`src/web/static/ts/mobile-nav.ts` or new `search-overlay.ts`) replacing the desktop inline search bar on mobile viewports, with the shared focus-trap helper
- [x] T022 [US1] Implement "Read More" smart truncation for long prompt text on mobile card/list views in `src/web/templates/index.html` + a small TS helper for expand/collapse state
- [x] T023 [US1] Run `npm run typecheck && npm run lint` and fix any issues introduced by T014-T022
- [x] T024 [US1] Run `npm run test:unit:coverage` and confirm new TS modules keep the suite ≥85% coverage

**Checkpoint**: User Story 1 fully functional and independently testable — mobile nav, touch targets, modals, keyboard handling, search overlay all working without touching offline/gesture code.

---

## Phase 4: User Story 2 - View and copy prompts offline (Priority: P2)

**⚠️ SCOPE CHANGE (post-hoc)**: T025-T039 below originally built offline **write** support (IndexedDB queue, auto-sync on reconnect, `expected_version` conflict detection). After real-device testing surfaced problems with that approach, offline scope was narrowed to **read/copy-only** — editing, creating, deleting, reverting, bulk actions, and secondary-page navigation are now blocked client-side while offline instead of queued. The queue/sync/conflict subsystem (`offline-queue.ts`, `offline-sync.ts`, the `TestUpdatePromptVersionConflict` backend tests, `check_version_conflict`/`VersionConflictResult`, `offline-sync.spec.ts`, `offline-conflict.spec.ts`) was removed entirely rather than left disabled. T025, T027, T029, T030, T033-T036 are historical record of work that was later reverted — see `contracts/offline-sync.md` and `data-model.md` for the current (read-only) contract. T026, T028, T031, T032, T037-T039 remain accurate for the caching/indicator pieces that were kept.

**Goal**: Cache previously-viewed prompts and static assets via a Service Worker so the main prompt list remains viewable and copyable offline; block all write actions and secondary-page navigation while offline with a clear message.

**Independent Test**: Load online, go offline, confirm cached prompts remain viewable with an offline indicator, copy a prompt (with and without version), confirm create/edit/delete/secondary-nav are all blocked with a "reconnect to continue" message, then restore connectivity and confirm normal editing works again.

### Tests for User Story 2

- [x] T025 [P] [US2] ~~Vitest unit test for `OfflineQueueEntry` CRUD + status transitions~~ — removed with the offline queue (see scope-change note above)
- [x] T026 [P] [US2] Vitest unit test for Service Worker registration + offline-indicator wiring in `src/web/static/ts/__tests__/sw-register.test.ts`
- [x] T027 [P] [US2] ~~pytest test for `expected_version` conflict detection~~ — removed with the conflict-detection backend code (see scope-change note above)
- [x] T028 [P] [US2] Playwright test: cached prompts remain viewable offline with visible offline indicator in `tests/e2e/offline-cache.spec.ts` (using `context.setOffline(true)`) — WebKit skipped (Playwright driver limitation, verified manually); requires AUTH_ENABLED=true + test-admin login
- [x] T029 [P] [US2] ~~Playwright test: offline edit queues, then auto-syncs~~ — removed (`offline-sync.spec.ts` deleted), editing is now blocked offline rather than queued
- [x] T030 [P] [US2] ~~Playwright test: conflicting concurrent offline edits~~ — removed (`offline-conflict.spec.ts` deleted), no longer applicable

### Implementation for User Story 2

- [x] T031 [US2] Implement `src/web/static/ts/sw.ts`: cache static assets (CSS/JS/manifest/icons) and previously-fetched prompt API responses using the Cache API, with a cache-versioning/invalidation strategy (depends on T006 build entry) — also caches navigation requests so a reload while offline has a shell to fall back to; served at root `/sw.js` (new route in app.py) instead of `/static/dist/sw.js` so its scope covers the whole app. Later revised to precache the shell + linked assets on `install` (a page is never controlled by the Service Worker that installs it, so a first-ever visit would otherwise leave the cache empty) and to scope caching to `/` only, since secondary pages are no longer accessible offline.
- [x] T032 [US2] Implement `src/web/static/ts/sw-register.ts`: register the compiled `sw.js`, listen for `online`/`offline` events, render the persistent offline indicator (depends on T031)
- [x] T033 [US2] ~~Implement `src/web/static/ts/utils/offline-queue.ts`~~ — removed (see scope-change note above)
- [x] T034 [US2] ~~Implement sync replay logic~~ — removed (see scope-change note above)
- [x] T035 [US2] ~~Implement conflict notification UI~~ — removed (see scope-change note above)
- [x] T036 [US2] ~~Add `expected_version` optional form field handling to `update_prompt`~~ — removed; `check_version_conflict`/`VersionConflictResult` deleted from `src/services/prompt_versioning_service.py`
- [x] T037 [US2] Wire `sw-register.ts` into `src/web/static/ts/app.ts`, gating prompt create/edit/delete/revert/bulk-action UI (and secondary-page navigation via `window.__requireOnlineNav`) behind `navigator.onLine` instead of queuing when offline — also fixed a pre-existing gap where checkAdminAccess() redirected to /auth/login on ANY /api/auth/me failure including network errors, which broke offline access entirely for authenticated deployments
- [x] T038 [US2] Run `python3 -m pytest` and confirm the updated router/service logic keeps backend coverage ≥85%
- [x] T039 [US2] Run `npm run typecheck && npm run lint && npm run test:unit:coverage` for the new TS modules

**Checkpoint**: User Stories 1 AND 2 both work independently — offline browsing and copying (read-only) functional on top of the P1 mobile layout; all write actions and secondary pages correctly require connectivity.

---

## Phase 5: User Story 3 - Use touch gestures and an installable app shortcut (Priority: P3)

**Goal**: Add swipe-to-edit/delete on prompt cards, pull-to-refresh on the prompt list, a FAB for new prompts, a swipeable version-history carousel, pinch-to-zoom/horizontal-scroll for long content, and confirm PWA installability.

**Independent Test**: Swipe a card left/right to reveal delete/edit actions (each with an accessible button fallback), pull down to refresh the list, and use "Add to Home Screen" to install the app with its own icon/name.

### Tests for User Story 3

- [x] T040 [P] [US3] Vitest unit test for swipe-reveal and pull-to-refresh Pointer Event handling in `src/web/static/ts/__tests__/gestures.test.ts` — jsdom lacks PointerEvent, tests build it from MouseEvent + defineProperty
- [x] T041 [P] [US3] Playwright test: swipe-left reveals delete action requiring confirmation, swipe-right reveals edit action, in `tests/e2e/gestures-swipe.spec.ts` — also covers the version-history carousel swipe (T049)
- [x] T042 [P] [US3] Playwright test: pull-to-refresh reloads the prompt list with a loading affordance, in `tests/e2e/gestures-pull-refresh.spec.ts`
- [x] T043 [P] [US3] Playwright test: every gesture action has a visible, keyboard/screen-reader-reachable equivalent control (FR-020) in `tests/e2e/gestures-a11y.spec.ts`
- [x] T044 [P] [US3] Playwright test: PWA installability (manifest fields present, "Add to Home Screen" affordance available) in `tests/e2e/pwa-install.spec.ts`

### Implementation for User Story 3

- [x] T045 [US3] Implement `src/web/static/ts/gestures.ts`: Pointer-Event-based swipe-reveal (left → delete action, right → edit action) with a confirming tap step for delete, per `research.md` gesture decision
- [x] T046 [US3] [P] [US3] Extend `gestures.ts` (or add a sibling module) with pull-to-refresh handling on the prompt list container, including a loading affordance
- [x] T047 [US3] Add visible, accessible fallback buttons (edit/delete/refresh) alongside every gesture-driven action in `src/web/templates/index.html`, wired to the same handlers as the gestures (depends on T045, T046) — Edit/Delete already existed as card buttons; added the Refresh button + loading indicator
- [x] T048 [US3] Implement a floating action button (FAB) for "New Prompt" in `src/web/templates/index.html` + supporting styles, visible only on mobile breakpoints
- [x] T049 [US3] [P] [US3] Implement a touch-friendly swipeable carousel for version history in the prompt detail/version view template, using `gestures.ts` primitives — mobile-only one-at-a-time paging with visible prev/next + position indicator; desktop keeps the vertical list unchanged
- [x] T050 [US3] [P] [US3] Enable pinch-to-zoom and horizontal-scroll containment for long prompt content and the diff viewer on mobile (viewport meta + CSS `overflow-x`/`touch-action` adjustments), without affecting desktop layout — pinch-zoom was already unrestricted (no user-scalable=no); added overflow-x-auto + touch-action to the diff viewer
- [x] T051 [US3] Implement `prefers-color-scheme` dark mode bootstrap script (adds/removes `dark` class on `<html>`) per `research.md` decision, loaded from the base template before first paint to avoid flash-of-wrong-theme — applied to all 12 page templates for consistency, not just index.html
- [x] T052 [US3] Apply `dark:` Tailwind variants across `src/web/templates/index.html` and `src/web/templates/import_export.html` primary UI surfaces — also covered JS-rendered surfaces (prompt cards, version history, diff viewer, tag autocomplete) in app.ts
- [x] T053 [US3] Implement lazy-loading for non-critical images/assets (`loading="lazy"` + any needed TS intersection-observer helper) across mobile views — verified not applicable: the only `<img>` in scope is the above-the-fold header logo (should not be lazy-loaded); no other images exist in current templates or JS-rendered content
- [x] T054 [US3] Wire `gestures.ts` and the dark-mode bootstrap into `src/web/static/ts/app.ts`
- [x] T055 [US3] Run `npm run typecheck && npm run lint && npm run test:unit:coverage` for gesture/dark-mode modules — 221 tests passing, 91.85% coverage

**Checkpoint**: All user stories independently functional — full mobile experience (nav, offline, gestures, install, dark mode) complete.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that span multiple user stories, and final validation

- [x] T056 [P] Add mobile-specific ARIA audit pass across drawer, FAB, swipe actions, and search overlay (FR-020) — extend or add to existing accessibility test coverage (`@axe-core/playwright` is already a dependency). Implemented in `tests/e2e/mobile-aria-audit.spec.ts` (8 tests: drawer, search overlay, FAB, swipe-delete-confirm dialog, full-page scan — all axe-clean, zero violations)
- [x] T057 [P] Add landscape-tablet layout check (≥768px width uses desktop layout per FR-021) as a Playwright test in `tests/e2e/tablet-landscape.spec.ts`. Verifies desktop sidebar visible / mobile nav-toggle+FAB hidden at 1024px and exactly at the 768px boundary, and the inverse at 767px
- [x] T058 Performance check: verify prompt list is interactive within 3s on simulated 4G on a mid-tier emulated device (SC-007), using Playwright's network throttling. Implemented in `tests/e2e/mobile-performance.spec.ts` using Chromium CDP `Network.emulateNetworkConditions` (Regular 4G profile) + 4x CPU throttling; measured ~1.9s to interactive (well under the 3s budget). Chromium-only (CDP not available on WebKit/Firefox drivers) — test skips cleanly on other engines
- [x] T059 Docker parity check: validate the feature under `docker-compose up --build` per constitution Development Workflow item 6. Verified in an isolated project-scoped compose stack (temporary override for container names/port to avoid colliding with a pre-existing unrelated stack on the same host, torn down after): image builds clean, container reaches healthy, `/sw.js` and `/static/manifest.json` both 200, login page renders with manifest link + theme-color meta. No new env vars/dependencies introduced by this feature
- [x] T060 Run full `specs/004-mobile-responsive-ui/quickstart.md` validation sweep (pytest, typecheck, lint, unit coverage, Playwright mobile suite) and record results. Results: `pytest` 2023 passed / 6 pre-existing unrelated `test_scheduler.py` failures (established baseline) / 5 skipped, 86.20% coverage (gate: ≥85%); `npm run typecheck` clean; `npm run lint` clean; `npm run test:unit:coverage` 221 passed, 91.85% coverage (gate: ≥85%); Playwright mobile suite (`mobile`, `iPhone 14`, `Pixel 7` projects, excluding the unrelated pre-existing `landmarks.spec.ts` which is hardcoded to port 8003 independent of this feature) — 36 passed, 4 skipped (WebKit-only skips for CDP-dependent/known-limitation specs), 0 failed; `offline-sync.spec.ts` and `offline-conflict.spec.ts` separately re-verified passing with `AUTH_ENABLED=true` + real login per the earlier scoping decision, then `.env` reverted to `AUTH_ENABLED=false`
- [x] T061 Update project documentation (README mobile/PWA section) reflecting the new capabilities. Added a "Mobile-Responsive UI & PWA" subsection under Usage/Features in `README.md` covering navigation, touch targets/layout, search overlay, gestures, offline support, installability, and dark mode; updated the top-level Features bullet to point to it

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
