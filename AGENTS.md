# AGENTS.md

Guidance for any coding agent working in this repository. Hosted on [Codeberg](https://codeberg.org/medenor/promptvault.git) (not GitHub).

## Overview

PromptVault is a FastAPI web app for organizing, versioning, and managing AI prompts — Git-like version control, backups, sharing, and multi-language support, built with a service-oriented architecture (business logic in `src/services/`, data access in `src/db/repositories/`, web layer in `src/web/`).

## Commands

Use the `Makefile` at the repo root as the canonical command surface (details: [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)):

```bash
make dev          # backend (:8003) + frontend (:5173) dev servers
make test         # backend + frontend test suites with coverage gates
make lint         # formatting, lint, and typecheck across both stacks
make lint-fix     # auto-fix formatting and lint issues
make build        # production frontend build + Docker image
```

- **Never manually start uvicorn** or run `docker-compose up` for local dev — always go through `make dev`.
- Python 3.14+ required. `python3 -m pytest` (not bare `pytest`) if you need to run a single suite directly — see [testing.md](docs/agents/testing.md).
- `docker-compose.yml` at the repo root is the user's **live production instance**, not a dev sandbox — read [git-and-docker-safety.md](docs/agents/git-and-docker-safety.md) before running any `docker-compose` command against it.

## Before non-trivial work

Read [git-and-docker-safety.md](docs/agents/git-and-docker-safety.md) — branch/PR requirements and a real production-incident case around the root `docker-compose.yml`.

## Reference

| Topic | File |
| --- | --- |
| System architecture, data model, API endpoints | [architecture.md](docs/agents/architecture.md), [api.md](docs/agents/api.md) |
| Python conventions, logging, Alembic migrations | [python-style.md](docs/agents/python-style.md) |
| TypeScript, components, Tailwind, i18n | [frontend.md](docs/agents/frontend.md) |
| Testing conventions and how to run suites | [testing.md](docs/agents/testing.md) |
| Git workflow & Docker safety (production compose file) | [git-and-docker-safety.md](docs/agents/git-and-docker-safety.md) |
| Step-by-step workflow and common pitfalls | [workflow-and-pitfalls.md](docs/agents/workflow-and-pitfalls.md) |

Also see: [`docs/TESTING.md`](docs/TESTING.md), [`docs/VERSION_CONTROL.md`](docs/VERSION_CONTROL.md), [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md) (Makefile reference), [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md), [`docs/SPECS/`](docs/SPECS/).

## License

MPL 2.0 — always add the MPL 2.0 header to new files.
