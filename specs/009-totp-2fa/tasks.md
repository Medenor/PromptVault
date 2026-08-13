# Tasks: Two-Factor Authentication (TOTP)

**Input**: Design documents from `/specs/009-totp-2fa/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/totp-api.md, quickstart.md

**Tests**: Included — constitution Principle II (Test Coverage Gate, NON-NEGOTIABLE) requires tests written alongside implementation for every new endpoint/service method.

**Organization**: Tasks are grouped by user story (US1–US4, matching spec.md priorities P1/P1/P2/P3) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)

## Path Conventions

Single-project web app layout per plan.md: `src/` (backend), `src/web/static/ts/` (frontend TS), `tests/` at repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies and config needed before any 2FA code can be written

- [X] T001 Add `pyotp>=2.9.0` and `qrcode>=7.4.2` to `pyproject.toml` dependencies; run `uv sync` (or project's dependency install command)
- [X] T002 Add `totp_encryption_key: str` field to `AuthConfig` in `src/config/auth_config.py` (required when any user has `totp_enabled=True`; documented in `.env.example`), following the existing `jwt_private_key_path` field-definition style
- [X] T003 [P] Document `TOTP_ENCRYPTION_KEY` in `.env.example` and `docs/DEPLOYMENT.md`

**Checkpoint**: Dependencies installed, config surface ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Data model, encryption service, and shared plumbing that every user story depends on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Add `totp_enabled: Mapped[bool | None]` column (`default=False`) to `User` model in `src/db/models/user.py`
- [X] T005 [P] Create `TotpCredential` model in `src/db/models/totp_credential.py` (id, user_id FK unique, secret_ciphertext, secret_nonce, confirmed, last_used_step, created_at, confirmed_at) per data-model.md
- [X] T006 [P] Create `TotpRecoveryCode` model in `src/db/models/totp_recovery_code.py` (id, user_id FK, batch_id, code_hash, used_at, created_at) per data-model.md
- [X] T007 [P] Create `TotpLoginChallenge` model in `src/db/models/totp_login_challenge.py` (id, user_id FK, expires_at, consumed_at, created_at) per data-model.md
- [X] T008 [P] Create `TotpRolePolicy` model in `src/db/models/totp_role_policy.py` (role PK, required, updated_at, updated_by_user_id FK) per data-model.md
- [X] T009 Wire new models into `src/db/base.py` / model registry and add relationships on `User` (mirroring existing `sessions`/`password_reset_tokens` relationships) in `src/db/models/user.py`
- [X] T010 Generate portable Alembic migration `src/db/migrations/versions/XXXX_add_totp_2fa.py` for the new column + 4 tables, using `sa.true()`/`sa.false()` for boolean defaults and no dialect-specific introspection (per repo Alembic-portability convention); verify with `alembic upgrade head` / `alembic downgrade -1` on SQLite
- [X] T011 [P] Create `TotpRepository` in `src/db/repositories/totp_repository.py` with CRUD methods: get/upsert credential, get/insert recovery-code batch, mark code used, get/create/consume login challenge, get/set role policy
- [X] T012 [P] Create `TotpEncryptionService` in `src/services/auth/totp_encryption_service.py`: HKDF-derive an AES-256-GCM key from `AuthConfig.totp_encryption_key` at construction; `encrypt_secret(plaintext: str) -> tuple[str, str]` (ciphertext_b64, nonce_hex) and `decrypt_secret(ciphertext_b64, nonce_hex) -> str`, mirroring `BackupEncryptionService`'s AES-GCM usage but keyed from the server secret, not a passphrase (research.md §3)
- [X] T013 [P] Unit tests for `TotpEncryptionService` round-trip and tamper-detection in `tests/unit/services/auth/test_totp_encryption_service.py`
- [X] T014 Add `expensive` rate-limit tier wiring confirmation for the new 2FA router (reuse existing `rate_limit_expensive_attempts`/`rate_limit_expensive_window_seconds` from `AuthConfig`, no new keys) — verify limiter dependency import path used by `auth_password_router.py` is reusable as-is

**Checkpoint**: Schema, migration, encryption, and repository ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Enroll in TOTP 2FA (Priority: P1) 🎯 MVP (part 1 of 2)

**Goal**: A user can start enrollment (QR + secret), confirm with a code, and receive one-time recovery codes.

**Independent Test**: Enroll a single test account end-to-end; verify QR/secret is a valid provisioning URI, confirm activates 2FA, recovery codes are shown exactly once.

### Tests for User Story 1 ⚠️

- [X] T015 [P] [US1] Contract test `POST /api/auth/2fa/enroll` (201, 409 when already enabled, 429) in `tests/contract/test_totp_endpoints.py`
- [X] T016 [P] [US1] Contract test `POST /api/auth/2fa/verify` (200 with recovery codes, 400 no pending enrollment, 401 wrong code, 429) in `tests/contract/test_totp_endpoints.py`
- [X] T017 [P] [US1] Unit tests for `TotpService.enroll` / `confirm` (secret generation, QR SVG, replacing pending enrollment, refusing re-enroll when already active, recovery-code batch issuance) in `tests/unit/services/auth/test_totp_service.py`
- [X] T018 [P] [US1] Integration test: full enroll → confirm → recovery codes flow in `tests/integration/test_totp_flow.py`

### Implementation for User Story 1

- [X] T019 [US1] Implement `TotpService.enroll(user)` and `TotpService.confirm(user, code)` in `src/services/auth/totp_service.py`: generate base32 secret via `pyotp.random_base32()`, build `provisioning_uri` via `pyotp.totp.TOTP`, encrypt with `TotpEncryptionService`, upsert pending `TotpCredential` (T005/T011); on confirm, verify with `valid_window=1`, set `confirmed=True`/`confirmed_at`, flip `users.totp_enabled=True`, generate 10 recovery codes, hash each with the existing `PasswordService` Argon2id hasher, persist as a new batch (T006/T011), return plaintext codes once
- [X] T020 [US1] Render QR as inline SVG (no Pillow) for the enroll response — helper in `src/services/auth/totp_service.py` or a small `totp_qr.py` util, using the `qrcode` package's SVG factory
- [X] T021 [US1] Add `TotpEnrollResponse`, `TotpVerifyRequest`, `TotpConfirmResponse` Pydantic models to `src/web/models/auth_requests.py` / `auth_responses.py` per contracts/totp-api.md
- [X] T022 [US1] Create `src/web/routers/auth_totp_router.py` with `POST /api/auth/2fa/enroll` and `POST /api/auth/2fa/verify`, authenticated, rate-limited on the expensive tier (T014), audit-logging enable events (FR-017)
- [X] T023 [US1] Register `auth_totp_router` in the FastAPI app router includes (wherever other `auth_*_router` modules are registered)
- [X] T024 [US1] [P] Create `src/web/static/ts/profile-2fa.ts`: enrollment card UI — start enrollment, render QR SVG + manual secret, code-confirmation form, recovery-codes display with copy/download, typed i18n strings via `t()`
- [X] T025 [US1] [P] Add profile-2fa translation keys for all four supported locales (EN/FR/ES/DE) and wire `profile-2fa.ts` into the profile page template
- [X] T026 [US1] [P] Frontend unit tests for `profile-2fa.ts` enrollment flow in `src/web/static/ts/__tests__/profile-2fa.test.ts`

**Checkpoint**: Enrollment is fully functional and independently testable (login enforcement comes in US2)

---

## Phase 4: User Story 2 - Authenticate with 2FA at login (Priority: P1) 🎯 MVP (part 2 of 2)

**Goal**: Login for a 2FA-enabled account issues a short-lived challenge instead of a session; the challenge is exchanged for real tokens via TOTP or recovery code, with replay/expiry/lockout protection.

**Independent Test**: With a 2FA-enabled account (from US1), attempt login and verify no session is issued until the second factor succeeds; verify wrong/expired/replayed codes are rejected and recovery-code exchange works and single-uses the code.

### Tests for User Story 2 ⚠️

- [X] T027 [P] [US2] Contract test `POST /api/auth/login` challenge-issuance branch (200 challenge shape when `totp_enabled=True`, unchanged 200/401/423/429 otherwise) in `tests/contract/test_totp_endpoints.py`
- [X] T028 [P] [US2] Contract test `POST /api/auth/login/2fa` (200 success, 401 wrong code + lockout counting, 410 expired/consumed, 423 locked, 429) in `tests/contract/test_totp_endpoints.py`
- [X] T029 [P] [US2] Unit tests for `TotpService.verify_login_code` / `consume_recovery_code` (replay guard via `last_used_step`, recovery-code single-use, expiry) in `tests/unit/services/auth/test_totp_service.py`
- [X] T030 [P] [US2] Integration test: password → challenge → wrong code retry → correct code → tokens; separate case for recovery-code exchange; separate case for expired challenge; separate case for code replay in `tests/integration/test_totp_flow.py`

### Implementation for User Story 2

- [X] T031 [US2] Extend `JwtService` (`src/services/auth/jwt_service.py`) with a distinct `typ: "2fa_challenge"` short-lived (2 min) token issuance/validation helper, per research.md §5
- [X] T032 [US2] Implement `TotpService.issue_login_challenge(user)` (creates `TotpLoginChallenge` row + signs challenge JWT) and `TotpService.exchange_challenge(challenge_token, code)` (validates single-use via `consumed_at`/`expires_at`, accepts TOTP or recovery code, marks challenge consumed atomically) in `src/services/auth/totp_service.py`
- [X] T033 [US2] Modify `AuthService.login()` in `src/services/auth/auth_service.py`: after password validation succeeds, branch on `user.totp_enabled` — issue challenge (T032) instead of tokens when true
- [X] T034 [US2] Extend `LockoutService` (`src/services/auth/lockout_service.py`) so failed 2FA-challenge attempts increment the same failed-attempt counter used for password failures (FR-010)
- [X] T035 [US2] Add `TotpChallengeIssuedResponse`, `TotpChallengeExchangeRequest` Pydantic models to `src/web/models/auth_requests.py` / `auth_responses.py`
- [X] T036 [US2] Modify `src/web/routers/auth_session_router.py`: `/api/auth/login` response branches per T033; add new `POST /api/auth/login/2fa` endpoint calling `TotpService.exchange_challenge`, rate-limited, audit-logging challenge success/failure and recovery-code-used events (FR-017)
- [X] T037 [US2] [P] Modify `src/web/static/ts/auth.ts`: after password submit, detect challenge-shaped response and render a code-entry step (reusing `profile-2fa.ts` code-input component where practical) instead of treating it as a completed login
- [X] T038 [US2] [P] Modify `src/web/templates/auth/login.html` to include the challenge-step markup/container
- [X] T039 [US2] [P] Frontend unit tests for the login challenge step in `src/web/static/ts/__tests__/auth.test.ts`

**Checkpoint**: User Stories 1 AND 2 together deliver the full MVP — opt-in 2FA that actually gates login

---

## Phase 5: User Story 3 - Disable 2FA and manage recovery codes (Priority: P2)

**Goal**: A 2FA-enabled user can disable 2FA or regenerate recovery codes, both re-authenticated with password + current code.

**Independent Test**: With a 2FA-enabled account, attempt disable/regenerate with and without correct password+code; verify old recovery codes stop working after regeneration/disable.

### Tests for User Story 3 ⚠️

- [X] T040 [P] [US3] Contract test `POST /api/auth/2fa/disable` (204, 401 wrong password/code, 429) in `tests/contract/test_totp_endpoints.py`
- [X] T041 [P] [US3] Contract test `POST /api/auth/2fa/recovery-codes/regenerate` (200 new codes, 401, 429; old codes invalidated) in `tests/contract/test_totp_endpoints.py`
- [X] T042 [P] [US3] Unit tests for `TotpService.disable` / `regenerate_recovery_codes` (password+code re-auth, cascade delete on disable, old-batch invalidation on regenerate) in `tests/unit/services/auth/test_totp_service.py`
- [X] T043 [P] [US3] Integration test: enroll → disable → login shows no challenge; enroll → regenerate → old code fails, new code works in `tests/integration/test_totp_flow.py`

### Implementation for User Story 3

- [X] T044 [US3] Implement `TotpService.disable(user, password, code)` and `TotpService.regenerate_recovery_codes(user, password, code)` in `src/services/auth/totp_service.py`: verify password via `PasswordService`, verify code via TOTP-or-recovery check (reuse T032's code-acceptance logic), then delete/replace rows per data-model.md lifecycle
- [X] T045 [US3] Add `TotpDisableRequest` Pydantic model to `src/web/models/auth_requests.py` (shared shape for disable + regenerate per contracts/totp-api.md)
- [X] T046 [US3] Add `POST /api/auth/2fa/disable` and `POST /api/auth/2fa/recovery-codes/regenerate` to `src/web/routers/auth_totp_router.py`, rate-limited, audit-logging disable events (FR-017)
- [X] T047 [US3] [P] Extend `src/web/static/ts/profile-2fa.ts` with disable and regenerate UI (password + code re-auth form, confirmation before disabling, new-codes display reusing the enrollment recovery-code component)
- [X] T048 [US3] [P] Frontend unit tests for disable/regenerate flows in `src/web/static/ts/__tests__/profile-2fa.test.ts`

**Checkpoint**: User Stories 1–3 fully functional; account lifecycle for 2FA is complete

---

## Phase 6: User Story 4 - Admin-enforced 2FA policy (Priority: P3)

**Goal**: Admins can require 2FA per role; non-enrolled users in a required role are routed into mandatory enrollment after login before reaching the rest of the app.

**Independent Test**: Configure a role as requiring 2FA, log in as a non-enrolled user in that role, verify they're blocked from other functionality until enrollment completes; verify other roles unaffected.

### Tests for User Story 4 ⚠️

- [X] T049 [P] [US4] Contract test `GET/PUT /api/admin/2fa/policy` (200, 403 non-admin, 422 unknown role) in `tests/contract/test_totp_endpoints.py`
- [X] T050 [P] [US4] Unit tests for `TotpPolicyService.get_policy` / `set_policy` / `is_required_for(role)` in `tests/unit/services/auth/test_totp_policy_service.py`
- [X] T051 [P] [US4] Integration test: set `admin` role required → non-enrolled admin login is routed to mandatory enrollment and blocked elsewhere; enrolled admin logs in normally; non-required role unaffected; unset policy removes enforcement in `tests/integration/test_totp_flow.py`

### Implementation for User Story 4

- [X] T052 [US4] Implement `TotpPolicyService` in `src/services/auth/totp_policy_service.py`: `get_all()`, `set(role, required, admin_user)`, `is_required_for(role) -> bool`, backed by `TotpRolePolicy` via `TotpRepository`
- [X] T053 [US4] Modify `AuthService.login()` / `src/web/routers/auth_session_router.py` password-step response: when `TotpPolicyService.is_required_for(user.role)` is true and `user.totp_enabled` is false, include the `enrollment_required: true` discriminator per contracts/totp-api.md §7 instead of a normal session
- [X] T054 [US4] Add `TotpPolicyResponse`, `TotpPolicyUpdateRequest` Pydantic models to `src/web/models/auth_requests.py` / `auth_responses.py`
- [X] T055 [US4] Create `src/web/routers/admin_totp_policy_router.py` with `GET`/`PUT /api/admin/2fa/policy`, admin-only, audit-logging policy changes
- [X] T056 [US4] Register `admin_totp_policy_router` in the FastAPI app router includes
- [X] T057 [US4] [P] Frontend: mandatory-enrollment interstitial in `src/web/static/ts/auth.ts` (or a new `enrollment-required.ts`) that intercepts the `enrollment_required` response and blocks navigation until `profile-2fa.ts` enrollment completes
- [X] T058 [US4] [P] Frontend: admin policy management screen (role list + required toggle) — new `src/web/static/ts/admin-2fa-policy.ts` + template hook in the existing admin users page
- [X] T059 [US4] [P] Frontend unit tests for the interstitial and admin policy screen in `src/web/static/ts/__tests__/`

**Checkpoint**: All four user stories independently functional

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Coverage gate, dialect portability, docs, and full-suite validation

- [X] T060 [P] Run the full backend suite and confirm ≥85% coverage on all new modules (`python3 -m pytest`)
- [X] T061 [P] Run the full frontend suite and confirm ≥85% coverage (`npm run test`)
- [X] T062 Run the migration round-trip against both SQLite (default dev db) and a throwaway Postgres container per `docs/agents/testing.md` / `docs/agents/git-and-docker-safety.md` conventions — never the production compose file
- [X] T063 [P] Add a changelog entry for the TOTP 2FA feature (Improvement Plan 2026-08 item #7) following the repo's existing changelog convention (see recent commits like "docs: add #86 coverage HTML report fix to changelog")
- [X] T064 Run `make lint` (formatting, lint, typecheck across both stacks) and fix any violations
- [X] T065 Execute the full quickstart.md validation guide end-to-end manually (all 6 sections) against `make dev`; while running §2 (enrollment), self-time the scan→confirm→recovery-codes flow and confirm it completes in under 2 minutes (SC-001)
- [X] T066 [P] Verify no TOTP secrets, codes, or recovery codes appear in application logs across all new code paths (grep-audit `src/services/auth/totp_*.py` and `src/web/routers/auth_totp_router.py` for logging statements)
- [X] T067 [P] Keyboard-navigation and screen-reader smoke test of the enrollment card (profile-2fa.ts), login challenge step (auth.ts), and mandatory-enrollment interstitial — verify all controls are reachable via Tab/Shift+Tab, form fields have accessible labels, and QR fallback (manual-entry secret) is announced (FR-019)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **US1 (Phase 3)** and **US2 (Phase 4)**: Both P1, together form the MVP. US2 depends on US1's `TotpCredential`/confirmed state existing, so implement US1 first even though both are P1.
- **US3 (Phase 5)**: Depends on Foundational + US1 (needs an active credential to disable/regenerate); independently testable once US1 is done.
- **US4 (Phase 6)**: Depends on Foundational + US2 (policy enforcement plugs into the login/challenge branch built in US2).
- **Polish (Phase 7)**: Depends on all desired user stories being complete.

### Within Each User Story

- Tests written and failing before implementation (T0xx test tasks precede implementation tasks in each phase)
- Models/migration (Phase 2) before services
- Services before endpoints
- Backend endpoints before frontend wiring
- Story complete before moving to next priority

### Parallel Opportunities

- T005–T008 (four new models) in parallel
- T011–T013 (repository, encryption service, encryption tests) in parallel after T004–T010
- Within each story's Tests block, all [P] contract/unit/integration test tasks in parallel
- Frontend tasks marked [P] within a story can run in parallel with that story's backend tasks once the relevant contract is stable (endpoints tasks T022/T036/T046/T055 define the contract frontend tasks consume)

---

## Parallel Example: User Story 1

```bash
# Tests for User Story 1 together:
Task: "Contract test POST /api/auth/2fa/enroll in tests/contract/test_totp_endpoints.py"
Task: "Contract test POST /api/auth/2fa/verify in tests/contract/test_totp_endpoints.py"
Task: "Unit tests for TotpService.enroll/confirm in tests/unit/services/auth/test_totp_service.py"
Task: "Integration test enroll->confirm->recovery-codes in tests/integration/test_totp_flow.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (enrollment)
4. Complete Phase 4: User Story 2 (login enforcement) — **this is where 2FA becomes a real security boundary**
5. **STOP and VALIDATE**: Run quickstart.md §2–§3 manually
6. Deploy/demo if ready — this is the MVP (spec explicitly marks both US1 and US2 as P1)

### Incremental Delivery

1. Setup + Foundational → foundation ready
2. US1 + US2 → MVP: opt-in 2FA that works end-to-end → validate → deploy
3. US3 → account lifecycle (disable/regenerate) → validate → deploy
4. US4 → admin enforcement policy → validate → deploy
5. Polish → coverage gate, dialect portability, docs, lint

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Verify tests fail before implementing (constitution Principle II)
- Commit after each task or logical group, following existing "[Generated by AI] type: description (#issue)" commit style
- Stop at each checkpoint to validate the story independently before continuing
- Never log TOTP secrets, codes, or recovery codes in any form (T066 is a final audit, but keep it in mind throughout)
