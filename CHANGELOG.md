# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- Web application runs on `http://localhost:8001` (Docker) or `http://localhost:8000` (development)
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
