# Phase 0 Research: Two-Factor Authentication (TOTP)

## 1. TOTP library

**Decision**: `pyotp` (new dependency).

**Rationale**: Standard, minimal, well-maintained RFC 6238 implementation. Provides `pyotp.random_base32()` for secret generation, `pyotp.totp.TOTP(secret).provisioning_uri(...)` for the `otpauth://` URI to encode in the QR, and `TOTP.verify(code, valid_window=1)` which natively supports the ±1 time-step tolerance required by FR-006.

**Alternatives considered**: Hand-rolled HMAC-based implementation — rejected, reinventing a security primitive with no benefit over a well-audited library. `python-otp` — smaller community, less maintained than `pyotp`.

## 2. QR code rendering

**Decision**: Server-rendered SVG using the `qrcode` Python package (new dependency, `qrcode[pil]` not needed — plain SVG factory avoids the Pillow dependency), returned inline in the enrollment API response (as an SVG string) rather than a client-side JS QR library.

**Rationale**: Keeps CSP clean (no inline `<script>`-driven canvas rendering, no third-party CDN script) — matches the improvement-plan note "server-rendered SVG... keep CSP-clean." The manual-entry secret is always shown alongside as a fallback for screen-reader users and QR-scan failures (FR-001, FR-019).

**Alternatives considered**: Client-side `qrcode` npm lib — rejected per plan guidance to avoid CSP complications from canvas/script-based rendering; would also add a new frontend dependency for a one-screen feature.

## 3. TOTP secret encryption at rest

**Decision**: AES-256-GCM, same primitive as `BackupEncryptionService`, but keyed from a **server-held** symmetric key rather than a per-operation user passphrase. The key is derived once at startup from a new `AuthConfig` setting `totp_encryption_key` (a required env var when 2FA is used, analogous to how `jwt_private_key_path` is required for JWT signing) via HKDF, and cached in `TotpEncryptionService`.

**Rationale**: Unlike backup files, the TOTP secret must be decrypted transparently on every login without prompting the user for a passphrase — there is no user-supplied secret available at verification time. This is a fundamentally different threat model from backup encryption (data-at-rest protected by a passphrase only the admin knows) — 2FA secrets need envelope encryption keyed by an application secret, the same trust boundary already relied on for JWT private keys and `SECRET_KEY`-style values. Reusing the *algorithm* (AES-256-GCM via `cryptography`) keeps the codebase consistent; reusing the *key-management pattern* (passphrase-derived) would be actively wrong here since it would require prompting for a passphrase on every login, breaking UX and FR-005.

**Alternatives considered**: Storing secrets in plaintext — rejected outright, violates FR-004 and constitution Principle III. Reusing `BackupEncryptionService.enable(passphrase)` — rejected, wrong trust model (see rationale). Per-user derived keys from the user's password hash — rejected, password changes would break the ability to decrypt the TOTP secret, and Argon2id hashes are intentionally one-way/non-reversible.

## 4. Recovery code storage

**Decision**: Generate 10 codes per batch (8-char alphanumeric, e.g. `xxxx-xxxx` formatted for readability), store each as an individual row with an Argon2id hash (reusing `PasswordService`'s hasher) and a `used_at` timestamp (NULL = unused). A batch is superseded wholesale on regeneration or disable.

**Rationale**: Matches FR-003/FR-008/FR-012/FR-013. Per-code rows (rather than a single JSON blob of hashes) make single-use consumption an atomic per-row update and make "remaining count" trivial to query — simpler than mutating a JSON array under concurrent access. 10 codes is the common industry default (GitHub, Google both issue 10).

**Alternatives considered**: JSON array of hashes on the `users` row (as the improvement-plan sketch literally suggested) — reconsidered in favor of a dedicated table for atomic single-code consumption and clean regeneration semantics; still portable across both dialects via a standard SQLAlchemy table, no JSON-column dialect quirks to manage.

## 5. Login challenge token

**Decision**: A signed, short-lived (2 min) JWT-like token issued via the existing `python-jose`/ES256 machinery already used for access/refresh tokens, with a distinct `typ: "2fa_challenge"` claim and a `jti` recorded server-side (new lightweight table or reuse of session-adjacent storage) to enforce single-use (FR-009, spec Edge Cases "challenge reuse after success").

**Rationale**: Reuses existing signing infrastructure (`JwtService`) rather than introducing a second token format/library. Server-side single-use tracking (rather than trusting a short expiry alone) is required because FR-009 and the edge cases explicitly call out both expiry *and* reuse-after-success as distinct failure modes.

**Alternatives considered**: Opaque random token stored server-side only (no JWT) — viable alternative with equivalent security properties; JWT chosen for consistency with the rest of the codebase's token handling and to reuse existing claim-validation code paths in `JwtService`.

## 6. Rate limiting

**Decision**: Reuse the existing `slowapi`-based tiered limiter. 2FA enroll/verify/disable/regenerate endpoints map to the existing "expensive" tier (`rate_limit_expensive_attempts` / `rate_limit_expensive_window_seconds`), which the codebase already defines for costly/sensitive operations — no new config keys needed beyond wiring the decorator, consistent with the plan's "5/min" target (the expensive tier's existing defaults are in this range; exact values confirmed against `auth_config.py` during implementation).

**Rationale**: Avoids inventing a parallel rate-limit configuration surface; keeps 2FA endpoints consistent with how `auth_password_router.py` / `auth_registration_router.py` already apply limits.

**Alternatives considered**: New dedicated `rate_limit_2fa_*` config keys — unnecessary duplication; the expensive tier already exists for exactly this class of endpoint.

## 7. Admin role policy storage

**Decision**: A small `totp_role_policies` table (`role: str primary key`, `required: bool`) rather than a single JSON/CSV settings blob, queried once per login and cacheable in-process with a short TTL if needed later (not required for v1 given expected scale).

**Rationale**: Matches existing DB-backed settings patterns in the codebase (Principle V — no JSON/file config for new features) and makes the policy queryable/auditable per-role rather than requiring blob parsing.

**Alternatives considered**: Single JSON column on a settings singleton table — rejected as it fights the "DB-backed persistence" principle's spirit of normalized, queryable data for anything beyond genuinely unstructured content.

## Outstanding NEEDS CLARIFICATION

None — all technical unknowns from the Technical Context are resolved above.
