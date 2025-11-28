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

   - **PromptVersioningService** ([`prompt_versioning_service.py`](src/services/prompt_versioning_service.py)): Git-like version control
     - UUID-based version identification
     - Automatic versioning on updates
     - Metadata tracking (timestamp, author, message)
     - Parent relationship management
     - Version history preservation

   - **BackupService** ([`backup_service.py`](src/services/backup_service.py)): Data backup and restoration
     - Timestamped automatic backups
     - Custom-named manual backups
     - Backup restoration with pre-restore safety backups
     - Configurable retention policies
     - Gzip compression for older backups
     - Comprehensive backup metadata

   - **PromptFilterService** ([`prompt_filter_service.py`](src/services/prompt_filter_service.py)): Search and filtering
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

   - **Version Management Services**:
     - **VersionCompressionService** ([`version_compression_service.py`](src/services/version_compression_service.py)): Compresses old versions with zlib
     - **VersionTaggingService** ([`version_tagging_service.py`](src/services/version_tagging_service.py)): Tag management for versions
     - **VersionExportService** ([`version_export_service.py`](src/services/version_export_service.py)): Export version history and diffs

2. **Web Application Layer** ([`src/web/`](src/web/))

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

3. **Data Storage**

   - **Primary Data Store**: [`data/prompts_data.json`](data/prompts_data.json)

     ```json
     {
       "next_id": integer,
       "prompts": {
         "1": {
           "data": {
             "title": string,
             "prompt": string,
             "category": string,
             "tags": array,
             "favorite": boolean,
             "note": string
           },
           "versions": [
             {
               "version_id": string (UUID),
               "timestamp": string (ISO 8601),
               "author": string,
               "message": string,
               "data": object (snapshot),
               "parents": array (version IDs)
             }
           ],
           "branches": {
             "main": string (version_id)
           }
         }
       },
       "categories": array,
       "global_tags": array
     }
     ```

   - **Backup Storage**: `data/backups/` (JSON and compressed .gz files)
   - **Logs**: `data/logs/` (application logs)

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

- **Data Fixtures**:
  - `temp_data_dir` - Temporary directory with automatic cleanup
  - `temp_data_file` - Temporary JSON file path
  - `sample_prompt_data` - Factory for creating test prompts
  - `sample_version_data` - Factory for creating test versions
  - `sample_csv_content` - CSV test data
  - `sample_markdown_content` - Markdown test data
  - `malformed_json_samples` - Invalid JSON for error testing

- **Service Fixtures**:
  - `empty_data_service` - Fresh PromptDataService instance
  - `populated_data_service` - Service with 5 test prompts
  - `large_dataset_service` - Service with 1000 prompts (performance testing)
  - `prompt_with_versions` - Prompt with 10 versions for history testing
  - `backup_service`, `filter_service`, `import_export_service` - Service instances
  - `compression_service`, `tagging_service`, `export_service`, `versioning_service` - Version services

- **API Testing**:
  - `test_client` - FastAPI TestClient
  - `api_client_context` - Isolated test client with temporary data

### Test Coverage Areas

1. **Unit Tests**: Test individual service methods in isolation
2. **Integration Tests**: Test API endpoints and service interactions
3. **Performance Tests**: Marked with `@pytest.mark.performance`, test large datasets
4. **Error Handling**: Test malformed data and edge cases

### Writing Tests

```python
def test_add_prompt(populated_data_service, sample_prompt_data):
    """Test adding a new prompt to the service."""
    # Arrange
    initial_count = len(populated_data_service.prompts)
    new_prompt = sample_prompt_data(title="New Prompt")

    # Act
    prompt_id = populated_data_service.add_new_prompt(new_prompt)

    # Assert
    assert prompt_id is not None
    assert len(populated_data_service.prompts) == initial_count + 1
    assert populated_data_service.prompts[prompt_id]['data']['title'] == "New Prompt"
```

### Test Markers

- `@pytest.mark.slow` - Marks slow-running tests
- `@pytest.mark.integration` - Marks integration tests
- `@pytest.mark.performance` - Marks performance tests

### Performance Baselines

Tests in [`test_performance.py`](tests/test_performance.py) enforce these baselines:

- Load/save 1,000 prompts: < 5 seconds
- Load 2,000 version records: < 10 seconds
- Filter/search/sort 1,000 prompts: < 1 second per operation
- Export 1,000 prompts to CSV/Markdown: < 5 seconds

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

### Data Format

- **JSON Storage**: All data stored in JSON format with UTF-8 encoding
- **Integer Keys**: Prompt IDs are integers, but stored as strings in JSON
- **Version IDs**: UUID strings for reliable version identification
- **Timestamps**: ISO 8601 format (e.g., "2024-01-01T12:00:00Z")

### Version Control System

- **Automatic Versioning**: Every prompt update creates a new version
- **Immutable History**: Version history is never lost, only extended
- **Revert Creates New Version**: Reverting doesn't delete history, creates new commit
- **Metadata Required**: Each version must have timestamp, author, and message

### Backup System

- **Pre-operation Backups**: Automatic before risky operations (delete, replace import)
- **Manual Backups**: User can create named backups anytime
- **Pre-restore Backups**: Automatic backup before restoring another backup
- **Retention Policy**: Configurable cleanup of old backups
- **Compression**: Older backups automatically compressed with gzip

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
- **Don't skip error handling**: Always wrap I/O operations in try-except
- **Don't forget to save data**: Call `save_prompts()` after modifications
- **Don't break the data format**: Maintain backward compatibility with existing JSON structure
- **Don't use console.log in production**: Remove debug statements before committing

### Technical Debt

See issues tracker at: <https://codeberg.org/medenor/promptvault/issues>

Current priorities:

- Input validation and sanitization
- Centralized error handling and logging
- TypeScript migration for frontend
- Tag and category management interface

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

### Testing

```bash
# Full test suite with coverage
pytest

# Specific test file
pytest tests/test_prompt_data_service.py

# Skip performance tests
pytest -m "not performance"

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
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
| [`src/services/prompt_data_service.py`](src/services/prompt_data_service.py) | Core data operations |
| [`data/prompts_data.json`](data/prompts_data.json) | Main data store |
| [`tests/conftest.py`](tests/conftest.py) | Test fixtures |
| [`pyproject.toml`](pyproject.toml) | Project configuration |
| [`pytest.ini`](pytest.ini) | Test configuration |
| [`Dockerfile`](Dockerfile) | Container configuration |
| [`docker-compose.yml`](docker-compose.yml) | Docker Compose setup |
| [`CHANGELOG.md`](CHANGELOG.md) | Release history |

## Summary

PromptVault is a production-ready web application for managing AI prompts with comprehensive version control and backup systems. The architecture follows service-oriented design principles with clear separation of concerns. All changes should maintain the 85% test coverage threshold and follow established code patterns. The application supports Docker deployment and includes internationalization for four languages.

When contributing, prioritize code readability, maintainability, and test coverage. Follow the existing architectural patterns and ensure all public APIs have comprehensive documentation.
