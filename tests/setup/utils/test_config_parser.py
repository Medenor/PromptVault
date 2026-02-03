# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Unit tests for configuration parsing utilities."""

import pytest
import tempfile
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
    write_env_file,
)


class TestParseEnvFile:
    """Test .env file parsing."""

    def test_parse_simple_env_file(self):
        """Test parsing simple .env file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp:
            tmp.write("KEY1=value1\n")
            tmp.write("KEY2=value2\n")
            tmp_path = tmp.name

        try:
            config = parse_env_file(tmp_path)
            assert config["KEY1"] == "value1"
            assert config["KEY2"] == "value2"
        finally:
            os.unlink(tmp_path)

    def test_parse_env_file_with_comments(self):
        """Test parsing .env file with comments."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp:
            tmp.write("# This is a comment\n")
            tmp.write("KEY1=value1\n")
            tmp.write("# Another comment\n")
            tmp.write("KEY2=value2\n")
            tmp_path = tmp.name

        try:
            config = parse_env_file(tmp_path)
            assert len(config) == 2
            assert config["KEY1"] == "value1"
        finally:
            os.unlink(tmp_path)

    def test_parse_env_file_with_empty_lines(self):
        """Test parsing .env file with empty lines."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp:
            tmp.write("KEY1=value1\n")
            tmp.write("\n")
            tmp.write("\n")
            tmp.write("KEY2=value2\n")
            tmp_path = tmp.name

        try:
            config = parse_env_file(tmp_path)
            assert len(config) == 2
        finally:
            os.unlink(tmp_path)

    def test_parse_env_file_with_quoted_values(self):
        """Test parsing .env file with quoted values."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp:
            tmp.write('KEY1="double quoted"\n')
            tmp.write("KEY2='single quoted'\n")
            tmp.write('KEY3=unquoted\n')
            tmp_path = tmp.name

        try:
            config = parse_env_file(tmp_path)
            assert config["KEY1"] == "double quoted"
            assert config["KEY2"] == "single quoted"
            assert config["KEY3"] == "unquoted"
        finally:
            os.unlink(tmp_path)

    def test_parse_env_file_with_equals_in_value(self):
        """Test parsing .env file with equals sign in value."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp:
            tmp.write("DATABASE_URL=postgresql://user:pass@host/db?param=value\n")
            tmp_path = tmp.name

        try:
            config = parse_env_file(tmp_path)
            assert "param=value" in config["DATABASE_URL"]
        finally:
            os.unlink(tmp_path)

    def test_parse_env_file_with_whitespace(self):
        """Test parsing .env file with whitespace."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp:
            tmp.write("  KEY1  =  value1  \n")
            tmp.write("KEY2=value2\n")
            tmp_path = tmp.name

        try:
            config = parse_env_file(tmp_path)
            assert config["KEY1"] == "value1"
            assert config["KEY2"] == "value2"
        finally:
            os.unlink(tmp_path)

    def test_parse_env_file_empty_value(self):
        """Test parsing .env file with empty value."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp:
            tmp.write("KEY1=\n")
            tmp.write("KEY2=value2\n")
            tmp_path = tmp.name

        try:
            config = parse_env_file(tmp_path)
            assert config["KEY1"] == ""
            assert config["KEY2"] == "value2"
        finally:
            os.unlink(tmp_path)

    def test_parse_nonexistent_file(self):
        """Test parsing nonexistent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_env_file("/nonexistent/.env")

    def test_parse_directory_path(self):
        """Test parsing directory path raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="not a file"):
                parse_env_file(tmpdir)

    def test_parse_invalid_format_missing_equals(self):
        """Test parsing file with invalid format raises ValueError."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp:
            tmp.write("INVALID_LINE\n")
            tmp_path = tmp.name

        try:
            with pytest.raises(ValueError, match="Missing '=' separator"):
                parse_env_file(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_parse_invalid_variable_name(self):
        """Test parsing file with invalid variable name raises ValueError."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp:
            tmp.write("123INVALID=value\n")
            tmp_path = tmp.name

        try:
            with pytest.raises(ValueError, match="Invalid variable name"):
                parse_env_file(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_parse_empty_variable_name(self):
        """Test parsing file with empty variable name raises ValueError."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.env') as tmp:
            tmp.write("=value\n")
            tmp_path = tmp.name

        try:
            with pytest.raises(ValueError, match="Empty variable name"):
                parse_env_file(tmp_path)
        finally:
            os.unlink(tmp_path)


class TestParseYamlConfig:
    """Test YAML configuration parsing."""

    def test_parse_simple_yaml(self):
        """Test parsing simple YAML file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tmp:
            tmp.write("database:\n")
            tmp.write("  host: localhost\n")
            tmp.write("  port: 5432\n")
            tmp.write("debug: true\n")
            tmp_path = tmp.name

        try:
            config = parse_yaml_config(tmp_path)
            assert config["database"]["host"] == "localhost"
            assert config["database"]["port"] == 5432
            assert config["debug"] is True
        finally:
            os.unlink(tmp_path)

    def test_parse_empty_yaml(self):
        """Test parsing empty YAML file returns empty dict."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tmp:
            tmp_path = tmp.name

        try:
            config = parse_yaml_config(tmp_path)
            assert config == {}
        finally:
            os.unlink(tmp_path)

    def test_parse_yaml_with_nested_structures(self):
        """Test parsing YAML with nested structures."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tmp:
            tmp.write("server:\n")
            tmp.write("  database:\n")
            tmp.write("    primary:\n")
            tmp.write("      host: db1.example.com\n")
            tmp.write("      port: 5432\n")
            tmp_path = tmp.name

        try:
            config = parse_yaml_config(tmp_path)
            assert config["server"]["database"]["primary"]["host"] == "db1.example.com"
        finally:
            os.unlink(tmp_path)

    def test_parse_yaml_with_list(self):
        """Test parsing YAML with lists."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tmp:
            tmp.write("servers:\n")
            tmp.write("  - host: server1\n")
            tmp.write("  - host: server2\n")
            tmp_path = tmp.name

        try:
            config = parse_yaml_config(tmp_path)
            assert len(config["servers"]) == 2
            assert config["servers"][0]["host"] == "server1"
        finally:
            os.unlink(tmp_path)

    def test_parse_nonexistent_yaml(self):
        """Test parsing nonexistent YAML raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_yaml_config("/nonexistent/config.yml")

    def test_parse_yaml_directory(self):
        """Test parsing directory raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with pytest.raises(ValueError, match="not a file"):
                parse_yaml_config(tmpdir)

    def test_parse_invalid_yaml(self):
        """Test parsing invalid YAML raises ValueError."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tmp:
            tmp.write("invalid: yaml: syntax:\n")
            tmp.write("  - wrong\n")
            tmp.write("- indentation\n")
            tmp_path = tmp.name

        try:
            with pytest.raises(ValueError, match="Invalid YAML format"):
                parse_yaml_config(tmp_path)
        finally:
            os.unlink(tmp_path)

    def test_parse_yaml_non_dict_root(self):
        """Test parsing YAML with non-dict root raises ValueError."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.yml') as tmp:
            tmp.write("- item1\n")
            tmp.write("- item2\n")
            tmp_path = tmp.name

        try:
            with pytest.raises(ValueError, match="must contain a mapping/dictionary"):
                parse_yaml_config(tmp_path)
        finally:
            os.unlink(tmp_path)

    @patch('scripts.setup.utils.config_parser.yaml', None)
    def test_parse_yaml_without_pyyaml(self):
        """Test parsing YAML without PyYAML installed raises ImportError."""
        with pytest.raises(ImportError, match="PyYAML is required"):
            parse_yaml_config("/some/file.yml")


class TestMergeConfigs:
    """Test configuration merging."""

    def test_merge_simple_configs(self):
        """Test merging simple configurations."""
        base = {"key1": "value1", "key2": "value2"}
        override = {"key2": "new_value2", "key3": "value3"}

        result = merge_configs(base, override)

        assert result["key1"] == "value1"
        assert result["key2"] == "new_value2"
        assert result["key3"] == "value3"

    def test_merge_nested_configs(self):
        """Test merging nested configurations."""
        base = {
            "database": {
                "host": "localhost",
                "port": 5432,
                "name": "mydb"
            },
            "debug": False
        }
        override = {
            "database": {
                "port": 3306,
                "user": "admin"
            },
            "debug": True
        }

        result = merge_configs(base, override)

        assert result["database"]["host"] == "localhost"
        assert result["database"]["port"] == 3306
        assert result["database"]["name"] == "mydb"
        assert result["database"]["user"] == "admin"
        assert result["debug"] is True

    def test_merge_preserves_original(self):
        """Test that merging doesn't modify original dictionaries."""
        base = {"key1": "value1"}
        override = {"key1": "value2"}

        result = merge_configs(base, override)

        assert base["key1"] == "value1"
        assert result["key1"] == "value2"

    def test_merge_empty_base(self):
        """Test merging with empty base."""
        base = {}
        override = {"key1": "value1"}

        result = merge_configs(base, override)

        assert result["key1"] == "value1"

    def test_merge_empty_override(self):
        """Test merging with empty override."""
        base = {"key1": "value1"}
        override = {}

        result = merge_configs(base, override)

        assert result["key1"] == "value1"

    def test_merge_deeply_nested(self):
        """Test merging deeply nested configurations."""
        base = {
            "level1": {
                "level2": {
                    "level3": {
                        "key1": "value1",
                        "key2": "value2"
                    }
                }
            }
        }
        override = {
            "level1": {
                "level2": {
                    "level3": {
                        "key2": "new_value2",
                        "key3": "value3"
                    }
                }
            }
        }

        result = merge_configs(base, override)

        assert result["level1"]["level2"]["level3"]["key1"] == "value1"
        assert result["level1"]["level2"]["level3"]["key2"] == "new_value2"
        assert result["level1"]["level2"]["level3"]["key3"] == "value3"

    def test_merge_different_types(self):
        """Test merging when values have different types."""
        base = {"key1": {"nested": "value"}}
        override = {"key1": "simple_value"}

        result = merge_configs(base, override)

        assert result["key1"] == "simple_value"


class TestSubstituteEnvVars:
    """Test environment variable substitution."""

    def test_substitute_simple_vars(self):
        """Test substituting simple variables."""
        template = "http://${HOST}:${PORT}"
        values = {"HOST": "localhost", "PORT": "8080"}

        result = substitute_env_vars(template, values)

        assert result == "http://localhost:8080"

    def test_substitute_with_default_values(self):
        """Test substituting with default values."""
        template = "${HOST:-localhost}:${PORT:-8080}"
        values = {}

        result = substitute_env_vars(template, values)

        assert result == "localhost:8080"

    def test_substitute_with_partial_defaults(self):
        """Test substituting with some values and some defaults."""
        template = "${HOST:-localhost}:${PORT:-8080}"
        values = {"HOST": "example.com"}

        result = substitute_env_vars(template, values)

        assert result == "example.com:8080"

    def test_substitute_simple_format(self):
        """Test substituting simple $VAR format."""
        template = "Server: $HOST"
        values = {"HOST": "localhost"}

        result = substitute_env_vars(template, values)

        assert result == "Server: localhost"

    def test_substitute_missing_var_without_default(self):
        """Test substituting missing variable without default leaves it as-is."""
        template = "${MISSING_VAR}"
        values = {}

        result = substitute_env_vars(template, values)

        assert result == "${MISSING_VAR}"

    def test_substitute_empty_string(self):
        """Test substituting in empty string."""
        template = ""
        values = {"KEY": "value"}

        result = substitute_env_vars(template, values)

        assert result == ""

    def test_substitute_no_variables(self):
        """Test substituting when no variables present."""
        template = "No variables here"
        values = {"KEY": "value"}

        result = substitute_env_vars(template, values)

        assert result == "No variables here"

    def test_substitute_multiple_occurrences(self):
        """Test substituting same variable multiple times."""
        template = "$VAR is great, $VAR is awesome, $VAR!"
        values = {"VAR": "Python"}

        result = substitute_env_vars(template, values)

        assert result == "Python is great, Python is awesome, Python!"

    def test_substitute_complex_template(self):
        """Test substituting in complex template."""
        template = "postgresql://${DB_USER}:${DB_PASS}@${DB_HOST:-localhost}:${DB_PORT:-5432}/${DB_NAME}"
        values = {
            "DB_USER": "admin",
            "DB_PASS": "secret",
            "DB_NAME": "mydb"
        }

        result = substitute_env_vars(template, values)

        assert result == "postgresql://admin:secret@localhost:5432/mydb"


class TestLoadEnvTemplate:
    """Test loading .env.example template."""

    def test_load_env_template_from_current_dir(self):
        """Test loading .env.example from current directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_example = Path(tmpdir) / ".env.example"
            env_example.write_text("KEY1=value1\nKEY2=value2\n")

            with patch('scripts.setup.utils.config_parser.Path.cwd', return_value=Path(tmpdir)):
                config = load_env_template()
                assert config["KEY1"] == "value1"
                assert config["KEY2"] == "value2"

    def test_load_env_template_from_parent_dir(self):
        """Test loading .env.example from parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_example = Path(tmpdir) / ".env.example"
            env_example.write_text("KEY1=value1\n")

            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()

            with patch('scripts.setup.utils.config_parser.Path.cwd', return_value=subdir):
                config = load_env_template()
                assert config["KEY1"] == "value1"

    def test_load_env_template_not_found(self):
        """Test loading when .env.example not found raises FileNotFoundError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('scripts.setup.utils.config_parser.Path.cwd', return_value=Path(tmpdir)):
                with pytest.raises(FileNotFoundError, match=".env.example"):
                    load_env_template()


class TestWriteEnvFile:
    """Test writing .env file."""

    def test_write_simple_config(self):
        """Test writing simple configuration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")
            config = {
                "KEY1": "value1",
                "KEY2": "value2"
            }

            write_env_file(env_path, config)

            assert os.path.exists(env_path)
            content = Path(env_path).read_text()
            assert "KEY1=value1" in content
            assert "KEY2=value2" in content

    def test_write_config_with_comments(self):
        """Test that written file includes header comments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")
            config = {"KEY": "value"}

            write_env_file(env_path, config)

            content = Path(env_path).read_text()
            assert "# Generated on" in content
            assert "# DO NOT COMMIT" in content

    def test_write_config_sorted_keys(self):
        """Test that keys are sorted alphabetically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")
            config = {
                "ZEBRA": "value",
                "APPLE": "value",
                "MIDDLE": "value"
            }

            write_env_file(env_path, config)

            content = Path(env_path).read_text()
            lines = [line for line in content.split('\n') if '=' in line]
            assert lines[0].startswith("APPLE")
            assert lines[1].startswith("MIDDLE")
            assert lines[2].startswith("ZEBRA")

    def test_write_config_with_special_chars(self):
        """Test writing values with special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")
            config = {
                "URL": "http://example.com/path?param=value",
                "MESSAGE": "Hello World",
                "COMMENT": "This has # in it"
            }

            write_env_file(env_path, config)

            content = Path(env_path).read_text()
            assert 'MESSAGE="Hello World"' in content
            assert 'COMMENT="This has # in it"' in content

    def test_write_config_file_permissions(self):
        """Test that file permissions are set to 600."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")
            config = {"KEY": "value"}

            write_env_file(env_path, config)

            file_stat = os.stat(env_path)
            file_mode = stat.S_IMODE(file_stat.st_mode)
            expected_mode = stat.S_IRUSR | stat.S_IWUSR  # 0o600

            assert file_mode == expected_mode

    def test_write_config_not_dict(self):
        """Test writing non-dict config raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")

            with pytest.raises(ValueError, match="must be a dictionary"):
                write_env_file(env_path, "not a dict")

    def test_write_config_invalid_key(self):
        """Test writing config with invalid key raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")
            config = {"123INVALID": "value"}

            with pytest.raises(ValueError, match="Invalid variable name"):
                write_env_file(env_path, config)

    def test_write_config_non_string_key(self):
        """Test writing config with non-string key raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")
            config = {123: "value"}

            with pytest.raises(ValueError, match="must be strings"):
                write_env_file(env_path, config)

    def test_write_config_empty_value(self):
        """Test writing config with empty value."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")
            config = {
                "KEY1": "",
                "KEY2": "value"
            }

            write_env_file(env_path, config)

            content = Path(env_path).read_text()
            assert "KEY1=" in content
            assert "KEY2=value" in content

    def test_write_config_overwrites_existing(self):
        """Test that writing overwrites existing file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = os.path.join(tmpdir, ".env")

            # Write first config
            config1 = {"KEY1": "value1"}
            write_env_file(env_path, config1)

            # Write second config
            config2 = {"KEY2": "value2"}
            write_env_file(env_path, config2)

            content = Path(env_path).read_text()
            assert "KEY2=value2" in content
            assert "KEY1" not in content
