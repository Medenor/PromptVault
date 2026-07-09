# Data Model: Mobile-Responsive UI Enhancements

## OfflineQueueEntry (client-side, IndexedDB)

Represents a single pending create/edit operation made while offline, persisted in the browser so it survives reloads until synced.

| Field         | Type                                                     | Notes                                                                                                            |
| ------------- | -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `id`          | string (UUID)                                            | Client-generated, used as the IndexedDB key                                                                      |
| `promptId`    | string \| null                                           | Target prompt ID; `null` for a queued "create new prompt" operation                                              |
| `operation`   | `"create"` \| `"update"`                                 | Matches the existing prompt endpoints this will replay against                                                   |
| `payload`     | object                                                   | The prompt fields being created/changed (title, body, tags, etc. — matches existing prompt update request shape) |
| `baseVersion` | number \| null                                           | The prompt version the client last saw before editing (from feature 001-prompt-versioning); `null` for creates   |
| `timestamp`   | number (epoch ms)                                        | When the change was queued, used for ordering and display                                                        |
| `status`      | `"pending"` \| `"syncing"` \| `"synced"` \| `"conflict"` | Drives UI state and retry behavior                                                                               |

**Validation rules**:

- `operation: "update"` entries MUST have a non-null `promptId` and `baseVersion`.
- `status` transitions only forward: `pending → syncing → (synced | conflict)`. A `conflict` entry may be retried, which resets it to `pending` with an updated `baseVersion` after the user acknowledges the conflict.

**Relationships**: References an existing `Prompt` entity (owned by the existing backend data model — not redefined here) via `promptId`.

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

This feature does not introduce new SQLAlchemy models or Alembic migrations. The only potential backend touch point is a version-check parameter (or header) accepted by the _existing_ prompt update endpoint, used to detect conflicts when replaying a queued `OfflineQueueEntry` — this reuses the `version` column already present on the `Prompt` model from feature 001-prompt-versioning rather than adding new schema.
