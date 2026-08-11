# Data Model: Prompt Sharing & Team Collaboration

**Feature**: 007-prompt-sharing | **Date**: 2026-08-04

## New Entity: PromptShare

One row per (prompt, grantee) pair — a grant of access by a prompt's owner (or admin) to another user.

**Table**: `prompt_shares` | **Model file**: `src/db/models/prompt_share.py`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | Integer | PK, autoincrement | Surrogate key, matches `BaseRepository` conventions |
| `prompt_id` | Integer | NOT NULL, FK `prompts.id` ON DELETE CASCADE, part of unique constraint | Grants die with the prompt (FR-014) |
| `grantee_user_id` | String(36) | NOT NULL, FK `users.id` ON DELETE CASCADE, part of unique constraint, indexed (`idx_prompt_shares_grantee`) | Grants to a hard-deleted user vanish (clarification #3) |
| `permission` | `sa.Enum('read', 'edit', name='share_permission', native_enum=False, validate_strings=True)` | NOT NULL | VARCHAR + CHECK on both dialects — no native PG enum |
| `granted_by` | String(36) | NULLABLE, FK `users.id` ON DELETE SET NULL | Survives grantor hard-delete (clarification #3); NULL = "granted by a since-deleted account" |
| `created_at` | DateTime (UTC) | NOT NULL, default now | Grant creation time |
| `updated_at` | DateTime (UTC) | NOT NULL, default now, onupdate now | Bumped on permission-level change (upsert) |

**Constraints**:

- `UniqueConstraint('prompt_id', 'grantee_user_id', name='uq_prompt_shares_prompt_grantee')` — at most one grant per pair (FR-003); re-granting updates `permission` in place.
- Application-level validation: `grantee_user_id != prompt.user_id` (no self-share / no sharing to the owner, FR-013); grantee must be an active user at grant time.

**Relationships**:

- `PromptShare.prompt` ↔ `Prompt.shares` — `cascade="all, delete-orphan"` on the Prompt side (ORM mirror of the DB cascade).
- `PromptShare.grantee` → `User` (via `grantee_user_id`); `User.received_shares` backref.
- `PromptShare.granted_by_user` → `User` (via `granted_by`, no cascade).

## Modified Entities

### Prompt (`src/db/models/prompt.py`)

- Add `shares = relationship("PromptShare", back_populates="prompt", cascade="all, delete-orphan")`.
- Add column `legacy_public: Boolean NOT NULL, default=False`. Migration backfills `True` on every pre-existing row (grandfathering, FR-017); new prompts get `False` (FR-016). Owner/admin can flip `True → False` via `PATCH /api/prompts/{id}` (FR-018); there is no path back to `True` — it is a one-time transition flag, not a re-enterable "make public" toggle.
- Derived, per-viewer attributes in API payloads only: `shared: bool` (an explicit `PromptShare` grants the viewer access; `false` for grandfathered-public visibility), `legacy_public: bool` (echoes the column, lets the frontend distinguish "Shared" from "Public (legacy)" badges), and `permission: 'read'|'edit'|'owner'` (viewer's effective level).

### User (`src/db/models/user.py`)

- Add `received_shares = relationship("PromptShare", foreign_keys="PromptShare.grantee_user_id", back_populates="grantee", cascade="all, delete-orphan")`.
- Existing `prompts` relationship stays cascade-free — owner hard-delete still orphans prompts (existing behavior, confirmed in research §1/clarification #3).

## Lifecycle & State Transitions

```text
(no grant) --grant(read|edit)--> ACTIVE(permission)
ACTIVE(read) --grant(edit)--> ACTIVE(edit)     # upsert, updated_at bumped, audit "granted"
ACTIVE(edit) --grant(read)--> ACTIVE(read)     # downgrade, same path
ACTIVE(*) --revoke--> (no grant)               # audit "revoked"
ACTIVE(*) --prompt deleted--> (row cascaded)
ACTIVE(*) --grantee hard-deleted--> (row cascaded)
ACTIVE(*) --grantor hard-deleted--> ACTIVE(*, granted_by=NULL)   # grant survives
ACTIVE(*) --grantee deactivated--> ACTIVE(*)   # row untouched; access moot (cannot log in)
```

## Effective Permission Resolution (authorization matrix source of truth)

For actor U on prompt P:

1. `AUTH_ENABLED=false` → legacy behavior, sharing inactive.
2. U is admin → `owner` level.
3. `P.user_id == U.id` → `owner` level.
4. Grant exists for (P, U) → grant's `permission` (`read` or `edit`).
5. `P.legacy_public == True` → `read` level (never `edit`).
6. Otherwise → no access (P invisible in listings; direct access 403/404).

| Action | Required level |
|--------|---------------|
| View prompt, version history, diffs | `read` (includes `legacy_public` prompts) |
| Update content/category/tags, revert version | `edit` (grandfathered-public alone is insufficient) |
| Delete, toggle favorite, grant/revoke/list shares, transfer ownership, un-grandfather (`legacy_public: true → false`) | `owner` |

## Repository Surface (`src/db/repositories/sharing_repository.py`)

- `upsert(prompt_id, grantee_user_id, permission, granted_by) -> PromptShare` — create or update-in-place (FR-003)
- `revoke(prompt_id, grantee_user_id) -> bool`
- `list_for_prompt(prompt_id) -> List[PromptShare]` — grant review (US3)
- `list_for_grantee(user_id) -> List[PromptShare]`
- `permission_for(prompt_id, user_id) -> Optional[str]` — hot path for authz checks

`PromptRepository.search()` / `search_count()` gain `visible_to_user_id: Optional[str]` and `shared_only: bool` per research §4 (the visibility filter itself is `owner ∪ shared-via-PromptShare ∪ legacy_public`; `shared_only` narrows to the `PromptShare` branch alone, excluding `legacy_public` rows).

`PromptRepository` also gains `set_legacy_public(prompt_id, value: bool) -> Prompt` (or reuses the existing update path) for the owner/admin-only un-grandfather action (FR-018); service layer rejects `value=True` when the prompt is already `legacy_public=False` (one-way).

## Volume Assumptions

Tens of users, thousands of prompts, ≤ hundreds of grants per prompt; `idx_prompt_shares_grantee` plus the unique constraint's composite index cover both lookup directions. No pagination needed on grant lists in v1.
