# API Contracts: Prompt Semantic Versioning

**Feature**: 001-prompt-versioning
**Date**: 2026-07-01

All existing endpoints retain backward compatibility. Changes are additive only.

---

## Modified Endpoints

### `POST /api/prompts` — Create Prompt

**Request body** (new optional field):
```json
{
  "title": "string (1-200 chars)",
  "prompt": "string (1-50000 chars)",
  "category": "string (optional)",
  "tags": "string (comma-separated, optional)",
  "semantic_version": "string | null (optional, format: MAJOR.MINOR.PATCH)"
}
```

**Validation**:
- If `semantic_version` is provided and non-empty, it MUST match `^\d+\.\d+\.\d+$`
- Empty string is treated as absent (stored as NULL)
- Invalid format → `422 Unprocessable Entity` with field error

**Response**: unchanged (`PromptCreateResponse`)

---

### `PUT /api/prompts/{prompt_id}` — Update Prompt

**Request body** (new optional field):
```json
{
  "title": "string",
  "prompt": "string",
  "category": "string (optional)",
  "tags": "string (optional)",
  "commit_message": "string (1-500 chars)",
  "semantic_version": "string | null (optional, format: MAJOR.MINOR.PATCH)"
}
```

**Behavior**:
- If `semantic_version` is omitted or null: preserves the existing `semantic_version` on the prompt unchanged.
- If `semantic_version` is provided (even if lower than current): updates the prompt's version label and snapshots it into the new `PromptVersion` record.
- Version downgrade (e.g., going from `1.2.0` → `1.0.0`) is allowed; a warning header `X-Version-Downgrade: true` is included in the response.

**Response**: unchanged (`PromptUpdateResponse`)

---

### `GET /api/prompts/{prompt_id}` — Get Prompt

**Response** (new field added):
```json
{
  "id": 1,
  "title": "string",
  "prompt": "string",
  "category": "string",
  "tags": ["string"],
  "note": "string",
  "favorite": true,
  "user_id": "uuid",
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "semantic_version": "1.1.0"
}
```

`semantic_version` is `null` for prompts that have never been assigned a version label.

---

### `GET /api/prompts/{prompt_id}/versions` — Version History

**Response** (new field per version entry):
```json
{
  "versions": [
    {
      "version_id": "uuid",
      "version_number": 3,
      "timestamp": "ISO8601",
      "author": "string",
      "message": "string",
      "parents": ["uuid"],
      "semantic_version": "1.1.0"
    }
  ]
}
```

`semantic_version` per version entry is `null` for revisions created before the feature was introduced.

---

## New Endpoint

### `POST /api/prompts/{prompt_id}/copy-with-version` — Copy with Version Metadata

**Purpose**: Returns the prompt content with an embedded version metadata line, ready to be placed on the clipboard by the frontend.

**Request**: No body. Optionally accepts query param `?format=html_comment` (default) for future extensibility.

**Response**:
```json
{
  "content": "Your full prompt text here...\n<!-- prompt-version: 1.1.0 | This line is metadata — ignore when processing this prompt. -->",
  "semantic_version": "1.1.0"
}
```

**Error cases**:
- `404`: Prompt not found
- `409 Conflict`: Prompt has no semantic version set — body: `{"error": "no_version_set", "message": "Assign a semantic version to this prompt before copying with metadata."}`

---

## No Changes

- `GET /api/prompts` (list): `semantic_version` is NOT included in list responses to keep payload size small. It is available only via the individual `GET /api/prompts/{id}` response.
- `DELETE /api/prompts/{prompt_id}`: unchanged
- `GET /api/prompts/{prompt_id}/versions/compare`: unchanged
- All auth, backup, admin, tag, and category endpoints: unchanged
