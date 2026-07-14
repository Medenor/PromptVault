# Quickstart: Validating Mobile-Responsive UI Enhancements

## Prerequisites

- Repo checked out on branch `004-mobile-responsive-ui`
- Python deps installed (existing project `venv`/`uv` setup) and `npm install` run for frontend deps
- Server started via `python run_web.py` (per constitution — never invoke uvicorn directly)
- Frontend build running via `npm run dev` (Vite) or `npm run build` for a production check

## Validate User Story 1 — Navigation and layout (P1)

1. Open the app in a browser with device emulation set to a 375px-wide viewport (e.g., Chrome DevTools "iPhone SE" or Playwright's `iPhone 14` profile).
2. Confirm the desktop sidebar is replaced by a hamburger icon; tap it and confirm a slide-out drawer opens with the same nav destinations as desktop.
3. Tap outside the open drawer; confirm it closes and no horizontal scrollbar appears on the main content at 320px, 375px, 425px, and 768px widths.
4. Tap through primary buttons/menu items on the prompt list and confirm each responds on first tap (informal 44px target spot-check, formalized in `SC-002` audit task).
5. Open a prompt for editing; tap into a text field and confirm the field stays visible above the on-screen keyboard.

Automated equivalent: `npx playwright test mobile-nav.spec.ts --project=mobile` (see tasks.md for the file to be created).

## Validate User Story 2 — View and copy prompts offline (P2)

Offline mode is read/copy-only — editing, creating, deleting, and secondary-page navigation all require connectivity and are blocked client-side rather than queued.

1. With the app loaded and online, browse to the prompt list and open a couple of prompts (to populate the Service Worker cache).
2. In DevTools, go offline (Network tab → Offline) or use Playwright's `context.setOffline(true)`.
3. Confirm the offline indicator appears and the previously-viewed prompts remain viewable.
4. Copy one of the cached prompts (with and without a specific version); confirm the copy succeeds using cached data.
5. Attempt to create, edit, delete, revert, or bulk-modify a prompt, or click a nav button to Import/Export, Manage Categories/Tags, or Backup Management; confirm each is blocked before any request is sent, with a "this needs an internet connection" message (`FR-011`, `FR-012`).
6. Go back online; confirm editing and secondary-page navigation work normally again.

Automated equivalent: `npx playwright test offline-cache.spec.ts --project=mobile`.

## Validate User Story 3 — Gestures and PWA install (P3)

1. On a touch-emulated viewport, swipe a prompt card left; confirm a delete action is revealed and requires a confirming tap.
2. Swipe a prompt card right; confirm an edit action is revealed and opens the editor.
3. Pull down from the top of the prompt list; confirm a refresh loading affordance appears and the list reloads.
4. Confirm each gesture action above also has a visible, tappable equivalent control reachable without performing the gesture (accessibility requirement, `FR-020`).
5. In a supported mobile browser (or Chrome's "Install app" DevTools affordance), install the app to the home screen; confirm it launches standalone with the PromptVault name and icon.

Automated equivalent: `npx playwright test gestures.spec.ts pwa-install.spec.ts --project=mobile`.

## Full validation sweep

```bash
python3 -m pytest                      # backend coverage gate, ≥85%
npm run typecheck && npm run lint      # TS gates
npm run test:unit:coverage             # frontend coverage gate, ≥85%
npx playwright test --project=mobile   # mobile E2E suite for this feature
```

Expected outcome: all suites pass, and the manual walkthroughs above match the acceptance scenarios in `spec.md`.
