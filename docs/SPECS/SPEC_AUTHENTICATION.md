---
id: spec-security-authentication
title: PromptVault Authentication & Authorization Specification
version: 1.0.1
date_created: 2025-11-29
last_updated: 2025-12-10
owner: medenor
tags: [security, authentication, authorization, jwt, rbac, app]
status: published
dependencies: [spec-app, spec-database]
---

## Introduction

This specification defines the authentication and authorization subsystem for the PromptVault application.  
It describes the **requirements**, **constraints**, **security properties**, **interfaces**, and **acceptance criteria** necessary to provide a secure, multi-user environment with robust identity, session, and permission management.

The objective is to enable predictable, testable, AI-ready development while ensuring strong security guarantees (confidentiality, integrity, traceability).

This document is **self-contained**, technology-agnostic, and normative.

---

## 1. Purpose & Scope

### 1.1 Purpose

The purpose of this specification is to define:

- user account lifecycle management
- secure password handling
- token-based authentication
- session lifecycle
- role-based access control (RBAC)
- authorization rules for all application entities
- operational security and configuration expectations

### 1.2 Scope

**In scope**

- Registration, login, logout
- Password hashing and password policy
- JWT-based access and refresh tokens
- Token rotation and revocation
- Session management
- Role-based access control (`viewer`, `editor`, `admin`)
- Ownership-based authorization on application data
- Password reset mechanism
- Admin-level user lifecycle actions (create, update, activate/deactivate, delete)
- Minimal API contracts relevant to authentication
- Minimal JSON schemas for tokens
- High-level database entities (not full model definitions)

**Out of scope**

- Implementation details of the backend or frontend
- Migrations, code structure, handlers, templates
- UI flows, test details, deployment instructions
- Third-party auth (OAuth2, SSO, 2FA, WebAuthn)

---

## 2. Definitions

- **User**: An authenticated identity with `id`, `username`, `email`, `role`, and `is_active`.
- **Role**: Authorization label determining global permissions. (`viewer`, `editor`, `admin`)
- **JWT Access Token**: Short-lived credential that proves authentication.
- **JWT Refresh Token**: Longer-lived credential allowing renewal of access tokens.
- **Token Family**: A group of refresh tokens derived through rotation; reused tokens invalidate the entire family.
- **Session**: Server-side record identifying a long-lived authenticated presence.
- **Password Hash**: One-way cryptographic hash of user password, stored instead of plaintext.
- **Password Reset Token**: Time-limited secret issued for resetting account credentials.
- **Ownership Rule**: Non-admin users may only modify data they created.
- **RBAC**: Role-based access control. Permissions depend on assigned user role.

---

## 3. Requirements, Constraints & Guidelines

### 3.1 Functional Requirements

- **REQ-AUTH-001**: The system must support user registration with `username`, `email`, and `password`.
- **REQ-AUTH-002**: The system must support user login and issue access & refresh tokens.
- **REQ-AUTH-003**: The system must validate access tokens on every protected endpoint.
- **REQ-AUTH-004**: The system must implement RBAC enforcing three roles: `viewer`, `editor`, `admin`.
- **REQ-AUTH-005**: The system must enforce ownership: non-admin users can only access or modify their resources.
- **REQ-AUTH-006**: The system must implement password reset using time-limited secure tokens.
- **REQ-AUTH-007**: The system must allow users to view and update part of their profile (`GET/PATCH /api/auth/me`).
- **REQ-AUTH-008**: The system must support user session listing and revocation.
- **REQ-AUTH-009**: The system must allow user account deletion and revoke all sessions.
- **REQ-AUTH-010**: Admins must be able to list, create, edit, activate/deactivate, and delete user accounts.
- **REQ-AUTH-011**: Admins must be able to transfer resource ownership when deleting users.

### 3.2 Security Requirements

- **SEC-AUTH-001**: Passwords must be stored as cryptographically secure one-way hashes.
- **SEC-AUTH-002**: Passwords must follow the policy:
  - minimum length: 12
  - at least one uppercase, one lowercase, one digit, one special character
- **SEC-AUTH-003**: JWTs must be cryptographically signed using asymmetric signing (e.g., ES256).
- **SEC-AUTH-004**: Access tokens must be short-lived.
- **SEC-AUTH-005**: Refresh tokens must support rotation; reuse detection must revoke all tokens from that token family.
- **SEC-AUTH-006**: Login must be rate-limited.
- **SEC-AUTH-007**: Repeated failed authentications must cause account lockout for a defined duration.
- **SEC-AUTH-008**: Maximum concurrent sessions per user must be limited.
- **SEC-AUTH-009**: Sensitive information (passwords, hashes, reset tokens) must never appear in logs or API responses.
- **SEC-AUTH-010**: The system must protect against user enumeration in authentication and reset flows.

### 3.3 Constraints

- **CON-AUTH-001**: The system must use the central relational database for all auth-related storage.
- **CON-AUTH-002**: Cryptographic keys must not be embedded in source code.
- **CON-AUTH-003**: Rate limiting storage must be durable and isolated per deployment.
- **CON-AUTH-004**: Authentication design must remain compatible with the PromptVault architecture (SPEC_APP).

### 3.4 Guidelines

- **GUD-AUTH-001**: Enforce validation at both API and service layers.
- **GUD-AUTH-002**: Use consistent response structures for auth errors.
- **GUD-AUTH-003**: Follow minimal privilege principles for authorization.

### 3.5 Patterns

- **PAT-AUTH-001**: Token family pattern for refresh token rotation.
- **PAT-AUTH-002**: Application of RBAC followed by ownership rules.

---

## 4. Interfaces & Data Contracts

### 4.1 Minimal JWT Token Schemas

#### Access Token (minimal representation)

```json
{
  "sub": "<user_id>",
  "role": "editor",
  "type": "access",
  "exp": 1701361800
}
```

#### Refresh Token (minimal representation)

```json
{
  "sub": "<user_id>",
  "type": "refresh",
  "family": "<family_id>",
  "exp": 1702569600
}
```

---

### 4.2 API Contracts (Minimal)

#### Authentication

| Endpoint             | Method | Description                   | Auth Required       |
| -------------------- | ------ | ----------------------------- | ------------------- |
| `/api/auth/register` | POST   | Create new user               | No                  |
| `/api/auth/login`    | POST   | Issue access + refresh tokens | No                  |
| `/api/auth/refresh`  | POST   | Rotate refresh token          | Yes (refresh token) |
| `/api/auth/logout`   | POST   | Revoke current session        | Yes                 |

#### User Profile

| Endpoint                    | Method | Description     | Auth |
| --------------------------- | ------ | --------------- | ---- |
| `/api/auth/me`              | GET    | Get profile     | Yes  |
| `/api/auth/me`              | PATCH  | Update profile  | Yes  |
| `/api/auth/me/stats`        | GET    | Get usage stats | Yes  |
| `/api/auth/change-password` | POST   | Change password | Yes  |
| `/api/auth/me`              | DELETE | Delete account  | Yes  |

#### Password Reset

| Endpoint                           | Method | Description                   | Auth |
| ---------------------------------- | ------ | ----------------------------- | ---- |
| `/api/auth/password-reset/request` | POST   | Request a reset token         | No   |
| `/api/auth/password-reset/confirm` | POST   | Use token to set new password | No   |

#### Admin User Management

| Endpoint                       | Method | Description                        | Role  |
| ------------------------------ | ------ | ---------------------------------- | ----- |
| `/api/admin/users`             | GET    | List users                         | admin |
| `/api/admin/users`             | POST   | Create user                        | admin |
| `/api/admin/users/{id}/role`   | PUT    | Modify role                        | admin |
| `/api/admin/users/{id}/status` | PUT    | Activate/deactivate                | admin |
| `/api/admin/users/{id}`        | DELETE | Delete user with optional transfer | admin |

---

### 4.3 RBAC Matrix (Minimal)

| Action                 | viewer | editor | admin |
| ---------------------- | ------ | ------ | ----- |
| Read own prompts       | ✓      | ✓      | ✓     |
| Create prompts         | ✗      | ✓      | ✓     |
| Edit own prompts       | ✗      | ✓      | ✓     |
| Delete own prompts     | ✗      | ✓      | ✓     |
| Access others' prompts | ✗      | ✗      | ✓     |
| User management        | ✗      | ✗      | ✓     |
| System-wide operations | ✗      | ✗      | ✓     |

---

## 5. Acceptance Criteria

- **AC-AUTH-001**: Users can register with valid credentials; invalid passwords are rejected.
- **AC-AUTH-002**: Login returns valid access & refresh tokens for correct credentials.
- **AC-AUTH-003**: Protected endpoints reject requests without valid access token.
- **AC-AUTH-004**: Token refresh returns a new access token and rotates the refresh token.
- **AC-AUTH-005**: Refresh token reuse revokes entire token family.
- **AC-AUTH-006**: Users can update their profile but cannot modify immutable fields (`id`, `role`, `email_verified`).
- **AC-AUTH-007**: Users can delete their account and all sessions are revoked.
- **AC-AUTH-008**: Non-admin users cannot access or modify resources they do not own.
- **AC-AUTH-009**: Admin users can manage user accounts as defined in §4.2.
- **AC-AUTH-010**: Password reset flow successfully generates, validates, and expires tokens.
- **AC-AUTH-011**: Authentication attempts beyond rate limits return appropriate errors.
- **AC-AUTH-012**: Locked accounts cannot authenticate until lockout expires.

---

## 6. Test Automation Strategy

Aligned with SPEC_APP.

### 6.1 Test Levels

- Unit tests for password hashing, validation, token generation, token parsing, lockout logic.
- Integration tests for registration, login, refresh, password reset, profile management, RBAC.
- Security tests for rate limiting, token reuse, enumeration protection.

### 6.2 Coverage Requirements

- Authentication subsystem: **≥ 90%**
- Token/crypto logic: **100%**

### 6.3 CI Integration

- Auth tests run on every PR.
- Coverage enforcement via CI pipeline.

---

## 7. Rationale & Context

- RBAC and ownership rules maintain a clear and minimal authorization model.
- JWTs enable scalable stateless access checks; sessions handle revocation and rotation.
- Strong hashing and password policy reduce credential compromise risks.
- Separation of roles maintains operational simplicity and security boundaries.

---

## 8. Dependencies & External Integrations

- SMTP service for password reset (abstracted).
- Cryptographic key store for signing tokens.
- Rate limiting storage backend (e.g., Redis).

---

## 9. Examples & Edge Cases

- Invalid login does not reveal whether username exists.
- Expired refresh token cannot be used to issue new tokens.
- Locked accounts return a consistent message without revealing lockout details.
- Admin user deletion may require ownership transfer of resources.

---

## 10. Validation Criteria

- Functional requirements in §3.1 are fully covered by automated tests.
- Security requirements in §3.2 validated by penetration testing and negative tests.
- RBAC enforcement is validated by test scenarios covering each role.
- Token expiration, rotation, and revocation must be reproducible across environments.

---

## 11. Versioning & Change Policy

- **VPOL-001**: This specification follows semantic versioning:
  - Major: incompatible changes to data contracts, invariants, or external behavior.
  - Minor: backward-compatible additions to functionality or interfaces.
  - Patch: backward-compatible bug fixes or clarifications.

- **VPOL-002**: A change is considered breaking if it:
  - Alters any existing field name, type, or semantics in the defined schemas.
  - Changes the behavior of existing operations in a way that violates any REQ, INV, or AC marked in this document.
  - Removes an existing operation or data field without providing a backward-compatible alternative.

- **VPOL-003**: When a breaking change is required:
  - The major version of this spec **MUST** be incremented.
  - Dependent specifications (e.g., application or API specs) **MUST** be updated to reference the new version and document the impact.

- **VPOL-004**: Backward-compatible changes (minor or patch) **SHOULD** be documented with clear notes, and any new optional fields or operations **MUST NOT** change behavior for clients that do not use them.

---

## 12. Related Specifications / Further Reading

- [SPEC_APP](SPEC_APP.md)
- [SPEC_DATABASE](SPEC_DATABASE.md)
- [SECURITY](../SECURITY.md)
- [AUTHENTICATION_DEPLOYMENT](../AUTHENTICATION_DEPLOYMENT.md)
- [AUTHENTICATION_API](../AUTHENTICATION_API.md)
- [AUTHENTICATION_SECURITY](../AUTHENTICATION_SECURITY.md)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
