# Contract: Offline Queue Sync

This feature does not introduce a new sync API. It extends the existing prompt update endpoint with an optional conflict-detection parameter, and defines the client-side contract for replaying a queued offline write.

## Backend: extend `PUT /prompts/{prompt_id}`

Existing endpoint (`src/web/routers/prompts.py:622`, form-encoded body) gains one optional field:

| Field | Type | Required | Notes |
|---|---|---|---|
| `expected_version` | int (form field) | No (backward compatible) | The prompt's version the client last saw before queuing the offline edit. When present, the server compares it against the prompt's current version before applying the update. |

**Behavior**:
- If `expected_version` is omitted: existing behavior, unchanged (no regression for non-offline clients).
- If `expected_version` is present and matches the current server-side version: update proceeds normally, creating a new version as today.
- If `expected_version` is present and does NOT match (server has moved on): respond `409 Conflict` with a JSON body `{"error": "version_conflict", "current_version": <int>, "current_prompt": {...}}` instead of applying the write.

**Responses added**:
| Code | Meaning |
|---|---|
| 409 | `expected_version` did not match the prompt's current version; client must surface a conflict to the user rather than silently overwrite |

This stays within the existing router → service → repository layering (Constitution Principle I): the version comparison is a service-layer check using data already exposed by `VersionRepository` / `PromptVersion`, not a new subsystem.

## Client: Offline Queue → Sync replay contract

When connectivity is restored, `offline-queue.ts` replays each `OfflineQueueEntry` with `status: "pending"` in `timestamp` order:

1. Set entry `status` to `syncing`.
2. For `operation: "update"`: POST to the existing update endpoint with the entry's `payload` fields plus `expected_version: entry.baseVersion`.
3. For `operation: "create"`: POST to the existing create endpoint (no version check applicable).
4. On `200`: set `status` to `synced`, remove from active queue display, update any local cache with the server's response.
5. On `409`: set `status` to `conflict`, surface a user-facing notification (per spec FR-012) with a link to review the current server version vs. the queued change. Do not retry automatically.
6. On network failure during replay: leave `status` as `pending` and retry on the next `online` event.

## Manifest contract (static asset, not an API)

`static/manifest.json` served at the app root, referenced via `<link rel="manifest" href="/static/manifest.json">` in the base template `<head>`. Must satisfy the [W3C Web App Manifest](https://www.w3.org/TR/appmanifest/) minimum fields for installability: `name`, `icons` (including a 512x512 entry), `start_url`, `display`.
