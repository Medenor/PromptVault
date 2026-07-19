# PromptVault Test Suite Documentation

**Version:** 2.2
**Last Updated:** 2026-07-18
**Status:** Production Ready ✅

---

## Overview

The PromptVault test suite provides comprehensive coverage of the database-backed architecture, with both backend (pytest) and frontend (Vitest) suites enforcing a **minimum 85% coverage gate** in CI. Test counts and exact coverage percentages are intentionally not pinned in this document — they change with every PR. Run the suites locally (see Quick Start below) to see current numbers; treat their console output and `htmlcov/index.html` / `coverage/index.html` as the source of truth, not this file.

Frontend unit tests run with Vitest against TypeScript sources in `src/web/static/ts`, with coverage enforced via v8. Coverage reports are printed to the console and saved to `coverage/` when enabled.

## Quick Start

```bash
# Install backend test dependencies
pip install -e .[test]

# Run backend test suite (use python3 -m pytest to ensure correct version)
python3 -m pytest

# Run backend coverage report
python3 -m pytest --cov=src --cov-report=html:htmlcov

# View backend coverage report
open htmlcov/index.html  # macOS

# Frontend unit tests (TypeScript)
npm run test:unit

# Frontend coverage (Vitest + v8)
npm run test:unit:coverage
```

> **Important:** Always use `python3 -m pytest` instead of `pytest` directly to ensure the correct pytest version and dependencies are used. This avoids version conflicts with globally installed packages.

> **Tip:** You can also use `make test` to run both backend and frontend suites with their coverage gates in one command. See [docs/DEVELOPMENT.md](DEVELOPMENT.md) for all available `make` targets.

## Test Suite Gates

| Gate                  | Enforced by                                           | Threshold                                                                                  |
| --------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **Backend coverage**  | `pytest.ini` (`--cov-fail-under`)                     | 85% minimum, all source under `src/`                                                       |
| **Frontend coverage** | `vitest.config.ts` (`coverage.thresholds`)            | 85% minimum on lines/branches/functions/statements, scoped to `src/web/static/ts/utils/**` |
| **Pass rate**         | CI (any test failure fails the build)                 | 100% — no expected failures                                                                |
| **Execution time**    | Informal — both suites are designed to run in seconds | Backend and frontend suites should each complete in well under a minute locally            |

A test run reports the current test count and coverage percentage directly in its output — see Quick Start below to reproduce it. If you need historical figures for a specific date, check the CI logs or `git log -- docs/TESTING.md` rather than this file.

---

## Test Files

### 1. Repository Layer Tests

**File:** `tests/test_db_repositories.py`

#### PromptRepository

Tests for the main prompt repository covering:

- ✅ CRUD operations (create, read, update, delete)
- ✅ Text search (title, content, notes)
- ✅ Filtering (category, tags, favorites)
- ✅ Combined filters with multiple criteria
- ✅ Pagination and limits
- ✅ Tag management (add, remove, duplicates)
- ✅ Statistics and counting
- ✅ Cascade deletion of versions
- ✅ Case-insensitive search
- ✅ Relationship eager loading

**Key Tests:**

- `test_create_prompt` - Basic prompt creation
- `test_search_by_text` - Full-text search
- `test_search_combined_filters` - Multiple filter criteria
- `test_pagination` - Offset and limit
- `test_cascade_delete_versions` - Referential integrity

#### VersionRepository

Tests for version control repository:

- ✅ Version creation with complete snapshots
- ✅ Parent-child version relationships
- ✅ Version history retrieval and ordering
- ✅ Latest version lookup
- ✅ Version chain traversal
- ✅ Immutability of snapshots
- ✅ Version comparison
- ✅ Revert operations

**Key Tests:**

- `test_create_version` - Version snapshot creation
- `test_get_versions_for_prompt` - History retrieval
- `test_version_chain` - Parent-child linking
- `test_immutability` - Snapshots don't change

#### CategoryRepository

Tests for category management:

- ✅ CRUD operations
- ✅ Get-or-create pattern
- ✅ Usage count tracking
- ✅ Rename operations
- ✅ Delete-if-unused logic
- ✅ Unique constraint enforcement

#### TagRepository

Tests for tag management:

- ✅ CRUD operations
- ✅ Get-or-create (single and bulk)
- ✅ Usage count tracking
- ✅ Rename and merge operations
- ✅ Popular tags retrieval
- ✅ Bulk lookup by names

---

### 2. Service Layer Tests

**File:** `tests/test_db_services.py`

#### PromptDataService

Tests for the main data service:

- ✅ CRUD operations with automatic versioning
- ✅ Data loading and caching
- ✅ Search and filtering
- ✅ Category/tag auto-creation
- ✅ Data sanitization
- ✅ Backward compatibility
- ✅ Bulk operations

**Key Tests:**

- `test_add_new_prompt` - Prompt creation
- `test_add_prompt_creates_initial_version` - Auto-versioning
- `test_update_creates_version` - Version on update
- `test_delete_prompts_bulk` - Bulk operations
- `test_normalize_tags` - Data sanitization

#### BackupService

Tests for backup and restore:

- ✅ Backup creation with metadata
- ✅ Backup listing and sorting
- ✅ Restore with pre-restore backup
- ✅ Cleanup and retention policies
- ✅ Compression functionality
- ✅ Database import/export

**Key Tests:**

- `test_create_backup` - Basic backup
- `test_restore_backup` - Restore operation
- `test_cleanup_old_backups` - Retention policy
- `test_compress_old_backups` - Compression

---

### 3. Version Control Tests

**File:** `tests/test_version_system.py`

#### Version Creation

- ✅ Automatic version on create/update
- ✅ Complete metadata capture
- ✅ Unique UUID generation
- ✅ Parent-child linking
- ✅ Custom commit messages

#### Version History

- ✅ History retrieval and ordering (newest first)
- ✅ Pagination and limiting
- ✅ Latest version lookup
- ✅ Version chain traversal
- ✅ Isolation between prompts
- ✅ Empty history handling
- ✅ Cascade delete on prompt deletion

#### Version Comparison

- ✅ Diff generation between versions
- ✅ Changed field detection
- ✅ Tag additions/removals
- ✅ Category changes
- ✅ Content differences
- ✅ Error handling for missing versions

#### Version Revert

- ✅ Revert to previous versions
- ✅ New version creation on revert (preserves history)
- ✅ Complete field restoration
- ✅ Multiple sequential reverts
- ✅ Custom revert messages

#### Integration Tests

- ✅ Complete version workflows
- ✅ Immutability verification
- ✅ Timestamp preservation
- ✅ Author tracking
- ✅ Export functionality
- ✅ Version statistics

**Key Tests:**

- `test_complete_version_workflow` - End-to-end flow
- `test_version_immutability` - Old versions never change
- `test_revert_creates_new_version` - History preservation
- `test_version_comparison` - Diff generation

---

## Test Infrastructure

### Rate Limiting in Tests

**Automatic Disabling**: Rate limiting is automatically disabled during test execution to prevent 429 (Too Many Requests) responses from blocking tests.

**How it Works:**

- Session-scoped `setup_test_environment()` fixture sets `DISABLE_RATE_LIMITING=true`
- All `@limiter.limit()` decorators become no-ops during tests
- Tests can make unlimited API requests without throttling delays
- No test modifications needed - it's automatic

**File:** `tests/conftest.py` (lines 70-80)

```python
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up environment variables for all tests."""
    os.environ["DISABLE_RATE_LIMITING"] = "true"
    yield
```

This means you can:

- ✅ Make multiple login attempts in rapid succession
- ✅ Test password reset flows without rate limit delays
- ✅ Perform stress testing without throttling
- ✅ Debug authentication issues faster

### Fixtures (`tests/conftest.py`)

**30 comprehensive fixtures** providing:

#### Database Fixtures

- `test_db_engine` - In-memory SQLite with thread-safe configuration
- `test_db_session` - Session with automatic rollback
- `reset_database` - Smart database reset (autouse)

#### Model Fixtures

- `test_user` - Pre-configured User
- `test_category` - Pre-configured Category
- `test_tags` - List of Tags
- `test_prompt` - Prompt with relationships
- `test_prompt_with_versions` - Prompt with version history

#### Repository Fixtures

- `prompt_repo` - PromptRepository instance
- `version_repo` - VersionRepository instance
- `category_repo` - CategoryRepository instance
- `tag_repo` - TagRepository instance

#### Service Fixtures

- `db_data_service` - PromptDataService with in-memory DB
- `db_backup_service` - BackupService with temp directory
- `filter_service` - PromptFilterService
- `import_export_service` - PromptImportExportService
- `versioning_service` - PromptVersioningService
- And more...

#### Data Factory Fixtures

- `sample_prompt_data()` - Factory for prompt dicts
- `sample_version_data()` - Factory for version dicts
- `sample_csv_content` - CSV test data
- `sample_markdown_content` - Markdown test data

#### API Testing Fixtures

- `temp_data_dir` - Temporary directory with auto-cleanup
- `api_client` - FastAPI TestClient with database backend
- `api_client_with_data` - Pre-populated API client

### Configuration Files

#### `.coveragerc`

Configures coverage reporting and exclusions:

```ini
[run]
source = src
omit =
    # Legacy JSON-based services (deprecated)
    */services/prompt_data_service.py
    */services/backup_service.py
    # Database health checks
    */db/health.py
```

#### `pytest.ini`

Pytest configuration with coverage requirements:

```ini
[pytest]
addopts =
    --verbose
    --cov=src
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=85
```

---

## Running Tests

### Basic Usage

```bash
# Run all tests (always use python3 -m pytest)
python3 -m pytest

# Run specific test file
python3 -m pytest tests/test_db_repositories.py

# Run specific test class
python3 -m pytest tests/test_db_repositories.py::TestPromptRepository

# Run specific test
python3 -m pytest tests/test_db_repositories.py::TestPromptRepository::test_create_prompt

# Run with verbose output
python3 -m pytest -v

# Run with quiet output
python3 -m pytest -q
```

> **Note:** Using `python3 -m pytest` instead of `pytest` directly ensures you're using the project's installed version rather than a potentially incompatible global installation.

### Coverage Reports

```bash
# Generate HTML coverage report
python3 -m pytest --cov=src --cov-report=html:htmlcov

# Generate terminal coverage report
python3 -m pytest --cov=src --cov-report=term-missing

# Check coverage threshold
python3 -m pytest --cov=src --cov-fail-under=85
```

### Test Selection

```bash
# Run only repository tests
python3 -m pytest tests/test_db_repositories.py

# Run only service tests
python3 -m pytest tests/test_db_services.py

# Run only version control tests
python3 -m pytest tests/test_version_system.py

# Run tests matching pattern
python3 -m pytest -k "test_create"

# Run tests by marker
python3 -m pytest -m integration
```

### Debugging

```bash
# Run with print output
python3 -m pytest -s

# Stop on first failure
python3 -m pytest -x

# Show local variables on failure
python3 -m pytest -l

# Enter debugger on failure
python3 -m pytest --pdb

# Show full diff on assertions
python3 -m pytest --tb=long
```

---

## Coverage Analysis

### Current Coverage by Component

Per-component coverage percentages are not tracked in this document because they shift with nearly every PR. To see current numbers by file/component:

```bash
# Backend: full per-file breakdown with missing line numbers
python3 -m pytest --cov=src --cov-report=term-missing

# Backend: browsable HTML report
python3 -m pytest --cov=src --cov-report=html:htmlcov
open htmlcov/index.html

# Frontend: per-file breakdown (scoped to src/web/static/ts/utils/**)
npm run test:unit:coverage
```

### Known Accepted Gaps

Some coverage gaps are accepted rather than actively pursued, because closing them would require introducing new test-mocking patterns (or mocking framework internals) for low bug-risk code:

1. **Generic `except Exception` fallback handlers** - e.g. in `src/web/routers/auth.py`, the catch-all 500 branches sitting alongside specific, well-tested exception handlers. These require injecting an unexpected exception to hit, which the existing integration-style test suite for that router does not do.
2. **Legacy/deprecated compatibility code** - superseded implementations kept temporarily for backward compatibility.
3. **Database health checks** (`src/db/health.py`) - excluded from coverage by design (see `.coveragerc`).

If you add a new accepted gap, note it here with the reason so it isn't mistaken for an oversight in a future coverage review.

---

## Best Practices

### Writing New Tests

1. **Use Fixtures**

   ```python
   def test_create_prompt(prompt_repo, test_user, test_category):
       prompt = prompt_repo.create(
           title="Test",
           user_id=test_user.id,
           category_id=test_category.id
       )
       assert prompt.id is not None
   ```

2. **Test Isolation**
   - Each test gets a fresh database (in-memory SQLite)
   - Sessions automatically rollback after each test
   - No shared state between tests

3. **Clear Test Names**

   ```python
   def test_search_by_category_returns_filtered_results():
       # Test name describes exactly what is tested
   ```

4. **Arrange-Act-Assert Pattern**

   ```python
   def test_update_prompt_creates_version(db_data_service):
       # Arrange
       prompt_id = db_data_service.add_new_prompt({...})

       # Act
       db_data_service.update_prompt(prompt_id, {...})

       # Assert
       versions = db_data_service.get_prompt_versions(prompt_id)
       assert len(versions) == 2
   ```

5. **Test Edge Cases**
   - Empty inputs
   - Invalid IDs
   - Missing resources
   - Concurrent operations

### Common Patterns

#### Testing CRUD Operations

```python
def test_crud_flow(prompt_repo, test_user):
    # Create
    prompt = prompt_repo.create(title="Test", user_id=test_user.id)
    assert prompt.id is not None

    # Read
    retrieved = prompt_repo.get_by_id(prompt.id)
    assert retrieved.title == "Test"

    # Update
    updated = prompt_repo.update(prompt.id, title="Updated")
    assert updated.title == "Updated"

    # Delete
    result = prompt_repo.delete(prompt.id)
    assert result is True
```

#### Testing Relationships

```python
def test_prompt_with_tags(prompt_repo, test_tags):
    prompt = prompt_repo.create(title="Test", tags=test_tags[:2])
    assert len(prompt.tags) == 2
    assert test_tags[0] in prompt.tags
```

#### Testing Error Handling

```python
def test_get_nonexistent_prompt(prompt_repo):
    result = prompt_repo.get_by_id(99999)
    assert result is None
```

---

## Continuous Integration

### Forgejo Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.14'

      - name: Install dependencies
        run: |
          pip install -e .[test]

      - name: Run tests with coverage
        run: |
          python3 -m pytest --cov=src --cov-report=term --cov-report=xml

      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## Troubleshooting

### Common Issues

#### Error: "Client.**init**() got an unexpected keyword argument 'app'"

**Problem:** Version incompatibility between FastAPI, Starlette, and httpx packages.

**Solution:** Reinstall dependencies from pyproject.toml:

```bash
pip install -e .[test] --force-reinstall --no-cache-dir
```

Then always use `python3 -m pytest` instead of the `pytest` command.

#### Error: "ModuleNotFoundError: No module named 'pygments'"

**Problem:** System pytest is using a different Python environment.

**Solution:** Always use `python3 -m pytest` to run tests:

```bash
python3 -m pytest
```

This ensures pytest runs in the correct Python environment with all dependencies.

#### Tests Fail with "Database is locked"

**Solution:** The in-memory SQLite database should prevent this, but if it occurs:

```python
# Ensure proper session cleanup in conftest.py
yield session
session.rollback()
session.close()
```

#### Import Errors

**Solution:** Install in editable mode:

```bash
pip install -e .
```

#### Coverage Below 85%

**Solution:** Check which files are included:

```bash
python3 -m pytest --cov=src --cov-report=term-missing
```

#### Slow Tests

**Solution:** Tests should be fast (~10s). If slow:

- Check for external API calls
- Ensure using in-memory SQLite
- Verify no unnecessary file I/O

#### Version Conflicts with Global Packages

**Problem:** Your system has globally installed packages (mcp, google-genai, chromadb, etc.) that conflict with PromptVault's pinned versions.

**Solution:** These conflicts can be ignored if you're only running PromptVault tests. The warnings don't affect the test suite. Alternatively, use a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e .[test]
python3 -m pytest
```

---

## Migration from Old Test Suite

The test suite was completely rewritten. Key changes:

### What Changed

- ❌ **Removed:** All JSON-file based tests
- ❌ **Removed:** Duplicate repository tests
- ❌ **Removed:** Old backup system tests
- ❌ **Removed:** Performance tests (to be reimplemented)
- ✅ **Added:** Comprehensive database-backed tests
- ✅ **Added:** Modern fixture architecture
- ✅ **Added:** Thread-safe database handling

### What Stayed the Same

- ✅ API endpoint tests (updated for database)
- ✅ Import/export tests
- ✅ Validation tests
- ✅ Sanitization tests

---

## Future Improvements

### Planned Enhancements

1. Add performance benchmarks for large datasets (10k+ prompts)
2. Add concurrent operation stress tests
3. Add PostgreSQL-specific integration tests
4. Add mutation testing for test quality validation
5. Add property-based testing with Hypothesis

### Current Limitations

1. No tests for PostgreSQL-specific features
2. Limited concurrent operation testing
3. No chaos/fault injection testing

---

## Resources

- **Coverage Report:** `htmlcov/index.html` (generated after running tests)
- **Test Files:** `tests/test_*.py`
- **Fixtures:** `tests/conftest.py`
- **Configuration:** `pytest.ini`, `.coveragerc`
- **Documentation:** This file

---

## Summary

The PromptVault test suite provides:

- ✅ **≥85% code coverage**, enforced as a hard gate on both backend and frontend
- ✅ **100% pass rate** required — any failure fails CI
- ✅ **Fast execution** (both suites run in well under a minute locally)
- ✅ **Comprehensive coverage** of database operations
- ✅ **Modern infrastructure** with proper isolation
- ✅ **CI/CD ready** with no external dependencies

The test suite is **production-ready** and provides excellent confidence in the database-backed codebase.

### Running Tests - Quick Reference

```bash
# Always use python3 -m pytest (not pytest directly)
python3 -m pytest                    # Run all tests
python3 -m pytest -x                 # Stop on first failure
python3 -m pytest -v                 # Verbose output
python3 -m pytest tests/test_*.py    # Run specific test file
```
