# API Validation & Monitoring Guide

> Phase 4 (Quality & Ops) deliverable for Issue [#9](https://codeberg.org/medenor/promptvault/issues/9)

## Validation Rules (Server)

All POST/PUT endpoints use Pydantic request models and shared validators:

- `/api/prompts` (`PromptCreateRequest`): `title` 1-200, `prompt` 1-50000, `category` ≤100, `tags` ≤50 items, each ≤50 chars.
- `/api/prompts/{id}` (`PromptUpdateRequest`): same as create + `commit_message` 1-500.
- `/api/export` (`ExportRequest`): `format` in `csv|markdown|json`, `filename` safe characters only (no path separators), ≤255 chars.
- `/api/import` (`ImportRequest` + upload validators): file extension in `.csv|.json|.md`, MIME type in `text/csv|application/json|text/markdown|text/plain`, size ≤10 MB.
- `/api/backups` (`BackupCreateRequest`): `name` optional, safe characters only, ≤64 chars.
- `/api/backups/cleanup` (`BackupCleanupRequest`): `retention_days` 1-3650.
- `/api/backups/compress` (`BackupCompressRequest`): `days_threshold` 1-365.
- `/api/prompts/{id}/versions/{version_id}/revert` (`VersionRevertRequest`): `commit_message` 1-500.

Client-side validators mirror these constraints in `src/web/static/js/validators.js` and `validation_constants.js`.

## Standardized Error Shape

Validation errors return HTTP 422 with:

```json
{
  "error": "Validation failed",
  "details": ["field: message", "..."],
  "errors": [
    {
      "type": "string_too_short",
      "loc": ["body", "title"],
      "msg": "Title cannot be empty or whitespace only",
      "input": "   "
    }
  ]
}
```

File-upload validation failures return HTTP 400 with `{ "error": "<reason>" }`.

## Monitoring Endpoint

Validation health is tracked and persisted to `data/logs/validation_metrics.json` via `/api/validation/stats`:

```json
{
  "total_events": 12,
  "successes": 8,
  "failures": 4,
  "failure_rate": 0.3333,
  "successes_by_endpoint": { "/api/prompts": 5, "/api/export": 1 },
  "failures_by_endpoint": { "/api/prompts": 2, "/api/import": 2 },
  "recent_failures": [
    {
      "endpoint": "/api/import",
      "errors": ["Invalid file extension '.exe'. Allowed extensions: .csv, .json, .markdown, .md"],
      "client": "127.0.0.1",
      "timestamp": "2025-11-26T12:00:00Z"
    }
  ],
  "last_updated": "2025-11-26T12:00:00Z"
}
```

Use this endpoint for dashboards/alerts. Failure rate is precomputed; `recent_failures` maintains the 20 most recent validation failures with endpoint and error context.

## Usage Notes

- Monitoring is initialized automatically using the configured data directory; metrics persist between runs.
- Validation failures are logged from both automatic FastAPI 422 handlers and explicit validation guards in endpoints (upload validation, enum checks).
- For investigations, inspect `data/logs/validation_metrics.json`; it is safe to delete between environments (auto-recreated).
