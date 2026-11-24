---
title: Set up a production environment
description: Keep production settings separate from development and replace the default database password.
---

# Set up a production environment

Use these steps on the server that runs PromptVault with Docker Compose. Docker Compose reads the `.env` file next to `docker-compose.yml`, the same file you use for development, so a development setting such as `ENVIRONMENT=development` or `DISABLE_RATE_LIMITING=true` can reach your production containers. These steps keep the production settings in their own file.

## Use a separate environment file {#use-a-separate-environment-file}

Run these commands from the PromptVault project folder. Make sure Git ignores the new file before it holds secrets:

```bash
echo '.env.production' >> .gitignore
cp .env .env.production

sed -i.bak \
  -e 's/^ENVIRONMENT=.*/ENVIRONMENT=production/' \
  -e 's/^LOG_LEVEL=.*/LOG_LEVEL=WARNING/' \
  -e 's/^DISABLE_RATE_LIMITING=.*/DISABLE_RATE_LIMITING=false/' \
  .env.production && rm .env.production.bak
grep -E '^(ENVIRONMENT|LOG_LEVEL|DISABLE_RATE_LIMITING)=' .env.production
```

The last command must show `ENVIRONMENT=production`, `LOG_LEVEL=WARNING` and `DISABLE_RATE_LIMITING=false`. If a variable is missing from the output, add it to `.env.production`.

Tell Docker Compose to use the new file. Do this once in each terminal window you use for production; every `docker-compose` command in that window then uses it:

```bash
export COMPOSE_ENV_FILES=.env.production
docker-compose up -d
```

`COMPOSE_ENV_FILES` needs Docker Compose 2.24 or later (check with `docker-compose version`). With an older version, add `--env-file .env.production` to every `docker-compose` command instead.

Docker Compose passes only these variables from the file to the containers:

- `ENVIRONMENT`, `LOG_LEVEL`, `DISABLE_RATE_LIMITING` and `POSTGRES_PASSWORD`
- `JWT_ACCESS_TOKEN_EXPIRE_SECONDS` and `JWT_REFRESH_TOKEN_EXPIRE_SECONDS`
- `DOCS_APP_URL` and `VITE_DOCS_PORTAL_URL`

The other values in `.env` (such as `DATABASE_URL`) only apply when you run PromptVault directly on a computer, not with Docker Compose. The [Configuration](../configuration/index.md) page describes each variable.

`ENVIRONMENT=production` can enforce stricter behavior than development. After you switch, read `docker-compose logs --tail 30 web` and fix anything it reports.

## Check the settings in use {#check-the-settings-in-use}

Show the settings the running container uses:

```bash
docker inspect promptvault-web --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E '^(ENVIRONMENT|LOG_LEVEL|DISABLE_RATE_LIMITING)='
```

The output must show `ENVIRONMENT=production`, `LOG_LEVEL=WARNING` and `DISABLE_RATE_LIMITING=false`. If it shows development values, the container was started without the production file: set `COMPOSE_ENV_FILES` as above and run `docker-compose up -d` again.

`docker-compose config` prints `POSTGRES_PASSWORD` in clear text, so do not paste its output anywhere.

## Replace the default database password {#replace-the-default-database-password}

If `POSTGRES_PASSWORD` is not set, Docker Compose silently uses `changeme`. Only containers on the same Docker network can reach the database, but replace the default anyway.

PostgreSQL reads `POSTGRES_PASSWORD` only when it first creates the data volume, so changing the variable alone does **not** change the password of an existing database. Change it in the database first, then in Compose:

```bash
# 1. Generate a password without special characters (it becomes part of a connection URL)
NEWPW=$(openssl rand -hex 24)

# 2. Change it in the database
docker exec promptvault-db psql -U promptvault -d promptvault -c "ALTER USER promptvault PASSWORD '$NEWPW'"

# 3. Store it for Compose and recreate the containers straight away
echo "POSTGRES_PASSWORD=$NEWPW" >> .env.production
docker-compose up -d
```

Do this at a quiet moment: between steps 2 and 3 the web container still holds the old password, so new connections fail for a few seconds. Take a fresh backup afterwards.

Check the result from the web container, not from inside the database container. The database image trusts connections made from inside its own container, so a test there accepts any password. Run both commands:

```bash
# The old password must be rejected
docker exec promptvault-web python -c "import psycopg; psycopg.connect(host='db', user='promptvault', password='changeme', dbname='promptvault', connect_timeout=5)" >/dev/null 2>&1 && echo "old password: ACCEPTED" || echo "old password: rejected"

# The current password must work
docker exec promptvault-web python -c "import os, psycopg; psycopg.connect(os.environ['DATABASE_URL'], connect_timeout=5)" >/dev/null 2>&1 && echo "current password: works" || echo "current password: FAILED"
```

Expected output: `old password: rejected`, then `current password: works`. If the password you replaced was not `changeme`, put it in the first command instead.

Store `.env.production` somewhere safe, such as a password manager: it holds the only copy of the password outside the database.
