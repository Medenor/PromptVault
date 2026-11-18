---
title: Troubleshooting
sidebar_position: 4
---

# Troubleshooting

Use this page to identify the symptom, make the smallest safe change, and try again. Do not delete a database or Docker volume while troubleshooting an existing installation. For exhaustive coverage, see the project's `docs/TROUBLESHOOTING.md`.

## Port Already in Use {#port-already-in-use}

If port `8001` (web), `5432` (PostgreSQL), or `6379` (Redis) is already bound by another process, `docker-compose up` will fail to start that service. Stop the conflicting process, or change the mapped port in your `.env`/`docker-compose.yml` before retrying.

## Docker Daemon Not Running {#docker-daemon-not-running}

`docker-compose` commands fail with a connection error if Docker itself isn't running. Start Docker Desktop (or the `docker` service on Linux) and retry.

## Database Connection Failed {#database-connection-failed}

If PromptVault can't reach PostgreSQL on startup:

- Confirm that the container or service is running with `docker-compose ps`.
- Double-check `DATABASE_URL` in `.env` matches the credentials and host/port PostgreSQL is actually listening on.
- If you changed `POSTGRES_PASSWORD`, an existing initialized data volume does not change its password automatically. For an existing installation, update the password in the database using your established database procedure. Recreate a volume only for a new installation with no data to keep.

## Migration Failures {#migration-failures}

If `alembic upgrade head` fails partway through:

- Re-run it — most migrations are written to be idempotent.
- If a migration on a new SQLite database reports a PostgreSQL-specific SQL error, check that you are running a current release before trying another workaround.
- Never edit the database schema by hand to work around a migration failure — open an issue with the exact error instead, since manual schema edits make future migrations unpredictable.

## JWT Key Errors {#jwt-key-errors}

If the app fails to start complaining about missing or invalid JWT keys, confirm `JWT_PRIVATE_KEY_PATH`/`JWT_PUBLIC_KEY_PATH` point to a valid ES256 keypair generated with:

```bash
openssl ecparam -name prime256v1 -genkey -noout -out es256-private.pem
openssl ec -in es256-private.pem -pubout -out es256-public.pem
```

Keys generated with a different curve or algorithm will not work — PromptVault specifically expects ES256 (P-256/prime256v1).

## Locked Out After Failed Logins {#locked-out-after-failed-logins}

Repeated failed login attempts temporarily lock your account. By default, this happens after five attempts (`MAX_LOGIN_ATTEMPTS`) and lasts 15 minutes (`ACCOUNT_LOCKOUT_DURATION_SECONDS`). Wait for the lockout to end. If you are the only administrator, wait rather than trying further passwords: retries do not shorten the timer.

## Rate Limit Errors (429) {#rate-limit-errors-429}

If bulk operations, imports, exports, or backup actions return `429 Too Many Requests`, you have reached a per-user rate limit. The response gives a `Retry-After` value. Wait for that period, then try once more. If the limit prevents a legitimate recurring workflow, an administrator can adjust the matching `RATE_LIMIT_*` setting described in [Configuration](../configuration/index.md#rate-limiting).

## Import/Export Doesn't Restore Sharing {#importexport-doesnt-restore-sharing}

If you import a previously exported file and shared prompts come back private with no grants, this is expected — export/import intentionally does not carry sharing state (see [Sharing Prompts](../user-guide/sharing.md#exportimport-and-sharing)). Use a full backup/restore instead if you need sharing preserved.

For planned upgrades, follow [Update PromptVault](../installation/update.md).

## Still Stuck? {#still-stuck}

Check the full `docs/TROUBLESHOOTING.md` in the repository, or open an issue on [GitHub](https://github.com/Medenor/PromptVault) with the exact error message and the command you ran.
