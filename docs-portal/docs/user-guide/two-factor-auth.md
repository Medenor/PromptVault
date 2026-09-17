---
title: Two-Factor Authentication
sidebar_position: 5
---

# Two-Factor Authentication

## Current Status

Time-based one-time password (TOTP) two-factor authentication is **not yet available** in PromptVault. It's a planned hardening of the authentication system, tracked on the project roadmap, but no enrollment flow, login challenge step, or admin enforcement policy exists in the application today.

## What's Already in Place

While dedicated 2FA isn't available yet, PromptVault's authentication stack already includes several layers of protection on your account:

- **Strong password hashing** (Argon2id) with an enforced password policy (minimum length and character-class requirements).
- **Account lockout** after repeated failed login attempts, for a configurable duration.
- **Short-lived, rotating JWT access/refresh tokens** with reuse detection — a stolen refresh token can't be replayed indefinitely.
- **A cap on concurrent sessions per account**, with device/IP tracking and the ability to revoke any active session.
- **A no-enumeration password reset flow** — reset requests never reveal whether an email address has an account.

See the project's `docs/AUTHENTICATION_SECURITY.md` for full detail on these controls.

## Planned Design

The roadmap describes TOTP 2FA as an opt-in enrollment (QR code + secret, with single-use recovery codes) that inserts a challenge step into login once enabled for an account, plus an admin policy to require it for specific roles. Verification attempts would be rate-limited, and enrollment/disable/challenge events would be audit-logged, consistent with how other security-sensitive actions in PromptVault are already logged today.

## Recommendation in the Meantime

If your deployment needs stronger-than-password protection today, the practical options are: keep `AUTH_ENABLED=true` (never run a networked, multi-user instance with authentication disabled), enforce a strong password policy via the `PASSWORD_*` environment variables, and rely on the existing session cap and revocation controls to limit the blast radius of a compromised credential. This page will be updated once TOTP support ships.
