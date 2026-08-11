# Git Workflow

- **Always work on a branch.** Never commit non-trivial changes directly to `main`. Create a feature/fix branch, push it, open a PR on Codeberg (see `.forgejo/PULL_REQUEST_TEMPLATE.md`) — even for solo work, so changes go through review and CI.
- **Docs-only exception**: small, low-risk documentation-only updates (e.g. marking a roadmap item done, changelog entries for already-merged work) may go directly to `main` **only if the user explicitly says so for that specific change**; otherwise default to branch + PR.
- **Read-only tasks stay read-only**: if a task is scoped as investigation/diagnosis only ("root-cause this failure," "find out why," anything marked read-only or "do not fix/modify"), do not commit, push, branch, or open a PR — report findings and let the requester decide on any fix. Being told to "investigate" or "look into" something is not authorization to also fix and publish it. This applies to subagents/forks too — a delegated read-only task must not escalate into a write action on its own.

# Docker Safety — `docker-compose.yml` is production

The `docker-compose.yml` at the repo root runs the user's **live production instance** (`promptvault-web`/`promptvault-db`/`promptvault-redis`, port 8001) — it is not a disposable dev sandbox, even though it lives in the repo like any other project's compose file.

> **Incident**: `docker-compose up --build` was used for a smoke check, and the subsequent `docker-compose down` stopped and removed the running production containers. Data survived only because named volumes aren't deleted by `down` without `-v` — the user had to restart the stack manually.

- **Never run `docker-compose down`, `stop`, `rm`, `restart`, or any command that stops/removes containers/networks/volumes against the root `docker-compose.yml`** without first confirming with the user — assume it's live until told otherwise.
- **Never run `docker-compose up`/`--build` against the root compose file for testing or verification** (a smoke check, validating a migration, checking a container boots). Instead:
  - Copy `docker-compose.yml` to a scratch file (session scratchpad) with renamed container names, a different host port, a distinct `-p <project-name>`, and either no volumes or fresh/fake-data volumes — so it can't collide with the running production containers, network, or named volumes.
  - Or use a temporary, unnamed container (`docker run --rm ...`) from the same Dockerfile when a full multi-service stack isn't needed.
  - Migration round-trips: use an isolated SQLite file or a throwaway Postgres container — never `data-dev/promptvault.db`, `data/promptvault.db`, or the production Postgres volume.
- If unsure whether a Docker action is safe, treat it as production and ask first.
