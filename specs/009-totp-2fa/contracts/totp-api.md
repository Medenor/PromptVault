# API Contracts: Two-Factor Authentication (TOTP)

**Feature**: 009-totp-2fa | **Date**: 2026-08-13

All endpoints require authentication (existing session/JWT) except the login-challenge exchange, which is authorized by the challenge token itself. All 2FA-mutating endpoints are rate-limited on the existing "expensive" tier (research.md §6). Request/response models live in `src/web/models/auth_requests.py` / `auth_responses.py`. Every state-changing action is audit-logged (FR-017). Secrets, codes, and recovery codes are never logged in plaintext.

## 1. Start enrollment

```
POST /api/auth/2fa/enroll
```

**Authorization**: any authenticated user without `totp_enabled=True`.

**Request body**: none.

**Responses**:

- `201 Created` (`TotpEnrollResponse`):

  ```json
  {
    "secret": "JBSWY3DPEHPK3PXP",
    "provisioning_uri": "otpauth://totp/PromptVault:alice?secret=...&issuer=PromptVault",
    "qr_svg": "<svg ...>...</svg>"
  }
  ```

- `409 Conflict` — user already has `totp_enabled=True`. Body `{"detail": "<i18n: auth.2fa_already_enabled>"}`.
- `429` — rate limit exceeded.

Starting enrollment again while unconfirmed replaces the pending secret (data-model.md, `TotpCredential` lifecycle).

## 2. Confirm enrollment

```
POST /api/auth/2fa/verify
```

**Authorization**: any authenticated user with a pending (unconfirmed) `TotpCredential`.

**Request body** (`TotpVerifyRequest`):

```json
{ "code": "123456" }
```

**Responses**:

- `200 OK` (`TotpConfirmResponse`) — activates 2FA, issues recovery codes exactly once:

  ```json
  {
    "enabled": true,
    "recovery_codes": ["xxxx-xxxx", "xxxx-xxxx", "... (10 total)"]
  }
  ```

- `400 Bad Request` — no pending enrollment to confirm.
- `401 Unauthorized` — code incorrect or outside the ±1 time-step window (FR-006). Body `{"detail": "<i18n: auth.2fa_code_invalid>"}`.
- `429` — rate limit exceeded.

`recovery_codes` is returned only in this response; it is never retrievable again (FR-003).

## 3. Disable 2FA

```
POST /api/auth/2fa/disable
```

**Authorization**: any authenticated user with `totp_enabled=True`.

**Request body** (`TotpDisableRequest`):

```json
{ "password": "current-password", "code": "123456" }
```

`code` accepts either a current TOTP code or an unused recovery code.

**Responses**:

- `204 No Content` — 2FA disabled; `TotpCredential` and all recovery codes deleted (FR-012).
- `401 Unauthorized` — wrong password or code. Body `{"detail": "<i18n: auth.2fa_disable_failed>"}` (generic — does not reveal which factor was wrong).
- `429` — rate limit exceeded.

## 4. Regenerate recovery codes

```
POST /api/auth/2fa/recovery-codes/regenerate
```

**Authorization**: any authenticated user with `totp_enabled=True`.

**Request body** (`TotpDisableRequest` — same shape, password + code):

```json
{ "password": "current-password", "code": "123456" }
```

**Responses**:

- `200 OK` (`TotpConfirmResponse` shape, reused):

  ```json
  { "recovery_codes": ["xxxx-xxxx", "... (10 total)"] }
  ```

  All previously issued codes are invalidated in the same transaction (FR-013).

- `401 Unauthorized` — wrong password or code.
- `429` — rate limit exceeded.

## 5. Login — password step (modified existing endpoint)

```
POST /api/auth/login
```

**Authorization**: none (public, existing behavior).

**Responses** (modified):

- `200 OK`, existing body — when the user has `totp_enabled=False` (unchanged behavior, FR-005 last clause).
- `200 OK`, new shape when `totp_enabled=True` (`TotpChallengeIssuedResponse`):

  ```json
  {
    "challenge_token": "eyJhbGciOi...",
    "expires_in": 120
  }
  ```

  No access/refresh tokens are issued at this step (FR-005).

- `401 Unauthorized` — bad credentials (unchanged).
- `423 Locked` — account locked (unchanged, shared lockout counter).
- `429` — rate limit exceeded (unchanged).

## 6. Login — 2FA exchange (new endpoint)

```
POST /api/auth/login/2fa
```

**Authorization**: none (public) — authorized by a valid, unconsumed, unexpired `challenge_token`.

**Request body** (`TotpChallengeExchangeRequest`):

```json
{ "challenge_token": "eyJhbGciOi...", "code": "123456" }
```

`code` accepts either a current TOTP code or an unused recovery code (FR-008).

**Responses**:

- `200 OK` — existing full-login response body (access + refresh tokens), challenge marked consumed.
- `401 Unauthorized` — wrong code. Body `{"detail": "<i18n: auth.2fa_code_invalid>"}`; counts toward shared lockout (FR-010).
- `410 Gone` — challenge expired or already consumed (FR-009, Edge Cases). Body `{"detail": "<i18n: auth.2fa_challenge_expired>"}`; client must restart from `/api/auth/login`.
- `423 Locked` — account locked by the shared counter.
- `429` — rate limit exceeded.

## 7. Admin — get/set required-2FA role policy

```
GET  /api/admin/2fa/policy
PUT  /api/admin/2fa/policy
```

**Authorization**: `admin` role only.

**GET response** (`TotpPolicyResponse`):

```json
{ "roles": [{"role": "admin", "required": true}, {"role": "editor", "required": false}, {"role": "viewer", "required": false}] }
```

**PUT request** (`TotpPolicyUpdateRequest`):

```json
{ "role": "admin", "required": true }
```

**PUT responses**:

- `200 OK` — updated policy row, same shape as one entry of the GET list.
- `403 Forbidden` — requester is not an admin.
- `422` — unknown role value.

Enforcement (FR-015) is evaluated at login for users in a `required=true` role without `totp_enabled=True`: the password-step response (`/api/auth/login`) is extended with an additional discriminator field (`enrollment_required: true`) alongside the normal full-login body, routing the frontend into the mandatory enrollment interstitial before granting access to other functionality. Exact response-shape wiring finalized during implementation; contract obligation is that non-enrolled, policy-required users never receive a usable session without completing enrollment first.
