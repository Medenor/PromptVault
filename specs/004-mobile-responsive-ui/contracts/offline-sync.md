# Contract: Offline Access

Offline mode is read/copy-only (spec.md User Story 2, FR-009 through FR-012). This feature does not introduce any offline write, sync, or conflict-detection API — there is no queued-write contract to define.

## Service Worker cache contract

`src/web/static/ts/sw.ts`, compiled to `/sw.js` (served at the site root so its scope covers the whole app):

- **`STATIC_CACHE` (`promptvault-static-v1`)**: the main prompt list page (`/`) and its linked `/static/...` assets (JS bundle, CSS, manifest, icons), precached on Service Worker `install` so a single online visit to `/` is enough for offline access — a page is never controlled by the Service Worker that installs it, so without precaching, a first-ever visit would leave the offline cache empty. Also serves subsequent navigations to `/` and any `/static/...` request cache-first/network-first per `sw.ts`.
- **`API_CACHE` (`promptvault-api-v1`)**: GET responses under `/api/prompts`, `/api/categories`, and `/api/tags` (including per-prompt sub-routes like `/api/prompts/{id}/versions`), cached network-first as they're fetched during normal browsing. This is what makes a previously-viewed prompt (and its version history, if opened) available offline.

Offline access is scoped to the main page only. Secondary pages (Import/Export, Manage Categories/Tags, Backup Management) are **not** precached or cached, and their write endpoints are never called while offline — see "Client: offline write gating" below.

## Client: offline write gating

There is no offline write queue. Instead, every create/edit/delete/revert/bulk-modify action and every secondary-page navigation checks `navigator.onLine` before attempting anything:

- If online: proceed normally (existing endpoints, unchanged — no `expected_version` or conflict-detection parameters).
- If offline: the action is blocked client-side before any request is sent, and a "this needs an internet connection" notification is shown (`offline.editUnavailable` translation key). Secondary-page nav buttons route through `window.__requireOnlineNav()` (wired in `app.ts`), which performs the same check before navigating.

This means the backend's `PUT /prompts/{prompt_id}` (and all other write endpoints) never see requests while the client is offline — there is nothing for the server to reconcile.

## Manifest contract (static asset, not an API)

`static/manifest.json` served at the app root, referenced via `<link rel="manifest" href="/static/manifest.json">` in the base template `<head>`. Must satisfy the [W3C Web App Manifest](https://www.w3.org/TR/appmanifest/) minimum fields for installability: `name`, `icons` (including a 512x512 entry), `start_url`, `display`.
