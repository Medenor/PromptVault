---
title: Configuration
sidebar_position: 2
---

# Configuration Reference

PromptVault is configured entirely through environment variables, typically set in a `.env` file at the repository root (copy `.env.example` as a starting point). This page covers the settings you're most likely to need.

## Database

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data-dev/promptvault.db` | Connection string. Use a `postgresql://` URL in production. |
| `DB_POOL_SIZE` | `20` | Connection pool size (ignored for SQLite). |
| `DB_POOL_TIMEOUT` | `30` | Pool checkout timeout, in seconds. |
| `DB_POOL_RECYCLE` | `3600` | Seconds before a pooled connection is recycled. |
| `DB_ECHO` | `false` | Log every SQL statement — useful for debugging, noisy in production. |

## Application

| Variable | Default | Purpose |
|---|---|---|
| `ENVIRONMENT` | `development` | One of `development`, `testing`, `production`. |
| `PROMPTVAULT_DATA_DIR` | `./data-dev` | Directory for data files, backups, and logs. **Use a distinct path per environment** (dev/staging/prod) even if they share a filesystem — sharing a data directory across environments can cause scheduled backups and restores to collide. |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. |
| `AUDIT_LOG_LEVEL` | `INFO` | Log level specifically for version-control and backup audit events. |

## Authentication

| Variable | Default | Purpose |
|---|---|---|
| `AUTH_ENABLED` | `true` | Set to `false` only for a trusted, single-user, non-networked deployment — this disables login and makes every endpoint publicly accessible. |
| `JWT_PRIVATE_KEY_PATH` / `JWT_PUBLIC_KEY_PATH` | — | Paths to the ES256 keypair used to sign/verify JWTs. Generate with `openssl ecparam`/`openssl ec` as shown in [Installation](../installation/index.md). |
| `JWT_ACCESS_TOKEN_EXPIRE_SECONDS` | `900` (15 min) | Access token lifetime. |
| `JWT_REFRESH_TOKEN_EXPIRE_SECONDS` | `604800` (7 days) | Refresh token lifetime. |
| `MAX_LOGIN_ATTEMPTS` | `5` | Failed attempts before account lockout. |
| `ACCOUNT_LOCKOUT_DURATION_SECONDS` | `900` | Lockout duration. |
| `MAX_SESSIONS_PER_USER` | `5` | Concurrent session cap (`0` = unlimited). |
| `SESSION_INACTIVE_TIMEOUT_SECONDS` | `2592000` (30 days) | Idle session expiry. |

Password policy (`PASSWORD_MIN_LENGTH`, `PASSWORD_REQUIRE_UPPERCASE`, `PASSWORD_REQUIRE_LOWERCASE`, `PASSWORD_REQUIRE_DIGIT`, `PASSWORD_REQUIRE_SPECIAL`) is also configurable — defaults enforce a 12-character minimum with all four character classes.

## Rate Limiting

Rate limits are per-user (falling back to per-IP for anonymous requests) and grouped into buckets, each independently tunable:

| Bucket | Default | Env prefix |
|---|---|---|
| Read (GET requests) | 300/min | `RATE_LIMIT_READ_*` |
| Write (create/update/delete/revert) | 60/min | `RATE_LIMIT_WRITE_*` |
| Expensive (import/export, backup create/restore/verify) | 10/min | `RATE_LIMIT_EXPENSIVE_*` |
| Bulk (bulk delete, delete-all-backups, compress) | 5/min | `RATE_LIMIT_BULK_*` |

Each bucket has `_ATTEMPTS` and `_WINDOW_SECONDS` variables, e.g. `RATE_LIMIT_WRITE_ATTEMPTS=60` / `RATE_LIMIT_WRITE_WINDOW_SECONDS=60`. Auth-specific endpoints (login, register, password reset) have their own separate limits (`RATE_LIMIT_LOGIN_*`, `RATE_LIMIT_REGISTER_*`, `RATE_LIMIT_PASSWORD_RESET_*`). Rate limiting requires `REDIS_URL` to be reachable.

## Email (Password Reset)

| Variable | Purpose |
|---|---|
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS` | SMTP server connection. |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | SMTP credentials. |
| `EMAIL_FROM_ADDRESS`, `EMAIL_FROM_NAME` | Sender identity on outgoing emails. |
| `PASSWORD_RESET_TOKEN_EXPIRE_SECONDS` | `3600` by default — how long a reset link stays valid. |
| `APP_BASE_URL` | Base URL used to build the reset link sent by email. |

## Backups

| Variable | Purpose |
|---|---|
| `PROMPTVAULT_CLOUD_CREDS_PASSPHRASE` | Required only if you configure cloud backup storage — encrypts stored provider credentials (access/secret keys) at rest. Generate with `python -c "import secrets; print(secrets.token_hex(32))"` and never commit it. |

See [Backups](../user-guide/backups.md) for how schedules, encryption, and cloud storage fit together.

## Frontend Assets

| Variable | Default | Purpose |
|---|---|---|
| `USE_VITE_ASSETS` | `false` | Set to `true` to serve CSS/JS from the compiled Vite build output rather than source. |

## Example: PostgreSQL Production

```bash
DATABASE_URL=postgresql://promptvault_user:secure_password@localhost:5432/promptvault_prod
DB_POOL_SIZE=30
DB_POOL_TIMEOUT=60
ENVIRONMENT=production
LOG_LEVEL=WARNING
```
