# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for SetupConsole utility class."""

from unittest.mock import MagicMock, Mock, patch

from scripts.setup.utils.console import SetupConsole


class TestSetupConsoleInit:
    """Test SetupConsole initialization."""

    def test_initialization(self):
        """Test that SetupConsole initializes with a Rich Console instance."""
        console = SetupConsole()
        assert console.console is not None
        assert hasattr(console.console, "print")


class TestSetupConsoleHeader:
    """Test header display method."""

    def test_header_with_subtitle(self):
        """Test header with title and subtitle."""
        console = SetupConsole()
        console.console = Mock()

        console.header("Test Title", "Test Subtitle")

        # Should call print twice (panel + empty line)
        assert console.console.print.call_count == 2

        # First call should be the panel
        first_call = console.console.print.call_args_list[0]
        panel_arg = first_call[0][0]
        assert hasattr(panel_arg, "renderable")

    def test_header_without_subtitle(self):
        """Test header with title only."""
        console = SetupConsole()
        console.console = Mock()

        console.header("Test Title")

        # Should call print twice (panel + empty line)
        assert console.console.print.call_count == 2


class TestSetupConsoleStep:
    """Test step indicator method."""

    def test_step_display(self):
        """Test step indicator displays correctly."""
        console = SetupConsole()
        console.console = Mock()

        console.step(1, 5, "Installing packages")

        # Should call print once
        console.console.print.assert_called_once()

        # Check that Text object is passed
        call_args = console.console.print.call_args[0][0]
        assert hasattr(call_args, "append")

    def test_step_formatting(self):
        """Test step number formatting."""
        console = SetupConsole()
        console.console = Mock()

        console.step(3, 10, "Configuring database")

        console.console.print.assert_called_once()


class TestSetupConsoleMessages:
    """Test message display methods."""

    def test_success_message(self):
        """Test success message displays with checkmark."""
        console = SetupConsole()
        console.console = Mock()

        console.success("Operation completed")

        console.console.print.assert_called_once()
        args = console.console.print.call_args[0]
        assert "✓" in args[0]
        assert "Operation completed" in args[0]

    def test_error_message(self):
        """Test error message displays with X."""
        console = SetupConsole()
        console.console = Mock()

        console.error("Something went wrong")

        console.console.print.assert_called_once()
        args = console.console.print.call_args[0]
        assert "✗" in args[0]
        assert "Something went wrong" in args[0]

    def test_warning_message(self):
        """Test warning message displays with warning icon."""
        console = SetupConsole()
        console.console = Mock()

        console.warning("This is a warning")

        console.console.print.assert_called_once()
        args = console.console.print.call_args[0]
        assert "⚠" in args[0]
        assert "This is a warning" in args[0]

    def test_info_message(self):
        """Test info message displays with info icon."""
        console = SetupConsole()
        console.console = Mock()

        console.info("Informational message")

        console.console.print.assert_called_once()
        args = console.console.print.call_args[0]
        assert "ℹ" in args[0]
        assert "Informational message" in args[0]


class TestSetupConsolePrompts:
    """Test prompt methods."""

    @patch("scripts.setup.utils.console.Prompt")
    def test_prompt_with_default(self, mock_prompt):
        """Test prompt with default value."""
        mock_prompt.ask.return_value = "user_input"
        console = SetupConsole()

        result = console.prompt("Enter name", default="admin")

        assert result == "user_input"
        mock_prompt.ask.assert_called_once_with(
            "Enter name", default="admin", password=False, console=console.console
        )

    @patch("scripts.setup.utils.console.Prompt")
    def test_prompt_without_default(self, mock_prompt):
        """Test prompt without default value."""
        mock_prompt.ask.return_value = "user_input"
        console = SetupConsole()

        result = console.prompt("Enter value")

        assert result == "user_input"
        mock_prompt.ask.assert_called_once_with(
            "Enter value", default=None, password=False, console=console.console
        )

    @patch("scripts.setup.utils.console.Prompt")
    def test_prompt_password_mode(self, mock_prompt):
        """Test prompt in password mode."""
        mock_prompt.ask.return_value = "secret"
        console = SetupConsole()

        result = console.prompt("Enter password", password=True)

        assert result == "secret"
        mock_prompt.ask.assert_called_once_with(
            "Enter password", default=None, password=True, console=console.console
        )

    @patch("scripts.setup.utils.console.Confirm")
    def test_confirm_default_false(self, mock_confirm):
        """Test confirm with default False."""
        mock_confirm.ask.return_value = True
        console = SetupConsole()

        result = console.confirm("Continue?", default=False)

        assert result is True
        mock_confirm.ask.assert_called_once_with(
            "Continue?", default=False, console=console.console
        )

    @patch("scripts.setup.utils.console.Confirm")
    def test_confirm_default_true(self, mock_confirm):
        """Test confirm with default True."""
        mock_confirm.ask.return_value = False
        console = SetupConsole()

        result = console.confirm("Delete?", default=True)

        assert result is False
        mock_confirm.ask.assert_called_once_with(
            "Delete?", default=True, console=console.console
        )


class TestSetupConsoleSelect:
    """Test select method."""

    @patch("scripts.setup.utils.console.Prompt")
    def test_select_from_choices(self, mock_prompt):
        """Test selecting from a list of choices."""
        mock_prompt.ask.return_value = "postgresql"
        console = SetupConsole()
        console.console = Mock()

        result = console.select("Select database", ["postgresql", "sqlite"])

        assert result == "postgresql"
        # Should print the message and choices
        assert console.console.print.call_count >= 3  # Message + 2 choices + newline

    @patch("scripts.setup.utils.console.Prompt")
    def test_select_displays_numbered_choices(self, mock_prompt):
        """Test that choices are displayed with numbers."""
        mock_prompt.ask.return_value = "option2"
        console = SetupConsole()
        console.console = Mock()

        console.select("Choose option", ["option1", "option2", "option3"])

        # Verify choices were printed
        print_calls = console.console.print.call_args_list
        assert len(print_calls) >= 4  # Message + 3 choices


class TestSetupConsoleTable:
    """Test table display method."""

    def test_table_with_data(self):
        """Test table displays with headers and rows."""
        console = SetupConsole()
        console.console = Mock()

        headers = ["Name", "Value"]
        rows = [
            ["Database", "PostgreSQL"],
            ["Port", "5432"],
        ]

        console.table("Configuration", headers, rows)

        # Should call print twice (table + empty line)
        assert console.console.print.call_count == 2

    def test_table_empty_rows(self):
        """Test table with no rows."""
        console = SetupConsole()
        console.console = Mock()

        headers = ["Column1", "Column2"]
        rows = []

        console.table("Empty Table", headers, rows)

        assert console.console.print.call_count == 2

    def test_table_multiple_columns(self):
        """Test table with multiple columns."""
        console = SetupConsole()
        console.console = Mock()

        headers = ["ID", "Name", "Status", "Date"]
        rows = [
            ["1", "Task1", "Done", "2024-01-01"],
            ["2", "Task2", "Pending", "2024-01-02"],
        ]

        console.table("Task List", headers, rows)

        assert console.console.print.call_count == 2


class TestSetupConsoleSpinner:
    """Test spinner context manager."""

    def test_spinner_starts_and_stops(self):
        """Test spinner context manager starts and stops."""
        console = SetupConsole()

        with patch("scripts.setup.utils.console.Status") as mock_status:
            mock_status_instance = MagicMock()
            mock_status.return_value = mock_status_instance

            with console.spinner("Loading..."):
                pass

            mock_status_instance.start.assert_called_once()
            mock_status_instance.stop.assert_called_once()

    def test_spinner_stops_on_exception(self):
        """Test spinner stops even if exception occurs."""
        console = SetupConsole()

        with patch("scripts.setup.utils.console.Status") as mock_status:
            mock_status_instance = MagicMock()
            mock_status.return_value = mock_status_instance

            try:
                with console.spinner("Processing..."):
                    raise ValueError("Test error")
            except ValueError:
                pass

            mock_status_instance.start.assert_called_once()
            mock_status_instance.stop.assert_called_once()

    def test_spinner_message(self):
        """Test spinner displays correct message."""
        console = SetupConsole()

        with patch("scripts.setup.utils.console.Status") as mock_status:
            mock_status_instance = MagicMock()
            mock_status.return_value = mock_status_instance

            with console.spinner("Installing dependencies..."):
                pass

            mock_status.assert_called_once()
            call_args = mock_status.call_args
            assert call_args[0][0] == "Installing dependencies..."


class TestSetupConsoleProgress:
    """Test progress bar context manager."""

    def test_progress_starts_and_stops(self):
        """Test progress context manager starts and stops."""
        console = SetupConsole()

        with patch("scripts.setup.utils.console.Progress") as mock_progress:
            mock_progress_instance = MagicMock()
            mock_progress.return_value = mock_progress_instance
            mock_progress_instance.add_task.return_value = "task_id"

            with console.progress("Processing", total=100):
                pass

            mock_progress_instance.start.assert_called_once()
            mock_progress_instance.stop.assert_called_once()

    def test_progress_adds_task(self):
        """Test progress bar adds task with description and total."""
        console = SetupConsole()

        with patch("scripts.setup.utils.console.Progress") as mock_progress:
            mock_progress_instance = MagicMock()
            mock_progress.return_value = mock_progress_instance
            mock_progress_instance.add_task.return_value = "task_id"

            with console.progress("Processing files", total=50) as (progress, task):
                assert task == "task_id"

            mock_progress_instance.add_task.assert_called_once_with(
                "Processing files", total=50
            )

    def test_progress_returns_objects(self):
        """Test progress context manager returns progress and task objects."""
        console = SetupConsole()

        with patch("scripts.setup.utils.console.Progress") as mock_progress:
            mock_progress_instance = MagicMock()
            mock_progress.return_value = mock_progress_instance
            mock_progress_instance.add_task.return_value = "task_id"

            with console.progress("Working", total=10) as (progress, task):
                assert progress == mock_progress_instance
                assert task == "task_id"

    def test_progress_stops_on_exception(self):
        """Test progress stops even if exception occurs."""
        console = SetupConsole()

        with patch("scripts.setup.utils.console.Progress") as mock_progress:
            mock_progress_instance = MagicMock()
            mock_progress.return_value = mock_progress_instance
            mock_progress_instance.add_task.return_value = "task_id"

            try:
                with console.progress("Processing", total=100):
                    raise RuntimeError("Test error")
            except RuntimeError:
                pass

            mock_progress_instance.start.assert_called_once()
            mock_progress_instance.stop.assert_called_once()
