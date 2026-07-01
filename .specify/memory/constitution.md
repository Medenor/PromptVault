<!--
SYNC IMPACT REPORT
==================
Version change: [unversioned template] → 1.0.0
Modified principles: N/A (initial population)
Added sections:
  - Core Principles (5 principles populated)
  - Security & Quality Standards
  - Development Workflow
  - Governance
Templates reviewed:
  - .specify/templates/plan-template.md ✅ aligned (Constitution Check gate already references constitution)
  - .specify/templates/spec-template.md ✅ aligned (no principle-specific references to update)
  - .specify/templates/tasks-template.md ✅ aligned (structure matches phased approach)
  - .specify/templates/checklist-template.md ✅ no principle-specific references
Deferred TODOs:
  - RATIFICATION_DATE: original project adoption date unknown; set to today (2026-07-01) as first formal ratification
Follow-up: None — all placeholders resolved.
-->

# PromptVault Constitution

## Core Principles

### I. Layered Service Architecture

The codebase MUST maintain strict separation across three layers: web/API, service, and
data/repository. No layer may bypass its neighbor (e.g., a route handler MUST NOT query the
database directly — it MUST go through a service). Services MUST NOT contain HTTP
request/response logic.

**Rationale**: Enforces testability and replaceability of each layer independently.
The repository pattern allows swapping PostgreSQL for SQLite in tests without touching
service logic; the service layer keeps FastAPI routes thin and readable.

### II. Test Coverage Gate (NON-NEGOTIABLE)

Backend MUST maintain ≥ 85% test coverage (enforced in `pytest.ini`). Frontend MUST
maintain ≥ 85% coverage (Vitest + v8). No feature branch MUST be merged below these
thresholds.

Tests MUST be written before or alongside implementation — not after. For any new endpoint
or service method, a corresponding test MUST exist in the PR.

**Rationale**: Coverage thresholds prevent regression creep on a codebase that spans
authentication, versioning, and backup — all high-stakes paths. The 85% floor was set
explicitly in the project README and pytest.ini and MUST be treated as a hard gate.

### III. Security-First Authentication

All endpoints that mutate data (POST, PUT, DELETE) MUST be protected against
unauthenticated access when `AUTH_ENABLED=true`. JWT ES256 tokens MUST be validated on
every protected request. Password hashing MUST use Argon2 (OWASP recommended). Rate
limiting MUST be applied to authentication endpoints via `slowapi`.

When `AUTH_ENABLED=false`, destructive endpoints MUST still guard against unintended
external access using configuration-level controls, not by skipping validation entirely.

**Rationale**: The auth system supports facultative (opt-in) authentication for
self-hosted deployments. Destructive endpoints remain sensitive regardless of auth mode —
the codebase MUST treat them as such.

### IV. TypeScript-Only Frontend

All new frontend logic MUST be written in TypeScript under `src/web/static/ts/`. The
legacy `src/web/static/js/` directory MUST NOT be edited — it is retained for historical
reference only. All TypeScript MUST pass `tsc` typecheck (`npm run typecheck`) and ESLint
(`npm run lint`) before merging.

Internationalization MUST use typed `t('key.path')` calls with `TranslationKey` for
compile-time safety. Dynamic keys MUST use `tUnsafe()` exclusively.

**Rationale**: The TypeScript migration is complete and irreversible. Mixing JS edits
back into the legacy directory would undermine the type-safety guarantees and split
maintenance burden across two code paths.

### V. Database-Backed Persistence (PostgreSQL/SQLite)

All data operations MUST go through SQLAlchemy ORM models and the repository layer.
JSON/file-based storage MUST NOT be used for new features — it is deprecated legacy.
Database schema changes MUST use Alembic migrations. Session management MUST use
context managers for transaction safety and automatic rollback.

**Rationale**: JSON storage is deprecated to guarantee consistency, concurrent access
safety, and production-grade reliability. Alembic migrations enforce schema versioning
and make rollbacks auditable.

## Security & Quality Standards

- Password storage: Argon2 hashing only (no MD5, SHA-1, bcrypt substitutes).
- JWT signing: ES256 algorithm only (no HS256 symmetric keys in production).
- API inputs: Validate at the FastAPI route level using Pydantic models.
- SQL: Access MUST go through SQLAlchemy ORM — no raw SQL strings with user input.
- Frontend: No `eval()`, no `innerHTML` with untrusted input.
- Code style: Black formatter (Python), Prettier (TypeScript/HTML/CSS).
- Python runtime: 3.14+ minimum — no compatibility shims for older versions.

## Development Workflow

1. **Branch**: Create a feature branch (`###-feature-name`) before any implementation work.
2. **Spec first**: Non-trivial features require a spec in `specs/###-feature-name/spec.md`
   before implementation begins.
3. **Tests alongside code**: Write tests as part of the feature PR, not in a follow-up.
4. **Coverage gate**: Verify `python3 -m pytest` passes with ≥ 85% coverage before
   requesting review.
5. **Frontend checks**: Run `npm run typecheck && npm run lint && npm run test:unit:coverage`
   before merging any TypeScript changes.
6. **Docker parity**: Changes that affect startup, environment variables, or dependencies
   MUST be validated against `docker-compose up --build`.
7. **Run server via scripts only**: Use `python run_web.py` — never invoke uvicorn manually.

## Governance

This constitution supersedes all other practices documented in the repository. Where a
conflict exists between this document and any other guideline (README, AGENTS.md,
inline comments), this constitution takes precedence.

**Amendments**: Any principle change requires: (1) a clear rationale, (2) a version bump
in this document following semantic versioning, and (3) a propagation check across
`.specify/templates/` files.

**Versioning policy**:
- MAJOR: Principle removal, redefinition of a non-negotiable rule.
- MINOR: New principle, new mandatory section.
- PATCH: Clarifications, wording fixes, date updates.

**Compliance review**: Every PR description MUST include a "Constitution Check" section
confirming no principles are violated. Plans generated by `/speckit-plan` enforce this
as a gate before Phase 0.

For day-to-day development guidance, see `AGENTS.md`.

**Version**: 1.0.0 | **Ratified**: 2026-07-01 | **Last Amended**: 2026-07-01
