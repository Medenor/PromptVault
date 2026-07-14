# Data Model: Mobile-Responsive UI Enhancements

## No offline write queue

Offline mode is read/copy-only (spec.md User Story 2). There is no client-side write queue, no IndexedDB-persisted entity, and no sync/conflict-resolution state machine — create/edit/delete/revert/bulk-modify actions are blocked client-side while offline (checked via `navigator.onLine`) rather than queued for later replay. See `contracts/offline-sync.md` for the gating contract.

## AppManifest (static asset, not a runtime entity)

Represents the installable PWA's metadata, served as a static `manifest.json`.

| Field                              | Notes                                                                                     |
| ---------------------------------- | ----------------------------------------------------------------------------------------- |
| `name` / `short_name`              | "PromptVault"                                                                             |
| `icons`                            | References to the 192x192, 512x512, and maskable icon assets under `static/images/icons/` |
| `start_url`                        | App root, so installed launches land on the main prompt list                              |
| `display`                          | `standalone`, so the installed app launches without browser chrome                        |
| `theme_color` / `background_color` | Matches existing brand palette from `tailwind.config.ts`                                  |

No state transitions — this is a static declarative asset, not a persisted or mutable entity.

## No new backend/database entities

This feature does not introduce new SQLAlchemy models or Alembic migrations, nor any backend changes to the existing prompt endpoints — offline write-gating happens entirely client-side.
