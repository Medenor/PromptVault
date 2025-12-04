# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### ✨ New Features

- **Authentication & Authorization System**: Complete multi-user authentication with JWT tokens and role-based access control
  - **User Management**: Registration, login, logout, profile management, password changes
  - **Security Features**:
    - Argon2id password hashing (OWASP recommended, winner of Password Hashing Competition)
    - ES256 (ECDSA) JWT tokens with access and refresh token rotation
    - Account lockout after 5 failed attempts (15-minute duration)
    - Password reset flow with email-based tokens (1-hour expiry)
    - Rate limiting on authentication endpoints (slowapi + Redis)
    - Session management with max 5 concurrent sessions per user
    - Token family tracking for reuse detection and automatic revocation
  - **Role-Based Access Control (RBAC)**:
    - **Viewer**: Read-only access to own prompts
    - **Editor**: Full CRUD on own prompts, version control, import/export
    - **Admin**: All editor permissions + user management + system-wide access
  - **API Layer** (20 endpoints):
    - 8 public auth endpoints (register, login, refresh, logout, password reset)
    - 5 protected user endpoints (profile, change password, sessions)
    - 7 admin endpoints (user management, role assignment, session monitoring)
  - **Frontend Components**:
    - 7 HTML templates (login, register, forgot password, reset password, profile, admin users, admin sessions)
    - 5 JavaScript files (1,917 lines) with auth logic, password strength, session management
    - 2 CSS files (1,105 lines) with responsive authentication UI
    - 156 i18n keys in English (ready for FR, ES, DE translations)
    - **Logout Button**: [Added logout button to main navigation header for easier access](http://localhost:8003/auth/login)
  - **Database Schema**:
    - Enhanced `users` table with authentication fields (password_hash, email_verified, is_active, failed_login_attempts, locked_until)
    - `user_sessions` table for token family tracking and session management
    - `refresh_token_families` table for token rotation and reuse detection
    - `password_reset_tokens` table for secure password reset flow
  - **Comprehensive Testing**: 481 passing tests (99.8% coverage)
    - 440 existing tests (backend, services, repositories, API)
    - 41 new security integration tests covering all critical security features
  - **Production-Ready**:
    - OWASP compliance (Top 10 coverage, cheat sheet alignment)
    - Defense-in-depth security (password policies, token security, rate limiting)
    - Session cleanup job for expired tokens
    - Audit logging integration
  - **Documentation**: 3,000+ lines of comprehensive guides
    - Deployment guide with JWT key generation (`docs/AUTHENTICATION_DEPLOYMENT.md`)
    - API documentation for all 20 authentication endpoints (`docs/AUTHENTICATION_API.md`)
    - Security documentation covering OWASP compliance and threat mitigation (`docs/AUTHENTICATION_SECURITY.md`)
    - Admin setup script for creating first admin user (`scripts/create_admin_user.py`)

### 📚 Documentation

- **Authentication Deployment Guide** (`docs/AUTHENTICATION_DEPLOYMENT.md`): Complete setup instructions with JWT key generation and environment configuration
- **Authentication API Guide** (`docs/AUTHENTICATION_API.md`): All 20 endpoints documented with request/response examples
- **Authentication Security Guide** (`docs/AUTHENTICATION_SECURITY.md`): OWASP compliance, security features, threat mitigation, audit checklist
- **Authentication Specification** (`docs/SPECS/SPEC_AUTHENTICATION.md`): Updated status from DRAFT to IMPLEMENTED with completion date
- **Testing Checklist** (`docs/AUTHENTICATION_TEST_CHECKLIST.md`): Comprehensive manual testing checklist with 123 test cases
- **README.md**: Added Authentication section documenting user roles, security features, first-time setup, and authentication endpoints

### 🔧 Fixed

- **Pytest Warnings**: Eliminated all 80 pytest warnings for clean test output
  - Updated Pydantic V2 configuration in `src/db/config.py` - replaced deprecated class-based `Config` with `model_config = ConfigDict()`
  - Removed 10 deprecated `save_prompts()` calls (7 in `src/web/app.py`, 3 in tests) - no longer needed with database backend as transactions auto-persist
  - Fixed `data_file_path` deprecation in `src/web/app.py` - database now uses `DATABASE_URL` environment variable exclusively
  - Test results: 514/514 passing (100% pass rate), 86.12% coverage, 0 warnings

### 📚 Documentation

- **Testing Documentation**: Updated all documentation to reflect correct pytest usage
  - Updated `docs/TESTING.md` with `python3 -m pytest` commands and comprehensive troubleshooting section
  - Updated `docs/SPECS/SPEC_APP.md` with testing framework requirements
  - Updated `README.md` with correct test commands and metrics (514 tests, 86.46% coverage)
  - Updated `docs/AGENTS.md` with testing quick reference and explanation
  - Added troubleshooting for version conflicts and dependency issues

## [1.2.0]

### ✨ New Features

- **Database Migration (Phases 1-11)**: Complete transition from JSON file storage to relational database backend
  - **SQLAlchemy ORM**: Type-safe database operations with declarative models for Prompt, PromptVersion, Category, Tag, User, and Backup
  - **Repository Pattern**: Clean data access layer with specialized repositories (PromptRepository, VersionRepository, CategoryRepository, TagRepository)
  - **Database Support**: Production-ready PostgreSQL and development-friendly SQLite backends
  - **Alembic Migrations**: Version-controlled database schema evolution with `alembic upgrade/downgrade`
  - **Transaction Safety**: Context managers with automatic commit/rollback for data consistency
  - **Session Management**: Connection pooling for PostgreSQL with configurable pool size and timeout
  - **Migration Script**: Automated JSON to database migration with dry-run mode and verbose logging (`scripts/migrate_json_to_db.py`)
  - **Backward Compatibility**: 100% API compatibility maintained - existing endpoints return identical responses
  - **Database Backups**: SQLite file copy and PostgreSQL pg_dump integration with metadata tracking
  - **Comprehensive Testing**: 509 passing tests (86.90% coverage) for repositories, services, and integration workflows using in-memory SQLite
  - **Docker Integration**: Production-ready Docker Compose setup with PostgreSQL service and health checks
  - **Complete Documentation**: Deployment guide, migration guide, and technical specification (see `docs/DEPLOYMENT.md`, `docs/MIGRATION_GUIDE.md`, `docs/SPECS/SPEC_DATABASE.md`)
  - **Performance**: Indexed queries, eager loading to prevent N+1, pagination support for large datasets
  - **Security**: Parameterized queries (SQL injection prevention), SSL/TLS support, environment-based credentials

- **Test Suite Rewrite**: Complete rewrite of backend pytest suite from scratch for database-backed architecture
  - **Coverage**: 86.90% (exceeds 85% requirement by 1.9%)
  - **Test Count**: 509 passing tests out of 514 total (99% pass rate)
  - **Execution Time**: ~8 seconds for full suite (13x faster than before)
  - **New Test Files**:
    - `tests/test_db_repositories.py` (78 tests) - Repository layer with 89-100% coverage
    - `tests/test_db_services.py` (88 tests) - Service layer with 75-82% coverage
    - `tests/test_version_system.py` (48 tests) - Version control with 95-100% coverage
  - **Test Infrastructure**: Complete rewrite of `tests/conftest.py` with 30 comprehensive fixtures
  - **Database Testing**: In-memory SQLite with thread-safe handling for FastAPI TestClient
  - **Modern Patterns**: Repository pattern testing, service isolation, integration testing
  - **Coverage Configuration**: `.coveragerc` excludes legacy JSON services for accurate metrics
  - **Documentation**: Comprehensive test suite documentation in `docs/TESTING.md`
  - **Cleanup**: Removed 11 obsolete test files (1,800+ lines of outdated code)
  - **CI/CD Ready**: Fast, deterministic tests with no external dependencies
- **Bulk Prompt Deletion**: Multi-select prompts with checkboxes and delete multiple prompts in a single operation
  - **Multi-select UI**: Checkboxes on each prompt card with "Select All" functionality
  - **Bulk Actions Toolbar**: Shows selection count and delete button when prompts are selected
  - **Bulk Delete API**: `DELETE /api/prompts/bulk` endpoint accepting 1-1000 unique prompt IDs
  - **Automatic Backups**: Pre-deletion backup created automatically before bulk operations
  - **Validation**: Pydantic validation prevents duplicate IDs and enforces limits
  - **Confirmation Dialog**: Shows count of prompts to be deleted with safety warning
  - **Success Feedback**: Displays statistics on successful and failed deletions
  - **Internationalization**: Full translation support in English, French, Spanish, and German
  - **Comprehensive Testing**: 10 tests covering API endpoints, service layer, and validation
- **Input Sanitization & Validation**: comprehensive input validation and sanitization across all user-facing forms and API endpoints to prevent injection attacks, ensure data integrity, and improve user experience with clear validation feedback.
- **Frontend Telemetry Reporting**: `telemetry.js` now captures browser errors via `window.FrontendLogger`, pipes them into the `/api/logs/frontend` endpoint with rate limiting/sanitization, and exposes opt-out controls plus helper wrappers across the UI.

### 🔧 Fixed

- **Version Revert Category Loss**: Fixed bug where reverting a prompt to a previous version would lose the category, setting it to "categories.noCategory" - `_version_to_dict` now properly looks up category name from stored `category_id` in version snapshots
- **Version Timestamp Display**: Fixed "Invalid Date" display in production (PostgreSQL/Docker) by properly converting timezone-aware datetimes to UTC with ISO 8601 format
- **Bulk Delete Checkbox Position**: Moved bulk deletion checkbox to appear next to favorite button in prompt actions for better visual grouping
- **Route Ordering**: Fixed bulk delete endpoint route ordering - moved `/api/prompts/bulk` before `/api/prompts/{prompt_id}` to prevent "bulk" being interpreted as a prompt ID

### 📚 Documentation

- **Deployment Guide** (`docs/DEPLOYMENT.md`): Complete guide for Docker Compose, Docker, and manual deployment with PostgreSQL/SQLite setup
- **Migration Guide** (`docs/MIGRATION_GUIDE.md`): Step-by-step instructions for migrating from JSON to database storage with rollback procedures
- **Database Specification** (`docs/SPECS/SPEC_DATABASE.md`): Technical specification with requirements, architecture, schema, and acceptance criteria
- **Phase Documentation**: Detailed implementation reports for Phases 1-11 covering dependencies, models, configuration, migrations, repositories, services, backups, testing, and deployment

### 🔄 Changed

- **Python Version**: Minimum required Python version updated to 3.11+ (was 3.8+)
- **Data Storage**: Database backend (PostgreSQL/SQLite) is now the recommended storage method; JSON file storage marked as deprecated
- **Docker Configuration**: Enhanced Dockerfile with PostgreSQL client, non-root user, and integrated health checks
- **Docker Compose**: Complete rewrite with PostgreSQL service, health checks, and environment-based configuration

## [1.1.0] - 2025-10-30

### ✨ New Features

- **Search & Filter UI improved**: Moving search/filter block on top of windows to ease the use of this feature - [`01a40cf`]
- **Tags autocompletion**: Added tag autocomplete with usage counts for prompt tags in the web UI, leveraging the new get_tags_with_counts() service method - [`62644ec`]

### 🔧 Fixed

- **Tag normalization**: Trim tag whitespace during save to avoid duplicate entries with leading spaces - [`dd53bc3`]
- **Category sorting**: Preserve category order from configuration when saving prompts - [`b8ef70e`]
- **Search localization**: Replaced hardcoded English text in the search/filter experience, added matching translation keys in all locales, and stopped HTML entities from showing up in filter summaries.

## [1.0.0] - 2025-10-22

### Added

- **🚀 Web Application Architecture**: Complete transformation from PyQt6 desktop application to modern web-based application
  - **FastAPI Backend**: High-performance ASGI web framework replacing PyQt6 GUI
  - **REST API**: Full CRUD operations via RESTful endpoints (`/api/prompts`, `/api/categories`, `/api/tags`)
  - **Web UI**: Responsive HTML interface with Jinja2 templating
  - **Interactive Frontend**: JavaScript-based client-side functionality for seamless user experience
  - **Real-time Updates**: Dynamic prompt list updates without page refreshes

- **🐳 Docker Containerization**: Production-ready deployment with Docker
  - **Dockerfile**: Multi-stage build with Python slim image and GCC for dependencies
  - **Docker Compose**: One-command deployment with volume mounting for data persistence
  - **Volume Management**: Secure data storage outside container (`./data:/app/data`)
  - **Health Checks**: Built-in container health monitoring

- **🔒 Security Enhancements**: Enterprise-grade security practices
  - **Data Isolation**: Personal data excluded from Docker images (no sensitive data in containers)
  - **Volume Mounting**: Data stored on host filesystem with proper access controls
  - **Clean Builds**: `--no-cache` builds ensure no residual data in images

- **📱 Responsive Web Design**: Modern, accessible user interface
  - **Mobile-First**: Works seamlessly on desktop, tablet, and mobile devices
  - **CSS Framework**: Clean, maintainable stylesheets with theming support
  - **Progressive Enhancement**: Graceful degradation for older browsers

- **🔧 Developer Experience**: Improved development workflow
  - **Hot Reload**: Development server with automatic code reloading
  - **Debug Logging**: Comprehensive client and server-side logging for troubleshooting
  - **Modular Architecture**: Clean separation between web, services, and legacy components

### Changed

- **Breaking Change**: Desktop application moved to legacy status
  - Original PyQt6 application preserved in `src/main.py` and `src/ui/`
  - Desktop version marked as deprecated, web version now primary
  - Data format remains compatible between versions

- **Project Structure**: Web-first architecture with clear separation
  - `src/web/` promoted to primary application module
  - `src/services/` shared between web and desktop versions
  - Legacy desktop components moved to `src/ui/` and `src/main.py`

- **Dependencies**: Complete technology stack modernization
  - **Removed**: PyQt6, Qt dependencies (desktop GUI framework)
  - **Added**: FastAPI, Uvicorn, Jinja2, python-multipart (web framework)
  - **Updated**: Python packaging to modern `pyproject.toml` standards

### Removed

- **PyQt6 Dependencies**: Desktop GUI framework completely removed from web deployment
- **Legacy UI Components**: Desktop-specific widgets and dialogs deprecated
- **Personal Data in Images**: Sensitive data no longer included in Docker containers

### Fixed

- **Data Persistence**: Fixed critical bug where prompt changes weren't saved to disk
- **API Endpoints**: Resolved type conversion issues between string URLs and integer IDs
- **Template Rendering**: Fixed Jinja2 template errors with incorrect field references
- **Form Validation**: Improved client-side validation and error handling

### Dependencies

- **Added**:
  - `fastapi` - Modern web framework
  - `uvicorn[standard]` - ASGI server with hot reload
  - `jinja2` - Template engine
  - `python-multipart` - Form data handling
  - `aiofiles` - Async file operations
- **Removed**:
  - `PyQt6` and all Qt-related packages
  - `PyQt6-Qt6` system dependencies

### Migration Guide

**For Existing Users:**

1. **Data Preservation**: Your existing `data/prompts_data.json` file is fully compatible
2. **Web Migration**: Use `docker-compose up --build` for new web deployment
3. **Legacy Access**: Desktop version still available via `PYTHONPATH=. python -m src.main`

**For Developers:**

- Web application runs on `http://localhost:8001` (Docker) or `http://localhost:8003` (development)
- API endpoints available at `/api/*` routes
- All original functionality preserved with improved performance

## [0.4.0] - 2025-10-17

### Added

- **Comprehensive Data Backup System**: Implemented a robust backup and restoration system to prevent data loss
  - **BackupService**: New service class providing complete backup functionality with metadata tracking
  - **Automatic Backups**: Pre-operation backups created before risky operations (import, bulk delete, bulk update)
  - **Manual Backups**: User-initiated backups available through File menu ("Create Backup", "Backup & Restore")
  - **Backup Management Dialog**: Full-featured interface for viewing, restoring, and managing all backups
  - **Smart Retention**: Configurable cleanup policies to automatically remove old backups (default: 30 days)
  - **Compression**: Automatic gzip compression of older backups (default: after 7 days) to save disk space
  - **Safety Features**: Pre-restore backups ensure no data loss during restoration operations
  - **Complete Metadata**: Every backup includes comprehensive information (timestamp, size, prompt count, author)
  - **Backup Statistics**: Real-time monitoring of backup status and storage usage
  - **Cross-Platform**: Works seamlessly on Windows, macOS, and Linux

### Dependencies

- Added `humanize` library for user-friendly timestamp formatting in backup dialogs

### Changed

- Migrated packaging to `pyproject.toml` with PEP 621 metadata and setuptools backend.
- Updated installation instructions to use `pip install .` and removed the redundant `requirements.txt`.

## [0.3.0] - 2025-09-16

### Added

- **Customizable Layout**: Implemented resizable panels and layout persistence.
  - The main application window now features a flexible layout with three resizable panels: Categories/Tags, Prompt List, and Prompt Editor.
  - Utilized `QSplitter` for dynamic resizing of these panels.
  - Integrated `QSettings` to save and restore the user's preferred panel sizes and window state across sessions.

## [0.2.0] - 2025-09-12

### Added

- Internationalization support: Added translation files for multiple languages (French, German, Spanish, English) and a build script for generating translation binaries.

## [0.1.1] - 2025-09-12

### Changed

- **Project Structure Reorganization**: Restructured the codebase for better organization and maintainability
  - Created `src/` directory as main source code container
  - Moved UI components to `src/ui/` (dialogs, widgets)
  - Moved business logic to `src/services/` (data, filter, versioning, import/export services)
  - Consolidated assets in `assets/` directory (images, themes)
  - Moved data files to `data/` directory
  - Added `__init__.py` files to create proper Python packages
  - Updated all import statements to use relative imports
  - Updated README.md with new project structure and run instructions
- Changed application launch command to `PYTHONPATH=. python -m src.main`
- Extracted duplicate prompt handling logic into `_handle_duplicate_prompt` method for improved clarity and maintainability.
- **Asset Path Fixes**:
  - Corrected image paths in `assets/themes/dark.qss` and `assets/themes/light.qss` to use `assets:images/` aliases.
  - Added `assets` as a search path in `src/main.py` to ensure proper loading of resources referenced in QSS files.
- **Bug Fix: Revert Functionality**:
  - Addressed a `NameError` in `src/ui/version_history_dialog.py` by adding `QLineEdit` to its imports.
  - Fixed an issue where the `prompt_id` was not correctly passed to `VersionHistoryDialog` from `src/ui/prompt_manager_widget.py`, resolving the "Could not find prompt with ID XXXXX to revert" error.

## [0.1.0] - 2025-09-11

### Added

- Dedicated service classes for improved modularity:
  - `PromptDataService` for data operations
  - `PromptFilterService` for filtering/searching
  - `PromptVersioningService` for version control
  - `PromptImportExportService` for import/export functionality
- Comprehensive test suite for verifying refactored code functionality
- Documentation of new architecture in README.md

### Changed

- Refactored `PromptManager` to use new service classes
- Made data file path configurable
- Improved code maintainability and extensibility through modular design
- Updated version identifier description in README.md

### Notes

- Initial release with refactored architecture
- Published app on various platforms
