---
title: Troubleshooting
sidebar_position: 4
---

# Troubleshooting

This page covers the issues most people hit when installing or running PromptVault. For exhaustive coverage, see the project's `docs/TROUBLESHOOTING.md`.

## Port Already in Use

If port `8001` (web), `5432` (PostgreSQL), or `6379` (Redis) is already bound by another process, `docker-compose up` will fail to start that service. Stop the conflicting process, or change the mapped port in your `.env`/`docker-compose.yml` before retrying.

## Docker Daemon Not Running

`docker-compose` commands fail with a connection error if Docker itself isn't running. Start Docker Desktop (or the `docker` service on Linux) and retry.

## Database Connection Failed

If PromptVault can't reach PostgreSQL on startup:

- Confirm the container/service is actually running (`docker-compose ps`).
- Double-check `DATABASE_URL` in `.env` matches the credentials and host/port PostgreSQL is actually listening on.
- If you just changed `POSTGRES_PASSWORD`, remember existing containers with an already-initialized data volume won't pick up the new password automatically — you may need to recreate the volume for a fresh install, or update the password inside the existing database instead.

## Migration Failures

If `alembic upgrade head` fails partway through:

- Re-run it — most migrations are written to be idempotent.
- If a migration fails specifically on a fresh SQLite database with a PostgreSQL-specific SQL error, you're likely on an outdated version — recent releases fixed migrations that used non-portable dialect-specific SQL, so make sure you're not running an older commit.
- Never edit the database schema by hand to work around a migration failure — open an issue with the exact error instead, since manual schema edits make future migrations unpredictable.

## JWT Key Errors

If the app fails to start complaining about missing or invalid JWT keys, confirm `JWT_PRIVATE_KEY_PATH`/`JWT_PUBLIC_KEY_PATH` point to a valid ES256 keypair generated with:

```bash
openssl ecparam -name prime256v1 -genkey -noout -out es256-private.pem
openssl ec -in es256-private.pem -pubout -out es256-public.pem
```

Keys generated with a different curve or algorithm will not work — PromptVault specifically expects ES256 (P-256/prime256v1).

## Locked Out After Failed Logins

Repeated failed login attempts trigger a temporary account lockout (`MAX_LOGIN_ATTEMPTS`, default 5 attempts, `ACCOUNT_LOCKOUT_DURATION_SECONDS`, default 15 minutes). Wait out the lockout window, or have an admin reset it, rather than repeatedly retrying — retrying during a lockout does not reset the timer early.

## Rate Limit Errors (429)

If bulk operations, imports/exports, or backup actions return `429 Too Many Requests`, you've hit one of the per-user rate-limit buckets described in [Configuration](../configuration/index.md#rate-limiting). The response includes a `Retry-After` header; wait for that window, or ask an admin to raise the relevant `RATE_LIMIT_*` variable if the default is genuinely too low for your workflow.

## Import/Export Doesn't Restore Sharing

If you import a previously exported file and shared prompts come back private with no grants, this is expected — export/import intentionally does not carry sharing state (see [Sharing Prompts](../user-guide/sharing.md#exportimport-and-sharing)). Use a full backup/restore instead if you need sharing preserved.

## Still Stuck?

Check the full `docs/TROUBLESHOOTING.md` in the repository, or open an issue on [Codeberg](https://codeberg.org/medenor/promptvault) with the exact error message and the command you ran.
