# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-09

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
