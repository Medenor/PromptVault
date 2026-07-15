# Research: Mobile-Responsive UI Enhancements

## Decision: Frontend implementation language

**Decision**: All new client-side logic (navigation drawer, gestures, offline queue, Service Worker registration bootstrap) is written in TypeScript under `src/web/static/ts/`, compiled via the existing Vite build.

**Rationale**: Constitution Principle IV mandates TypeScript-only frontend work and explicitly forbids editing the legacy `src/web/static/js/` directory. The project already has a working `tsc && vite build` pipeline and typed `t('key.path')` i18n helpers to reuse.

**Alternatives considered**: Extending `app.js` directly — rejected, violates Principle IV. Introducing a frontend framework (React/Vue) for the mobile components — rejected by Simplicity/Anti-Abstraction gates and by the user's explicit constraint of not adding new frontend tooling beyond what already exists.

## Decision: Service Worker source and build output

**Decision**: Author the Service Worker as `src/web/static/ts/sw.ts`, compiled to a standalone `sw.js` at the static root (not bundled into the main app chunk), registered from `app.ts`. Use Vite's support for additional build entry points (or a small dedicated `tsc` compile step if Vite multi-entry output proves awkward) to emit `static/sw.js` alongside the existing bundle.

**Rationale**: Service Workers must be served from the origin root scope (or the scope path passed to `register()`) as a plain `.js` file — bundling it into the main hashed app chunk would break `navigator.serviceWorker.register()` and cache invalidation semantics. Keeping it as a discrete compiled output keeps the build additive rather than a rewrite of the existing Vite config.

**Alternatives considered**: Third-party SW tooling (Workbox) — rejected as an added dependency beyond what the ticket requires for a cache-static-assets + queue-offline-writes scope; a hand-rolled SW using the Cache API and IndexedDB is sufficient and keeps the dependency surface small (Simplicity gate).

## Decision: Offline write queue persistence — SUPERSEDED

**⚠️ This decision and its implementation were later reverted.** Real-device testing showed problems with the queue/sync/conflict approach; offline scope was narrowed to read/copy-only, and `offline-queue.ts` was deleted. See `contracts/offline-sync.md` for the current, accurate contract. Left below as historical record of the original design.

**Decision**: Use IndexedDB (via a small typed wrapper module `src/web/static/ts/utils/offline-queue.ts`) to persist queued create/edit operations, keyed by a client-generated operation ID, with fields `{id, promptId, operation, payload, timestamp, status}`.

**Rationale**: IndexedDB is the standard, dependency-free browser storage mechanism for structured offline data that must survive page reloads and be accessible from both the Service Worker and page contexts. `localStorage` is unsuitable (synchronous, string-only, not accessible from SW in all cases reliably for structured queries).

**Alternatives considered**: `localStorage` — rejected, string-only and awkward for structured queue records with status transitions. A dedicated backend "outbox" table — rejected as unnecessary; the queue is a client concern until sync, at which point it uses the existing prompt update endpoints.

## Decision: Offline sync conflict handling — SUPERSEDED

**⚠️ This decision and its implementation were later reverted**, along with the write queue above. There is no conflict detection in the current implementation — writes are simply blocked while offline. Left below as historical record.

**Decision**: Reuse the existing prompt update endpoint(s) for syncing queued changes. On sync, compare the queued change's base version/timestamp against the server's current version (already tracked per feature 001-prompt-versioning); if the server version has advanced past what the client last saw, mark the queued entry `conflict` and surface a notification rather than silently overwriting.

**Rationale**: Feature 001 already introduced prompt versioning — this gives a natural, already-existing signal for conflict detection without inventing new backend concepts, keeping this feature additive at the API layer (at most a version-check parameter on an existing endpoint, no new subsystem).

**Alternatives considered**: A dedicated `/api/sync` batch endpoint — considered, deferred as unnecessary complexity for the current scope (queue lengths are expected to be small — a handful of edits — since offline periods are commute-length, not extended outages); replaying queued operations via the existing per-prompt endpoints keeps the change additive per the Anti-Abstraction gate. Should batch sync volume become a real problem later, a dedicated endpoint can be introduced in a follow-up feature.

## Decision: Gesture handling approach

**Decision**: Implement swipe/pull-to-refresh gestures with native Pointer Events (`pointerdown`/`pointermove`/`pointerup`) in a small typed utility module, not a gesture library.

**Rationale**: The gesture surface needed (horizontal swipe reveal on a card, vertical pull-to-refresh) is narrow enough to implement directly in ~100-150 lines of typed code, avoiding a new runtime dependency. Every gesture action also requires a visible, keyboard/screen-reader-accessible equivalent control per FR-007/FR-008/FR-020, so the gesture layer is additive UI sugar on top of buttons that already need to exist.

**Alternatives considered**: Hammer.js or similar gesture libraries — rejected as an unnecessary dependency (unmaintained/legacy in Hammer's case) for a narrow, well-understood gesture set; native Pointer Events have full support in target browsers (iOS Safari, Android Chrome).

## Decision: PWA manifest and icons

**Decision**: Add `src/web/static/manifest.json` (or `manifest.webmanifest`) plus icon assets under `src/web/static/images/icons/` at standard sizes (192x192, 512x512, plus maskable variants), linked from the base template's `<head>`.

**Rationale**: Standard, framework-agnostic mechanism for "Add to Home Screen" on both iOS Safari and Android Chrome; no server-side generation needed, matches the constraint of adding assets under `src/web/static/`.

**Alternatives considered**: Dynamic manifest generation per-user/tenant — rejected as unneeded; PromptVault is self-hosted per-instance, so a static manifest reflecting instance branding is sufficient (icon color/name can be a config-time asset swap, not a runtime feature).

## Decision: Testing strategy

**Decision**: Use Playwright (already a dependency, `playwright.config.ts` present) with mobile device emulation profiles (`Pixel 7`, `iPhone 14`) for viewport/gesture/offline-mode E2E tests under `tests/e2e/` (or the project's existing Playwright test directory). Use Vitest for unit tests of the offline queue module, gesture utility, and Service Worker registration logic (mocking `caches`/`indexedDB` where needed, consistent with existing `ts/__tests__` patterns). Backend touch points (any conflict-check logic added to the existing prompt update endpoint) are covered with pytest per the existing ≥85% coverage gate.

**Rationale**: Matches existing project tooling exactly — no new test runner or framework introduced. Playwright supports `context.setOffline(true)` and touch/gesture simulation natively, covering the offline and gesture acceptance scenarios end-to-end.

**Alternatives considered**: Manual-only mobile device testing — rejected as insufficient for a constitution that requires tests alongside implementation and an 85% coverage gate.

## Decision: Dark mode implementation

**Decision**: Use Tailwind's built-in `dark:` variant driven by the `class` strategy, toggled automatically via a small script that reads `prefers-color-scheme` and applies/removes a `dark` class on `<html>` — no manual toggle UI required for this feature (per spec Assumptions).

**Rationale**: Tailwind already ships `darkMode` configuration support; using the `class` strategy driven purely by the media query keeps the CSS additive (existing utility classes gain `dark:` variants incrementally per component) rather than requiring a full theme rewrite.

**Alternatives considered**: CSS `prefers-color-scheme` media query only, without a `dark` class — rejected because it prevents any future manual override toggle from being added later without rework; the `class`-strategy approach keeps that door open at negligible extra cost.
