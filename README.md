<h1 align="center">
  <a href="https://codeberg.org/medenor/promptvault">
    <img src="docs/images/promptvault_logo.svg" alt="Logo" width="250" height="250">
  </a>
</h1>

<div align="center">
  PromptVault
  <br />
  <a href="#about"><strong>Explore the screenshots »</strong></a>
  <br />
  <br />
  <a href="https://codeberg.org/medenor/promptvault/issues/new?assignees=&labels=bug&template=01_BUG_REPORT.md&title=bug%3A+">Report a Bug</a>
  ·
  <a href="https://codeberg.org/medenor/promptvault/issues/new?assignees=&labels=enhancement&template=02_FEATURE_REQUEST.md&title=feat%3A+">Request a Feature</a>
  ·
  <a href="https://codeberg.org/medenor/promptvault/issues/new?assignees=&labels=question&template=04_SUPPORT_QUESTION.md&title=support%3A+">Ask a Question</a>
</div>

<div align="center">
<br />

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Pull Requests welcome](https://img.shields.io/badge/PRs-welcome-ff69b4.svg?style=flat-square)](https://codeberg.org/medenor/promptvault/issues)
[![Vibe-coded with love by Medenor](https://img.shields.io/badge/%3C%2F%3E%20with%20%E2%99%A5%20by-Medenor-ff1414.svg?style=flat-square)](https://codeberg.org/medenor)
[![Switched to Codeberg](https://img.shields.io/badge/Switched_to-Codeberg-blue?style=flat-square&logo=codeberg&logoColor=white)](https://codeberg.org/medenor/promptvault/)
[![Visual Studio Code](https://custom-icon-badges.demolab.com/badge/Visual%20Studio%20Code-0078d7.svg?logo=vsc&logoColor=white)](https://code.visualstudio.com)
</div>

<details open="open">
<summary>Table of Contents</summary>

- [About](#about)
  - [Built With](#built-with)
  - [Version Control](#version-control)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
- [Usage](#usage)
- [Roadmap](#roadmap)
- [Support](#support)
- [Project assistance](#project-assistance)
- [Contributing](#contributing)
- [Authors & contributors](#authors--contributors)
- [Security](#security)
- [License](#license)
- [Acknowledgements](#acknowledgements)

</details>

---

## About

PromptVault is a modern web-based prompt management application designed to help users easily organize, store, and retrieve their prompts for various AI applications, software development, content marketing, and much more. Whether you are a developer, writer, marketer, or simply a user of AI-based tools, PromptVault allows you to centralize your prompts and improve your productivity through a responsive web interface accessible from any browser.

### Built With

- [Python](https://www.python.org/)
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Uvicorn](https://www.uvicorn.org/) - High-performance ASGI server
- [Jinja2](https://jinja.palletsprojects.com/) - Template engine
- [TypeScript](https://www.typescriptlang.org/) - Type-safe JavaScript for frontend
- [Docker](https://www.docker.com/) - Containerization platform

### Version Control

PromptVault includes a robust, Git-like version control system for all prompts, ensuring full traceability and a clear history of changes. Key features include:

- **Unique Version Identifiers**: Each prompt version is assigned an UUID.
- **Detailed Metadata**: Every version tracks essential metadata such as timestamp, author, and a mandatory commit message.
- **Version History View**: A dedicated dialog allows users to browse a prompt's complete version history, displaying each commit with its details.
- **Diff Visualization**: Easily compare any two versions to see precise changes in prompt content, title, notes, categories, and tags.
- **Revert Functionality**: Users can revert a prompt to any previous version, which creates a new commit reflecting the reverted state.

### Architecture

PromptVault follows a modular architecture with dedicated service classes for different functionalities:

- **PromptDataService**: Handles all data-related operations including loading, saving, and migration of prompt data
- **PromptFilterService**: Manages filtering and searching logic for prompts
- **PromptVersioningService**: Handles version control operations for prompts
- **PromptImportExportService**: Manages import and export operations in various formats (CSV, Markdown)
- **BackupService**: Provides comprehensive data backup and restoration capabilities with automatic pre-operation backups

This modular design improves code maintainability, testability, and extensibility.

### Data Backup System

PromptVault includes a robust backup system to prevent data loss and enable easy recovery:

- **Automatic Backups**: Pre-operation backups are created automatically before risky operations (import, bulk delete, bulk update)
- **Manual Backups**: Users can create manual backups at any time through the File menu
- **Backup Management**: Full-featured backup dialog for viewing, restoring, and managing all backups
- **Smart Retention**: Configurable cleanup policies to remove old backups and save disk space
- **Compression**: Automatic compression of older backups to optimize storage usage
- **Safety Features**: Pre-restore backups ensure no data loss during restoration operations
- **Complete Metadata**: Every backup includes comprehensive metadata (timestamp, size, prompt count, author)

<details>
<summary>Screenshots</summary>
<br>

| Main Window | Prompt Editor Panel | Version History |
| :---: | :---: | :---: |
| <img src="docs/images/promptvault_main_window.jpg" title="Main Window" width="100%"> | <img src="docs/images/promptvault_prompt_edit_panel.jpg" title="Prompt Editor Panel" width="100%"> | <img src="docs/images/promptvault_version_history.jpg" title="Version History" width="100%"> |

| Manage Tags | Export Prompts |
| :---: | :---: |
| <img src="docs/images/promptvault_manage_tags.jpg" title="Manage Tags" width="100%"> | <img src="docs/images/promptvault_export.jpg" title="Export Prompts" width="100%"> |

</details>

## Getting Started

### Prerequisites

- Python 3.8+
- Docker (recommended for production deployment)

### Quick Start with Docker

The fastest way to get started is using Docker:

```bash
git clone https://codeberg.org/medenor/promptvault.git
cd PromptVault
docker-compose up --build
```

Then open your browser to `http://localhost:8001`

### Manual Installation

1. **Clone the repository**:

    ```bash
    git clone https://codeberg.org/medenor/promptvault.git
    cd PromptVault
    ```

2. **Create a virtual environment** (recommended):

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3. **Install PromptVault and its dependencies**:

    ```bash
    pip install .
    ```

    For development work you can install in editable mode:

    ```bash
    pip install -e .
    ```

## Usage

### Web Application (Recommended)

PromptVault is primarily a web-based application that runs in your browser and can be deployed as a Docker container.

#### Running with Docker (Production)

```bash
docker-compose up --build
```

Open your browser and go to `http://localhost:8001`

#### Running Locally (Development)

1. Install dependencies:
```bash
pip install -e .
```

2. Run the web application:
```bash
python run_web.py
```

3. Open your browser and go to `http://localhost:8000`

### Desktop Application (Legacy)

The original desktop application is still available but is now considered legacy. To launch it:

```bash
PYTHONPATH=. python -m src.main
```

**Note:** The desktop version uses PyQt6 and may require additional system dependencies. The web version is recommended for all new deployments.

### Features

Both versions provide the same core functionality:

- **Prompt Management**: Create, edit, delete, and organize prompts
- **Version Control**: Git-like versioning system for all prompts
- **Categories & Tags**: Organize prompts with categories and tags
- **Search & Filter**: Find prompts quickly with advanced filtering
- **Import/Export**: Support for CSV and Markdown formats
- **Backup System**: Automatic and manual data backups
- **Responsive Design**: Works on desktop and mobile devices

Your data is stored persistently in the `data/` directory and is compatible between web and desktop versions.

### Internationalization

PromptVault supports multiple languages. The application will automatically detect your system language, but you can also change languages from the View → Language menu.

#### For Developers

**Translation Files:**

- `.ts` files (source): Human-readable XML files containing translatable strings
- `.qm` files (compiled): Binary files used by Qt at runtime

**Building Translations:**
Before packaging or distribution, compile the translation files:

```bash
python3 i18n/build_translations.py
```

This will generate `.qm` files from all `.ts` files in the `i18n/` directory.

**Note:** Only `.ts` files are tracked in version control. `.qm` files are generated during build and are ignored by git.

### Frontend Development

The web frontend has been migrated from vanilla JavaScript to TypeScript for improved type safety and developer experience.

#### Frontend Technology Stack

- **TypeScript**: Type-safe JavaScript with compile-time error checking
- **ES2018**: Modern JavaScript features for browser compatibility
- **i18next**: Internationalization framework for multi-language support
- **Modular Architecture**: Separate modules for main app and import/export functionality

#### Frontend Build Process

The frontend uses a TypeScript build system with the following structure:

```
src/web/static/
├── js/                    # TypeScript source files
│   ├── types.ts          # Type definitions
│   ├── app.ts            # Main application logic
│   └── import_export.ts  # Import/export functionality
├── dist/                 # Compiled JavaScript (generated)
│   ├── app.js           # Compiled main app
│   ├── import_export.js # Compiled import/export
│   └── *.js.map         # Source maps for debugging
├── package.json         # Node.js dependencies and scripts
├── tsconfig.json        # TypeScript configuration
└── README.md           # Frontend development documentation
```

#### Building the Frontend

For development with automatic recompilation:

```bash
cd src/web/static
npm run dev
```

For production builds:

```bash
cd src/web/static
npm run build
```

The compiled JavaScript files are automatically served by the FastAPI application and are referenced in the HTML templates.

### Project Structure

The project follows a modular structure with web-first architecture:

- `src/`: Main source code directory
  - `src/web/`: **Primary web application module**
    - `src/web/app.py`: FastAPI application and REST API routes
    - `src/web/templates/`: Jinja2 HTML templates
    - `src/web/static/`: CSS stylesheets, TypeScript source, and compiled JavaScript
  - `src/services/`: Business logic and data services (shared between web/desktop)
  - `src/main.py`: Legacy desktop application entry point
  - `src/ui/`: Legacy desktop UI components (dialogs, widgets)
- `assets/`: Static assets (images, themes)
- `data/`: Application data files (JSON storage, mounted as Docker volume)
- `docs/`: Documentation and screenshots
- `i18n/`: Translation files (Qt-based, legacy)
- `run_web.py`: Web application startup script
- `Dockerfile`: Docker container configuration
- `docker-compose.yml`: Docker Compose configuration for easy deployment

## Roadmap

- [ ] **Input Validation & Sanitization:** Ensures data integrity and prevents injection attacks by validating all user inputs.
- [x] **Data Backup System:** Automatically creates backups to prevent data loss and enable recovery from corruption.
- [ ] **Error Handling & Logging:** Implements centralized logging and comprehensive error handling for better debugging and user experience.
- [ ] **Unit Tests:** Establishes comprehensive test coverage for core functionality to catch bugs early and enable safe refactoring.

See the [open issues](https://codeberg.org/medenor/promptvault/issues) for a list of proposed features (and known issues).

## Support

Reach out to the maintainer at one of the following places:

- [Codeberg issues](https://codeberg.org/medenor/promptvault/issues)
- Contact options listed on [this Codeberg profile](https://codeberg.org/medenor)

## Project assistance

If you want to say **thank you** or/and support active development of PromptVault:

- Add a [Star](https://codeberg.org/medenor/promptvault) to the project.
- Write interesting articles about the project on [Dev.to](https://dev.to/), [Medium](https://medium.com/) or your personal blog.

Together, we can make PromptVault **better**!

## Contributing

First off, thanks for taking the time to contribute! Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make will benefit everybody else and are **greatly appreciated**.

Please read our contribution guidelines, and thank you for being involved!

## Authors & contributors

The original setup of this repository is by [Medenor](https://codeberg.org/medenor).

For a full list of all authors and contributors, see [the contributors page](https://codeberg.org/medenor/promptvault/graphs/contributors).

## Security

PromptVault follows good practices of security, but 100% security cannot be assured.
PromptVault is provided **"as is"** without any **warranty**. Use at your own risk.

## License

This project is licensed under the **GNU AGPLv3 license**.

See [LICENSE](LICENSE) for more information.

## Acknowledgements

- Repository files templates provided by [dec0dOS/amazing-github-template](https://github.com/dec0dOS/amazing-github-template)
