# Phase 1 Data Model: Two-Factor Authentication (TOTP)

## `users` table (modified)

Add one column:

| Column | Type | Default | Notes |
|---|---|---|---|
| `totp_enabled` | `bool` | `sa.false()` | Whether 2FA is active (confirmed enrollment). Drives login branching (FR-005). |

The secret and recovery codes live in dedicated tables (see below), not on `users`, so that a pending/unconfirmed enrollment doesn't require nullable secret columns on the hot-path `users` row.

## `totp_credentials` (new)

One row per user, created on enrollment start, holds the encrypted secret.

| Column | Type | Notes |
|---|---|---|
| `id` | `String(36)` PK | UUID |
| `user_id` | `String(36)` FK → `users.id`, unique, indexed | One credential per user |
| `secret_ciphertext` | `String` (base64) | AES-256-GCM ciphertext of the base32 TOTP secret |
| `secret_nonce` | `String(32)` (hex) | GCM nonce, unique per encryption |
| `confirmed` | `bool`, default `sa.false()` | False until the user verifies a code (FR-002) |
| `last_used_step` | `int`, nullable | Last successfully-verified TOTP time-step counter — replay guard (FR-007) |
| `created_at` | `DateTime(timezone=True)` | |
| `confirmed_at` | `DateTime(timezone=True)`, nullable | |

**Lifecycle**: Starting enrollment replaces any existing unconfirmed row for that user (upsert). Confirming sets `confirmed=True`, `confirmed_at=now()`, and flips `users.totp_enabled=True`. Disabling deletes the row and flips `users.totp_enabled=False`.

## `totp_recovery_codes` (new)

Multiple rows per user per batch; a regeneration event creates a new batch and invalidates the old one.

| Column | Type | Notes |
|---|---|---|
| `id` | `String(36)` PK | UUID |
| `user_id` | `String(36)` FK → `users.id`, indexed | |
| `batch_id` | `String(36)`, indexed | Groups codes issued together; only the latest batch per user is valid |
| `code_hash` | `String(255)` | Argon2id hash of the code (reuses `PasswordService` hasher) |
| `used_at` | `DateTime(timezone=True)`, nullable | NULL = unused; set on consumption (FR-008) |
| `created_at` | `DateTime(timezone=True)` | |

**Lifecycle**: Enrollment confirmation and each regeneration insert a fresh batch of 10 rows and mark any prior batch's unused rows as invalidated (deleted, or superseded — implementation may hard-delete the prior batch since old codes must stop working immediately per FR-013). Disabling 2FA deletes all rows for the user.

## `totp_login_challenges` (new)

Short-lived, single-use record backing the login-challenge token (see research.md §5).

| Column | Type | Notes |
|---|---|---|
| `id` | `String(36)` PK | Matches the `jti` claim in the issued challenge JWT |
| `user_id` | `String(36)` FK → `users.id`, indexed | |
| `expires_at` | `DateTime(timezone=True)` | `created_at + 2min` |
| `consumed_at` | `DateTime(timezone=True)`, nullable | Set on successful exchange; a consumed or expired row refuses reuse (FR-009, Edge Cases) |
| `created_at` | `DateTime(timezone=True)` | |

**Lifecycle**: Created when password validation succeeds for a `totp_enabled` user. Consumed (single write) on successful TOTP/recovery-code exchange. Expired/consumed rows are inert; a periodic cleanup (or lazy delete-on-lookup) prevents unbounded growth — not a v1 blocker given short TTL.

## `totp_role_policies` (new)

Admin-configured per-role enforcement (FR-014).

| Column | Type | Notes |
|---|---|---|
| `role` | `String(50)` PK | Matches `users.role` values (`viewer`, `editor`, `admin`) |
| `required` | `bool`, default `sa.false()` | Whether members of this role must have 2FA enabled |
| `updated_at` | `DateTime(timezone=True)` | |
| `updated_by_user_id` | `String(36)` FK → `users.id`, nullable | Admin who last changed the policy (audit trail) |

**Lifecycle**: Rows are upserted by admin policy updates; absence of a row for a role is equivalent to `required=False`. Checked at login for users without `totp_enabled` (FR-015).

## Relationships

```text
User (1) ──── (0..1) TotpCredential
User (1) ──── (0..N) TotpRecoveryCode   [only latest batch_id is "live"]
User (1) ──── (0..N) TotpLoginChallenge [ephemeral]
Role (string, not a table) ── (0..1) TotpRolePolicy
```

## Validation rules (from Functional Requirements)

- `TotpCredential.confirmed=False` rows never satisfy a login challenge or set `users.totp_enabled=True` (FR-002).
- `TotpCredential` insert/replace on repeated enrollment start only affects the unconfirmed row; an already-`confirmed=True` credential blocks a new enrollment start (spec User Story 1, Acceptance Scenario 5; the service must reject re-enrollment while `totp_enabled=True`).
- `last_used_step` must be strictly greater than any previously accepted step for that credential to accept a new code (FR-007 replay guard).
- `TotpRecoveryCode.used_at` is set exactly once, atomically (guard against double-spend races) (FR-008).
- `TotpLoginChallenge` rows are checked for `consumed_at IS NULL AND expires_at > now()` before accepting an exchange; a matching row's `consumed_at` is set in the same transaction as success to prevent replay (FR-009, Edge Cases).
- Alembic migration must use `sa.inspect()`/dialect-neutral APIs, `sa.true()`/`sa.false()` for boolean defaults — no `sqlite_master`/`PRAGMA` introspection, no raw int literals for booleans (project convention, see repo memory on Alembic portability).
