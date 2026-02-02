"""
Configuration file parsing and manipulation utilities.

Provides functions for working with .env files, YAML configurations,
and template variable substitution.
"""

import re
import os
import stat
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

try:
    import yaml
except ImportError:
    yaml = None


def parse_env_file(path: str) -> Dict[str, str]:
    """
    Parse .env file into dictionary.

    Reads a .env file and parses it into a dictionary of key-value pairs.
    Handles comments, empty lines, quoted values, and whitespace trimming.

    Format:
        - KEY=value
        - KEY="quoted value"
        - KEY='single quoted value'
        - # Comments (lines starting with #)
        - Empty lines (ignored)

    Args:
        path: Path to the .env file

    Returns:
        Dictionary mapping variable names to their values

    Raises:
        FileNotFoundError: If the .env file doesn't exist
        PermissionError: If the .env file is not readable
        ValueError: If the file contains invalid format

    Examples:
        >>> config = parse_env_file(".env")
        >>> config["DATABASE_URL"]
        'postgresql://user:pass@localhost:5432/db'

        >>> # File content:
        >>> # DATABASE_URL=postgresql://localhost/db
        >>> # API_KEY="secret-key-123"
        >>> # # This is a comment
        >>> # DEBUG=true
        >>> config = parse_env_file(".env")
        >>> len(config)
        3
    """
    path_obj = Path(path)

    if not path_obj.exists():
        raise FileNotFoundError(f"Env file not found: {path}")

    if not path_obj.is_file():
        raise ValueError(f"Path is not a file: {path}")

    result = {}

    try:
        with open(path_obj, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except PermissionError:
        raise PermissionError(f"Cannot read file: {path}")
    except Exception as e:
        raise ValueError(f"Error reading file: {str(e)}")

    for line_num, line in enumerate(lines, 1):
        # Strip whitespace
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue

        # Check for = separator
        if '=' not in line:
            raise ValueError(f"Line {line_num}: Missing '=' separator in: {line}")

        # Split on first = only
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()

        # Validate key format
        if not key:
            raise ValueError(f"Line {line_num}: Empty variable name")

        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', key):
            raise ValueError(f"Line {line_num}: Invalid variable name '{key}'")

        # Handle quoted values
        if value:
            # Remove quotes if present (both single and double)
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]

        result[key] = value

    return result


def parse_yaml_config(path: str) -> Dict[str, Any]:
    """
    Parse YAML configuration file.

    Loads a YAML file safely and returns its contents as a dictionary.
    Handles file not found and parsing errors gracefully.

    Args:
        path: Path to the YAML file

    Returns:
        Dictionary containing the parsed YAML configuration

    Raises:
        ImportError: If PyYAML is not installed
        FileNotFoundError: If the YAML file doesn't exist
        ValueError: If the YAML file is invalid or cannot be parsed

    Examples:
        >>> config = parse_yaml_config("config.yaml")
        >>> config["database"]["host"]
        'localhost'

        >>> # File content:
        >>> # database:
        >>> #   host: localhost
        >>> #   port: 5432
        >>> # debug: true
        >>> config = parse_yaml_config("config.yaml")
        >>> config["debug"]
        True
    """
    if yaml is None:
        raise ImportError(
            "PyYAML is required for YAML parsing. "
            "Install it with: pip install PyYAML"
        )

    path_obj = Path(path)

    if not path_obj.exists():
        raise FileNotFoundError(f"YAML file not found: {path}")

    if not path_obj.is_file():
        raise ValueError(f"Path is not a file: {path}")

    try:
        with open(path_obj, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Handle empty YAML file
        if config is None:
            return {}

        # Ensure we return a dictionary
        if not isinstance(config, dict):
            raise ValueError(f"YAML file must contain a mapping/dictionary at root level")

        return config

    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML format in {path}: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error reading YAML file {path}: {str(e)}")


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge configuration dictionaries with deep merge support.

    Recursively merges two dictionaries, with override values taking precedence.
    For nested dictionaries, merges recursively. For other types, override replaces base.
    Does not modify the original dictionaries.

    Args:
        base: Base configuration dictionary
        override: Override configuration dictionary (takes precedence)

    Returns:
        New merged dictionary

    Examples:
        >>> base = {"db": {"host": "localhost", "port": 5432}, "debug": False}
        >>> override = {"db": {"port": 3306}, "debug": True}
        >>> merged = merge_configs(base, override)
        >>> merged["db"]["host"]
        'localhost'
        >>> merged["db"]["port"]
        3306
        >>> merged["debug"]
        True

        >>> # Simple override
        >>> base = {"key1": "value1", "key2": "value2"}
        >>> override = {"key2": "new_value2", "key3": "value3"}
        >>> merged = merge_configs(base, override)
        >>> merged
        {'key1': 'value1', 'key2': 'new_value2', 'key3': 'value3'}
    """
    # Create a copy of base to avoid modifying original
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursively merge nested dictionaries
            result[key] = merge_configs(result[key], value)
        else:
            # Override value (or add new key)
            result[key] = value

    return result


def substitute_env_vars(template: str, values: Dict[str, str]) -> str:
    """
    Substitute environment variables in template string.

    Replaces variable references in the template with actual values.
    Supports two formats:
    - ${VAR_NAME} - Standard format
    - ${VAR_NAME:-default} - With default value
    - $VAR_NAME - Simple format (alphanumeric and underscore only)

    Missing variables without defaults are left as-is.

    Args:
        template: Template string containing variable references
        values: Dictionary mapping variable names to values

    Returns:
        String with variables substituted

    Examples:
        >>> values = {"HOST": "localhost", "PORT": "8080"}
        >>> substitute_env_vars("http://${HOST}:${PORT}", values)
        'http://localhost:8080'

        >>> # With default values
        >>> substitute_env_vars("${MISSING:-default}", {})
        'default'
        >>> substitute_env_vars("${HOST:-localhost}", {"HOST": "example.com"})
        'example.com'

        >>> # Simple format
        >>> substitute_env_vars("Server: $HOST", {"HOST": "localhost"})
        'Server: localhost'

        >>> # Missing variable without default (left as-is)
        >>> substitute_env_vars("${MISSING}", {})
        '${MISSING}'
    """
    result = template

    # Pattern 1: ${VAR_NAME:-default} with default value
    pattern_with_default = r'\$\{([A-Za-z_][A-Za-z0-9_]*):-([^}]*)\}'

    def replace_with_default(match):
        var_name = match.group(1)
        default_value = match.group(2)
        return values.get(var_name, default_value)

    result = re.sub(pattern_with_default, replace_with_default, result)

    # Pattern 2: ${VAR_NAME} without default
    pattern_braces = r'\$\{([A-Za-z_][A-Za-z0-9_]*)\}'

    def replace_braces(match):
        var_name = match.group(1)
        # Only replace if value exists, otherwise leave as-is
        return values.get(var_name, match.group(0))

    result = re.sub(pattern_braces, replace_braces, result)

    # Pattern 3: $VAR_NAME simple format
    pattern_simple = r'\$([A-Za-z_][A-Za-z0-9_]*)'

    def replace_simple(match):
        var_name = match.group(1)
        # Only replace if value exists, otherwise leave as-is
        return values.get(var_name, match.group(0))

    result = re.sub(pattern_simple, replace_simple, result)

    return result


def load_env_template() -> Dict[str, str]:
    """
    Load .env.example as template configuration.

    Reads the .env.example file from the project root and parses it
    into a dictionary. This provides a template for required environment
    variables.

    Returns:
        Dictionary containing template configuration from .env.example

    Raises:
        FileNotFoundError: If .env.example doesn't exist
        ValueError: If .env.example has invalid format

    Examples:
        >>> template = load_env_template()
        >>> "DATABASE_URL" in template
        True
        >>> template["DEBUG"]
        'false'
    """
    # Find project root (look for .env.example)
    current = Path.cwd()
    env_example_path = None

    # Search up to 5 levels up for .env.example
    for _ in range(5):
        candidate = current / ".env.example"
        if candidate.exists():
            env_example_path = candidate
            break
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    if env_example_path is None:
        raise FileNotFoundError(
            ".env.example file not found in current directory or parent directories"
        )

    return parse_env_file(str(env_example_path))


def write_env_file(path: str, config: Dict[str, str]) -> None:
    """
    Write configuration to .env file.

    Writes a dictionary of key-value pairs to a .env file in the standard format.
    Keys are sorted alphabetically for consistency. Adds a header comment with
    timestamp. Sets file permissions to 600 (owner read/write only) for security.

    Args:
        path: Path where the .env file should be written
        config: Dictionary of configuration key-value pairs

    Raises:
        ValueError: If config is not a dictionary or contains invalid keys
        PermissionError: If cannot write to the specified path
        OSError: If cannot set file permissions

    Examples:
        >>> config = {
        ...     "DATABASE_URL": "postgresql://localhost/db",
        ...     "DEBUG": "false",
        ...     "SECRET_KEY": "my-secret-key"
        ... }
        >>> write_env_file(".env", config)

        >>> # Result file content:
        >>> # # Generated on 2024-01-15 10:30:45
        >>> # # DO NOT COMMIT THIS FILE
        >>> #
        >>> # DATABASE_URL=postgresql://localhost/db
        >>> # DEBUG=false
        >>> # SECRET_KEY=my-secret-key
    """
    if not isinstance(config, dict):
        raise ValueError("Config must be a dictionary")

    path_obj = Path(path)

    # Validate all keys
    for key in config.keys():
        if not isinstance(key, str):
            raise ValueError(f"All keys must be strings, got: {type(key)}")
        if not re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', key):
            raise ValueError(f"Invalid variable name: {key}")

    # Prepare content
    lines = []

    # Add header
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"# Generated on {timestamp}")
    lines.append("# DO NOT COMMIT THIS FILE")
    lines.append("")

    # Sort keys alphabetically and add to file
    for key in sorted(config.keys()):
        value = config[key]

        # Quote value if it contains spaces or special characters
        if value and (' ' in value or '#' in value or '"' in value or "'" in value):
            # Escape any existing quotes
            value = value.replace('"', '\\"')
            lines.append(f'{key}="{value}"')
        else:
            lines.append(f'{key}={value}')

    # Write to file
    try:
        with open(path_obj, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
            f.write('\n')  # Trailing newline
    except PermissionError:
        raise PermissionError(f"Cannot write to file: {path}")
    except Exception as e:
        raise OSError(f"Error writing file: {str(e)}")

    # Set file permissions to 600 (owner read/write only)
    try:
        os.chmod(path_obj, stat.S_IRUSR | stat.S_IWUSR)
    except Exception as e:
        # Log warning but don't fail - permissions might not be supported on all systems
        import warnings
        warnings.warn(f"Could not set file permissions on {path}: {str(e)}")
