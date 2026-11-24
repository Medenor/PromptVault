#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Unit Tests for Setup Wizard

Tests the main setup wizard functionality including:
- State management (save/load/resume)
- Mode selection logic
- Component orchestration
- Error handling
"""

import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "scripts" / "setup" / "utils"))

# Import after path setup
from scripts.setup.setup import SetupState, SetupWizard


class TestSetupState:
    """Test SetupState class for state management."""

    def test_init(self):
        """Test SetupState initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".setup_state.json"
            state = SetupState(state_file)

            assert state.state_file == state_file
            assert state.state['completed_steps'] == []
            assert state.state['mode'] is None
            assert state.state['profile'] is None

    def test_save_and_load(self):
        """Test state save and load operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".setup_state.json"
            state = SetupState(state_file)

            # Save state
            state.state['mode'] = 'quick'
            state.state['profile'] = 'development'
            state.state['completed_steps'] = ['jwt', 'env']
            state.save()

            # Verify file exists
            assert state_file.exists()

            # Load state in new instance
            new_state = SetupState(state_file)
            assert new_state.load()

            # Verify loaded state
            assert new_state.state['mode'] == 'quick'
            assert new_state.state['profile'] == 'development'
            assert new_state.state['completed_steps'] == ['jwt', 'env']

    def test_load_nonexistent(self):
        """Test loading state when file doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".setup_state.json"
            state = SetupState(state_file)

            # Should return False when file doesn't exist
            assert not state.load()

    def test_mark_complete(self):
        """Test marking steps as complete."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".setup_state.json"
            state = SetupState(state_file)

            # Mark steps complete
            state.mark_complete('jwt')
            state.mark_complete('env')

            assert state.is_complete('jwt')
            assert state.is_complete('env')
            assert not state.is_complete('database')

            # Verify no duplicates
            state.mark_complete('jwt')
            assert state.state['completed_steps'].count('jwt') == 1

    def test_clear(self):
        """Test clearing state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".setup_state.json"
            state = SetupState(state_file)

            # Create state file
            state.state['mode'] = 'quick'
            state.save()
            assert state_file.exists()

            # Clear state
            state.clear()
            assert not state_file.exists()


class TestSetupWizard:
    """Test SetupWizard class for orchestration."""

    @patch('scripts.setup.setup.SetupConsole')
    def test_init(self, mock_console):
        """Test SetupWizard initialization."""
        wizard = SetupWizard(non_interactive=True)

        assert wizard.non_interactive is True
        assert wizard.mode is None
        assert wizard.profile == 'development'
        assert wizard.admin_username is None

    @patch('scripts.setup.setup.SetupConsole')
    @patch('subprocess.run')
    def test_run_jwt_setup_success(self, mock_run, mock_console):
        """Test successful JWT setup."""
        wizard = SetupWizard(non_interactive=True)

        # Mock successful subprocess
        mock_run.return_value = Mock(returncode=0, stderr='')

        result = wizard.run_jwt_setup()

        assert result is True
        assert mock_run.called
        # Verify it called setup_jwt.py
        call_args = mock_run.call_args[0][0]
        assert 'setup_jwt.py' in str(call_args)

    @patch('scripts.setup.setup.SetupConsole')
    @patch('subprocess.run')
    def test_run_jwt_setup_failure(self, mock_run, mock_console):
        """Test JWT setup failure handling."""
        wizard = SetupWizard(non_interactive=True)

        # Mock failed subprocess
        mock_run.return_value = Mock(returncode=1, stderr='Error generating keys')

        result = wizard.run_jwt_setup()

        assert result is False

    @patch('scripts.setup.setup.SetupConsole')
    @patch('subprocess.run')
    def test_run_env_setup(self, mock_run, mock_console):
        """Test environment setup."""
        wizard = SetupWizard(non_interactive=True)

        # Mock successful subprocess
        mock_run.return_value = Mock(returncode=0, stderr='')

        result = wizard.run_env_setup(profile='development', non_interactive=True)

        assert result is True
        assert mock_run.called

        # Verify arguments
        call_args = mock_run.call_args[0][0]
        assert 'setup_env.py' in str(call_args)
        assert '--profile' in call_args
        assert 'development' in call_args
        assert '--non-interactive' in call_args

    @patch('scripts.setup.setup.SetupConsole')
    @patch('subprocess.run')
    def test_run_database_setup(self, mock_run, mock_console):
        """Test database setup."""
        wizard = SetupWizard(non_interactive=True)

        # Mock successful subprocess
        mock_run.return_value = Mock(returncode=0, stderr='')

        result = wizard.run_database_setup(db_type='sqlite')

        assert result is True
        assert mock_run.called

        # Verify arguments
        call_args = mock_run.call_args[0][0]
        assert 'setup_database.py' in str(call_args)
        assert '--type' in call_args
        assert 'sqlite' in call_args

    @patch('scripts.setup.setup.SetupConsole')
    @patch('subprocess.run')
    def test_run_deploy(self, mock_run, mock_console):
        """Test deployment."""
        wizard = SetupWizard(non_interactive=True)

        # Mock successful subprocess
        mock_run.return_value = Mock(returncode=0, stderr='')

        result = wizard.run_deploy(non_interactive=True)

        assert result is True
        assert mock_run.called

        # Verify arguments
        call_args = mock_run.call_args[0][0]
        assert 'deploy.py' in str(call_args)
        assert '--non-interactive' in call_args

    @patch('scripts.setup.setup.SetupConsole')
    def test_create_admin_user_non_interactive(self, mock_console):
        """Test admin user creation in non-interactive mode."""
        wizard = SetupWizard(non_interactive=True)

        result = wizard.create_admin_user()

        # Should skip in non-interactive mode
        assert result is True

    @patch('scripts.setup.setup.SetupConsole')
    def test_run_component_dispatcher(self, mock_console):
        """Test component dispatcher routes to correct methods."""
        wizard = SetupWizard(non_interactive=True)

        # Mock the component methods
        wizard.run_jwt_setup = Mock(return_value=True)
        wizard.run_env_setup = Mock(return_value=True)
        wizard.run_database_setup = Mock(return_value=True)
        wizard.run_deploy = Mock(return_value=True)

        # Test each component
        assert wizard.run_component('jwt') == 0
        assert wizard.run_jwt_setup.called

        assert wizard.run_component('env') == 0
        assert wizard.run_env_setup.called

        assert wizard.run_component('database') == 0
        assert wizard.run_database_setup.called

        assert wizard.run_component('deploy') == 0
        assert wizard.run_deploy.called

        # Test invalid component
        assert wizard.run_component('invalid') == 1


class TestQuickSetup:
    """Test quick setup flow."""

    @patch('scripts.setup.setup.SetupConsole')
    @patch('subprocess.run')
    def test_quick_setup_success(self, mock_run, mock_console):
        """Test successful quick setup flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".setup_state.json"

            # Mock console to avoid user interaction
            mock_console_instance = MagicMock()
            mock_console.return_value = mock_console_instance
            mock_console_instance.confirm.return_value = True

            wizard = SetupWizard(non_interactive=True)
            wizard.state = SetupState(state_file)

            # Mock all subprocess calls to succeed
            mock_run.return_value = Mock(returncode=0, stderr='')

            # Run quick setup
            result = wizard.run_quick_setup()

            # Should complete successfully
            assert result == 0

            # Verify all steps were called
            assert mock_run.call_count >= 3  # JWT, env, database, deploy

    @patch('scripts.setup.setup.SetupConsole')
    @patch('subprocess.run')
    def test_quick_setup_jwt_failure(self, mock_run, mock_console):
        """Test quick setup fails if JWT generation fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".setup_state.json"

            mock_console_instance = MagicMock()
            mock_console.return_value = mock_console_instance

            wizard = SetupWizard(non_interactive=True)
            wizard.state = SetupState(state_file)

            # Mock JWT setup to fail
            mock_run.return_value = Mock(returncode=1, stderr='JWT error')

            result = wizard.run_quick_setup()

            # Should fail
            assert result == 1

    @patch('scripts.setup.setup.SetupConsole')
    @patch('subprocess.run')
    def test_quick_setup_resume(self, mock_run, mock_console):
        """Test quick setup resumes from saved state."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".setup_state.json"

            mock_console_instance = Mock()
            mock_console.return_value = mock_console_instance

            wizard = SetupWizard(non_interactive=True)
            wizard.state = SetupState(state_file)

            # Mark some steps as complete
            wizard.state.mark_complete('jwt')
            wizard.state.mark_complete('env')

            # Mock subprocess
            mock_run.return_value = Mock(returncode=0, stderr='')

            result = wizard.run_quick_setup()

            # Should succeed and skip completed steps
            assert result == 0

            # JWT and env should not be called again
            calls = [str(call[0][0]) for call in mock_run.call_args_list]
            jwt_calls = sum('setup_jwt.py' in str(call) for call in calls)
            env_calls = sum('setup_env.py' in str(call) for call in calls)

            # These should be 0 since steps were already complete
            assert jwt_calls == 0
            assert env_calls == 0


class TestAdvancedSetup:
    """Test advanced setup flow."""

    @patch('scripts.setup.setup.SetupConsole')
    @patch('subprocess.run')
    def test_advanced_setup_success(self, mock_run, mock_console):
        """Test successful advanced setup flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".setup_state.json"

            mock_console_instance = MagicMock()
            mock_console.return_value = mock_console_instance
            mock_console_instance.confirm.return_value = True

            wizard = SetupWizard(non_interactive=True)
            wizard.state = SetupState(state_file)
            wizard.profile = 'production'

            # Mock all subprocess calls to succeed
            mock_run.return_value = Mock(returncode=0, stderr='')

            result = wizard.run_advanced_setup()

            # Should complete successfully
            assert result == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
