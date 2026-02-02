"""
SetupConsole - Rich-based console utilities for setup scripts.

This module provides a consistent, visually appealing interface for all setup
scripts using the Rich library for terminal formatting and styling.
"""

from contextlib import contextmanager
from typing import List, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.status import Status
from rich.text import Text


class SetupConsole:
    """
    A comprehensive console utility class for setup scripts.

    Provides consistent styling and formatting for headers, messages, prompts,
    tables, and progress indicators using the Rich library.

    Attributes:
        console: The Rich Console instance used for all output operations.
    """

    def __init__(self):
        """Initialize the SetupConsole with a Rich Console instance."""
        self.console = Console()

    def header(self, title: str, subtitle: Optional[str] = None) -> None:
        """
        Display a prominent header panel.

        Creates a visually distinct header using Rich Panel with the title
        and optional subtitle. Useful for marking the beginning of setup
        scripts or major sections.

        Args:
            title: The main header text to display.
            subtitle: Optional subtitle text displayed below the title.

        Example:
            console.header("PromptVault Setup", "Configuring your installation")
        """
        if subtitle:
            content = f"[bold white]{title}[/bold white]\n[dim]{subtitle}[/dim]"
        else:
            content = f"[bold white]{title}[/bold white]"

        panel = Panel(
            content,
            border_style="blue",
            padding=(1, 2),
        )
        self.console.print(panel)
        self.console.print()

    def step(self, number: int, total: int, description: str) -> None:
        """
        Display a step indicator with progress.

        Shows the current step number out of total steps with a description,
        useful for multi-step setup processes.

        Args:
            number: The current step number (1-indexed).
            total: The total number of steps.
            description: Description of what this step does.

        Example:
            console.step(1, 5, "Generating JWT keys")
            # Output: [1/5] Generating JWT keys
        """
        step_text = Text()
        step_text.append(f"[{number}/{total}] ", style="bold cyan")
        step_text.append(description, style="white")
        self.console.print(step_text)

    def success(self, message: str) -> None:
        """
        Display a success message with a green checkmark.

        Args:
            message: The success message to display.

        Example:
            console.success("Database initialized successfully")
        """
        self.console.print(f"[green]✓[/green] {message}")

    def error(self, message: str) -> None:
        """
        Display an error message with a red X.

        Args:
            message: The error message to display.

        Example:
            console.error("Failed to connect to database")
        """
        self.console.print(f"[red]✗[/red] {message}", style="red")

    def warning(self, message: str) -> None:
        """
        Display a warning message with a yellow warning icon.

        Args:
            message: The warning message to display.

        Example:
            console.warning("Using default configuration values")
        """
        self.console.print(f"[yellow]⚠[/yellow] {message}", style="yellow")

    def info(self, message: str) -> None:
        """
        Display an informational message with a blue info icon.

        Args:
            message: The informational message to display.

        Example:
            console.info("Configuration file saved to /etc/promptvault")
        """
        self.console.print(f"[blue]ℹ[/blue] {message}")

    def prompt(
        self,
        message: str,
        default: Optional[str] = None,
        password: bool = False
    ) -> str:
        """
        Get user input with an optional default value.

        Uses Rich Prompt for styled user input. Supports password mode
        for sensitive input (characters will be hidden).

        Args:
            message: The prompt message to display to the user.
            default: Optional default value shown in brackets.
            password: If True, input will be hidden (for passwords).

        Returns:
            The user's input as a string.

        Example:
            name = console.prompt("Enter your name", default="admin")
            password = console.prompt("Enter password", password=True)
        """
        return Prompt.ask(
            message,
            default=default,
            password=password,
            console=self.console
        )

    def confirm(self, message: str, default: bool = False) -> bool:
        """
        Get yes/no confirmation from the user.

        Uses Rich Confirm for styled yes/no prompts.

        Args:
            message: The confirmation question to display.
            default: The default response if user just presses Enter.

        Returns:
            True if user confirms (yes), False otherwise (no).

        Example:
            if console.confirm("Do you want to continue?", default=True):
                # proceed with action
        """
        return Confirm.ask(
            message,
            default=default,
            console=self.console
        )

    def select(self, message: str, choices: List[str]) -> str:
        """
        Get selection from a list of choices.

        Displays available choices and prompts user to select one.
        The user must enter one of the provided choices exactly.

        Args:
            message: The prompt message to display.
            choices: List of valid string choices.

        Returns:
            The user's selected choice.

        Example:
            db = console.select(
                "Select database",
                choices=["postgresql", "sqlite"]
            )
        """
        # Display choices
        self.console.print(f"\n{message}")
        for i, choice in enumerate(choices, 1):
            self.console.print(f"  {i}. {choice}")
        self.console.print()

        # Get selection
        return Prompt.ask(
            "Enter your choice",
            choices=choices,
            console=self.console
        )

    def table(
        self,
        title: str,
        headers: List[str],
        rows: List[List[str]]
    ) -> None:
        """
        Display a formatted table.

        Creates a Rich Table with the specified title, headers, and rows.
        Useful for displaying configuration summaries or status information.

        Args:
            title: The table title displayed above the table.
            headers: List of column header strings.
            rows: List of rows, where each row is a list of cell values.

        Example:
            console.table(
                "Configuration Summary",
                headers=["Setting", "Value"],
                rows=[
                    ["Database", "PostgreSQL"],
                    ["Port", "5432"],
                    ["Host", "localhost"]
                ]
            )
        """
        table = Table(title=title, show_header=True, header_style="bold cyan")

        # Add columns
        for header in headers:
            table.add_column(header)

        # Add rows
        for row in rows:
            table.add_row(*row)

        self.console.print(table)
        self.console.print()

    @contextmanager
    def spinner(self, message: str):
        """
        Context manager for displaying a spinner during long operations.

        Shows an animated spinner with a status message while code
        executes within the context.

        Args:
            message: The status message to display alongside the spinner.

        Yields:
            The Status object (can be used to update the message).

        Example:
            with console.spinner("Installing dependencies..."):
                # perform long operation
                install_packages()
        """
        status = Status(message, console=self.console, spinner="dots")
        status.start()
        try:
            yield status
        finally:
            status.stop()

    @contextmanager
    def progress(self, description: str, total: int):
        """
        Context manager for displaying a progress bar.

        Shows a progress bar that can be updated as work progresses.
        The progress bar includes a spinner, description, bar, and percentage.

        Args:
            description: Description of the task being performed.
            total: Total number of units of work to complete.

        Yields:
            A tuple of (Progress object, Task ID) for updating progress.

        Example:
            with console.progress("Processing files", total=100) as (progress, task):
                for i in range(100):
                    # do work
                    progress.update(task, advance=1)
        """
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
        progress.start()
        try:
            task = progress.add_task(description, total=total)
            yield progress, task
        finally:
            progress.stop()
