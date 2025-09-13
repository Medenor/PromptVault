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
[![Visual Studio Code](https://custom-icon-badges.demolab.com/badge/Visual%20Studio%20Code-0078d7.svg?logo=vsc&logoColor=white)](#)
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

PromptVault is a prompt management application designed to help users easily organize, store, and retrieve their prompts for various AI applications, software development, content marketing, and much more. Whether you are a developer, writer, marketer, or simply a user of AI-based tools, PromptVault allows you to centralize your prompts and improve your productivity.

### Built With

*   [Python](https://www.python.org/)
*   [PyQt6](https://riverbankcomputing.com/software/pyqt/)

### Version Control

PromptVault includes a robust, Git-like version control system for all prompts, ensuring full traceability and a clear history of changes. Key features include:

*   **Unique Version Identifiers**: Each prompt version is assigned an UUID.
*   **Detailed Metadata**: Every version tracks essential metadata such as timestamp, author, and a mandatory commit message.
*   **Version History View**: A dedicated dialog allows users to browse a prompt's complete version history, displaying each commit with its details.
*   **Diff Visualization**: Easily compare any two versions to see precise changes in prompt content, title, notes, categories, and tags.
*   **Revert Functionality**: Users can revert a prompt to any previous version, which creates a new commit reflecting the reverted state.

### Architecture

PromptVault follows a modular architecture with dedicated service classes for different functionalities:

*   **PromptDataService**: Handles all data-related operations including loading, saving, and migration of prompt data
*   **PromptFilterService**: Manages filtering and searching logic for prompts
*   **PromptVersioningService**: Handles version control operations for prompts
*   **PromptImportExportService**: Manages import and export operations in various formats (CSV, Markdown)

This modular design improves code maintainability, testability, and extensibility.

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

*   Python 3.6+

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://codeberg.org/medenor/promptvault.git
    cd PromptVault
    ```

2.  **Create a virtual environment** (recommended):
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

To launch the application, run the main module from the project root:

```bash
PYTHONPATH=. python -m src.main
```

The application will open, allowing you to start managing your prompts.

### Internationalization

PromptVault supports multiple languages. The application will automatically detect your system language, but you can also change languages from the View → Language menu.

#### For Developers

**Translation Files:**
- `.ts` files (source): Human-readable XML files containing translatable strings
- `.qm` files (compiled): Binary files used by Qt at runtime

**Building Translations:**
Before packaging or distribution, compile the translation files:

```bash
python build_translations.py
```

This will generate `.qm` files from all `.ts` files in the `i18n/` directory.

**Note:** Only `.ts` files are tracked in version control. `.qm` files are generated during build and are ignored by git.

### Project Structure

The project follows a modular structure:

- `src/`: Main source code directory
  - `src/main.py`: Application entry point
  - `src/ui/`: User interface components (dialogs, widgets)
  - `src/services/`: Business logic and data services
- `assets/`: Static assets (images, themes)
- `data/`: Application data files
- `docs/`: Documentation and screenshots
- `i18n/`: Translation files

## Roadmap

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

*   Repository files templates provided by [dec0dOS/amazing-github-template](https://github.com/dec0dOS/amazing-github-template)
*   Icons by [icons8.com](https://icons8.com)
