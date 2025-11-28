---
title: Database Migration: JSON to Relational (SQLite / PostgreSQL)
version: 1.0
date_created: 2025-11-28
last_updated: 2025-11-28
owner: medenor
tags: [infrastructure, schema, design, database, migration]
---

## Database Migration Specification

This specification describes the architecture, schema design, migration strategy, and operational and testing requirements for migrating PromptVault from JSON-file storage to an RDBMS using SQLite for development/small deployments and PostgreSQL for production.

## 1. Purpose & Scope

Purpose: Replace JSON file storage with a relational database to address concurrent access, data durability, query efficiency, and scalability.

- Scope:

- Migrate data persisted in `data/prompts_data.json` to a relational database.
- Implement SQLAlchemy ORM models with a migration pipeline (Alembic) and database-related code changes in services that access prompt data (notably `src/services/prompt_data_service.py`, `src/services/prompt_versioning_service.py`, and related services).
- Provide environment and development configurations to support SQLite for tests/dev and PostgreSQL for production.
- Provide backup and healthcheck operations for the new data layer.
- Deliver test coverage, migration scripts, and a guide for upgrading from JSON storage.

Intended audience: Developers, maintainers, SREs, CI/CD owners, and data migration engineers.

Assumptions:

- The application currently expects JSON files in `data/prompts_data.json` and may rely on file I/O operations from the `PromptDataService`.
- This spec targets existing code and public API behavior; downstream clients should not be impacted by the storage migration.

## 2. Definitions

- ACID: Atomicity, Consistency, Isolation, Durability.
- ORM: Object Relational Mapper – SQLAlchemy is the chosen ORM.
- FTS: Full-Text Search (PostgreSQL tsvector, SQLite FTS5).
- Alembic: Database schema migration tool for SQLAlchemy.
- Read replica: A database instance that asynchronously replicates reads from a primary node.
- pg_dump: PostgreSQL utility for database backups.
- DB: Database (SQLite or PostgreSQL depending on environment).
- DTO: Data Transfer Object.

## 3. Requirements, Constraints & Guidelines

- Requirements (functional and non-functional):

- **REQ-001**: A schema that models users, prompts, versions, categories, tags, and backups; versioning and relationships must be normalized.
- **REQ-002**: Use SQLAlchemy as the application ORM for DB operations.
- **REQ-003**: Provide migrations via Alembic with initial creation and follow-up migrations.
- **REQ-004**: Data migration tool to import existing JSON (including historical versions and metadata) without data loss.
- **REQ-005**: Implement indices for frequent queries: `prompt.title`, `prompt.category`, `prompt.created_at`, `user_id`, and tags (with join table optimization).
- **REQ-006**: Implement full-text search support (PostgreSQL tsvector for production, SQLite FTS5 for development/test).
- **REQ-007**: Support transactional operations for multi-step changes (create prompt + version, update multiple prompt fields, delete cascade behavior).
- **REQ-008**: Add connection pooling and session management suitable for web applications.
- **REQ-009**: Add DB health checks to API startup, with failure modes clearly logged and safe-fallback behavior (e.g., API refuses to start if DB not ready for production, while SQLite may allow local use with warnings).
- **REQ-010**: Implement database backup strategy and integration into the `BackupService`.
- **REQ-011**: Make DB connection configurable via environment variables (connection string, pool size, timeout, retry parameters).
- **REQ-012**: Update CI/test configuration to use ephemeral in-memory SQLite databases for speed.
- **REQ-013**: Provide a migration guide and README content for users migrating from JSON to DB.

Security Requirements:

- **SEC-001**: Use secure default DB credentials for production; prefer secrets manager for production environments.
- **SEC-002**: Ensure that user data access follows permissions and typical authentication model in the app. No unintended data exposure via joins or search.

Constraints:

- **CON-001**: The solution must be compatible with both SQLite and PostgreSQL; avoid using features not supported by both unless guarded by the environment (e.g., FTS implementation differences).
- **CON-002**: Keep API backward compatibility where possible so that client-side behavior doesn't require changes.
- **CON-003**: Avoid adding dependencies that will not be easily installable on macOS/Linux CI (use `psycopg2-binary` and `sqlite3` built-in, `SQLAlchemy` >= 1.4 / 2.0 compatible, `Alembic` >= 1.8).

Guidelines:

- **GUD-001**: Build tests first – ensure service behavior is tested with an in-memory SQLite DB.
- **GUD-002**: Use SQLAlchemy models with explicit relationships and join tables (no dynamic JSON columns for core data).
- **GUD-003**: Keep DB migrations idempotent and reversible (Alembic `upgrade`/`downgrade`).
- **GUD-004**: Use consistent timestamps (UTC) and store them in `created_at` / `updated_at` fields.

Patterns:

- **PAT-001**: Repository/Service pattern: keep DB logic inside `PromptDataService` and `PromptVersioningService` by deferring to a `models.py` ORM layer.
- **PAT-002**: Use DTOs and data mappers to translate ORM models to existing JSON-style payloads to maintain the public API.

## 4. Interfaces & Data Contracts

High-level Entities and Relationships (ERD):

- `users`: stores user accounts and credentials metadata (id, username, email, role, created_at)
- `prompts`: stores the prompt core metadata (id, title, description, user_id -> users.id, category_id, state, created_at, updated_at)
- `prompt_versions`: stores historical versions of a prompt (id, prompt_id -> prompts.id, version_number, content (text), metadata (JSONB for Postgres/JSON for SQLite), created_by -> user.id, created_at, notes)
- `categories`: stores prompt categories (id, name, parent_category_id?)
- `tags`: stores tags (id, name)
- `prompt_tags` (join table): prompt_id, tag_id
- `backups`: records backup metadata (id, backup_type, storage_path, created_at, size_bytes, succeeded)

 Column schemas (recommended):

 ```yaml
 users:
   id: UUID/serial primary key
   username: varchar, unique
   display_name: varchar
   email: varchar
   role: enum (admin, user) or varchar
   created_at: timestamp UTC

 categories:
   id: serial pk
   name: varchar
   description: text
   created_at: timestamp UTC

 tags:
   id: serial pk
   name: varchar (unique)

 prompts:
   id: UUID or serial primary key
   title: varchar
   description: text
   user_id: FK users.id (owner)
   category_id: FK categories.id
   visibility: enum (private, public)
   state: varchar or enum (active, archived)
   created_at: timestamp UTC
   updated_at: timestamp UTC

 prompt_versions:
   id: serial pk
   prompt_id: FK prompts.id
   version_number: integer
   content: text
   content_metadata: JSON/JSONB
   changed_by: FK users.id
   created_at: timestamp
   notes: text

 prompt_tags:
   prompt_id: FK prompts.id
   tag_id: FK tags.id
   PRIMARY KEY: (prompt_id, tag_id)

 backups:
   id: UUID/serial pk
   backup_type: enum (json, dbdump, sqlite-copy)
   storage_path: text
   size_bytes: bigint
   created_at: timestamp
   succeeded: boolean
 ```

Indices & Search considerations:

- Create indices on `prompts.title`, `prompts.category_id`, `prompts.user_id`, `prompts.created_at`, `prompt_versions.created_at`.
- For tag searches, maintain `prompt_tags` foreign keys and index the `tag_id` side.
- For full-text search.
  - PostgreSQL: add a tsvector column and index: `CREATE INDEX ON prompts USING GIN (to_tsvector('english', title || ' ' || description));`.
  - SQLite: create an FTS5 virtual table for prompts content and keep it in-sync with triggers or maintain a separate `prompts_fts` table.

Data contracts (JSON payload examples):

Example POST /prompts (create):

```json
{
  "title": "Design an onboarding prompt",
  "description": "A detailed guide for prompt writers...",
  "user_id": "user-123",
  "category": "onboarding",
  "tags": ["onboarding", "guide"],
  "content": "Full prompt content here"
}
```

Example Response (API consistent with existing behavior):

```json
{
  "id": "prompt-1",
  "title": "Design an onboarding prompt",
  "description": "A detailed guide...",
  "versions": [
    {
       "version_number": 1,
       "content": "Full prompt content here",
       "created_at": "2025-11-28T12:34:56Z"
    }
  ]
}
```

Access Patterns & Constraints:

- Most queries: List prompts by user, list prompts by category, filter by tags, search by title/content.
- Acceptable pagination contract: `GET /prompts?limit=20&offset=0` (cursor-based pagination is recommended for large datasets; define a follow-up improvement if needed).

## 5. Acceptance Criteria

- **AC-001**: Given the application starts with JSON files and an empty DB, when the migration script is run, then all prompts, versions, categories, tags, and backups are imported exactly with counts equal to JSON data and no loss of metadata.
- **AC-002**: Given a new prompt creation operation, when called via API, then a new prompt row and prompt_versions row are created in one transaction, and no partial writes are visible to other transactions.
- **AC-003**: Given the DB is PostgreSQL, when a text search is performed, then results match the content using a tsvector-backed index and return results within a response time threshold (e.g., < 200ms for 10k prompts on a typical dev machine; define more rigorous infra thresholds for production).
- **AC-004**: Given the API starts in production, when DB is not reachable, then the app should log a critical error and either exit or refuse to start (configurable behavior); health endpoints should reflect DB status.
- **AC-005**: Given a backup operation, when invoked, then a consistent DB dump is created (pg_dump) and records the dump metadata in `backups`.
- **AC-006**: Given the tests run with in-memory SQLite, the test suite should pass and be faster than the JSON-based tests for the same workloads, and existing tests that exercised prompt operations must be preserved (or slightly adapted for ORM responses).
- **AC-007**: Given JSON files exist, when the migration is complete, then the UI and API behavior (payload shape and endpoints) remain compatible with existing clients. If backward compatibility is not feasible, deprecations must be documented in the migration guide.

## 6. Test Automation Strategy

- Test Levels: Unit, Integration, End-to-End.
- Frameworks: pytest (existing), SQLAlchemy ORM session fixtures, Alembic for migration test harnessing.
- Test ephemeral DBs:
  - Unit tests should mock DB access or use the repository/API layer with fixtures that load an in-memory SQLite DB.
  - Integration tests should run migrations in a containerized PostgreSQL (GitHub Actions) or use SQLite for faster iteration. For broader integration/CI, run a matrix of SQLite and PostgreSQL tests.
- Test Data Management:
  - The test harness will create and drop schemas between tests. Use fixtures in `tests/conftest.py` to set up initial data and roll back transactions.
  - Test seeds for prompts should be a small dataset (100–1000 rows) and include versions and tags to exercise joins.
- CI/CD Integration:
  - Add job matrix to run with SQLite and PostgreSQL using official Postgres Docker images.
  - Run Alembic migrations as part of the CI pipeline and test that `upgrade`/`downgrade` performs correctly.
- Coverage & Performance Testing:
  - Maintain or increase existing code coverage thresholds; adapt existing tests where needed (e.g., tests emphasizing direct file I/O will be removed or migrated).
  - Add performance benchmarks for scaled datasets using `pytest-benchmark` or a CI job that creates 1k, 10k, 100k prompts and measures search/filter/pagination latencies. Set thresholds for acceptable performance.

## 7. Rationale & Context

Why move to a DB?

- JSON files are simple but not suitable for concurrent access and efficient querying. Database provides ACID properties, concurrency, indexing and the ability to scale read and write workloads.

Why SQLAlchemy?

- SQLAlchemy is a mature, widely used Python ORM, offering strong support, compatibility, and Alembic migration integration. It enables a consistent domain model.

Why SQLite + PostgreSQL?

- SQLite: lightweight for local development and CI tests; minimal setup, fast iteration. PostgreSQL: the recommended production DB with advanced features, strong full-text search, and multi-connection reliability.

Trade-offs:

- Migration work and DB operational overhead vs. clear operational and performance benefits; the spec insists on backward compatibility to limit client disruption.

## 8. Dependencies & External Integrations

External Systems:

- EXT-001: PostgreSQL DB – Persistent store in production; required for durability and indexing.

Third-Party Services:

- SVC-001: Optional secrets management service to store production DB credentials and backup targets.

Infrastructure Dependencies:

- INF-001: Docker Compose and a volume for PostgreSQL data in development.
- INF-002: CI/CD runners with Postgres service for integration tests.

Data Dependencies:

- DAT-001: `data/prompts_data.json` – canonical source for migration.

Platform Dependencies:

- PLT-001: Python 3.11+ - consistent with existing `pyproject.toml`.

Compliance Dependencies:

- COM-001: GDPR / data retention – The backups and DB must support retention policies and safe deletion of user data upon request. This is an implementation concern, but the DB schema should include data deletion policies.

## 9. Examples & Edge Cases

Edge Case: Conflicting prompt IDs

- If JSON data contains duplicate prompt IDs or version numbers, the migration script must:
  1. Log any conflicts and map duplicate IDs to new UUIDs (ensuring cross-references maintain integrity), or
  2. Fail with an import error and produce a reconciliation report to be fixed prior to migration.

Edge Case: Partial migration / retry

- If the migration fails midway, migration scripts must implement idempotency to resume or re-run safely (e.g., write a `migration_status` record that tracks progress and ensures operations are atomic per prompt batch).

Edge Case: Attachment or external binary data

- If prompts include binary attachments stored on disk or in JSON as base64, the migration should either:
  - Push attachments to a storage service and store a stable URI, or
  - Continue referencing local files with metadata, without in-lining them in DB fields.

Example SQLAlchemy model outline (pseudocode)

```python
class Prompt(Base):
    __tablename__ = 'prompts'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(256), nullable=False)
    description = Column(Text)
    user_id = Column(UUID, ForeignKey('users.id'))
    versions = relationship('PromptVersion', back_populates='prompt')
    tags = relationship('Tag', secondary='prompt_tags')
```

Migration example

```bash
# Run migrations
alembic upgrade head

# Run migration from JSON to DB
python scripts/migrate_json_to_db.py --source data/prompts_data.json --db-url $DATABASE_URL
```

## 10. Validation Criteria

- Data equivalence checks: A migration script must produce a row count equality report and a hash-based checksum for row sets across prompts and versions.
- Transactional integrity: Operations that change multiple tables must use database transactions and fail cleanly on error.
- Performance threshold: Simple prompt list queries must respond in <200ms on dev hardware for 10k prompts when using PostgreSQL with proper indices. This is a starting benchmark; production SLAs should be set further.
- Backups and restores: The `BackupService` must produce successful dumps and restore steps must be tested in a staging environment.

## 11. Related Specifications / Further Reading

- docs/SPECS/spec-backup-restore.md (if the project has one) or [BackupService design]
- PostgreSQL: [PostgreSQL Documentation](https://www.postgresql.org/docs/current/index.html)
- SQLAlchemy: [SQLAlchemy Documentation](https://www.sqlalchemy.org/docs/)
- Alembic: [Alembic Documentation](https://alembic.sqlalchemy.org/en/latest/)
- SQLite FTS5: [SQLite FTS5](https://www.sqlite.org/fts5.html)

## Implementation Checklist & Migration Steps (Suggested)

1. Install dependencies: `SQLAlchemy`, `psycopg2-binary`, `alembic`.
2. Create `src/models/*.py` with SQLAlchemy models for `users`, `prompts`, `prompt_versions`, `tags`, `prompt_tags`, `categories`, `backups`.
3. Create Alembic configuration and initial migration script to create schema.
4. Create database initialization script to create default roles and admin user – idempotent.
5. Create a data migration script to import content from `data/prompts_data.json` (maintain metadata and version history).
6. Refactor `PromptDataService` and `PromptVersioningService` to use ORM and DB sessions.
7. Add DB indices and FTS support for performance.
8. Add DB health checks on app startup.
9. Add backup hooks to `BackupService` to create DB dumps.
10. Add tests for ORM operations, migrations, and verification of data parity with a JSON import sample.
11. Add docs/README updates and `env` configuration examples, `docker-compose` with `postgres` service and `volumes`.
12. Create a migration guide for users.

## 12. Appendices: Environment & Example Configs

`.env.example`

```bash
# Development SQLite (default)
DATABASE_URL=sqlite+pysqlite:///./data/promptvault.db

# Production PostgreSQL example
# DATABASE_URL=postgresql+psycopg2://username:password@db:5432/promptvault

DB_POOL_SIZE=20
DB_POOL_TIMEOUT=30
```

Docker Compose example snippet (development with Postgres)

```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_USER: promptvault
      POSTGRES_PASSWORD: promptvault
      POSTGRES_DB: promptvault
    volumes:
      - promptvault_db:/var/lib/postgresql/data

volumes:
  promptvault_db:
```

---

### Notes and Next Steps

- Developer tasks and code owners should proceed with model changes, necessary refactors, and tests. A separate task should be created for the migration script and for DB-backed backup support.

---

End of specification: Database Migration: JSON to Relational (SQLite / PostgreSQL)
