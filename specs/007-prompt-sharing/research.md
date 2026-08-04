# Research: Prompt Sharing & Team Collaboration

**Feature**: 007-prompt-sharing | **Date**: 2026-08-04

All Technical Context unknowns are resolved below. Each entry records the decision, rationale, and alternatives considered.

## 1. Read-visibility scoping (the hidden behavioral change)

**Decision**: When `AUTH_ENABLED=true`, list/search endpoints return only prompts the requester owns, prompts shared with them, and (for admins) everything. When `AUTH_ENABLED=false` (anonymous single-user mode), behavior is unchanged (all prompts visible) and the sharing UI/endpoints are disabled.

**Rationale**: Investigation confirmed `PromptRepository.search()` has **no user filter today** — every authenticated user sees every prompt; ownership only gates mutations. The spec's US2 ("B's list contains B's own prompts plus prompts shared with B") is meaningless without visibility scoping, and the feature's premise ("middle ground between own and admin-sees-all") assumes it. Existing deployments already assign every prompt an owner (migration `ccdab5b31836_assign_existing_prompts_to_default_user`), so scoping is well-defined on upgrade. This IS a visible behavior change for multi-user deployments — it must be a highlighted CHANGELOG/migration note: "users now see only their own and shared prompts."

**Alternatives considered**: (a) Keep global read visibility and make sharing only govern *edit* rights — rejected: contradicts spec US2/FR-008/FR-009 and makes "read" grants meaningless. (b) Add a deployment flag to opt into scoping — rejected for v1: two visibility regimes double the test matrix; can be added later if an actual deployment needs the old behavior.

## 2. Anonymous mode (`AUTH_ENABLED=false`) interaction

**Decision**: Sharing endpoints return 404/disabled and the frontend hides share controls when auth is disabled. No schema or query differences — the visibility scope simply isn't applied.

**Rationale**: Sharing between users is undefined without users. The codebase already has the `get_current_user_or_none` / `get_admin_or_bypass` dependency pattern for auth-optional behavior; the routers follow it. Constitution III requires destructive endpoints stay guarded even in anonymous mode — disabling sharing entirely is the simplest compliant posture.

**Alternatives considered**: Allowing share management in anonymous mode against the default user — rejected as meaningless and an enumeration surface.

## 3. Schema & migration portability

**Decision**: New table `prompt_shares`:

- `id` INTEGER PK autoincrement
- `prompt_id` INTEGER NOT NULL, FK → `prompts.id` ON DELETE CASCADE
- `grantee_user_id` VARCHAR(36) NOT NULL, FK → `users.id` ON DELETE CASCADE
- `permission` VARCHAR via `sa.Enum('read', 'edit', name='share_permission', native_enum=False, validate_strings=True)` NOT NULL
- `granted_by` VARCHAR(36) NULL, FK → `users.id` ON DELETE SET NULL
- `created_at` / `updated_at` timestamps (ISO 8601 UTC, matching existing models)
- `UniqueConstraint(prompt_id, grantee_user_id, name='uq_prompt_shares_prompt_grantee')`
- Indexes: `idx_prompt_shares_grantee` on `grantee_user_id`, plus the unique constraint covers prompt-side lookups

Alembic migration uses plain `op.create_table`/`op.drop_table`, no dialect introspection, no PRAGMA/sqlite_master, `sa.true()/sa.false()` if boolean defaults are ever needed (none are).

**Rationale**: Matches existing conventions — `users.id` is VARCHAR(36) UUID, `prompts.id` is INTEGER (see `src/db/models/`). `native_enum=False` renders a VARCHAR + CHECK constraint identically on SQLite and Postgres, avoiding Postgres `CREATE TYPE` divergence (per project memory: the v1.10.0/v1.10.1 dialect-portability incident and `docs/DEVELOPMENT.md#writing-alembic-migrations`). DB-level `ON DELETE CASCADE` on `prompt_id`/`grantee_user_id` implements FR-014's cascades even for bulk deletes that bypass ORM cascade; `SET NULL` on `granted_by` implements the clarified "grants survive owner hard-delete" rule.

**Alternatives considered**: Native Postgres ENUM — rejected (portability incident precedent). Composite PK (prompt_id, grantee_user_id) without surrogate id — workable, but a surrogate `id` matches every other model and `BaseRepository.delete(id)` conventions.

## 4. Combined owned ∪ shared query strategy

**Decision**: Extend `PromptRepository.search()` (and `search_count()`) with an optional `visible_to_user_id: Optional[str]` parameter. When set, add a single filter:

```
q = q.filter(or_(
    Prompt.user_id == user_id,
    Prompt.id.in_(select(PromptShare.prompt_id).where(PromptShare.grantee_user_id == user_id)),
))
```

plus an optional `shared_with_user_id` variant for the `filter=shared-with-me` mode (only the EXISTS/IN branch). Admins pass `None` (no scoping). The router marks each returned prompt with `shared: true` when `prompt.user_id != requester.id`. One interaction rule: `favorite=True` combined with visibility scoping restricts to owned prompts only — the favorite flag is the owner's personal preference (spec Edge Cases; per-user favorites deferred).

**Rationale**: A filter (OR + IN-subquery) preserves the existing single-query shape, ordering, pagination, and all current filters without deduplication concerns — unlike an OUTER JOIN, which would require `distinct()` interacting badly with `ORDER BY updated_at` limit/offset on both dialects. The subquery hits `idx_prompt_shares_grantee`. Count stays consistent because the same filter applies to both.

**Alternatives considered**: (a) LEFT OUTER JOIN + distinct (as sketched in the improvement plan) — rejected: duplicate-row handling with pagination is fragile across dialects; the IN-subquery is equivalent and simpler. (b) UNION of two queries — rejected: breaks shared pagination/ordering code. (c) Loading grant lists in Python — rejected: N+1 and scales poorly.

## 5. Authorization model placement

**Decision**: Add `check_prompt_access(prompt, user, level: 'read'|'edit'|'owner')` to `src/web/routers/prompts_shared.py` next to the existing `check_prompt_ownership`, backed by `SharingRepository.permission_for(prompt_id, user_id)`. Mapping:

- `owner` level (delete, favorite toggle, share management): owner or admin only — existing `check_prompt_ownership` semantics.
- `edit` level (update content/category/tags, revert version): owner, admin, or grantee with `edit`.
- `read` level (view prompt, version history, diffs): owner, admin, or any grantee.

Service-layer methods in `PromptDataServiceDB` receive the acting user id and enforce the same matrix (defense in depth, and it keeps routes thin per Constitution I).

**Rationale**: Mirrors the established pattern; a single named helper keeps the 5-actors × 4-actions matrix testable in one place. Favorite toggling is owner-level per clarification (favorite flag stays owner-only).

**Alternatives considered**: Decorator/dependency-based permissions on routes only — rejected: leaves service layer unprotected and harder to unit-test.

## 6. No-enumeration + typeahead coexistence

**Decision**: `POST /api/prompts/{id}/shares` failures (unknown identifier, inactive account, self-share) all return the same generic 400 `sharing.grant_failed` message. The typeahead endpoint `GET /api/users/search?q=` is separate: auth-required, returns at most 10 `{id, username}` of **active** users, rate-limited, minimum query length 2. Matching runs against username OR email prefixes (spec US1 scenario 3 promises both), but responses never contain emails.

**Rationale**: Per clarification, directory typeahead for authenticated users is accepted (team-internal model); the enumeration guarantee applies to *failure responses* only, mirroring `auth_password_router.py`'s password-reset pattern. Excluding emails from suggestion payloads limits harvesting value; the grant request still accepts email as an identifier server-side.

**Alternatives considered**: Returning emails in suggestions — rejected (unnecessary exposure). Making failures descriptive for "better UX" — rejected: violates FR-010/SC-006.

## 7. Rate limiting

**Decision**: Apply `@limiter.limit(...)` from `src/web/middleware/rate_limit.py` to the three share-mutation endpoints and the typeahead endpoint, using limits consistent with the existing sensitive-endpoint taxonomy (share grant/revoke: moderate, e.g. 20/minute; typeahead: higher, e.g. 30/minute — final values to match the taxonomy table in item 3 of the improvement plan during implementation).

**Rationale**: Existing slowapi + Redis-backed infrastructure; the same pattern as `auth_password_router.py:230`. Typeahead needs a higher ceiling because it fires per keystroke (debounced client-side via `utils/debounce.ts`).

**Alternatives considered**: No limit on typeahead — rejected: it's the directory-scraping surface.

## 8. Audit events

**Decision**: Emit `prompt.share.granted` and `prompt.share.revoked` through `logging_service.log_audit_event` with the Issue #10 field set: `event`, `request_id`, `actor` (grantor/revoker), `action`, `resource_id` (prompt id), `status`, `duration_ms`, plus `grantee` and `permission` in the payload. Grant *updates* (read→edit) log as `granted` with the new permission.

**Rationale**: FR-011 and the existing observability requirements (AGENTS.md Issue #10). No prompt bodies in logs, metadata only — consistent with current practice.

## 9. Frontend composition

**Decision**:

- **Share modal**: new `components/share-modal.ts` composed from `components/modal.ts` primitives; user picker uses `utils/typeahead.ts` + `utils/debounce.ts`; permission `<select>` (read/edit); current-grants list with per-row revoke buttons; all strings via typed `t()` keys under `sharing.*`.
- **Badge**: "Shared" pill on prompt cards rendered when the API payload marks `shared: true`; text via i18n; safe rendering (`textContent`, no `innerHTML`).
- **Filter chip**: sidebar "Shared with me" entry driving `?filter=shared-with-me`, following the existing favorites-filter wiring in `app/`.
- **Tests**: Vitest specs for modal open/grant/revoke flows and badge logic, ≥85% for new modules.

**Rationale**: Every element reuses an existing primitive; no new frontend infrastructure. i18n keys added to all four locale files (`en`, `fr`, `es`, `de`) in the same change (FR-015).

**Alternatives considered**: Inline share controls on the card (no modal) — rejected: grant listing + revoke + picker needs modal real estate; matches how backup-restore-preview handles similar complexity.

## 10. Export/import & backup interaction

**Decision**: No changes. Backups copy the whole database (grants included). Prompt exports (CSV/Markdown/JSON) do not gain share fields; imported prompts arrive unshared, owned by the importer.

**Rationale**: Matches the spec assumption; grants are relationships between local accounts and are meaningless outside the instance.

## 11. Performance target for SC-004 (deferred from clarify)

**Decision**: Quantify SC-004 as: combined owned+shared listing adds < 10% latency vs. owned-only on a 1k-prompt / 100-share seeded dataset, asserted loosely in an integration test (functional correctness strict, timing advisory to avoid CI flakiness).

**Rationale**: The IN-subquery on an indexed column is O(log n) per row candidate; a hard timing gate in CI invites flakes, so the test asserts correctness strictly and logs timing.
