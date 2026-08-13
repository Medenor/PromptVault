# Implementation Plan: Two-Factor Authentication (TOTP)

**Branch**: `009-totp-2fa` | **Date**: 2026-08-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-totp-2fa/spec.md`

## Summary

Add optional TOTP-based two-factor authentication to the existing auth stack: enrollment (QR + manual secret), login-time challenge (short-lived token issued after password success, exchanged for real tokens with a TOTP or recovery code), self-service disable/regenerate (re-authenticated with password + code), and an admin-configurable per-role enforcement policy. Built entirely on existing patterns — Argon2id hashing, ES256 JWTs, `slowapi` rate limiting, SQLAlchemy/Alembic, service-layer architecture — with one new server-held symmetric key for encrypting TOTP secrets at rest.

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript (frontend, `src/web/static/ts/`)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, Alembic, `pyotp` (new), `cryptography` (AES-256-GCM, already a dependency), `argon2-cffi` (already a dependency, reused for recovery-code hashing), `slowapi` (rate limiting), `python-jose` (JWT)

**Storage**: PostgreSQL (prod) / SQLite (dev/test) via SQLAlchemy ORM + Alembic migrations — dialect-portable per existing project convention

**Testing**: pytest + pytest-cov (backend, ≥85% coverage gate), Vitest (frontend TS)

**Target Platform**: Linux server (Docker), existing FastAPI web app

**Project Type**: Web application (backend `src/`, frontend `src/web/static/ts/` + Jinja templates) — single repo, not separate frontend/backend projects

**Performance Goals**: 2FA verification adds no more than one extra DB round trip + one TOTP computation (~microseconds) to the login path; no measurable latency regression for non-enrolled users (unchanged code path)

**Constraints**: TOTP secret must be decryptable transparently by the server on every login (not passphrase-gated like backup encryption) — requires a server-held symmetric key, not a per-request user secret. Auth endpoints must stay rate-limited per existing `slowapi` conventions. No new plaintext secrets in logs (existing "never log credentials" rule extends to TOTP secrets/codes/recovery codes).

**Scale/Scope**: Single-tenant self-hosted deployments (per existing PromptVault scale), auth tables already sized for the existing user base; 2FA adds 2 new tables + 3 columns on `users`, no expected scale concerns.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Layered Service Architecture**: New `TotpService` and `TotpPolicyService` in `src/services/auth/`; new `TotpRepository`/reuse of `UserRepository` in `src/db/repositories/`; new thin router(s) in `src/web/routers/`. No layer bypass. ✅ PASS
- **II. Test Coverage Gate**: All new service methods and endpoints get corresponding tests written alongside implementation; coverage gate (≥85%) applies to the branch as a whole. ✅ PASS (tracked in tasks.md)
- **III. Security-First Authentication**: 2FA endpoints are all authenticated (except the login-challenge exchange, which is protected by the challenge token + rate limiting) and rate-limited via `slowapi`, consistent with existing auth endpoints. TOTP secrets encrypted at rest, recovery codes Argon2-hashed, never plaintext-logged. ✅ PASS
- **IV. TypeScript-Only Frontend**: All new frontend code (enrollment card, QR display, challenge step, recovery-code prompt) written in TypeScript under `src/web/static/ts/`, typed i18n via `t()`. ✅ PASS
- **V. Database-Backed Persistence**: New tables/columns via SQLAlchemy ORM + Alembic migration, portable across SQLite/PostgreSQL (no raw dialect-specific SQL, no `sqlite_master`/`PRAGMA` introspection, booleans via `sa.true()`/`sa.false()`). ✅ PASS

No violations requiring justification. Complexity Tracking section is empty.

## Project Structure

### Documentation (this feature)

```text
specs/009-totp-2fa/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/             # Phase 1 output
└── tasks.md               # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/
├── db/
│   ├── models/
│   │   ├── user.py                     # MODIFIED: totp_enabled column only (secret lives in new totp_credentials table, see data-model.md)
│   │   ├── totp_credential.py          # NEW: encrypted secret, confirmed flag, last-used step (replay guard)
│   │   ├── totp_recovery_code.py       # NEW: per-code Argon2 hash, used flag, batch id
│   │   └── totp_role_policy.py         # NEW: role -> required bool
│   ├── repositories/
│   │   └── totp_repository.py          # NEW: CRUD for the three tables above
│   └── migrations/versions/
│       └── XXXX_add_totp_2fa.py        # NEW: portable Alembic migration
├── services/
│   └── auth/
│       ├── totp_service.py             # NEW: enroll, confirm, verify, consume-recovery, disable, regenerate
│       ├── totp_encryption_service.py  # NEW: AES-256-GCM encrypt/decrypt of TOTP secret using server-held key (env-derived, like JWT key material)
│       ├── totp_policy_service.py      # NEW: admin role-policy get/set, enforcement check
│       ├── auth_service.py             # MODIFIED: login() branches to challenge issuance when totp_enabled
│       └── lockout_service.py          # MODIFIED: shared counter extended to 2FA challenge failures
├── web/
│   ├── routers/
│   │   ├── auth_totp_router.py         # NEW: /api/auth/2fa/enroll, /verify, /disable, /recovery-codes/regenerate
│   │   ├── auth_session_router.py      # MODIFIED: /api/auth/login returns challenge when applicable; new /api/auth/login/2fa
│   │   └── admin_totp_policy_router.py # NEW: admin GET/PUT for require_2fa_roles
│   ├── models/
│   │   └── auth_requests.py / auth_responses.py  # MODIFIED: new request/response schemas
│   ├── static/ts/
│   │   ├── profile-2fa.ts              # NEW: enrollment card, QR render, recovery-code display/download
│   │   └── auth.ts                     # MODIFIED: login flow branches to challenge step
│   └── templates/auth/
│       └── login.html                  # MODIFIED: challenge-step markup
tests/
├── unit/services/auth/
│   ├── test_totp_service.py            # NEW
│   └── test_totp_encryption_service.py # NEW
├── integration/
│   └── test_totp_flow.py               # NEW: enroll → login-challenge → disable, both dialects for migration
└── contract/
    └── test_totp_endpoints.py          # NEW
```

**Structure Decision**: Single web application repo (existing PromptVault layout) — service-oriented backend under `src/`, TypeScript frontend under `src/web/static/ts/` + Jinja templates. No new top-level projects; 2FA is additive to the existing `src/services/auth/` and `src/web/routers/` auth surface, following the same layering and naming conventions as the current `password_reset_service.py` / `auth_password_router.py` pair.

## Complexity Tracking

*No constitution violations — section not needed.*
