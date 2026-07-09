# Implementation Plan: Mobile-Responsive UI Enhancements

**Branch**: `004-mobile-responsive-ui` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-mobile-responsive-ui/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Deliver a mobile-first navigation and interaction layer (slide-out drawer, 44px touch targets, full-screen modals/search, FAB, swipe/pull-to-refresh gestures with accessible fallbacks) plus offline resilience (Service Worker asset/API caching, IndexedDB-backed offline write queue with version-based conflict detection, install-to-home-screen PWA manifest) and `prefers-color-scheme` dark mode — all implemented additively in TypeScript (`src/web/static/ts/`) and Tailwind utility classes on top of the existing Jinja2/FastAPI server-rendered app, without introducing new frontend frameworks or rewriting desktop layouts.

## Technical Context

**Language/Version**: Python 3.14+ (backend), TypeScript (frontend, compiled via `tsc`/Vite)

**Primary Dependencies**: FastAPI, SQLAlchemy + Alembic, Jinja2 templates, Tailwind CSS, Vite (existing build), no new runtime dependencies added

**Storage**: PostgreSQL/SQLite via existing SQLAlchemy models/repositories (server); IndexedDB (client, for the offline write queue) and the Cache Storage API (client, for Service-Worker-cached static assets/API responses)

**Testing**: pytest (backend, ≥85% coverage gate), Vitest (frontend unit tests, ≥85% coverage gate), Playwright with mobile device emulation (`iPhone 14`, `Pixel 7`) + `context.setOffline()` for E2E mobile/gesture/offline scenarios

**Target Platform**: Server-rendered web app; mobile browsers iOS Safari and Android Chrome (current versions) as primary targets, existing desktop browser support unchanged

**Project Type**: Web application (single FastAPI backend + Jinja2/TS frontend within one repo — not a separate frontend/backend project split)

**Performance Goals**: Prompt list interactive within 3s on simulated 4G on a mid-tier mobile device (SC-007); offline queued edits sync within 10s of reconnect (SC-005)

**Constraints**: No new frontend framework or build tooling; Service Worker and offline queue implemented as plain TypeScript modules under `src/web/static/ts/`, not a new subsystem/package; must not regress desktop layout/behavior; all gesture-driven actions require an accessible non-gesture equivalent (spec FR-007/FR-008/FR-020)

**Scale/Scope**: 3 user stories (P1 navigation/layout, P2 offline sync, P3 gestures/PWA install), ~4 templates touched (`index.html`, `import_export.html`, base layout, manage/backup templates as needed for consistent nav), new manifest + icon assets, one Service Worker entry point, one offline-queue module, one gesture-utility module

## Constitution Check

_GATE: Must pass before Phase 0 research. Re-check after Phase 1 design._

| Principle                          | Check                                                                                                                                                                                   | Status |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| I. Layered Service Architecture    | Any backend change (conflict-check on prompt update) stays in the existing router → service → repository layering; no new layer bypass                                                  | PASS   |
| II. Test Coverage Gate             | Plan requires pytest coverage for backend touch points, Vitest coverage for new TS modules, both against the existing ≥85% gate; tests written alongside implementation (Phase 2 tasks) | PASS   |
| III. Security-First Authentication | Offline sync reuses existing authenticated prompt endpoints; no new unauthenticated mutation path introduced                                                                            | PASS   |
| IV. TypeScript-Only Frontend       | All new client logic written under `src/web/static/ts/`; legacy `src/web/static/js/app.js` is not edited                                                                                | PASS   |
| V. Database-Backed Persistence     | No new JSON/file storage; offline queue lives client-side in IndexedDB (a client cache, not a persistence-of-record concern) and syncs through existing SQLAlchemy-backed endpoints     | PASS   |

No violations requiring Complexity Tracking justification.

## Project Structure

### Documentation (this feature)

```text
specs/004-mobile-responsive-ui/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/
├── web/
│   ├── routers/                  # existing FastAPI routers; minor addition: version-check param on prompt update route
│   ├── services/                 # existing service layer (referenced from src/services/)
│   ├── templates/
│   │   ├── base.html (or equivalent shared layout)  # add manifest link, dark-mode bootstrap script, drawer/bottom-nav markup
│   │   ├── index.html            # add hamburger trigger, drawer, FAB, swipe/pull-to-refresh hooks, full-screen search overlay
│   │   └── import_export.html    # apply full-screen modal / touch-target updates
│   └── static/
│       ├── ts/
│       │   ├── app.ts                       # existing entry; wire up new modules
│       │   ├── mobile-nav.ts                # NEW: drawer open/close, focus trap, outside-tap close
│       │   ├── sw-register.ts               # NEW: Service Worker registration + offline indicator wiring
│       │   ├── sw.ts                        # NEW: Service Worker source (compiled to static/sw.js as a separate entry)
│       │   ├── gestures.ts                  # NEW: swipe-reveal + pull-to-refresh via Pointer Events
│       │   └── utils/
│       │       └── offline-queue.ts         # NEW: IndexedDB-backed offline write queue
│       ├── manifest.json                    # NEW: PWA manifest
│       └── images/icons/                    # NEW: app icons (192, 512, maskable)
└── services/ (or db/repositories/)          # existing layers; touched only if a version-check helper is added for conflict detection

tests/
├── unit/ (pytest)                # backend conflict-check logic if added
└── (Vitest) src/web/static/ts/__tests__/    # offline-queue, gestures, sw-register unit tests

playwright tests (existing e2e location, e.g. tests/e2e/ or root-level per playwright.config.ts)
└── mobile-nav.spec.ts, offline-sync.spec.ts, gestures.spec.ts, pwa-install.spec.ts  # NEW
```

**Structure Decision**: Single-project web application (existing FastAPI + Jinja2 + Vite/TypeScript layout is retained). No frontend/backend project split is introduced — this feature extends the existing `src/web/` tree in place, consistent with prior features 001 and 002.

## Complexity Tracking

_No Constitution Check violations — table intentionally omitted._
