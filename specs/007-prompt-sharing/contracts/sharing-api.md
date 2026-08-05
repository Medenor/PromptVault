# API Contracts: Prompt Sharing & Team Collaboration

**Feature**: 007-prompt-sharing | **Date**: 2026-08-04

All endpoints require authentication when `AUTH_ENABLED=true`; when `AUTH_ENABLED=false` the sharing endpoints respond `404 Not Found` (feature inactive, research §2). Request/response models live in `src/web/models/sharing_requests.py` and `sharing_responses.py`. All mutations are audit-logged (research §8) and rate-limited (research §7).

## 1. Grant (or update) a share

```
POST /api/prompts/{prompt_id}/shares
```

**Authorization**: prompt owner or admin (`owner` level).

**Request body** (`ShareGrantRequest`):

```json
{
  "identifier": "alice",          // username OR email of grantee
  "permission": "read"            // "read" | "edit"
}
```

**Responses**:

- `201 Created` — new grant. Body (`ShareResponse`):

  ```json
  {
    "prompt_id": 42,
    "grantee": {"id": "uuid", "username": "alice"},
    "permission": "read",
    "granted_by": "bob",
    "created_at": "2026-08-04T12:00:00Z",
    "updated_at": "2026-08-04T12:00:00Z"
  }
  ```

- `200 OK` — existing grant's permission updated (same body, `updated_at` bumped).
- `400 Bad Request` — generic failure, body `{"detail": "<i18n: sharing.grant_failed>"}`. Used uniformly for: unknown identifier, inactive grantee, self-share, sharing to the owner. **MUST NOT distinguish these cases** (FR-010, SC-006).
- `403 Forbidden` — requester is neither owner nor admin.
- `404 Not Found` — prompt does not exist or is invisible to requester.
- `422` — malformed body (Pydantic).
- `429` — rate limit exceeded.

## 2. Revoke a share

```
DELETE /api/prompts/{prompt_id}/shares/{user_id}
```

**Authorization**: prompt owner or admin.

**Responses**:

- `200 OK` — `{"message": "<i18n: sharing.revoked>"}`; access ends immediately (FR-007).
- `404 Not Found` — prompt invisible/nonexistent, or no grant for that user (no distinction).
- `403 Forbidden` — requester is neither owner nor admin.
- `429` — rate limit exceeded.

## 3. List a prompt's grants

```
GET /api/prompts/{prompt_id}/shares
```

**Authorization**: prompt owner or admin only — grantees receive `403` (FR-006, US3 scenario 4).

**Response** `200 OK` (`ShareListResponse`):

```json
{
  "prompt_id": 42,
  "shares": [
    {"grantee": {"id": "uuid", "username": "alice"}, "permission": "edit",
     "granted_by": "bob", "created_at": "...", "updated_at": "..."}
  ]
}
```

## 4. Listing & search with sharing (modified endpoints)

```
GET /api/prompts?filter=shared-with-me
GET /api/prompts/search?...&filter=shared-with-me
```

**Behavior changes** (apply to the existing list/search endpoints):

- Default scope (auth enabled): owned ∪ shared-with-me ∪ legacy-public; admins see all, including private prompts (research §1/§4).
- `filter=shared-with-me`: only prompts with an explicit `PromptShare` grant to the requester — grandfathered-public prompts are excluded from this filter (they aren't a grant to anyone specifically).
- Every prompt object in list/search/detail responses gains three fields:

  ```json
  {"shared": true, "legacy_public": false, "permission": "read"}
  ```

  `shared` = an explicit `PromptShare` names the requester (never `true` for legacy-public-only visibility); `legacy_public` = echoes `Prompt.legacy_public`, letting the frontend show a distinct "Public (legacy)" indicator from the "Shared" badge; `permission` = requester's effective level (`"owner"`, `"edit"`, `"read"`). The frontend gates edit controls on `permission`, not on `shared`/`legacy_public` individually.
- Pagination, ordering, and the `category`/`tags`/text-query filters operate on the combined set unchanged (FR-008). Exception: the `favorite` filter matches **owned prompts only** — the flag is the owner's personal preference, so shared and legacy-public prompts are excluded from a recipient's favorites results (spec Edge Cases).

## 4b. Un-grandfather a prompt (make a legacy-public prompt private)

```
PATCH /api/prompts/{prompt_id}
```

Reuses the existing prompt-update endpoint; body carries `{"legacy_public": false}` alongside (or instead of) other editable fields.

**Authorization**: prompt owner or admin (`owner` level) — same as favorite/delete (FR-018).

**Responses**:

- `200 OK` — updated prompt payload with `legacy_public: false`.
- `400 Bad Request` — `legacy_public: true` submitted (one-way; there is no re-publish action, FR-018).
- `403 Forbidden` — requester is neither owner nor admin, or holds only a `read`/`edit` share grant.
- `404 Not Found` — prompt invisible/nonexistent.

This action does **not** create any `PromptShare` rows — a user who could previously view the prompt via `legacy_public` loses that access immediately unless the owner separately grants them an explicit share (spec Edge Cases: un-grandfathering is not automatically re-shared).

## 5. User typeahead

```
GET /api/users/search?q=<prefix>
```

**Authorization**: any authenticated user (clarification #4).

**Constraints**: `q` minimum 2 characters; max 10 results; active accounts only; matching is against username OR email prefix (so typing a partial email finds the account, per spec US1 scenario 3) but the response payload contains usernames only (no emails); rate-limited; client debounces via `utils/debounce.ts`.

**Response** `200 OK`:

```json
{"users": [{"id": "uuid", "username": "alice"}]}
```

`400` for `q` too short; `401` unauthenticated; `429` rate-limited.

## 6. Existing endpoints — authorization changes

| Endpoint | Old rule | New rule |
|----------|----------|----------|
| `GET /api/prompts/{id}` | any authenticated (or anonymous) user | `read` level (owner/admin/any grantee/`legacy_public=true`); otherwise 404 |
| `PUT /api/prompts/{id}` | owner or admin | `edit` level (owner/admin/edit-grantee); category & tags included; favorite and `legacy_public` fields ignored/rejected for grantees — `legacy_public: false` accepted from owner/admin only (§4b) |
| `PUT /api/prompts/{id}/favorite` | owner or admin | unchanged — `owner` level (clarification #1) |
| `DELETE /api/prompts/{id}` | owner or admin | unchanged — `owner` level |
| `GET /api/prompts/{id}/versions*` | any authenticated user | `read` level |
| `POST /api/prompts/{id}/versions/{vid}/revert` | owner or admin | `edit` level |

Inaccessible prompts return `404` (not `403`) on read paths to avoid existence disclosure; mutation attempts on visible-but-insufficient-permission prompts return `403`.

## Audit events (contract)

| Event | When | Payload fields |
|-------|------|----------------|
| `prompt.share.granted` | grant created or permission changed | `actor`, `grantee`, `permission`, `resource_id` (prompt), `status`, `request_id`, `duration_ms` |
| `prompt.share.revoked` | grant revoked | same fields, including `permission` (the revoked grant's level — required per spec US3 scenario 3) |

## i18n keys (contract)

New `sharing.*` namespace in `src/web/static/locales/{en,fr,es,de}.json` — at minimum: `sharing.title`, `sharing.grant`, `sharing.permission.read`, `sharing.permission.edit`, `sharing.revoke`, `sharing.badge`, `sharing.shared_with_me`, `sharing.grant_failed`, `sharing.revoked`, `sharing.no_shares`, `sharing.picker_placeholder`.
