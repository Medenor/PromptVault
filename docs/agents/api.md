# API Endpoints

## Prompt Management

- `GET /api/prompts` — List all prompts
- `POST /api/prompts` — Create new prompt
- `GET /api/prompts/{id}` — Get specific prompt (requires `read` access: owner, admin, any grantee, or a `legacy_public` prompt; 404 if invisible)
- `PUT /api/prompts/{id}` — Update prompt, creates new version (requires `edit` access — owner, admin, or an edit-grantee; `favorite` and `legacy_public: true` are rejected for non-owners)
- `DELETE /api/prompts/{id}` — Delete prompt (owner/admin only)
- `GET /api/prompts/search` — Search with filters (default scope: owned ∪ shared-with-me ∪ legacy-public; `?filter=shared-with-me` narrows to explicit grants only; admins see all)
- `PUT /api/prompts/{id}/favorite` — Toggle favorite status (owner/admin only)

## Categorization

- `GET /api/categories` — List all categories
- `GET /api/tags` — List all tags

## Version Control

- `GET /api/prompts/{id}/versions` — Get version history (requires `read` access: owner, admin, any grantee, or a `legacy_public` prompt)
- `GET /api/prompts/{id}/versions/compare` — Compare versions
- `GET /api/prompts/{id}/versions/{version_id}` — Get specific version
- `POST /api/prompts/{id}/versions/{version_id}/revert` — Revert to version (requires `edit` access: owner, admin, or an edit-grantee — `legacy_public` alone is insufficient)

## Sharing & Collaboration

- `POST /api/prompts/{id}/shares` — Grant or update a share (owner/admin only; body `{"identifier": "<username or email>", "permission": "read"|"edit"}`; generic 400 on unknown/inactive/self identifiers to avoid user enumeration)
- `GET /api/prompts/{id}/shares` — List a prompt's grants (owner/admin only; 403 for grantees)
- `DELETE /api/prompts/{id}/shares/{user_id}` — Revoke a share (owner/admin only; access loss is immediate)
- `GET /api/users/search?q=` — Typeahead recipient lookup (any authenticated user; ≥2 chars; ≤10 active users; matches username/email prefix but returns usernames only)
- `PATCH /api/prompts/{id}` with `{"legacy_public": false}` (JSON body) — Un-grandfather a prompt, making it private (owner/admin only; one-way — `legacy_public: true` is rejected with 400)
- All sharing endpoints require `AUTH_ENABLED=true` (404 otherwise), are rate-limited, and audit-log `prompt.share.granted`/`prompt.share.revoked`

## Import/Export

- `GET /import-export` — Management page
- `POST /api/export` — Export prompts (CSV/Markdown/JSON)
- `POST /api/import` — Import prompts
- `GET /api/import-export/stats` — Import/export statistics
- Export/import is grant-blind by design: `prompt_shares` grants and the `legacy_public` flag are never included in export payloads or restored on import, since they're runtime access-control state tied to this instance's user accounts. Full database backup/restore is the only path that preserves them.

## Backup Management

- `GET /backup-management` — Management page
- `GET /api/backups` — List all backups
- `POST /api/backups` — Create backup
- `POST /api/backups/{id}/restore` — Restore backup
- `DELETE /api/backups/{id}` — Delete backup
- `POST /api/backups/cleanup` — Cleanup old backups
- `POST /api/backups/compress` — Compress old backups
- `GET /api/backups/stats` — Backup statistics

## Page Routes

- `GET /` — Main application interface
- `GET /import-export` — Import/export interface
- `GET /backup-management` — Backup management interface
