---
name: steward
description: Use when an agent owns or is asked to drive a pull request in this repository and a CI, review, merge-conflict, base-movement, check-in, merge, or close event arrives.
---

<!-- SPDX-License-Identifier: MPL-2.0 -->

# Steward

Use this skill after you open a pull request in this repository, or when its
author asks you to drive it, and an event about that pull request arrives. It
maps events to the next action; it does not grant repository access, expand the
requested scope, authorize a merge, or override `AGENTS.md` or the owning
documentation below.

A pull request you were only asked to watch remains read-only. Investigations
and other read-only tasks never become permission to create a branch, commit,
push, or open a pull request.

## Owning documentation

This skill is a map, not a second source of truth. When it conflicts with an
owning document, the owning document wins.

- [`AGENTS.md`](../../../AGENTS.md) defines the canonical commands and points
  to the repository's topic-specific guidance.
- [`docs/agents/git-and-docker-safety.md`](../../../docs/agents/git-and-docker-safety.md)
  owns the branch and pull-request workflow, read-only boundaries, and
  production Docker safety rules.
- [`docs/agents/workflow-and-pitfalls.md`](../../../docs/agents/workflow-and-pitfalls.md)
  owns the implementation, validation, changelog, static-cache, and
  sharing/validation workflow.
- [`docs/agents/testing.md`](../../../docs/agents/testing.md) owns test commands
  and test conventions.
- [`docs/agents/python-style.md`](../../../docs/agents/python-style.md) owns
  database migration requirements.
- [`docs/agents/frontend.md`](../../../docs/agents/frontend.md) owns frontend
  typechecking, linting, package management, and service-worker cache rules.
- [`.github/PULL_REQUEST_TEMPLATE.md`](../../../.github/PULL_REQUEST_TEMPLATE.md)
  owns the pull-request description format.

## Event to action

Before acting, read the pull request's current head, mergeability, checks,
reviews, unresolved threads, and latest human comments using the available
`mcp__github__*` tools. Make one decision from one current snapshot; do not
poll continuously.

| Event | Action | Owning document |
| --- | --- | --- |
| A required CI check is red | Root-cause the failure. If this pull request caused it, make the smallest in-scope fix and run the relevant local checks before pushing. If it is unrelated or also failing on the base branch, report the evidence and wait; do not import another contributor's change. Never skip, disable, or quarantine a test to get green. | [`workflow-and-pitfalls.md`](../../../docs/agents/workflow-and-pitfalls.md), [`testing.md`](../../../docs/agents/testing.md) |
| A merge conflict is reported | Integrate the current base into the feature branch, resolve only the conflicts needed for this pull request, validate, and push. Never amend, rebase, or force-push published history. | [`git-and-docker-safety.md`](../../../docs/agents/git-and-docker-safety.md) |
| The base branch moved without a conflict | Re-read the pull request state and determine whether the landed changes interact with this pull request. If they do, integrate the base, validate, and push; if they do not, leave the head unchanged. Any new head invalidates prior check and review results. | [`git-and-docker-safety.md`](../../../docs/agents/git-and-docker-safety.md), [`workflow-and-pitfalls.md`](../../../docs/agents/workflow-and-pitfalls.md) |
| A review-bot finding arrives | Verify it against the current code. Fix valid, in-scope findings and reply with the evidence; explain why an invalid finding does not apply. Do not push solely to silence an optional stylistic finding. | [`workflow-and-pitfalls.md`](../../../docs/agents/workflow-and-pitfalls.md) |
| A human review comment arrives | For a small, clear, in-scope request, implement it, validate it, push, and reply. For a large, ambiguous, or scope-expanding request, respond with a proposal and wait for the author or user to decide. | [`git-and-docker-safety.md`](../../../docs/agents/git-and-docker-safety.md), [`workflow-and-pitfalls.md`](../../../docs/agents/workflow-and-pitfalls.md) |
| Checks turn green on the current head | Confirm mergeability and that no review thread remains unresolved. Report the current state and wait for human direction. Green CI is not merge authorization. | [`testing.md`](../../../docs/agents/testing.md), [`git-and-docker-safety.md`](../../../docs/agents/git-and-docker-safety.md) |
| Explicit merge authorization is given | Confirm that the authorization names this pull request. Re-read the exact head, base, mergeability, required checks, and unresolved reviews immediately before merging. Merge only if all remain acceptable. | [`git-and-docker-safety.md`](../../../docs/agents/git-and-docker-safety.md) |
| The pull request is merged | Report the result, cancel pending check-ins, and stop driving the pull request. Remove only temporary worktrees or scratch resources you created. | [`git-and-docker-safety.md`](../../../docs/agents/git-and-docker-safety.md) |
| The pull request is closed without merge | Report the stopped state, cancel pending check-ins, and make no further changes. Remove only temporary worktrees or scratch resources you created. | [`git-and-docker-safety.md`](../../../docs/agents/git-and-docker-safety.md) |
| A scheduled check-in finds no change | Do not comment on the pull request. Re-arm silently with the bounded cadence below, or stop when its limit is reached. | This skill's [Check-in cadence](#check-in-cadence) |

## Repository-specific guardrails

- Use the root `Makefile` as the canonical command surface: `make dev`,
  `make test`, `make lint`, `make lint-fix`, and `make build`. Never start
  uvicorn manually.
- Always work on a branch and use
  [`.github/PULL_REQUEST_TEMPLATE.md`](../../../.github/PULL_REQUEST_TEMPLATE.md).
  A direct commit to `main` is allowed only for a small docs-only change when
  the user explicitly authorizes it for that change.
- Treat the root `docker-compose.yml` as the live production instance. Never
  run `up`, `down`, `stop`, `rm`, or `restart` against it. Test only with an
  isolated scratch copy, a distinct project name, and no shared volumes.
- Read the relevant specification in [`docs/SPECS/`](../../../docs/SPECS/)
  before feature work.
- Add a [`docs/CHANGELOG.md`](../../../docs/CHANGELOG.md) entry for a
  user-facing change.
- Every change under `src/web/static/` requires a `CACHE_VERSION` bump in
  `src/web/static/ts/sw.ts`.
- A database model change requires an Alembic migration tested with SQLite and
  PostgreSQL.
- Keep `docs/API_VALIDATION_AND_MONITORING.md` and
  `docs/VALIDATION_TEST_CHECKLIST.md` aligned with sharing or validation
  changes.
- The CI workflows to inspect are `ci`, `docs-portal`, and `security-audit`.
- Frontend dependencies use `npm` and `package-lock.json`; run
  `npm run typecheck` and `npm run lint` for frontend changes.
- Keep every repair within the pull request's scope. Never add unrelated work,
  rewrite published history, or use an empty commit to restart CI.

## GitHub tool surface

Use the available `mcp__github__*` tools for pull-request and issue reads,
comments, review replies, metadata changes, pushes, and merges. Prefer the
operation-specific tool for each mutation, preserve existing metadata, and
bind a merge to the exact head when the tool supports it. Do not use `gh pr
edit`-style shortcuts or replace complete label, assignee, or reviewer arrays
to make a one-item change.

## Merge authorization

Never merge without explicit user authorization for this specific pull
request. Green CI, clean reviews, labels, approvals, readiness comments, or a
previous authorization for another pull request are not authorization. A new
head or base target expires authorization; ask again. If any preflight state
has changed, report it and wait instead of merging.

## Check-in cadence

Check-ins are a bounded safety net while the pull request waits on CI, a
reviewer, a decision, or merge authorization:

1. Schedule the first check-in about 15 minutes after the last activity.
2. If nothing changed, re-arm for about 30 minutes, then about 60 minutes.
3. Do not comment or send a status message for a quiet check-in.
4. Stop after three consecutive quiet check-ins, when the pull request merges
   or closes, or when the user says to stop. New activity resets the count.
5. When the limit is reached, cancel the pending check-in and report once that
   automatic check-ins have stopped.

This cadence does not authorize continuous polling and does not extend a
user-specified deadline.
