# AGENTS.md

This file provides guidance to any coding agent when working with code in this repository.

## Overview

PromptVault is a modern web-based prompt management application built with FastAPI. It provides a responsive interface for organizing, versioning, and managing AI prompts with features including Git-like version control, comprehensive backup systems, and multi-language support. The application uses a modular service-oriented architecture with clear separation between business logic, web layer, and data persistence.

## Development Commands

### Build & Development

- **Run Development Server**: `python run_web.py` (default port 8000)
- **Run with Custom Port**: `PORT=8001 python run_web.py`
- **Run with Docker**: `docker-compose up --build` (production, port 8001)
- **NEVER manually start uvicorn** - Always use the provided startup scripts

### Code Quality

- **Format Code**: Use black code formatter (configured in project)
- **Python Version**: Python 3.11+ minimum (required for database features)
- **Before Commits**: Run full test suite and ensure coverage meets 85% threshold

### Testing

- **Run Full Test Suite**: `pytest` (includes coverage reporting, ~8 seconds)
- **Run Repository Tests**: `pytest tests/test_db_repositories.py`
- **Run Service Tests**: `pytest tests/test_db_services.py`
- **Run Version Control Tests**: `pytest tests/test_version_system.py`
- **Run API Tests**: `pytest tests/test_web_api.py`
- **Coverage Report**: Generated in `htmlcov/index.html` after running pytest
- **Coverage Threshold**: 85% minimum (enforced in pytest.ini)
- **Current Coverage**: 86.90% (509 passing tests, 99% pass rate)
- **Test Documentation**: See `docs/TESTING.md` for comprehensive guide

## High-Level Architecture

### Core Systems

1. **Database Layer** ([`src/db/`](src/db/))

   - **Database Models** ([`models.py`](src/db/models.py)): SQLAlchemy ORM models
     - `Prompt`: Main prompt entity with relationships
     - `PromptVersion`: Git-like version snapshots
     - `Category`: Prompt categorization
     - `Tag`: Tagging system with many-to-many relationships
     - `User`: User entity for authorship tracking
     - `Backup`: Backup metadata tracking

   - **Repositories** ([`repositories/`](src/db/repositories/)): Data access layer
     - **PromptRepository**: CRUD operations, search, filtering, pagination
     - **VersionRepository**: Version history, comparison, revert operations
     - **CategoryRepository**: Category management with usage tracking
     - **TagRepository**: Tag management, bulk operations, popular tags

   - **Database Configuration** ([`config.py`](src/db/config.py)): Database setup
     - PostgreSQL support (production)
     - SQLite support (development)
     - Environment-based configuration
     - Connection pooling and session management

2. **Service Layer** ([`src/services/`](src/services/))

   - **PromptDataServiceDB** ([`prompt_data_service_db.py`](src/services/prompt_data_service_db.py)): Core data operations
     - Handles all CRUD operations for prompts
     - Database-backed persistence with transactions
     - Automatic versioning on updates
     - Category and tag management
     - Search and filtering capabilities
     - **Note**: Legacy JSON-based service ([`prompt_data_service.py`](src/services/prompt_data_service.py)) deprecated

   - **BackupServiceDB** ([`backup_service_db.py`](src/services/backup_service_db.py)): Database backup system
     - SQLite: File copy with metadata tracking
     - PostgreSQL: pg_dump integration
     - Backup restoration with safety features
     - Retention policies and cleanup
     - Compression for older backups
     - **Note**: Legacy JSON-based service ([`backup_service.py`](src/services/backup_service.py)) deprecated

   - **PromptVersioningService** ([`prompt_versioning_service.py`](src/services/prompt_versioning_service.py)): Git-like version control (legacy)
     - **Note**: Version control now integrated into database models and PromptDataServiceDB
     - UUID-based version identification
     - Automatic versioning on updates
     - Metadata tracking (timestamp, author, message)
     - Parent relationship management
     - Version history preservation

   - **PromptFilterService** ([`prompt_filter_service.py`](src/services/prompt_filter_service.py)): Search and filtering (legacy)
     - **Note**: Filtering now integrated into PromptRepository with database-backed search
     - Multi-criteria filtering (category, tags, search term)
     - Case-sensitive/insensitive search
     - Favorites filtering
     - Sorting by title

   - **PromptImportExportService** ([`prompt_import_export_service.py`](src/services/prompt_import_export_service.py)): Data import/export
     - CSV format support
     - Markdown format support
     - JSON format support
     - Multiple import modes (append, merge, replace)
     - Data validation on import

   - **Version Management Services** (legacy):
     - **VersionCompressionService** ([`version_compression_service.py`](src/services/version_compression_service.py)): Compresses old versions with zlib (deprecated)
     - **VersionTaggingService** ([`version_tagging_service.py`](src/services/version_tagging_service.py)): Tag management for versions (deprecated)
     - **VersionExportService** ([`version_export_service.py`](src/services/version_export_service.py)): Export version history and diffs (deprecated)

3. **Web Application Layer** ([`src/web/`](src/web/))

   - **FastAPI Application** ([`app.py`](src/web/app.py)): Main web server
     - RESTful API endpoints
     - Jinja2 template rendering
     - Static file serving
     - Service coordination and dependency injection
     - Error handling and logging

   - **Templates** ([`templates/`](src/web/templates/)): Server-side HTML rendering
     - [`index.html`](src/web/templates/index.html): Main application interface
     - [`import_export.html`](src/web/templates/import_export.html): Import/export management page
     - [`backup_management.html`](src/web/templates/backup_management.html): Backup management interface

   - **Static Assets** ([`static/`](src/web/static/)):
     - **JavaScript** ([`js/`](src/web/static/js/)): Client-side application logic
       - [`app.js`](src/web/static/js/app.js): Main UI logic and API interactions
       - [`import_export.js`](src/web/static/js/import_export.js): Import/export functionality
       - [`backup_management.js`](src/web/static/js/backup_management.js): Backup management UI
     - **CSS** ([`css/style.css`](src/web/static/css/style.css)): Application styling
     - **i18n** ([`locales/`](src/web/static/locales/)): Translation files (en, fr, es, de)

4. **Data Storage**

   - **Primary Data Store**: Database (SQLite or PostgreSQL)
     - **SQLite**: `data/prompts.db` (development and default)
     - **PostgreSQL**: Configured via `DATABASE_URL` environment variable (production)

   - **Database Schema**:
     - `users`: User accounts with username and email
     - `categories`: Prompt categories with usage tracking
     - `tags`: Global tag definitions
     - `prompts`: Main prompt entities with title, content, note, favorite status
     - `prompt_tags`: Many-to-many relationship between prompts and tags
     - `prompt_versions`: Git-like version snapshots with parent relationships
     - `backups`: Backup metadata tracking

   - **Legacy Data Store**: `data/prompts_data.json` (deprecated, kept for migration)

   - **Backup Storage**:
     - SQLite: `data/backups/` (database file copies + metadata)
     - PostgreSQL: `data/backups/` (pg_dump SQL files + metadata)

   - **Logs**: `data/logs/` (application and audit logs)

### API Endpoints

#### Prompt Management

- `GET /api/prompts` - List all prompts
- `POST /api/prompts` - Create new prompt
- `GET /api/prompts/{id}` - Get specific prompt
- `PUT /api/prompts/{id}` - Update prompt (creates new version)
- `DELETE /api/prompts/{id}` - Delete prompt
- `GET /api/prompts/search` - Search with filters
- `PUT /api/prompts/{id}/favorite` - Toggle favorite status

#### Categorization

- `GET /api/categories` - List all categories
- `GET /api/tags` - List all tags

#### Version Control

- `GET /api/prompts/{id}/versions` - Get version history
- `GET /api/prompts/{id}/versions/compare` - Compare versions
- `GET /api/prompts/{id}/versions/{version_id}` - Get specific version
- `POST /api/prompts/{id}/versions/{version_id}/revert` - Revert to version

#### Import/Export

- `GET /import-export` - Management page
- `POST /api/export` - Export prompts (CSV/Markdown/JSON)
- `POST /api/import` - Import prompts
- `GET /api/import-export/stats` - Import/export statistics

#### Backup Management

- `GET /backup-management` - Management page
- `GET /api/backups` - List all backups
- `POST /api/backups` - Create backup
- `POST /api/backups/{id}/restore` - Restore backup
- `DELETE /api/backups/{id}` - Delete backup
- `POST /api/backups/cleanup` - Cleanup old backups
- `POST /api/backups/compress` - Compress old backups
- `GET /api/backups/stats` - Backup statistics

#### Page Routes

- `GET /` - Main application interface
- `GET /import-export` - Import/export interface
- `GET /backup-management` - Backup management interface

### Key Patterns

- **Service-Oriented Architecture**: Clear separation between data, business logic, and presentation layers
- **RESTful Design**: All operations follow REST principles with proper HTTP methods
- **Factory Pattern**: Service instances created and injected into web application
- **Error Handling**: Try-catch blocks with proper error logging and user-friendly messages
- **Data Validation**: Input validation at both client and server levels
- **Async Operations**: FastAPI async support for file operations (aiofiles)
- **Event-Driven UI**: JavaScript event handlers for real-time updates
- **i18n Support**: Internationalization with i18next library

## Code Style Guidelines

### MAJOR PRINCIPLES

- **WRITE CLEAN, MAINTAINABLE CODE**: Prioritize readability and maintainability over cleverness
- **FOLLOW EXISTING PATTERNS**: Match the established code style and architecture patterns in the repository
- **SERVICE LAYER FIRST**: All business logic belongs in service classes, not in web routes
- **NO HARDCODING**: Use configuration files, environment variables, or constants for configurable values
- **DEFENSIVE PROGRAMMING**: Always validate inputs and handle edge cases gracefully
- **DOCUMENTATION**: All public methods must have docstrings with Args, Returns, and Raises sections

### Python

- **Type Hints**: Use type hints for all function signatures

  ```python
  def get_prompt(self, prompt_id: int) -> Dict[str, Any]:
  ```

- **Docstrings**: Google-style docstrings for all classes and public methods

  ```python
  def save_prompts(self) -> bool:
      """
      Save prompts to the data file.

      Returns:
          bool: True if successful, False otherwise
      """
  ```

- **Error Handling**: Always use try-except blocks for I/O operations and external calls
- **Naming Conventions**:
  - `snake_case` for functions, methods, and variables
  - `PascalCase` for class names
  - `UPPER_SNAKE_CASE` for constants
- **Imports**: Organize imports in three groups:
  1. Standard library
  2. Third-party packages
  3. Local application imports

### JavaScript

- **ES6+ Features**: Use modern JavaScript features (arrow functions, const/let, async/await)
- **Event-Driven**: Use event listeners and delegation patterns
- **API Calls**: Use fetch API with async/await
- **Error Handling**: Always catch errors in promises and display user-friendly messages
- **Telemetry Hooks**: Funnel handled UI errors through `window.FrontendLogger.reportError()` (or provided helpers) so client failures land in the centralized logs—avoid raw `console.error` unless also reporting.
- **i18n**: Use i18next translation keys, never hardcoded strings in UI

  ```javascript
  document.title = i18next.t('title');
  ```

### HTML/Jinja2

- **Semantic HTML**: Use proper HTML5 semantic elements
- **Accessibility**: Include ARIA labels and proper form structure
- **Template Inheritance**: Use Jinja2 template inheritance for consistency
- **Variable Interpolation**: Use `{{ variable }}` for safe HTML escaping

### CSS

- **Responsive Design**: Mobile-first approach with media queries
- **Naming**: Use meaningful class names that describe purpose
- **Organization**: Group related styles together
- **Comments**: Add comments for complex styling rules

### General

- **DRY Principle**: Don't Repeat Yourself - extract common logic into reusable functions
- **KISS Principle**: Keep It Simple, Stupid - prefer simple solutions over complex ones
- **Single Responsibility**: Each function/class should have one clear purpose
- **Code Organization**: Group related functionality together in modules
- **Constants**: Define magic numbers and strings as named constants
- **Logging**: Legacy code still uses `print()` for error reporting, but Issue #10 requires migrating to centralized structured logging with JSON payloads, request IDs, and rotating files in `data/logs/`. Reference `docs/plan_centralized_error_logging.md` for the mandated fields and retention targets, and prefer the shared logging helpers once they land. Use direct `print()` only as a short-lived fallback when no logger is injected yet.

### Observability Requirements (Issue #10)

- **Structured Output**: Application logs (`data/logs/app.log`) and audit logs (`data/logs/audit.log`) must emit JSON objects containing `timestamp`, `level`, `event`, `request_id`, `actor`, `action`, `resource_id`, `status`, and `duration_ms`. Avoid logging prompt or note bodies—stick to metadata.
- **Request Correlation**: Each FastAPI request must receive a request ID (UUIDv4 hex) propagated via `contextvars` into all services and included in every downstream log event.
- **Retention & Rotation**: Target five 10 MB app log files (~2 weeks) and ten 5 MB audit files (~30 days). The `./data` host volume (mounted as `/app/data` in Docker) already persists logs; no extra volume is required, but operators need to copy `data/logs/` if they want log backups.
- **Audit Coverage**: Emit audit entries for prompt CRUD, version reverts, import/export actions, backup lifecycle events, cleanup/compression operations, and any automated intervention (auto backups before deletes/imports). Include actor identity (`getpass.getuser()` until auth ships) and outcome (`success`, `failure`).
- **Configurability**: Support `LOG_LEVEL` and `AUDIT_LOG_LEVEL` env vars (default `INFO`) plus developer-friendly console formatting when `ENVIRONMENT=development`. Provide documentation in README/AGENTS describing the knobs.
- **Health Signals**: ValidationMonitor write failures, frontend error reports, and logging subsystem issues must be logged through the structured logger so ops teams can alert on them.

## Testing Guidelines

### Test Organization

- **Location**: All tests in [`tests/`](tests/) directory
- **Fixtures**: Shared fixtures in [`conftest.py`](tests/conftest.py)
- **Naming**: Test files must start with `test_` (e.g., `test_prompt_data_service.py`)
- **Structure**: One test file per service/module being tested

### Test Fixtures

Available in [`conftest.py`](tests/conftest.py):

- **Database Fixtures**:
  - `test_db_engine` - In-memory SQLite engine for fast, isolated tests
  - `test_db_session` - Database session with automatic rollback
  - `reset_database` - Smart database reset (autouse, backward compatible)

- **Model Fixtures**:
  - `test_user` - Test user for authorship tracking
  - `test_category` - Test category with unique name
  - `test_tags` - List of test tags
  - `test_prompt` - Single prompt with relationships
  - `test_prompt_with_versions` - Prompt with 10 versions for history testing

- **Repository Fixtures**:
  - `prompt_repo` - PromptRepository instance
  - `version_repo` - VersionRepository instance
  - `category_repo` - CategoryRepository instance
  - `tag_repo` - TagRepository instance

- **Service Fixtures**:
  - `db_data_service` - Database-backed PromptDataService
  - `db_backup_service` - Database-backed BackupService
  - `sample_prompt_data` - Factory for creating test prompt data

- **API Testing**:
  - `api_client` - FastAPI TestClient with database backend
  - `api_client_context` - Isolated test client with temporary data

- **Legacy Fixtures** (for backward compatibility):
  - `empty_data_service`, `populated_data_service` - JSON-based services (deprecated)
  - `sample_csv_content`, `sample_markdown_content` - Import/export test data

### Test Suite Structure

**See [`docs/TESTING.md`](docs/TESTING.md) for comprehensive testing documentation.**

1. **Repository Tests** ([`test_db_repositories.py`](tests/test_db_repositories.py)): 78 tests, 89-100% coverage
   - PromptRepository CRUD operations, search, filtering, pagination
   - VersionRepository history, comparison, revert operations
   - CategoryRepository management with usage tracking
   - TagRepository bulk operations and popular tags

2. **Service Tests** ([`test_db_services.py`](tests/test_db_services.py)): 88 tests, 94% pass rate
   - PromptDataService with database backend
   - BackupService for SQLite and PostgreSQL

3. **Version Control Tests** ([`test_version_system.py`](tests/test_version_system.py)): 48 tests, 95-100% coverage
   - Version creation and history tracking
   - Version comparison and diff generation
   - Version revert operations
   - Integration workflows

4. **API Endpoint Tests** ([`test_web_api.py`](tests/test_web_api.py)): API integration tests
   - RESTful endpoints for prompts, categories, tags
   - Version control endpoints
   - Import/export functionality
   - Backup management

### Test Coverage Metrics

- **Overall Coverage**: 86.90% (exceeds 85% threshold)
- **Total Tests**: 509 passing out of 514 (99% pass rate)
- **Execution Time**: ~8 seconds (13x faster than legacy suite)
- **Test Infrastructure**: 30 comprehensive fixtures supporting database-backed testing

### Writing Tests

Database-backed test example:

```python
def test_add_prompt(db_data_service, sample_prompt_data):
    """Test adding a new prompt with database backend."""
    # Arrange
    prompt_data = sample_prompt_data(title="New Prompt")

    # Act
    prompt_id = db_data_service.add_new_prompt(prompt_data)

    # Assert
    assert prompt_id is not None
    prompt = db_data_service.get_prompt_by_id(prompt_id)
    assert prompt['title'] == "New Prompt"

    # Verify version created
    versions = db_data_service.get_prompt_versions(prompt_id)
    assert len(versions) == 1
    assert versions[0]['message'] == "Initial version"
```

## Development Session Planning

### Session Workflow

When working on a development session:

1. **Understand the Request**: Carefully read and analyze the user's requirements
2. **Explore the Codebase**: Use Read, Grep, and Glob tools to understand existing implementation
3. **Plan Your Approach**: Consider impact on existing code and tests
4. **Implement Changes**: Follow established patterns and code style
5. **Update Tests**: Ensure test coverage remains above 85%
6. **Test Your Changes**: Run relevant tests before committing
7. **Document Changes**: Update CHANGELOG.md with user-facing changes
8. **Validation Framework**: Verify client/server validation parity, `/api/validation/stats` monitoring, and keep `docs/API_VALIDATION_AND_MONITORING.md` + `docs/VALIDATION_TEST_CHECKLIST.md` aligned

### Before Making Changes

- **Read Existing Code**: Always read the relevant service/module first
- **Check Tests**: Review existing tests to understand expected behavior
- **Identify Patterns**: Follow established architectural patterns
- **Consider Impact**: Think about downstream effects of changes

### After Making Changes

- **Run Tests**: `pytest` to ensure all tests pass
- **Check Coverage**: Verify coverage remains ≥ 85%
- **Update Documentation**: Update docstrings and comments
- **Verify Functionality**: Manually test the feature if possible

## Important Notes

### Data Storage and Migration

- **Current System**: Database-backed (SQLite or PostgreSQL)
- **Database Models**: SQLAlchemy ORM with relationships and constraints
- **Primary Keys**: Integer IDs for prompts, categories, tags, users
- **Version IDs**: UUID strings for reliable version identification
- **Timestamps**: ISO 8601 format stored in database (e.g., "2024-01-01T12:00:00Z")
- **Legacy System**: JSON file storage (deprecated, kept for migration only)
- **Migration Path**: Use database-backed services (PromptDataServiceDB, BackupServiceDB)

### Version Control System

- **Database-Backed**: Version snapshots stored in `prompt_versions` table
- **Git-like Design**: Parent-child relationships, immutable history
- **Automatic Versioning**: Every prompt update creates a new version
- **Immutable History**: Version history is never lost, only extended
- **Revert Creates New Version**: Reverting doesn't delete history, creates new commit
- **Metadata Required**: Each version has timestamp, author, message, and full data snapshot
- **Version Comparison**: Built-in diff generation for comparing versions

### Backup System

- **Database-Specific**:
  - **SQLite**: File copy with metadata tracking in `backups` table
  - **PostgreSQL**: pg_dump integration with SQL file storage
- **Pre-operation Backups**: Automatic before risky operations (delete, replace import)
- **Manual Backups**: User can create named backups anytime
- **Pre-restore Backups**: Automatic safety backup before restoring another backup
- **Retention Policy**: Configurable cleanup of old backups
- **Compression**: Older backups automatically compressed with gzip
- **Metadata Tracking**: All backup operations tracked in database

### Internationalization

- **Translation Keys**: All UI strings use i18next translation keys
- **Supported Languages**: English (en), French (fr), Spanish (es), German (de)
- **Translation Files**: JSON files in [`src/web/static/locales/`](src/web/static/locales/)
- **Dynamic Switching**: Users can change language without restarting

### Docker Deployment

- **Data Persistence**: Data directory mounted as volume (`./data:/app/data:rw`)
- **Port Mapping**: 8001 (host) → 8000 (container)
- **Hot Reload**: Enabled in development mode
- **Health Checks**: Container health monitoring configured

### Common Pitfalls

- **Don't modify the web app without updating tests**: Always maintain test coverage
- **Don't hardcode file paths**: Use `os.path.join()` and relative paths
- **Don't skip error handling**: Always wrap I/O and database operations in try-except
- **Don't forget transactions**: Use database sessions with proper commit/rollback
- **Don't use legacy services**: Use database-backed services (PromptDataServiceDB, BackupServiceDB)
- **Don't break database migrations**: Test with both SQLite and PostgreSQL when modifying models
- **Don't use console.log in production**: Remove debug statements before committing
- **Don't skip database session management**: Always close sessions properly

### Technical Debt and Future Work

See issues tracker at: <https://codeberg.org/medenor/promptvault/issues>

Current priorities:

- Input validation and sanitization
- Centralized error handling and logging (Issue #10)
- TypeScript migration for frontend
- Tag and category management interface
- Complete removal of legacy JSON-based services
- PostgreSQL production deployment guide

## Quick Reference

### Running the Application

```bash
# Development
python run_web.py

# Custom port
PORT=8001 python run_web.py

# Docker production
docker-compose up --build
```

### Testing (Quick Reference)

```bash
# Full test suite with coverage (~8 seconds)
pytest

# Repository layer tests
pytest tests/test_db_repositories.py

# Service layer tests
pytest tests/test_db_services.py

# Version control tests
pytest tests/test_version_system.py

# API endpoint tests
pytest tests/test_web_api.py

# View coverage report (current: 86.90%)
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux

# See comprehensive testing guide
cat docs/TESTING.md
```

### Project URLs

- **Repository**: <https://codeberg.org/medenor/promptvault>
- **Issues**: <https://codeberg.org/medenor/promptvault/issues>
- **License**: AGPL v3

### Key Files

| File | Purpose |
|------|---------|
| [`run_web.py`](run_web.py) | Web server startup script |
| [`src/web/app.py`](src/web/app.py) | FastAPI application and routes |
| [`src/db/models.py`](src/db/models.py) | SQLAlchemy database models |
| [`src/db/config.py`](src/db/config.py) | Database configuration and session management |
| [`src/db/repositories/`](src/db/repositories/) | Repository layer (data access) |
| [`src/services/prompt_data_service_db.py`](src/services/prompt_data_service_db.py) | Database-backed data service |
| [`src/services/backup_service_db.py`](src/services/backup_service_db.py) | Database-backed backup service |
| [`data/prompts.db`](data/prompts.db) | SQLite database (development) |
| [`tests/conftest.py`](tests/conftest.py) | Test fixtures (30 database-aware fixtures) |
| [`tests/test_db_repositories.py`](tests/test_db_repositories.py) | Repository layer tests |
| [`tests/test_db_services.py`](tests/test_db_services.py) | Service layer tests |
| [`tests/test_version_system.py`](tests/test_version_system.py) | Version control tests |
| [`docs/TESTING.md`](docs/TESTING.md) | Comprehensive testing guide |
| [`docs/SPECS/SPEC_DATABASE.md`](docs/SPECS/SPEC_DATABASE.md) | Database architecture specification |
| [`pyproject.toml`](pyproject.toml) | Project configuration |
| [`pytest.ini`](pytest.ini) | Test configuration |
| [`.coveragerc`](.coveragerc) | Coverage configuration (excludes legacy code) |
| [`Dockerfile`](Dockerfile) | Container configuration |
| [`docker-compose.yml`](docker-compose.yml) | Docker Compose setup |
| [`CHANGELOG.md`](CHANGELOG.md) | Release history |

## Summary

PromptVault is a production-ready web application for managing AI prompts with comprehensive version control and backup systems. The application has migrated from JSON file storage to a robust database-backed architecture using SQLAlchemy ORM with support for both SQLite (development) and PostgreSQL (production).

**Key Features:**

- **Database-Backed Architecture**: SQLAlchemy models with repository pattern for data access
- **Git-like Version Control**: Immutable version history with parent-child relationships
- **Comprehensive Backup System**: Database-specific backup strategies for SQLite and PostgreSQL
- **Service-Oriented Design**: Clear separation between repositories, services, and web layer
- **High Test Coverage**: 86.90% coverage with 509 passing tests (99% pass rate)
- **Fast Test Execution**: 8-second test suite using in-memory SQLite
- **Multi-Language Support**: Internationalization for English, French, Spanish, and German
- **Docker Deployment**: Production-ready containerization with data persistence

**Development Guidelines:**

- Use database-backed services (PromptDataServiceDB, BackupServiceDB)
- Maintain 85% test coverage threshold (current: 86.90%)
- Follow repository pattern for data access
- Use proper database session management with transactions
- Test with both SQLite and PostgreSQL when modifying models
- Refer to `docs/TESTING.md` for comprehensive testing guide

When contributing, prioritize code readability, maintainability, and test coverage. Follow the existing architectural patterns and ensure all public APIs have comprehensive documentation.
