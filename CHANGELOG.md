# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2025-09-16

### Added
- **Customizable Layout**: Implemented resizable panels and layout persistence.
  * The main application window now features a flexible layout with three resizable panels: Categories/Tags, Prompt List, and Prompt Editor.
  * Utilized `QSplitter` for dynamic resizing of these panels.
  * Integrated `QSettings` to save and restore the user's preferred panel sizes and window state across sessions.

## [0.2.0] - 2025-09-12

### Added
- Internationalization support: Added translation files for multiple languages (French, German, Spanish, English) and a build script for generating translation binaries.

## [0.1.1] - 2025-09-12

### Changed
- **Project Structure Reorganization**: Restructured the codebase for better organization and maintainability
  * Created `src/` directory as main source code container
  * Moved UI components to `src/ui/` (dialogs, widgets)
  * Moved business logic to `src/services/` (data, filter, versioning, import/export services)
  * Consolidated assets in `assets/` directory (images, themes)
  * Moved data files to `data/` directory
  * Added `__init__.py` files to create proper Python packages
  * Updated all import statements to use relative imports
  * Updated README.md with new project structure and run instructions
- Changed application launch command to `PYTHONPATH=. python -m src.main`
- Extracted duplicate prompt handling logic into `_handle_duplicate_prompt` method for improved clarity and maintainability.
- **Asset Path Fixes**:
  * Corrected image paths in `assets/themes/dark.qss` and `assets/themes/light.qss` to use `assets:images/` aliases.
  * Added `assets` as a search path in `src/main.py` to ensure proper loading of resources referenced in QSS files.
- **Bug Fix: Revert Functionality**:
  * Addressed a `NameError` in `src/ui/version_history_dialog.py` by adding `QLineEdit` to its imports.
  * Fixed an issue where the `prompt_id` was not correctly passed to `VersionHistoryDialog` from `src/ui/prompt_manager_widget.py`, resolving the "Could not find prompt with ID XXXXX to revert" error.

## [0.1.0] - 2025-09-11

### Added
- Dedicated service classes for improved modularity:
  * `PromptDataService` for data operations
  * `PromptFilterService` for filtering/searching
  * `PromptVersioningService` for version control
  * `PromptImportExportService` for import/export functionality
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
