# Feature Specification: Two-Factor Authentication (TOTP)

**Feature Branch**: `009-totp-2fa`

**Created**: 2026-08-13

**Status**: Draft

**Input**: User description: "Optional TOTP 2FA with QR enrollment, single-use recovery codes, and an admin policy to require 2FA per role. Improvement Plan 2026-08 item #7; carried from ROADMAP 2026 #5."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enroll in TOTP 2FA (Priority: P1)

A security-conscious user wants to add a second factor to their account. From their profile page they start enrollment, scan a displayed QR code with an authenticator app (Google Authenticator, Authy, 1Password, etc.), and confirm enrollment by entering a current code from the app. Once confirmed, 2FA is active on their account and they are shown a set of one-time recovery codes to store safely.

**Why this priority**: Without enrollment, no other story has anything to operate on. This is the foundational capability the whole feature exists to deliver.

**Independent Test**: Can be fully tested by enrolling a single test account, verifying the QR/secret encodes a valid TOTP provisioning URI, confirming with a correct code activates 2FA, and confirming recovery codes are issued exactly once at enrollment.

**Acceptance Scenarios**:

1. **Given** a logged-in user without 2FA enabled, **When** they start enrollment, **Then** they are shown a QR code (and a manual-entry secret as a fallback) that a standard authenticator app can register.
2. **Given** a user has started enrollment but not yet confirmed it, **When** they enter a valid current code from their authenticator app, **Then** 2FA becomes active on their account and they are shown a set of single-use recovery codes exactly once.
3. **Given** a user has started enrollment, **When** they enter an incorrect or malformed code, **Then** enrollment is not confirmed, 2FA remains inactive, and they may retry.
4. **Given** a user completes enrollment, **When** they view their profile afterward, **Then** the recovery codes are never displayed again in full (only remaining-count / regeneration is offered).
5. **Given** a user already has 2FA enabled, **When** they attempt to start enrollment again, **Then** the system refuses and directs them to disable 2FA first.

---

### User Story 2 - Authenticate with 2FA at login (Priority: P1)

A user with 2FA enabled logs in with their password as usual, then is prompted for a code from their authenticator app (or a recovery code) before receiving full access. Only after the second factor succeeds does the user get a working session.

**Why this priority**: Enrollment (Story 1) is worthless if login doesn't actually enforce the second factor. This closes the loop and is the actual security boundary the feature delivers — co-equal in priority with enrollment.

**Independent Test**: With a 2FA-enabled test account (from Story 1 or fixtures), attempt login and verify no full session is issued until a correct second factor is supplied; verify wrong/expired/replayed codes are rejected.

**Acceptance Scenarios**:

1. **Given** a user with 2FA enabled submits a correct password, **When** the password is validated, **Then** the system issues a short-lived challenge (not a full session) and prompts for a second factor instead of granting access.
2. **Given** a user has a valid challenge, **When** they submit a correct current TOTP code, **Then** they receive full access (access + refresh tokens) as normal.
3. **Given** a user has a valid challenge, **When** they submit an incorrect code, **Then** access is refused, the attempt counts toward the existing account lockout threshold, and the challenge remains open for retry (until expiry or lockout).
4. **Given** a user has a valid challenge, **When** they let it sit unused past its expiry window, **Then** the challenge becomes invalid and they must restart login from the password step.
5. **Given** a user successfully authenticates with a TOTP code, **When** an attacker replays that exact same code immediately afterward, **Then** the replay is refused.
6. **Given** a user has lost access to their authenticator app, **When** they submit a valid unused recovery code at the challenge step instead of a TOTP code, **Then** they receive full access and that recovery code is permanently consumed (cannot be used again).
7. **Given** a user without 2FA enabled submits a correct password, **When** the password is validated, **Then** they receive full access immediately as they do today, with no second-factor step.

---

### User Story 3 - Disable 2FA and manage recovery codes (Priority: P2)

A user who no longer wants 2FA (or who needs fresh recovery codes because they've used most of theirs) can turn it off or regenerate codes from their profile, but only by re-proving both factors — current password and a valid TOTP/recovery code — so an attacker with a hijacked session alone cannot strip the protection.

**Why this priority**: Important for account lifecycle and recovery-code hygiene, but the feature is usable and secure without it in a first cut — enrollment and login enforcement deliver the core value on their own.

**Independent Test**: With a 2FA-enabled test account, attempt to disable or regenerate codes with and without correct password+code, and verify recovery codes issued before regeneration stop working afterward.

**Acceptance Scenarios**:

1. **Given** a user with 2FA enabled, **When** they request to disable it and supply their current password plus a valid TOTP or recovery code, **Then** 2FA is turned off, the stored secret and remaining recovery codes are invalidated, and future logins no longer prompt for a second factor.
2. **Given** a user with 2FA enabled, **When** they request to disable it but supply an incorrect password or code, **Then** the request is refused and 2FA remains active.
3. **Given** a user with 2FA enabled, **When** they request new recovery codes and authenticate the request, **Then** a fresh set of single-use codes is issued and all previously issued recovery codes stop working immediately.

---

### User Story 4 - Admin-enforced 2FA policy (Priority: P3)

An administrator wants certain roles (e.g., admins themselves) to be required to use 2FA, for compliance or organizational security reasons. The admin configures which roles require 2FA; users in those roles who haven't enrolled are guided through mandatory enrollment immediately after their next login, before they can use the rest of the application.

**Why this priority**: Valuable for team deployments and compliance-minded admins, but it's a policy layer on top of the self-serve capability delivered by Stories 1–3, and can ship after the core opt-in feature is solid.

**Independent Test**: With the core feature already working, configure a role as requiring 2FA, log in as a non-enrolled user in that role, and verify they're blocked from other functionality until they complete enrollment; verify users outside that role are unaffected.

**Acceptance Scenarios**:

1. **Given** an admin sets a role as requiring 2FA, **When** a user in that role without 2FA logs in, **Then** they are placed into a mandatory enrollment flow and cannot reach other parts of the application until 2FA is active.
2. **Given** a role is marked as requiring 2FA, **When** a user in that role already has 2FA enabled, **Then** login proceeds through the normal challenge flow (Story 2) with no extra interstitial.
3. **Given** a role is not marked as requiring 2FA, **When** a user in that role logs in, **Then** they are never forced into enrollment, though they may still opt in voluntarily.
4. **Given** an admin removes a role from the required-2FA policy, **When** users in that role next log in, **Then** they are no longer forced into enrollment (existing enrollments, if any, are unaffected and remain active until the user disables them).

---

### Edge Cases

- What happens if a user's device clock has drifted slightly? The verification window tolerates one time-step of drift in either direction; beyond that, the code is rejected.
- What happens if a user loses both their authenticator app and all recovery codes? They cannot self-service recovery; this requires an administrator to disable 2FA on their behalf (existing admin user-management capability), which is logged as a security-relevant action.
- What happens if a user tries to reuse a challenge token after it already succeeded once? The challenge is single-use; reuse is refused.
- What happens if a user hammers the second-factor step with repeated wrong codes? The existing account lockout mechanism (shared counter with password attempts) engages, temporarily blocking further attempts.
- What happens if an admin enables a required-2FA policy for a role that already has active sessions? Enforcement is evaluated at next login, not by revoking existing sessions.
- What happens if a user's account is deleted or deactivated while 2FA is enabled? 2FA state is scoped to the user record and follows existing account deletion/deactivation behavior — no separate handling needed.
- What happens if a user attempts to enroll while a prior unconfirmed enrollment attempt exists? Starting enrollment again replaces the pending (unconfirmed) secret; nothing is active until confirmed.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow an authenticated user without 2FA enabled to start TOTP enrollment, generating a secret and displaying it as both a scannable QR code and a manual-entry string.
- **FR-002**: System MUST NOT activate 2FA on enrollment start alone — activation only occurs after the user confirms with a valid current code.
- **FR-003**: Upon successful enrollment confirmation, system MUST generate and display a set of single-use recovery codes exactly once; the plaintext codes MUST NOT be retrievable again afterward.
- **FR-004**: System MUST store the TOTP secret encrypted at rest and store recovery codes only as irreversible hashes, never in plaintext.
- **FR-005**: At login, when a user with 2FA enabled supplies a correct password, system MUST issue a short-lived, single-use challenge instead of full access tokens, and MUST require a valid second factor before issuing access/refresh tokens.
- **FR-006**: System MUST accept a valid current TOTP code within a small clock-drift tolerance (one time-step in either direction) as satisfying the challenge, and MUST reject codes outside that tolerance.
- **FR-007**: System MUST prevent replay of a previously accepted TOTP code (a given code/time-step, once used successfully, cannot be used again for that user).
- **FR-008**: System MUST allow a valid unused recovery code to satisfy the login challenge as an alternative to a TOTP code, and MUST permanently invalidate that recovery code upon use.
- **FR-009**: System MUST expire an unused login challenge after a short fixed window, after which the user must restart login from the password step.
- **FR-010**: System MUST count failed second-factor attempts toward the same account lockout mechanism used for failed password attempts.
- **FR-011**: System MUST allow a user with 2FA enabled to disable it only after re-authenticating with both their current password and a valid TOTP or recovery code in the same request.
- **FR-012**: Disabling 2FA MUST invalidate the stored secret and all remaining recovery codes for that user.
- **FR-013**: System MUST allow a user with 2FA enabled to regenerate their recovery codes after re-authenticating with password and a valid code, and regeneration MUST invalidate all previously issued recovery codes.
- **FR-014**: System MUST allow an administrator to configure which user roles require 2FA to be enabled.
- **FR-015**: When a user in a role marked as requiring 2FA logs in without 2FA enabled, system MUST route them into a mandatory enrollment flow and MUST block access to other application functionality until enrollment is confirmed.
- **FR-016**: System MUST NOT force enrollment on users outside a role currently marked as requiring 2FA, though such users MAY opt in voluntarily.
- **FR-017**: System MUST record an audit event for each of: 2FA enabled, 2FA disabled, successful login challenge, failed login challenge, and recovery code used.
- **FR-018**: System MUST enforce the same login rate-limiting expectations on 2FA-related endpoints (enrollment, verification, disable, recovery-code regeneration) as on other sensitive auth endpoints, to prevent brute-force guessing of codes.
- **FR-019**: The 2FA setup and challenge screens MUST be usable by keyboard and screen reader, consistent with the rest of the authentication UI.

### Key Entities

- **TOTP Credential**: Represents a user's second-factor enrollment — the encrypted secret, whether it is confirmed/active, and bookkeeping needed to prevent code replay. Belongs to exactly one user.
- **Recovery Code Set**: A batch of single-use codes issued at enrollment or regeneration, stored as hashes with per-code used/unused state. Belongs to exactly one user; a regeneration event supersedes the previous set entirely.
- **Login Challenge**: A short-lived, single-use token representing "password verified, second factor pending" for one login attempt. Expires quickly and is consumed on success or discarded on expiry/failure exhaustion.
- **2FA Role Policy**: Admin-configured association between a role and whether 2FA is mandatory for members of that role.
- **Audit Event (2FA-related)**: A record of a security-relevant 2FA action (enable, disable, challenge success/failure, recovery code used), consistent with existing audit logging for other auth events.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can complete 2FA enrollment (scan QR, confirm code, receive recovery codes) in under 2 minutes.
- **SC-002**: 100% of login attempts for 2FA-enabled accounts require a valid second factor before any access is granted — zero bypass paths.
- **SC-003**: A previously accepted TOTP code can never be successfully reused; replay attempts have a 0% success rate.
- **SC-004**: Recovery codes are single-use with 0% success rate on reuse, verified across enrollment, regeneration, and disable flows.
- **SC-005**: For roles under a required-2FA policy, 100% of non-enrolled users are routed to mandatory enrollment on next login and cannot reach other functionality first.
- **SC-006**: Every enable, disable, challenge success, challenge failure, and recovery-code-use event is discoverable in the audit trail after the fact.

## Assumptions

- The existing authentication stack (password hashing, ES256-signed tokens, token rotation, account lockout, session cap) is reused and extended, not replaced.
- "Second factor" in v1 means TOTP only (RFC 6238-style app-based codes); WebAuthn/hardware keys and SMS-based codes are out of scope.
- Recovery codes are generated in a fixed-size batch (a standard count, e.g. 8–10 codes) at enrollment and regeneration; the exact count is an implementation detail, not a user-facing configuration.
- The mandatory-enrollment interstitial for policy-required roles blocks navigation but does not revoke or otherwise affect any other in-progress session state.
- Auth UI remains English-only for this feature, consistent with current auth screens; other application surfaces keep their existing i18n behavior.
- Admins can disable 2FA on behalf of a locked-out user via existing user-management capabilities; this spec does not introduce a new self-service account-recovery channel beyond recovery codes.
