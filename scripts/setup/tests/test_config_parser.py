"""
Unit tests for config_parser.py module.

Tests configuration file parsing, merging, variable substitution,
and .env file operations.
"""

import pytest
import os
import stat
from pathlib import Path
from unittest.mock import patch, MagicMock

from scripts.setup.utils.config_parser import (
    parse_env_file,
    parse_yaml_config,
    merge_configs,
    substitute_env_vars,
    load_env_template,
    write_env_file
)


class TestParseEnvFile:
    """Tests for parse_env_file function."""

    def test_parse_simple_env_file(self, tmp_path):
        """Test parsing simple .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("""DATABASE_URL=postgresql://localhost/db
API_KEY=secret-key-123
DEBUG=true
""")

        result = parse_env_file(str(env_file))

        assert result == {
            "DATABASE_URL": "postgresql://localhost/db",
            "API_KEY": "secret-key-123",
            "DEBUG": "true"
        }

    def test_parse_env_with_comments(self, tmp_path):
        """Test parsing .env file with comments."""
        env_file = tmp_path / ".env"
        env_file.write_text("""# Database configuration
DATABASE_URL=postgresql://localhost/db
# API settings
API_KEY=secret-key-123
""")

        result = parse_env_file(str(env_file))

        assert result == {
            "DATABASE_URL": "postgresql://localhost/db",
            "API_KEY": "secret-key-123"
        }

    def test_parse_env_with_empty_lines(self, tmp_path):
        """Test parsing .env file with empty lines."""
        env_file = tmp_path / ".env"
        env_file.write_text("""DATABASE_URL=postgresql://localhost/db

API_KEY=secret-key-123

DEBUG=true
""")

        result = parse_env_file(str(env_file))

        assert len(result) == 3
        assert "DATABASE_URL" in result

    def test_parse_env_with_quoted_values(self, tmp_path):
        """Test parsing .env file with quoted values."""
        env_file = tmp_path / ".env"
        env_file.write_text("""SINGLE_QUOTED='single quote value'
DOUBLE_QUOTED="double quote value"
UNQUOTED=unquoted value
""")

        result = parse_env_file(str(env_file))

        assert result["SINGLE_QUOTED"] == "single quote value"
        assert result["DOUBLE_QUOTED"] == "double quote value"
        assert result["UNQUOTED"] == "unquoted value"

    def test_parse_env_with_equals_in_value(self, tmp_path):
        """Test parsing .env file with = in value."""
        env_file = tmp_path / ".env"
        env_file.write_text("URL=http://example.com?param=value")

        result = parse_env_file(str(env_file))

        assert result["URL"] == "http://example.com?param=value"

    def test_parse_env_with_empty_value(self, tmp_path):
        """Test parsing .env file with empty value."""
        env_file = tmp_path / ".env"
        env_file.write_text("EMPTY_KEY=")

        result = parse_env_file(str(env_file))

        assert result["EMPTY_KEY"] == ""

    def test_parse_env_file_not_found(self):
        """Test parsing non-existent .env file."""
        with pytest.raises(FileNotFoundError):
            parse_env_file("/nonexistent/.env")

    def test_parse_env_invalid_format(self, tmp_path):
        """Test parsing .env file with invalid format."""
        env_file = tmp_path / ".env"
        env_file.write_text("INVALID LINE WITHOUT EQUALS")

        with pytest.raises(ValueError) as exc_info:
            parse_env_file(str(env_file))

        assert "missing '=' separator" in str(exc_info.value).lower()

    def test_parse_env_empty_variable_name(self, tmp_path):
        """Test parsing .env file with empty variable name."""
        env_file = tmp_path / ".env"
        env_file.write_text("=value")

        with pytest.raises(ValueError) as exc_info:
            parse_env_file(str(env_file))

        assert "empty variable name" in str(exc_info.value).lower()

    def test_parse_env_invalid_variable_name(self, tmp_path):
        """Test parsing .env file with invalid variable name."""
        env_file = tmp_path / ".env"
        env_file.write_text("123INVALID=value")

        with pytest.raises(ValueError) as exc_info:
            parse_env_file(str(env_file))

        assert "invalid variable name" in str(exc_info.value).lower()

    def test_parse_env_with_whitespace(self, tmp_path):
        """Test parsing .env file with whitespace around keys and values."""
        env_file = tmp_path / ".env"
        env_file.write_text("""  KEY1  =  value1
KEY2=value2
  KEY3=value3
""")

        result = parse_env_file(str(env_file))

        assert result["KEY1"] == "value1"
        assert result["KEY2"] == "value2"
        assert result["KEY3"] == "value3"

    def test_parse_env_directory_instead_of_file(self, tmp_path):
        """Test parsing directory instead of file."""
        with pytest.raises(ValueError) as exc_info:
            parse_env_file(str(tmp_path))

        assert "not a file" in str(exc_info.value).lower()


class TestParseYamlConfig:
    """Tests for parse_yaml_config function."""

    def test_parse_simple_yaml(self, tmp_path):
        """Test parsing simple YAML file."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("""database:
  host: localhost
  port: 5432
debug: true
""")

        result = parse_yaml_config(str(yaml_file))

        assert result["database"]["host"] == "localhost"
        assert result["database"]["port"] == 5432
        assert result["debug"] is True

    def test_parse_empty_yaml(self, tmp_path):
        """Test parsing empty YAML file."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("")

        result = parse_yaml_config(str(yaml_file))

        assert result == {}

    def test_parse_yaml_with_lists(self, tmp_path):
        """Test parsing YAML with lists."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("""servers:
  - host: server1.com
    port: 8080
  - host: server2.com
    port: 8081
""")

        result = parse_yaml_config(str(yaml_file))

        assert len(result["servers"]) == 2
        assert result["servers"][0]["host"] == "server1.com"

    def test_parse_yaml_nested_structure(self, tmp_path):
        """Test parsing YAML with deeply nested structure."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("""level1:
  level2:
    level3:
      value: deep
""")

        result = parse_yaml_config(str(yaml_file))

        assert result["level1"]["level2"]["level3"]["value"] == "deep"

    def test_parse_yaml_file_not_found(self):
        """Test parsing non-existent YAML file."""
        with pytest.raises(FileNotFoundError):
            parse_yaml_config("/nonexistent/config.yaml")

    def test_parse_yaml_invalid_format(self, tmp_path):
        """Test parsing invalid YAML format."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("""invalid: yaml: format:
  - broken
    structure
""")

        with pytest.raises(ValueError) as exc_info:
            parse_yaml_config(str(yaml_file))

        assert "invalid yaml" in str(exc_info.value).lower()

    def test_parse_yaml_non_dict_root(self, tmp_path):
        """Test parsing YAML with non-dictionary at root."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("- item1\n- item2\n")

        with pytest.raises(ValueError) as exc_info:
            parse_yaml_config(str(yaml_file))

        assert "dictionary" in str(exc_info.value).lower()

    def test_parse_yaml_directory_instead_of_file(self, tmp_path):
        """Test parsing directory instead of file."""
        with pytest.raises(ValueError) as exc_info:
            parse_yaml_config(str(tmp_path))

        assert "not a file" in str(exc_info.value).lower()

    @patch('scripts.setup.utils.config_parser.yaml', None)
    def test_parse_yaml_without_pyyaml(self, tmp_path):
        """Test parsing YAML when PyYAML is not installed."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("key: value")

        with pytest.raises(ImportError) as exc_info:
            parse_yaml_config(str(yaml_file))

        assert "pyyaml" in str(exc_info.value).lower()


class TestMergeConfigs:
    """Tests for merge_configs function."""

    def test_merge_simple_dicts(self):
        """Test merging simple dictionaries."""
        base = {"key1": "value1", "key2": "value2"}
        override = {"key2": "new_value2", "key3": "value3"}

        result = merge_configs(base, override)

        assert result["key1"] == "value1"
        assert result["key2"] == "new_value2"
        assert result["key3"] == "value3"

    def test_merge_nested_dicts(self):
        """Test merging nested dictionaries."""
        base = {
            "db": {
                "host": "localhost",
                "port": 5432,
                "name": "mydb"
            },
            "debug": False
        }
        override = {
            "db": {
                "port": 3306,
                "password": "secret"
            },
            "debug": True
        }

        result = merge_configs(base, override)

        assert result["db"]["host"] == "localhost"
        assert result["db"]["port"] == 3306
        assert result["db"]["password"] == "secret"
        assert result["db"]["name"] == "mydb"
        assert result["debug"] is True

    def test_merge_empty_override(self):
        """Test merging with empty override."""
        base = {"key1": "value1", "key2": "value2"}
        override = {}

        result = merge_configs(base, override)

        assert result == base

    def test_merge_empty_base(self):
        """Test merging with empty base."""
        base = {}
        override = {"key1": "value1", "key2": "value2"}

        result = merge_configs(base, override)

        assert result == override

    def test_merge_does_not_modify_originals(self):
        """Test that merge doesn't modify original dictionaries."""
        base = {"key1": "value1", "nested": {"a": 1}}
        override = {"key2": "value2", "nested": {"b": 2}}

        result = merge_configs(base, override)

        # Original dicts should not be modified
        assert "key2" not in base
        assert "b" not in base["nested"]
        assert "key1" not in override

    def test_merge_override_replaces_non_dict(self):
        """Test that override replaces non-dict values."""
        base = {"key": "string_value"}
        override = {"key": {"nested": "dict_value"}}

        result = merge_configs(base, override)

        assert isinstance(result["key"], dict)
        assert result["key"]["nested"] == "dict_value"

    def test_merge_deeply_nested(self):
        """Test merging deeply nested structures."""
        base = {
            "level1": {
                "level2": {
                    "level3": {
                        "keep": "this",
                        "override": "old"
                    }
                }
            }
        }
        override = {
            "level1": {
                "level2": {
                    "level3": {
                        "override": "new",
                        "add": "this"
                    }
                }
            }
        }

        result = merge_configs(base, override)

        assert result["level1"]["level2"]["level3"]["keep"] == "this"
        assert result["level1"]["level2"]["level3"]["override"] == "new"
        assert result["level1"]["level2"]["level3"]["add"] == "this"

    def test_merge_with_lists(self):
        """Test that lists are replaced, not merged."""
        base = {"items": [1, 2, 3]}
        override = {"items": [4, 5]}

        result = merge_configs(base, override)

        assert result["items"] == [4, 5]


class TestSubstituteEnvVars:
    """Tests for substitute_env_vars function."""

    def test_substitute_simple_vars(self):
        """Test substituting simple variables."""
        template = "Host: ${HOST}, Port: ${PORT}"
        values = {"HOST": "localhost", "PORT": "8080"}

        result = substitute_env_vars(template, values)

        assert result == "Host: localhost, Port: 8080"

    def test_substitute_with_defaults(self):
        """Test substituting with default values."""
        template = "${HOST:-localhost}:${PORT:-8080}"
        values = {}

        result = substitute_env_vars(template, values)

        assert result == "localhost:8080"

    def test_substitute_override_defaults(self):
        """Test that values override defaults."""
        template = "${HOST:-localhost}:${PORT:-8080}"
        values = {"HOST": "example.com", "PORT": "443"}

        result = substitute_env_vars(template, values)

        assert result == "example.com:443"

    def test_substitute_simple_format(self):
        """Test substituting simple $VAR format."""
        template = "Server: $HOST:$PORT"
        values = {"HOST": "example.com", "PORT": "443"}

        result = substitute_env_vars(template, values)

        assert result == "Server: example.com:443"

    def test_substitute_missing_var_without_default(self):
        """Test that missing variables without defaults are left as-is."""
        template = "Value: ${MISSING}"
        values = {}

        result = substitute_env_vars(template, values)

        assert result == "Value: ${MISSING}"

    def test_substitute_mixed_formats(self):
        """Test substituting mixed variable formats."""
        template = "${VAR1} and $VAR2 and ${VAR3:-default3}"
        values = {"VAR1": "value1", "VAR2": "value2"}

        result = substitute_env_vars(template, values)

        assert result == "value1 and value2 and default3"

    def test_substitute_empty_value(self):
        """Test substituting with empty value."""
        template = "${VAR1}${VAR2}"
        values = {"VAR1": "", "VAR2": "value2"}

        result = substitute_env_vars(template, values)

        assert result == "value2"

    def test_substitute_special_characters_in_value(self):
        """Test substituting values with special characters."""
        template = "URL: ${URL}"
        values = {"URL": "https://example.com?param=value&other=123"}

        result = substitute_env_vars(template, values)

        assert result == "URL: https://example.com?param=value&other=123"

    def test_substitute_no_variables(self):
        """Test template with no variables."""
        template = "This is a plain string"
        values = {"VAR": "value"}

        result = substitute_env_vars(template, values)

        assert result == "This is a plain string"

    def test_substitute_empty_template(self):
        """Test empty template."""
        result = substitute_env_vars("", {"VAR": "value"})

        assert result == ""

    def test_substitute_complex_default(self):
        """Test default value with special characters."""
        template = "${DATABASE_URL:-postgresql://user:pass@localhost:5432/db}"
        values = {}

        result = substitute_env_vars(template, values)

        assert result == "postgresql://user:pass@localhost:5432/db"


class TestLoadEnvTemplate:
    """Tests for load_env_template function."""

    def test_load_env_template_from_current_dir(self, tmp_path):
        """Test loading .env.example from current directory."""
        env_example = tmp_path / ".env.example"
        env_example.write_text("""DATABASE_URL=postgresql://localhost/db
API_KEY=your-api-key-here
DEBUG=false
""")

        with patch('scripts.setup.utils.config_parser.Path.cwd', return_value=tmp_path):
            result = load_env_template()

        assert result["DATABASE_URL"] == "postgresql://localhost/db"
        assert result["API_KEY"] == "your-api-key-here"
        assert result["DEBUG"] == "false"

    def test_load_env_template_from_parent_dir(self, tmp_path):
        """Test loading .env.example from parent directory."""
        env_example = tmp_path / ".env.example"
        env_example.write_text("KEY=value")

        subdir = tmp_path / "subdir"
        subdir.mkdir()

        with patch('scripts.setup.utils.config_parser.Path.cwd', return_value=subdir):
            result = load_env_template()

        assert result["KEY"] == "value"

    def test_load_env_template_not_found(self, tmp_path):
        """Test error when .env.example not found."""
        with patch('scripts.setup.utils.config_parser.Path.cwd', return_value=tmp_path):
            with pytest.raises(FileNotFoundError) as exc_info:
                load_env_template()

        assert ".env.example" in str(exc_info.value)


class TestWriteEnvFile:
    """Tests for write_env_file function."""

    def test_write_simple_env_file(self, tmp_path):
        """Test writing simple .env file."""
        env_file = tmp_path / ".env"
        config = {
            "DATABASE_URL": "postgresql://localhost/db",
            "API_KEY": "secret-key-123",
            "DEBUG": "false"
        }

        write_env_file(str(env_file), config)

        # Read and verify
        content = env_file.read_text()
        assert "DATABASE_URL=postgresql://localhost/db" in content
        assert "API_KEY=secret-key-123" in content
        assert "DEBUG=false" in content

    def test_write_env_file_sorted_keys(self, tmp_path):
        """Test that keys are sorted alphabetically."""
        env_file = tmp_path / ".env"
        config = {
            "ZEBRA": "last",
            "ALPHA": "first",
            "MIKE": "middle"
        }

        write_env_file(str(env_file), config)

        content = env_file.read_text()
        lines = [l for l in content.split('\n') if '=' in l]

        # Check order
        assert lines[0].startswith("ALPHA")
        assert lines[1].startswith("MIKE")
        assert lines[2].startswith("ZEBRA")

    def test_write_env_file_with_header(self, tmp_path):
        """Test that file includes header comment."""
        env_file = tmp_path / ".env"
        config = {"KEY": "value"}

        write_env_file(str(env_file), config)

        content = env_file.read_text()
        assert "# Generated on" in content
        assert "# DO NOT COMMIT THIS FILE" in content

    def test_write_env_file_quotes_special_values(self, tmp_path):
        """Test that values with spaces are quoted."""
        env_file = tmp_path / ".env"
        config = {
            "SIMPLE": "value",
            "WITH_SPACES": "value with spaces",
            "WITH_HASH": "value#comment"
        }

        write_env_file(str(env_file), config)

        content = env_file.read_text()
        assert 'SIMPLE=value' in content
        assert 'WITH_SPACES="value with spaces"' in content
        assert 'WITH_HASH="value#comment"' in content

    def test_write_env_file_escapes_quotes(self, tmp_path):
        """Test that quotes in values are escaped."""
        env_file = tmp_path / ".env"
        config = {"KEY": 'value with "quotes"'}

        write_env_file(str(env_file), config)

        content = env_file.read_text()
        assert r'KEY="value with \"quotes\""' in content

    def test_write_env_file_empty_config(self, tmp_path):
        """Test writing empty configuration."""
        env_file = tmp_path / ".env"
        config = {}

        write_env_file(str(env_file), config)

        content = env_file.read_text()
        # Should still have header
        assert "# Generated on" in content

    def test_write_env_file_permissions(self, tmp_path):
        """Test that file permissions are set to 600."""
        env_file = tmp_path / ".env"
        config = {"KEY": "value"}

        write_env_file(str(env_file), config)

        # Check file permissions
        file_stat = env_file.stat()
        mode = stat.S_IMODE(file_stat.st_mode)

        # Should be readable and writable by owner only (0o600)
        expected = stat.S_IRUSR | stat.S_IWUSR
        assert mode == expected

    def test_write_env_file_invalid_config_type(self, tmp_path):
        """Test error when config is not a dictionary."""
        env_file = tmp_path / ".env"

        with pytest.raises(ValueError) as exc_info:
            write_env_file(str(env_file), "not a dict")

        assert "must be a dictionary" in str(exc_info.value).lower()

    def test_write_env_file_invalid_key(self, tmp_path):
        """Test error when key is invalid."""
        env_file = tmp_path / ".env"
        config = {"invalid-key": "value"}

        with pytest.raises(ValueError) as exc_info:
            write_env_file(str(env_file), config)

        assert "invalid variable name" in str(exc_info.value).lower()

    def test_write_env_file_non_string_key(self, tmp_path):
        """Test error when key is not a string."""
        env_file = tmp_path / ".env"
        config = {123: "value"}

        with pytest.raises(ValueError) as exc_info:
            write_env_file(str(env_file), config)

        assert "must be strings" in str(exc_info.value).lower()

    def test_write_env_file_overwrites_existing(self, tmp_path):
        """Test that existing file is overwritten."""
        env_file = tmp_path / ".env"
        env_file.write_text("OLD_CONTENT=old")

        config = {"NEW_CONTENT": "new"}
        write_env_file(str(env_file), config)

        content = env_file.read_text()
        assert "NEW_CONTENT=new" in content
        assert "OLD_CONTENT" not in content

    def test_write_env_file_trailing_newline(self, tmp_path):
        """Test that file ends with newline."""
        env_file = tmp_path / ".env"
        config = {"KEY": "value"}

        write_env_file(str(env_file), config)

        content = env_file.read_text()
        assert content.endswith('\n')
