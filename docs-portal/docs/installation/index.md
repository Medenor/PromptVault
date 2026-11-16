---
title: Installation
sidebar_position: 1
---

# Installation

PromptVault is a self-hosted application: you run it on infrastructure you control. Choose the setup wizard if you want the application to create the required configuration interactively. Choose the manual path only if you are comfortable editing environment variables and running Docker commands.

## Prerequisites

- Python 3.14+
- PostgreSQL 15+ (recommended for production) or SQLite (fine for development/single-user use)
- Docker and Docker Compose (recommended deployment path)
- Git

## Quick Start with the Setup Wizard

The fastest way to get a working instance is the bundled setup wizard. It creates JSON Web Token (JWT) signing keys, configures the environment, sets up the database, and creates an administrator account.

```bash
git clone https://codeberg.org/medenor/promptvault.git
cd PromptVault
python scripts/setup/setup.py
```

Follow the prompts. When it finishes, open the address it displays and sign in with the administrator credentials you created.

## Manual Docker Compose Setup

Use this path only when you need to control each setting yourself. Complete the commands in order; later commands use the files and services created by earlier ones.

```bash
# Clone the repository
git clone https://codeberg.org/medenor/promptvault.git
cd PromptVault

# Configure environment
cp .env.example .env
# Edit .env and set POSTGRES_PASSWORD (and other values as needed)

# Generate JWT signing keys for authentication
openssl ecparam -name prime256v1 -genkey -noout -out es256-private.pem
openssl ec -in es256-private.pem -pubout -out es256-public.pem

# Point .env at the generated keys
echo "JWT_PRIVATE_KEY_PATH=$(pwd)/es256-private.pem" >> .env
echo "JWT_PUBLIC_KEY_PATH=$(pwd)/es256-public.pem" >> .env

# Start services (PostgreSQL + PromptVault)
docker-compose up -d

# Run database migrations
docker-compose exec web alembic upgrade head

# Create the default admin user
docker-compose exec web python scripts/create_admin_user.py

# (Optional) Migrate existing JSON data from a prior installation
docker-compose exec web python scripts/migrate_json_to_db.py
```

When the containers are running, open `http://localhost:8001` and sign in with the administrator credentials you created. If the page does not open, use [Troubleshooting](../troubleshooting/index.md) before changing any data or Docker volumes.

## Building from Source

If you're developing locally rather than deploying via Docker, the repository's `Makefile` wraps the full build/test/lint workflow:

```bash
make install   # backend (.venv) + frontend (npm) dependencies
make dev       # backend on :8003, frontend dev server on :5173
make build     # production frontend assets + Docker image
```

See the project's `docs/DEVELOPMENT.md` for the full target reference, environment variables, and common failure modes if a step doesn't behave as expected.

## Creating the Admin User

Every fresh installation needs at least one admin account:

```bash
# Docker Compose
docker-compose exec web python scripts/create_admin_user.py

# Local
python scripts/create_admin_user.py
```

The script asks for a username, email address, and password. It checks the password against the configured policy, then creates a user with full administrator permissions. Store these credentials securely.

- To update an existing installation, follow [Update PromptVault](update.md).
## Next Steps

- Review the [Configuration Reference](../configuration/index.md) for environment variables you'll likely want to tune (rate limits, session timeouts, backup storage).
- If something doesn't come up as expected, check [Troubleshooting](../troubleshooting/index.md).
