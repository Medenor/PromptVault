# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Comprehensive end-to-end tests for the setup wizard.

Tests cover:
- SetupWizard class initialization
- Quick setup mode workflow
- Advanced setup mode workflow
- Component setup mode
- State persistence and recovery
- Interactive and non-interactive modes
- CLI argument handling
- Error handling and recovery
- Integration tests
"""

import os
import sys
import json
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from click.testing import CliRunner
from datetime import datetime

# Import the module to test
from scripts.setup.setup import (
    SetupState,
    SetupWizard,
    main,
)


def create_mock_console():
    """Create a properly mocked SetupConsole with context manager support."""
    mock_console = Mock()
    mock_console.console = Mock()
    mock_console.console.print = Mock()

    # Mock spinner as context manager
    mock_spinner = MagicMock()
    mock_spinner.__enter__ = Mock(return_value=mock_spinner)
    mock_spinner.__exit__ = Mock(return_value=False)
    mock_console.spinner = Mock(return_value=mock_spinner)

    # Mock other methods
    mock_console.header = Mock()
    mock_console.step = Mock()
    mock_console.success = Mock()
    mock_console.error = Mock()
    mock_console.info = Mock()
    mock_console.warning = Mock()
    mock_console.confirm = Mock(return_value=True)
    mock_console.select = Mock()
    mock_console.prompt = Mock()

    return mock_console


class TestSetupStateInitialization:
    """Test SetupState class initialization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_file = self.temp_dir / '.setup_state.json'

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_state_initialization_creates_default_structure(self):
        """Test that SetupState initializes with default structure."""
        state = SetupState(self.state_file)

        assert state.state_file == self.state_file
        assert state.state['completed_steps'] == []
        assert state.state['mode'] is None
        assert state.state['profile'] is None
        assert state.state['config'] == {}
        assert state.state['last_updated'] is None

    def test_state_initialization_with_custom_path(self):
        """Test SetupState initialization with custom path."""
        custom_path = self.temp_dir / 'custom_state.json'
        state = SetupState(custom_path)

        assert state.state_file == custom_path


class TestSetupStateLoadSave:
    """Test SetupState load and save operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_file = self.temp_dir / '.setup_state.json'
        self.state = SetupState(self.state_file)

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_save_creates_state_file(self):
        """Test that save() creates state file."""
        self.state.state['mode'] = 'quick'
        self.state.save()

        assert self.state_file.exists()

    def test_save_includes_timestamp(self):
        """Test that save() includes last_updated timestamp."""
        self.state.save()

        with open(self.state_file, 'r') as f:
            data = json.load(f)

        assert 'last_updated' in data
        assert data['last_updated'] is not None

    def test_save_preserves_all_fields(self):
        """Test that save() preserves all state fields."""
        self.state.state['mode'] = 'advanced'
        self.state.state['profile'] = 'production'
        self.state.state['completed_steps'] = ['jwt', 'env']
        self.state.state['config'] = {'db_type': 'postgresql'}
        self.state.save()

        with open(self.state_file, 'r') as f:
            data = json.load(f)

        assert data['mode'] == 'advanced'
        assert data['profile'] == 'production'
        assert data['completed_steps'] == ['jwt', 'env']
        assert data['config'] == {'db_type': 'postgresql'}

    def test_load_returns_false_when_no_file_exists(self):
        """Test that load() returns False when no state file exists."""
        result = self.state.load()

        assert result is False

    def test_load_returns_true_when_file_exists(self):
        """Test that load() returns True when state file exists."""
        self.state.save()

        new_state = SetupState(self.state_file)
        result = new_state.load()

        assert result is True

    def test_load_restores_saved_state(self):
        """Test that load() restores previously saved state."""
        self.state.state['mode'] = 'quick'
        self.state.state['profile'] = 'development'
        self.state.state['completed_steps'] = ['jwt']
        self.state.save()

        new_state = SetupState(self.state_file)
        new_state.load()

        assert new_state.state['mode'] == 'quick'
        assert new_state.state['profile'] == 'development'
        assert new_state.state['completed_steps'] == ['jwt']

    def test_load_handles_corrupted_file(self):
        """Test that load() handles corrupted state file gracefully."""
        self.state_file.write_text('CORRUPTED JSON{{{')

        result = self.state.load()

        assert result is False

    def test_save_handles_permission_error_silently(self):
        """Test that save() handles permission errors silently."""
        if sys.platform != 'win32':
            # Create read-only directory
            readonly_dir = self.temp_dir / 'readonly'
            readonly_dir.mkdir()
            os.chmod(readonly_dir, 0o444)

            state_file = readonly_dir / '.setup_state.json'
            state = SetupState(state_file)

            # Should not raise exception
            state.save()

            # Restore permissions for cleanup
            os.chmod(readonly_dir, 0o755)


class TestSetupStateOperations:
    """Test SetupState mark_complete and is_complete operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.state_file = self.temp_dir / '.setup_state.json'
        self.state = SetupState(self.state_file)

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_mark_complete_adds_step(self):
        """Test that mark_complete() adds step to completed_steps."""
        self.state.mark_complete('jwt')

        assert 'jwt' in self.state.state['completed_steps']

    def test_mark_complete_saves_state(self):
        """Test that mark_complete() saves state to file."""
        self.state.mark_complete('jwt')

        assert self.state_file.exists()

    def test_mark_complete_prevents_duplicates(self):
        """Test that mark_complete() doesn't add duplicates."""
        self.state.mark_complete('jwt')
        self.state.mark_complete('jwt')

        assert self.state.state['completed_steps'].count('jwt') == 1

    def test_is_complete_returns_true_for_completed_step(self):
        """Test that is_complete() returns True for completed step."""
        self.state.mark_complete('env')

        assert self.state.is_complete('env') is True

    def test_is_complete_returns_false_for_incomplete_step(self):
        """Test that is_complete() returns False for incomplete step."""
        assert self.state.is_complete('database') is False

    def test_mark_complete_multiple_steps(self):
        """Test marking multiple steps as complete."""
        steps = ['jwt', 'env', 'database', 'admin', 'deploy']
        for step in steps:
            self.state.mark_complete(step)

        for step in steps:
            assert self.state.is_complete(step)

    def test_clear_removes_state_file(self):
        """Test that clear() removes state file."""
        self.state.save()
        assert self.state_file.exists()

        self.state.clear()

        assert not self.state_file.exists()

    def test_clear_handles_missing_file(self):
        """Test that clear() handles missing file gracefully."""
        # Should not raise exception
        self.state.clear()


class TestSetupWizardInitialization:
    """Test SetupWizard class initialization."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_wizard_initialization_default(self):
        """Test SetupWizard initializes with defaults."""
        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard()

            assert wizard.non_interactive is False
            assert wizard.config_file is None
            assert wizard.mode is None
            assert wizard.profile == 'development'
            assert wizard.admin_username is None
            assert wizard.admin_email is None

    def test_wizard_initialization_non_interactive(self):
        """Test SetupWizard initialization with non_interactive flag."""
        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=True)

            assert wizard.non_interactive is True

    def test_wizard_initialization_with_config_file(self):
        """Test SetupWizard initialization with config file."""
        config_path = str(self.temp_dir / 'config.yaml')
        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(config_file=config_path)

            assert wizard.config_file == config_path

    def test_wizard_initializes_console(self):
        """Test that wizard initializes SetupConsole."""
        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard()

            assert wizard.console is not None

    def test_wizard_initializes_state(self):
        """Test that wizard initializes SetupState."""
        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard()

            assert wizard.state is not None
            assert isinstance(wizard.state, SetupState)


class TestQuickSetupMode:
    """Test quick setup mode workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_quick_setup_complete_workflow(self, mock_console_class, mock_subprocess):
        """Test complete quick setup workflow."""
        # Mock console
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_console.prompt.side_effect = ['admin', 'admin@example.com']

        # Mock subprocess to succeed
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=True)
            exit_code = wizard.run_quick_setup()

            assert exit_code == 0
            # Verify all steps were called
            assert mock_subprocess.call_count >= 4  # jwt, env, database, deploy

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_quick_setup_marks_steps_complete(self, mock_console_class, mock_subprocess):
        """Test that quick setup marks all steps as complete."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=True)
            wizard.run_quick_setup()

            assert wizard.state.is_complete('jwt')
            assert wizard.state.is_complete('env')
            assert wizard.state.is_complete('database')
            assert wizard.state.is_complete('admin')
            assert wizard.state.is_complete('deploy')

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_quick_setup_clears_state_on_success(self, mock_console_class, mock_subprocess):
        """Test that quick setup clears state after successful completion."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=True)
            wizard.run_quick_setup()

            # State file should be cleared
            assert not wizard.state.state_file.exists()

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_quick_setup_fails_on_jwt_error(self, mock_console_class, mock_subprocess):
        """Test that quick setup fails if JWT generation fails."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=1, stderr='JWT error')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=True)
            exit_code = wizard.run_quick_setup()

            assert exit_code == 1

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_quick_setup_skips_completed_steps(self, mock_console_class, mock_subprocess):
        """Test that quick setup skips already completed steps."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=True)
            wizard.state.mark_complete('jwt')
            wizard.state.mark_complete('env')

            wizard.run_quick_setup()

            # Should skip JWT and ENV steps
            # Verify subprocess was called fewer times
            assert mock_subprocess.call_count < 4

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_quick_setup_uses_development_profile(self, mock_console_class, mock_subprocess):
        """Test that quick setup uses development profile."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=True)
            wizard.run_quick_setup()

            assert wizard.profile == 'development'

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_quick_setup_with_user_confirmation(self, mock_console_class, mock_subprocess):
        """Test quick setup with user confirmation in interactive mode."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_console.confirm.return_value = False
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=False)
            exit_code = wizard.run_quick_setup()

            # User declined, should exit cleanly
            assert exit_code == 0
            # Subprocess should not be called
            mock_subprocess.assert_not_called()


class TestAdvancedSetupMode:
    """Test advanced setup mode workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_advanced_setup_complete_workflow(self, mock_console_class, mock_subprocess):
        """Test complete advanced setup workflow."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_console.select.side_effect = ['production', 'postgresql']
        mock_console.confirm.side_effect = [True, True, True]
        mock_console.prompt.side_effect = ['admin', 'admin@example.com']
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=False)
            exit_code = wizard.run_advanced_setup()

            assert exit_code == 0

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_advanced_setup_with_production_profile(self, mock_console_class, mock_subprocess):
        """Test advanced setup with production profile."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_console.select.side_effect = ['production', 'postgresql']
        mock_console.confirm.side_effect = [True, True]
        mock_console.prompt.side_effect = ['admin', 'admin@example.com']
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=False)
            wizard.run_advanced_setup()

            assert wizard.profile == 'production'

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_advanced_setup_allows_skip_jwt(self, mock_console_class, mock_subprocess):
        """Test that advanced setup allows skipping JWT generation."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_console.select.side_effect = ['development', 'sqlite']
        mock_console.confirm.side_effect = [False, True]  # Skip JWT, deploy
        mock_console.prompt.side_effect = ['admin', 'admin@example.com']
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=False)
            exit_code = wizard.run_advanced_setup()

            assert exit_code == 0
            # JWT should not be marked complete
            assert not wizard.state.is_complete('jwt')

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_advanced_setup_allows_postpone_deployment(self, mock_console_class, mock_subprocess):
        """Test that advanced setup allows postponing deployment."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_console.select.side_effect = ['development', 'sqlite']
        # Confirm JWT, skip deployment
        mock_console.confirm.side_effect = [True, False]
        mock_console.prompt.side_effect = ['admin', 'admin@example.com']
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=False)
            exit_code = wizard.run_advanced_setup()

            assert exit_code == 0
            # Deploy should not be complete
            assert not wizard.state.is_complete('deploy')

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_advanced_setup_non_interactive_mode(self, mock_console_class, mock_subprocess):
        """Test advanced setup in non-interactive mode."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=True)
            wizard.profile = 'production'
            exit_code = wizard.run_advanced_setup()

            assert exit_code == 0

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_advanced_setup_database_selection(self, mock_console_class, mock_subprocess):
        """Test advanced setup database selection."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_console.select.side_effect = ['production', 'postgresql']
        mock_console.confirm.side_effect = [True, True]
        mock_console.prompt.side_effect = ['admin', 'admin@example.com']
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=False)
            wizard.run_advanced_setup()

            # Check that database setup was called with postgresql
            database_calls = [call for call in mock_subprocess.call_args_list
                            if 'setup_database.py' in str(call)]
            assert len(database_calls) > 0


class TestComponentMode:
    """Test component setup mode."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_run_component_jwt(self, mock_console_class, mock_subprocess):
        """Test running JWT component."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard()
            exit_code = wizard.run_component('jwt')

            assert exit_code == 0
            # Verify subprocess was called with jwt script
            assert mock_subprocess.called

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_run_component_env(self, mock_console_class, mock_subprocess):
        """Test running ENV component."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard()
            exit_code = wizard.run_component('env')

            assert exit_code == 0

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_run_component_database(self, mock_console_class, mock_subprocess):
        """Test running database component."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard()
            exit_code = wizard.run_component('database')

            assert exit_code == 0

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_run_component_deploy(self, mock_console_class, mock_subprocess):
        """Test running deploy component."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard()
            exit_code = wizard.run_component('deploy')

            assert exit_code == 0

    @patch('scripts.setup.setup.SetupConsole')
    def test_run_component_invalid_name(self, mock_console_class):
        """Test running component with invalid name."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard()
            exit_code = wizard.run_component('invalid')

            assert exit_code == 1
            mock_console.error.assert_called()

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_run_component_handles_failure(self, mock_console_class, mock_subprocess):
        """Test that run_component handles component failure."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=1, stderr='Error')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard()
            exit_code = wizard.run_component('jwt')

            assert exit_code == 1


class TestStateResumption:
    """Test state persistence and resumption."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_resume_from_interrupted_setup(self, mock_console_class, mock_subprocess):
        """Test resuming from interrupted setup."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_console.confirm.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            # First wizard - partial setup
            wizard1 = SetupWizard(non_interactive=True)
            wizard1.state.state['mode'] = 'quick'
            wizard1.state.state['profile'] = 'development'
            wizard1.state.mark_complete('jwt')
            wizard1.state.mark_complete('env')
            wizard1.state.save()

            # Second wizard - should resume
            wizard2 = SetupWizard(non_interactive=True)
            wizard2.state.load()
            wizard2.mode = wizard2.state.state['mode']
            wizard2.profile = wizard2.state.state['profile']

            # Verify state was restored
            assert wizard2.mode == 'quick'
            assert wizard2.profile == 'development'
            assert wizard2.state.is_complete('jwt')
            assert wizard2.state.is_complete('env')

    @patch('scripts.setup.setup.SetupConsole')
    def test_state_persistence_between_runs(self, mock_console_class):
        """Test that state persists between wizard runs."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            # First run
            wizard1 = SetupWizard()
            wizard1.state.state['mode'] = 'advanced'
            wizard1.state.mark_complete('jwt')
            wizard1.state.save()

            # Second run
            wizard2 = SetupWizard()
            loaded = wizard2.state.load()

            assert loaded is True
            assert wizard2.state.state['mode'] == 'advanced'
            assert wizard2.state.is_complete('jwt')

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_state_cleared_after_successful_completion(self, mock_console_class, mock_subprocess):
        """Test that state is cleared after successful completion."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=True)
            wizard.run_quick_setup()

            # State file should not exist
            assert not wizard.state.state_file.exists()


class TestInteractiveMode:
    """Test interactive mode functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_mode_selection_quick(self, mock_console_class, mock_subprocess):
        """Test selecting quick mode in interactive wizard."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_console.select.return_value = 'quick'
        mock_console.confirm.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=True)
            wizard.mode = wizard.select_mode()

            assert wizard.mode == 'quick'

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_admin_user_prompts(self, mock_console_class, mock_subprocess):
        """Test admin user prompts in interactive mode."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_console.prompt.side_effect = ['testadmin', 'test@example.com']
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=False)
            result = wizard.create_admin_user()

            assert result is True
            assert wizard.admin_username == 'testadmin'
            assert wizard.admin_email == 'test@example.com'

    @patch('scripts.setup.setup.SetupConsole')
    def test_non_interactive_skips_admin_creation(self, mock_console_class):
        """Test that non-interactive mode skips admin user creation."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=True)
            result = wizard.create_admin_user()

            assert result is True
            assert wizard.admin_username is None
            assert wizard.admin_email is None


class TestCLIIntegration:
    """Test CLI argument handling and main function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_cli_quick_flag(self, mock_console_class, mock_subprocess):
        """Test --quick flag."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            with patch('scripts.setup.setup.project_root', Path(temp_dir)):
                result = self.runner.invoke(main, ['--quick', '--non-interactive'])

                assert result.exit_code == 0

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_cli_advanced_flag(self, mock_console_class, mock_subprocess):
        """Test --advanced flag."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            with patch('scripts.setup.setup.project_root', Path(temp_dir)):
                result = self.runner.invoke(main, ['--advanced', '--non-interactive'])

                assert result.exit_code == 0

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_cli_component_flag(self, mock_console_class, mock_subprocess):
        """Test --component flag."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            with patch('scripts.setup.setup.project_root', Path(temp_dir)):
                result = self.runner.invoke(main, ['--component', 'jwt'])

                assert result.exit_code == 0

    @patch('scripts.setup.setup.SetupConsole')
    def test_cli_non_interactive_flag(self, mock_console_class):
        """Test --non-interactive flag."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console

        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            with patch('scripts.setup.setup.project_root', Path(temp_dir)):
                # Mock the wizard methods to avoid actual execution
                with patch('scripts.setup.setup.SetupWizard.run_quick_setup', return_value=0):
                    result = self.runner.invoke(main, ['--quick', '--non-interactive'])

                    assert result.exit_code == 0

    @patch('scripts.setup.setup.SetupConsole')
    def test_cli_config_flag(self, mock_console_class):
        """Test --config flag."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console

        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            config_file = Path(temp_dir) / 'config.yaml'
            config_file.write_text('profile: production')

            with patch('scripts.setup.setup.project_root', Path(temp_dir)):
                with patch('scripts.setup.setup.SetupWizard.run_quick_setup', return_value=0):
                    result = self.runner.invoke(main, [
                        '--quick',
                        '--config', str(config_file),
                        '--non-interactive'
                    ])

                    assert result.exit_code == 0

    @patch('scripts.setup.setup.SetupConsole')
    def test_cli_keyboard_interrupt(self, mock_console_class):
        """Test handling of keyboard interrupt."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console

        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            with patch('scripts.setup.setup.project_root', Path(temp_dir)):
                with patch('scripts.setup.setup.SetupWizard.run_interactive',
                          side_effect=KeyboardInterrupt):
                    result = self.runner.invoke(main, [])

                    assert result.exit_code == 1

    @patch('scripts.setup.setup.SetupConsole')
    def test_cli_unexpected_exception(self, mock_console_class):
        """Test handling of unexpected exception."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console

        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            with patch('scripts.setup.setup.project_root', Path(temp_dir)):
                with patch('scripts.setup.setup.SetupWizard.run_interactive',
                          side_effect=RuntimeError("Test error")):
                    result = self.runner.invoke(main, [])

                    assert result.exit_code == 1


class TestErrorHandling:
    """Test error handling and recovery."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_handles_component_failure(self, mock_console_class, mock_subprocess):
        """Test handling of component failure."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        # First call succeeds (JWT), second fails (ENV)
        mock_subprocess.side_effect = [
            Mock(returncode=0, stderr=''),
            Mock(returncode=1, stderr='ENV error')
        ]

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=True)
            exit_code = wizard.run_quick_setup()

            assert exit_code == 1
            mock_console.error.assert_called()

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_handles_subprocess_exception(self, mock_console_class, mock_subprocess):
        """Test handling of subprocess exception."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.side_effect = Exception("Subprocess error")

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard(non_interactive=True)
            # Should raise exception
            with pytest.raises(Exception):
                wizard.run_quick_setup()

    @patch('scripts.setup.setup.SetupConsole')
    def test_handles_missing_scripts_dir(self, mock_console_class):
        """Test handling of missing scripts directory."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard()
            # Scripts dir doesn't exist, should handle gracefully
            assert wizard.scripts_dir.exists() is False


class TestAdditionalCoverage:
    """Targeted tests to cover uncovered branches."""

    @patch('scripts.setup.setup.SetupConsole')
    def test_run_interactive_resume_declined_unknown_mode(self, mock_console_class):
        """Test interactive flow when resume is declined and mode is invalid."""
        mock_console = create_mock_console()
        mock_console.confirm.return_value = False
        mock_console_class.return_value = mock_console

        wizard = SetupWizard()
        wizard.state.load = Mock(return_value=True)
        wizard.state.state = {"last_updated": "2026-01-01"}
        wizard.state.clear = Mock()
        wizard.state.save = Mock()
        wizard.select_mode = Mock(return_value="invalid")

        exit_code = wizard.run_interactive()

        assert exit_code == 1
        mock_console.error.assert_called_with("Unknown mode: invalid")

    @patch('scripts.setup.setup.SetupConsole')
    def test_run_component_menu_exit(self, mock_console_class):
        """Test component menu exit option."""
        mock_console = create_mock_console()
        mock_console.select.return_value = "exit"
        mock_console_class.return_value = mock_console

        wizard = SetupWizard()
        wizard.run_component = Mock()

        exit_code = wizard.run_component_menu()

        assert exit_code == 0
        wizard.run_component.assert_not_called()

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_run_env_setup_failure_with_stderr(self, mock_console_class, mock_subprocess):
        """Test environment setup failure prints stderr."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=1, stderr="ENV error")

        wizard = SetupWizard()
        result = wizard.run_env_setup(profile="development", non_interactive=False)

        assert result is False
        mock_console.error.assert_called_with("Environment configuration failed")
        mock_console.console.print.assert_any_call("ENV error", style="red")

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_run_database_setup_failure(self, mock_console_class, mock_subprocess):
        """Test database setup failure path."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=1)

        wizard = SetupWizard()
        result = wizard.run_database_setup(db_type="sqlite")

        assert result is False
        mock_console.error.assert_called_with("Database setup failed")

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_run_deploy_failure(self, mock_console_class, mock_subprocess):
        """Test deploy failure path."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=1)

        wizard = SetupWizard()
        result = wizard.run_deploy(non_interactive=True)

        assert result is False
        mock_console.error.assert_called_with("Deployment failed")

    @patch('scripts.setup.setup.SetupConsole')
    def test_run_advanced_setup_jwt_failure_non_interactive(self, mock_console_class):
        """Test advanced setup when non-interactive JWT setup fails."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console

        wizard = SetupWizard(non_interactive=True)
        wizard.state.state["profile"] = "production"
        wizard.state.is_complete = Mock(return_value=False)
        wizard.run_jwt_setup = Mock(return_value=False)

        exit_code = wizard.run_advanced_setup()

        assert exit_code == 1
        mock_console.error.assert_called_with("JWT key generation failed")

    @patch('scripts.setup.setup.SetupConsole')
    def test_run_advanced_setup_deploy_postponed(self, mock_console_class):
        """Test advanced setup when deployment is postponed."""
        mock_console = create_mock_console()
        mock_console.confirm.return_value = False
        mock_console.select.side_effect = ["production", "postgresql"]
        mock_console_class.return_value = mock_console

        wizard = SetupWizard(non_interactive=False)
        wizard.state.is_complete = Mock(return_value=False)
        wizard.run_jwt_setup = Mock(return_value=True)
        wizard.run_env_setup = Mock(return_value=True)
        wizard.run_database_setup = Mock(return_value=True)
        wizard.create_admin_user = Mock(return_value=True)

        exit_code = wizard.run_advanced_setup()

        assert exit_code == 0
        mock_console.info.assert_any_call("Deployment postponed")

    @patch('scripts.setup.setup.SetupConsole')
    def test_run_quick_setup_skips_completed_steps(self, mock_console_class):
        """Test quick setup when all steps are already complete."""
        mock_console = create_mock_console()
        mock_console.confirm.return_value = True
        mock_console_class.return_value = mock_console

        wizard = SetupWizard(non_interactive=False)
        wizard.state = Mock()
        wizard.state.state = {}
        wizard.state.is_complete = Mock(return_value=True)
        wizard.state.save = Mock()
        wizard.state.clear = Mock()
        wizard.show_success_summary = Mock()

        exit_code = wizard.run_quick_setup()

        assert exit_code == 0


class TestIntegrationWorkflows:
    """Integration tests for complete workflows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = None

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_complete_quick_setup_end_to_end(self, mock_console_class, mock_subprocess):
        """Test complete quick setup from start to finish."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            with patch('scripts.setup.setup.project_root', Path(temp_dir)):
                result = self.runner.invoke(main, ['--quick', '--non-interactive'])

                assert result.exit_code == 0
                # Verify subprocess was called for each component
                assert mock_subprocess.call_count >= 4

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_component_by_component_setup(self, mock_console_class, mock_subprocess):
        """Test setting up components one by one."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            with patch('scripts.setup.setup.project_root', Path(temp_dir)):
                # Run each component separately
                components = ['jwt', 'env', 'database', 'deploy']
                for component in components:
                    result = self.runner.invoke(main, ['--component', component])
                    assert result.exit_code == 0

    @patch('scripts.setup.setup.subprocess.run')
    @patch('scripts.setup.setup.SetupConsole')
    def test_interrupted_and_resumed_setup(self, mock_console_class, mock_subprocess):
        """Test setup interruption and resumption."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console
        mock_console.confirm.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with self.runner.isolated_filesystem() as temp_dir:
            self.temp_dir = temp_dir
            state_file = Path(temp_dir) / '.setup_state.json'

            with patch('scripts.setup.setup.project_root', Path(temp_dir)):
                # First run - partial setup
                wizard1 = SetupWizard(non_interactive=True)
                wizard1.state.state['mode'] = 'quick'
                wizard1.state.mark_complete('jwt')
                wizard1.state.mark_complete('env')
                wizard1.state.save()

                # Verify state was saved
                assert state_file.exists()

                # Second run - resume and complete
                wizard2 = SetupWizard(non_interactive=True)
                wizard2.state.load()
                assert wizard2.state.is_complete('jwt')
                assert wizard2.state.is_complete('env')

                # Continue setup
                wizard2.mode = 'quick'
                wizard2.run_quick_setup()

                # State should be cleared after completion
                assert not state_file.exists()


class TestShowSuccessSummary:
    """Test success summary display."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    @patch('scripts.setup.setup.SetupConsole')
    def test_success_summary_displays(self, mock_console_class):
        """Test that success summary is displayed."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard()
            wizard.admin_username = 'admin'
            wizard.admin_email = 'admin@example.com'

            wizard.show_success_summary()

            # Verify console print was called
            assert mock_console.console.print.called

    @patch('scripts.setup.setup.SetupConsole')
    def test_success_summary_without_admin(self, mock_console_class):
        """Test success summary without admin credentials."""
        mock_console = create_mock_console()
        mock_console_class.return_value = mock_console

        with patch('scripts.setup.setup.project_root', self.temp_dir):
            wizard = SetupWizard()
            wizard.show_success_summary()

            # Should still display without error
            assert mock_console.console.print.called
