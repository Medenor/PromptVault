# Quickstart Validation: Two-Factor Authentication (TOTP)

**Feature**: 009-totp-2fa | **Date**: 2026-08-13

Runnable scenarios proving the feature end-to-end. Contracts: [contracts/totp-api.md](contracts/totp-api.md). Data model: [data-model.md](data-model.md).

## Prerequisites

```bash
git checkout 009-totp-2fa
pip install -r requirements.txt && npm install
export TOTP_ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")  # dev-only value
alembic upgrade head          # applies the totp_credentials / totp_recovery_codes / totp_login_challenges / totp_role_policies migration
npm run build                 # TS must be compiled before manual UI testing
make dev                      # backend (:8003) + frontend (:5173)
```

## 1. Automated suites (primary gate)

```bash
# Backend — coverage must stay ≥ 85%
python3 -m pytest tests/unit/services/auth/test_totp_service.py \
                   tests/unit/services/auth/test_totp_encryption_service.py \
                   tests/integration/test_totp_flow.py \
                   tests/contract/test_totp_endpoints.py

# Migration portability — run once against SQLite (default) and once against a throwaway Postgres container
alembic upgrade head && alembic downgrade -1   # SQLite
# (Postgres round-trip per docs/agents/testing.md conventions — never the prod compose file)

# Frontend
npm run test -- profile-2fa
```

## 2. Manual: enroll (User Story 1)

1. Log in as a test user without 2FA.
2. Open Profile → Security → "Enable two-factor authentication".
3. Confirm a QR code and a manual-entry secret are both shown.
4. Scan with an authenticator app (or compute a code manually with `pyotp.TOTP(secret).now()` for a quick check), enter the 6-digit code.
5. Confirm the response shows 10 recovery codes, offers a download/copy action, and that reloading the profile page never shows the codes again.
6. Confirm attempting to start enrollment again is refused (`409`) while 2FA stays active.

**Expected**: matches spec User Story 1, acceptance scenarios 1–5.

## 3. Manual: login challenge (User Story 2)

1. Log out. Log back in with the enrolled account's username/password.
2. Confirm the response is a challenge (no session yet) and the UI prompts for a code.
3. Enter a wrong code — confirm refusal and that the challenge is still usable for a retry.
4. Enter the correct current code — confirm full login succeeds.
5. Immediately replay the same code against a fresh login attempt — confirm it is rejected (FR-007).
6. Start a new login, let the challenge sit idle past 2 minutes, then submit a correct code — confirm `410 Gone` and that the client is routed back to the password step.
7. Start a new login and use one of the recovery codes instead of a TOTP code — confirm success and that the same recovery code fails on a second use.

**Expected**: matches spec User Story 2, acceptance scenarios 1–7.

## 4. Manual: disable & regenerate (User Story 3)

1. From Profile → Security, attempt "Disable 2FA" with a wrong password — confirm refusal, 2FA stays on.
2. Retry with correct password + valid code — confirm 2FA turns off and a subsequent login needs no second factor.
3. Re-enroll, then use "Regenerate recovery codes" with correct password + code — confirm new codes are issued and any code from the original batch (retained from step 2 of §2) no longer works.

**Expected**: matches spec User Story 3, acceptance scenarios 1–3.

## 5. Manual: admin policy enforcement (User Story 4)

1. Log in as an admin, set the `admin` role as requiring 2FA via the admin policy screen/API.
2. Log in as a second admin account that has no 2FA enabled — confirm they land on a mandatory enrollment interstitial and cannot navigate elsewhere until enrollment completes.
3. Confirm a `viewer`/`editor` account without 2FA logs in normally, unaffected.
4. Unset the `admin` policy — confirm a non-enrolled admin can now log in normally without the interstitial.

**Expected**: matches spec User Story 4, acceptance scenarios 1–4.

## 6. Audit trail check

After running §2–§5, confirm the audit log contains entries for: enable, disable, challenge-success, challenge-failure, and recovery-code-used events (FR-017, SC-006).
