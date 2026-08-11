# Research: Prompt Sharing & Team Collaboration

**Feature**: 007-prompt-sharing | **Date**: 2026-08-04

All Technical Context unknowns are resolved below. Each entry records the decision, rationale, and alternatives considered.

## 1. Read-visibility scoping (the hidden behavioral change) + grandfathering

**Decision**: When `AUTH_ENABLED=true`, list/search/detail endpoints return only prompts the requester owns, prompts shared with them, prompts flagged `legacy_public` (view-only, see below), and (for admins) everything. When `AUTH_ENABLED=false` (anonymous single-user mode), behavior is unchanged (all prompts visible) and the sharing UI/endpoints are disabled.

New prompts default `legacy_public=false` (private-by-default, FR-016). The migration that adds the column backfills `legacy_public=true` on every row that exists at migration time (FR-017) — this is the grandfathering mechanism, not a separate table or implicit-share rows. `legacy_public=true` grants **view only**, never edit (FR-017); it is surfaced to the owner/admin as a one-way-revocable flag: `PATCH /api/prompts/{id}` (owner/admin only) can flip `legacy_public` from `true` to `false` but never back (FR-018) — see contract addition below.

**Rationale**: Investigation confirmed `PromptRepository.search()` has **no user filter today** — every authenticated user sees every prompt; ownership only gates mutations. The spec's US2 ("B's list contains B's own prompts plus prompts shared with B") is meaningless without visibility scoping, and the feature's premise ("middle ground between own and admin-sees-all") assumes it. Existing deployments already assign every prompt an owner (migration `ccdab5b31836_assign_existing_prompts_to_default_user`), so scoping is well-defined on upgrade. A straight cutover to private-by-default for *all* prompts (including pre-existing ones) was the original plan but is now superseded by the spec's clarified grandfathering requirement (FR-017/FR-018): existing prompts must keep working for every current viewer on day one, with an explicit, auditable, one-way opt-out into the new private model per prompt. This is still a visible behavior change for multi-user deployments — it must be a highlighted CHANGELOG/migration note: "prompts created from now on are private by default; prompts that existed before this release remain visible to all authenticated users until their owner/an admin makes them private."

**Alternatives considered**: (a) Keep global read visibility and make sharing only govern *edit* rights — rejected: contradicts spec US2/FR-008/FR-009 and makes "read" grants meaningless. (b) Cut over every prompt (old and new) to private-by-default with no grandfathering — rejected per clarification: breaks existing workflows on day one with no transition path. (c) Model grandfathering as an implicit `PromptShare` row per (prompt, every user) pair — rejected: O(prompts × users) rows, doesn't self-maintain as new users are created, and conflates "legacy public" with an actual grant in audit/UI surfaces; a single boolean column with migration-time backfill is simpler and matches "grandfathering is a transition aid, not a permanent tier" (spec Edge Cases). (d) Deployment-wide flag to opt into scoping — superseded by per-prompt grandfathering, which is more precise than an all-or-nothing switch.

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

**Grandfathering column** (separate migration on the existing `prompts` table, same portability rules): `legacy_public` BOOLEAN NOT NULL, `server_default=sa.false()` for the column-add DDL (so it's dialect-portable on both SQLite/Postgres), immediately followed by a data migration `op.execute(sa.update(prompts_table).values(legacy_public=True))` scoped to rows that existed before this migration ran — new inserts after migration use the model-level `default=False`. No composite index needed beyond a plain index on `legacy_public` if query plans show it's warranted at seed-scale (research §11); at "tens of users, thousands of prompts" scale a sequential scan on a boolean filter is cheap and this is deferred, not required, for v1.

## 4. Combined owned ∪ shared query strategy

**Decision**: Extend `PromptRepository.search()` (and `search_count()`) with an optional `visible_to_user_id: Optional[str]` parameter. When set, add a single filter:

```
q = q.filter(or_(
    Prompt.user_id == user_id,
    Prompt.id.in_(select(PromptShare.prompt_id).where(PromptShare.grantee_user_id == user_id)),
))
```

plus an optional `shared_with_user_id` variant for the `filter=shared-with-me` mode (only the EXISTS/IN branch). The base filter becomes:

```
q = q.filter(or_(
    Prompt.user_id == user_id,
    Prompt.legacy_public.is_(True),
    Prompt.id.in_(select(PromptShare.prompt_id).where(PromptShare.grantee_user_id == user_id)),
))
```

`filter=shared-with-me` narrows to the explicit-grant branch only — grandfathered-public prompts are not "shared with me" (they're not a grant to anyone in particular) and must not appear under that filter (spec Edge Cases: grandfathering is view access, not a share). Admins pass `None` (no scoping, see everything including private prompts). The router marks each returned prompt with `shared: true` only when a real `PromptShare` exists for the requester (not for `legacy_public`); a separate `legacy_public: bool` field lets the frontend render a distinct "Public (legacy)" indicator rather than conflating it with the "Shared" badge (contract §4 updated below). One interaction rule: `favorite=True` combined with visibility scoping restricts to owned prompts only — the favorite flag is the owner's personal preference (spec Edge Cases; per-user favorites deferred).

**Rationale**: A filter (OR + IN-subquery) preserves the existing single-query shape, ordering, pagination, and all current filters without deduplication concerns — unlike an OUTER JOIN, which would require `distinct()` interacting badly with `ORDER BY updated_at` limit/offset on both dialects. The subquery hits `idx_prompt_shares_grantee`. Count stays consistent because the same filter applies to both.

**Alternatives considered**: (a) LEFT OUTER JOIN + distinct (as sketched in the improvement plan) — rejected: duplicate-row handling with pagination is fragile across dialects; the IN-subquery is equivalent and simpler. (b) UNION of two queries — rejected: breaks shared pagination/ordering code. (c) Loading grant lists in Python — rejected: N+1 and scales poorly.

## 5. Authorization model placement

**Decision**: Add `check_prompt_access(prompt, user, level: 'read'|'edit'|'owner')` to `src/web/routers/prompts_shared.py` next to the existing `check_prompt_ownership`, backed by `SharingRepository.permission_for(prompt_id, user_id)`. Mapping:

- `owner` level (delete, favorite toggle, share management): owner or admin only — existing `check_prompt_ownership` semantics.
- `edit` level (update content/category/tags, revert version): owner, admin, or grantee with `edit`.
- `read` level (view prompt, version history, diffs): owner, admin, any grantee, or any authenticated user when `prompt.legacy_public` is `true`.

`legacy_public` never grants `edit` level — editing a grandfathered-public prompt still requires ownership, admin, or an explicit `edit` grant (FR-017). Flipping `legacy_public` from `true` to `false` (`un-grandfather`) requires `owner` level, same as favorite/delete/share-management, and is one-way — there is no endpoint to set it back to `true` (FR-018).

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
