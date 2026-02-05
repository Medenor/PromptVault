"""
Unit tests for console.py module.

Tests all SetupConsole methods including:
- Header and step display
- Success, error, warning, and info messages
- Prompts and confirmations
- Tables
- Context managers (spinner, progress)
"""

import pytest
from unittest.mock import MagicMock, patch, call
from io import StringIO

from scripts.setup.utils.console import SetupConsole


class TestSetupConsole:
    """Test suite for SetupConsole class."""

    @pytest.fixture
    def console(self):
        """Create a SetupConsole instance for testing."""
        return SetupConsole()

    @pytest.fixture
    def mock_console(self):
        """Create a mock Rich Console for testing."""
        with patch('scripts.setup.utils.console.Console') as mock:
            mock_instance = MagicMock()
            mock.return_value = mock_instance
            yield mock_instance

    def test_initialization(self, console):
        """Test that SetupConsole initializes correctly."""
        assert console is not None
        assert hasattr(console, 'console')
        assert console.console is not None

    def test_header_without_subtitle(self, console):
        """Test header display without subtitle."""
        with patch.object(console.console, 'print') as mock_print:
            console.header("Test Header")

            # Should print Panel and empty line
            assert mock_print.call_count == 2

            # First call should be the Panel
            first_call = mock_print.call_args_list[0]
            panel = first_call[0][0]
            assert hasattr(panel, '__class__')
            assert panel.__class__.__name__ == 'Panel'

    def test_header_with_subtitle(self, console):
        """Test header display with subtitle."""
        with patch.object(console.console, 'print') as mock_print:
            console.header("Test Header", "Test Subtitle")

            # Should print Panel and empty line
            assert mock_print.call_count == 2

    def test_step_display(self, console):
        """Test step indicator display."""
        with patch.object(console.console, 'print') as mock_print:
            console.step(1, 5, "Test step description")

            # Should print once
            assert mock_print.call_count == 1

            # Get the Text object that was printed
            text_obj = mock_print.call_args[0][0]
            assert hasattr(text_obj, '__class__')
            assert text_obj.__class__.__name__ == 'Text'

    def test_success_message(self, console):
        """Test success message display."""
        with patch.object(console.console, 'print') as mock_print:
            console.success("Test success")

            mock_print.assert_called_once()
            printed_text = mock_print.call_args[0][0]
            assert "✓" in printed_text
            assert "Test success" in printed_text

    def test_error_message(self, console):
        """Test error message display."""
        with patch.object(console.console, 'print') as mock_print:
            console.error("Test error")

            mock_print.assert_called_once()
            printed_text = mock_print.call_args[0][0]
            assert "✗" in printed_text
            assert "Test error" in printed_text

    def test_warning_message(self, console):
        """Test warning message display."""
        with patch.object(console.console, 'print') as mock_print:
            console.warning("Test warning")

            mock_print.assert_called_once()
            printed_text = mock_print.call_args[0][0]
            assert "⚠" in printed_text
            assert "Test warning" in printed_text

    def test_info_message(self, console):
        """Test info message display."""
        with patch.object(console.console, 'print') as mock_print:
            console.info("Test info")

            mock_print.assert_called_once()
            printed_text = mock_print.call_args[0][0]
            assert "ℹ" in printed_text
            assert "Test info" in printed_text

    @patch('scripts.setup.utils.console.Prompt.ask')
    def test_prompt_simple(self, mock_ask, console):
        """Test simple prompt without default."""
        mock_ask.return_value = "user input"

        result = console.prompt("Enter value")

        assert result == "user input"
        mock_ask.assert_called_once_with(
            "Enter value",
            default=None,
            password=False,
            console=console.console
        )

    @patch('scripts.setup.utils.console.Prompt.ask')
    def test_prompt_with_default(self, mock_ask, console):
        """Test prompt with default value."""
        mock_ask.return_value = "default_value"

        result = console.prompt("Enter value", default="default_value")

        assert result == "default_value"
        mock_ask.assert_called_once_with(
            "Enter value",
            default="default_value",
            password=False,
            console=console.console
        )

    @patch('scripts.setup.utils.console.Prompt.ask')
    def test_prompt_password(self, mock_ask, console):
        """Test password prompt (hidden input)."""
        mock_ask.return_value = "secret"

        result = console.prompt("Enter password", password=True)

        assert result == "secret"
        mock_ask.assert_called_once_with(
            "Enter password",
            default=None,
            password=True,
            console=console.console
        )

    @patch('scripts.setup.utils.console.Confirm.ask')
    def test_confirm_default_false(self, mock_confirm, console):
        """Test confirmation with default False."""
        mock_confirm.return_value = False

        result = console.confirm("Are you sure?")

        assert result is False
        mock_confirm.assert_called_once_with(
            "Are you sure?",
            default=False,
            console=console.console
        )

    @patch('scripts.setup.utils.console.Confirm.ask')
    def test_confirm_default_true(self, mock_confirm, console):
        """Test confirmation with default True."""
        mock_confirm.return_value = True

        result = console.confirm("Continue?", default=True)

        assert result is True
        mock_confirm.assert_called_once_with(
            "Continue?",
            default=True,
            console=console.console
        )

    @patch('scripts.setup.utils.console.Prompt.ask')
    def test_select_choice(self, mock_ask, console):
        """Test selection from list of choices."""
        mock_ask.return_value = "option2"

        choices = ["option1", "option2", "option3"]
        result = console.select("Choose option", choices)

        assert result == "option2"

        # Should print the message and choices
        mock_ask.assert_called_once()
        call_args = mock_ask.call_args
        assert call_args[1]['choices'] == choices

    def test_table_display(self, console):
        """Test table display with headers and rows."""
        with patch.object(console.console, 'print') as mock_print:
            headers = ["Column1", "Column2"]
            rows = [
                ["Value1", "Value2"],
                ["Value3", "Value4"]
            ]

            console.table("Test Table", headers, rows)

            # Should print Table and empty line
            assert mock_print.call_count == 2

            # First call should be the Table
            first_call = mock_print.call_args_list[0]
            table = first_call[0][0]
            assert hasattr(table, '__class__')
            assert table.__class__.__name__ == 'Table'

    def test_table_empty_rows(self, console):
        """Test table with no rows."""
        with patch.object(console.console, 'print') as mock_print:
            headers = ["Column1", "Column2"]
            rows = []

            console.table("Empty Table", headers, rows)

            # Should still print Table and empty line
            assert mock_print.call_count == 2

    @patch('scripts.setup.utils.console.Status')
    def test_spinner_context_manager(self, mock_status_class, console):
        """Test spinner context manager."""
        mock_status = MagicMock()
        mock_status_class.return_value = mock_status

        with console.spinner("Loading..."):
            # Inside context
            mock_status.start.assert_called_once()
            mock_status.stop.assert_not_called()

        # After context
        mock_status.stop.assert_called_once()

    @patch('scripts.setup.utils.console.Status')
    def test_spinner_exception_handling(self, mock_status_class, console):
        """Test that spinner stops even if exception occurs."""
        mock_status = MagicMock()
        mock_status_class.return_value = mock_status

        with pytest.raises(ValueError):
            with console.spinner("Loading..."):
                raise ValueError("Test error")

        # Spinner should still stop
        mock_status.stop.assert_called_once()

    @patch('scripts.setup.utils.console.Progress')
    def test_progress_context_manager(self, mock_progress_class, console):
        """Test progress bar context manager."""
        mock_progress = MagicMock()
        mock_task_id = "task-123"
        mock_progress.add_task.return_value = mock_task_id
        mock_progress_class.return_value = mock_progress

        with console.progress("Processing", total=100) as (progress, task):
            # Inside context
            mock_progress.start.assert_called_once()
            mock_progress.add_task.assert_called_once_with("Processing", total=100)
            assert task == mock_task_id
            mock_progress.stop.assert_not_called()

        # After context
        mock_progress.stop.assert_called_once()

    @patch('scripts.setup.utils.console.Progress')
    def test_progress_exception_handling(self, mock_progress_class, console):
        """Test that progress stops even if exception occurs."""
        mock_progress = MagicMock()
        mock_progress.add_task.return_value = "task-123"
        mock_progress_class.return_value = mock_progress

        with pytest.raises(RuntimeError):
            with console.progress("Processing", total=50):
                raise RuntimeError("Test error")

        # Progress should still stop
        mock_progress.stop.assert_called_once()

    @patch('scripts.setup.utils.console.Progress')
    def test_progress_update(self, mock_progress_class, console):
        """Test updating progress bar."""
        mock_progress = MagicMock()
        mock_task_id = "task-123"
        mock_progress.add_task.return_value = mock_task_id
        mock_progress_class.return_value = mock_progress

        with console.progress("Processing", total=100) as (progress, task):
            # Simulate progress updates
            progress.update(task, advance=10)
            progress.update(task, advance=20)

        # Verify update was called
        assert mock_progress.update.call_count == 2

    def test_step_with_various_totals(self, console):
        """Test step display with different step numbers and totals."""
        with patch.object(console.console, 'print') as mock_print:
            console.step(1, 10, "First step")
            console.step(5, 10, "Middle step")
            console.step(10, 10, "Final step")

            assert mock_print.call_count == 3

    def test_multiple_messages(self, console):
        """Test printing multiple messages in sequence."""
        with patch.object(console.console, 'print') as mock_print:
            console.success("Success 1")
            console.error("Error 1")
            console.warning("Warning 1")
            console.info("Info 1")

            assert mock_print.call_count == 4

    @patch('scripts.setup.utils.console.Prompt.ask')
    def test_select_displays_choices(self, mock_ask, console):
        """Test that select method displays choices to user."""
        mock_ask.return_value = "choice1"

        with patch.object(console.console, 'print') as mock_print:
            choices = ["choice1", "choice2", "choice3"]
            result = console.select("Select an option", choices)

            # Should print the message, each choice, and an empty line
            # Plus the prompt call
            assert mock_print.call_count >= 4  # message + 3 choices + empty line

    def test_table_with_single_row(self, console):
        """Test table with a single row."""
        with patch.object(console.console, 'print') as mock_print:
            headers = ["Name", "Value"]
            rows = [["Setting", "Value1"]]

            console.table("Single Row", headers, rows)

            assert mock_print.call_count == 2

    def test_table_with_many_columns(self, console):
        """Test table with many columns."""
        with patch.object(console.console, 'print') as mock_print:
            headers = ["Col1", "Col2", "Col3", "Col4", "Col5"]
            rows = [
                ["A", "B", "C", "D", "E"],
                ["F", "G", "H", "I", "J"]
            ]

            console.table("Wide Table", headers, rows)

            assert mock_print.call_count == 2
