"""
Comprehensive input validation functions for setup scripts.

All validators return a tuple: (is_valid: bool, error_message: str | None)
"""

import re
import os
from pathlib import Path
from typing import Tuple
from urllib.parse import urlparse


def validate_database_url(url: str) -> Tuple[bool, str | None]:
    """
    Validate database URL format.

    Supports PostgreSQL and SQLite database URLs.
    - PostgreSQL: postgresql://user:password@host:port/database
    - SQLite: sqlite:///path/to/database.db

    Args:
        url: Database URL string to validate

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Examples:
        >>> validate_database_url("postgresql://user:pass@localhost:5432/db")
        (True, None)
        >>> validate_database_url("sqlite:///./data.db")
        (True, None)
        >>> validate_database_url("invalid://url")
        (False, "Unsupported database scheme: invalid. Use postgresql or sqlite")
    """
    if not url or not isinstance(url, str):
        return False, "Database URL cannot be empty"

    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"

    scheme = parsed.scheme.lower()

    # Check for supported schemes
    if scheme not in ["postgresql", "sqlite"]:
        return False, f"Unsupported database scheme: {scheme}. Use postgresql or sqlite"

    # Validate PostgreSQL URL
    if scheme == "postgresql":
        if not parsed.username:
            return False, "PostgreSQL URL missing username"
        if not parsed.password:
            return False, "PostgreSQL URL missing password"
        if not parsed.hostname:
            return False, "PostgreSQL URL missing hostname"
        if not parsed.port:
            return False, "PostgreSQL URL missing port"
        if not parsed.path or parsed.path == "/":
            return False, "PostgreSQL URL missing database name"

        # Validate the database name (remove leading slash)
        db_name = parsed.path.lstrip("/")
        if not db_name:
            return False, "PostgreSQL URL missing database name"

    # Validate SQLite URL
    elif scheme == "sqlite":
        # SQLite URLs should have a path
        if not parsed.path:
            return False, "SQLite URL missing database path"

        # Check for proper SQLite URL format (sqlite:/// for absolute, sqlite:// for relative)
        if not url.startswith("sqlite:///") and not url.startswith("sqlite://"):
            return False, "SQLite URL must start with sqlite:/// or sqlite://"

    return True, None


def validate_password_strength(password: str, min_length: int = 16) -> Tuple[bool, str | None]:
    """
    Validate password complexity and strength.

    Requirements:
    - Minimum length (default: 16 characters)
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        password: Password string to validate
        min_length: Minimum required length (default: 16)

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Examples:
        >>> validate_password_strength("Ab1!defghijklmno")
        (True, None)
        >>> validate_password_strength("short")
        (False, "Password must be at least 16 characters long")
    """
    if not password or not isinstance(password, str):
        return False, "Password cannot be empty"

    # Check minimum length
    if len(password) < min_length:
        return False, f"Password must be at least {min_length} characters long"

    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"

    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"

    # Check for digit
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"

    # Check for special character
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>?/\\|`~]', password):
        return False, "Password must contain at least one special character"

    return True, None


def validate_port(port: int | str) -> Tuple[bool, str | None]:
    """
    Validate port number.

    Port must be a valid integer between 1 and 65535.

    Args:
        port: Port number as int or string

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Examples:
        >>> validate_port(8080)
        (True, None)
        >>> validate_port("443")
        (True, None)
        >>> validate_port(70000)
        (False, "Port must be between 1 and 65535")
    """
    try:
        port_num = int(port)
    except (ValueError, TypeError):
        return False, "Port must be a valid number"

    if port_num < 1 or port_num > 65535:
        return False, "Port must be between 1 and 65535"

    return True, None


def validate_hostname(hostname: str) -> Tuple[bool, str | None]:
    """
    Validate hostname format.

    Accepts:
    - Valid hostnames (RFC 1123)
    - IPv4 addresses
    - IPv6 addresses
    - localhost

    Args:
        hostname: Hostname or IP address string

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Examples:
        >>> validate_hostname("localhost")
        (True, None)
        >>> validate_hostname("example.com")
        (True, None)
        >>> validate_hostname("192.168.1.1")
        (True, None)
    """
    if not hostname or not isinstance(hostname, str):
        return False, "Hostname cannot be empty"

    # Check for localhost
    if hostname.lower() == "localhost":
        return True, None

    # Check for IPv4 address
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    if re.match(ipv4_pattern, hostname):
        # Validate each octet is 0-255
        octets = hostname.split('.')
        for octet in octets:
            if int(octet) > 255:
                return False, f"Invalid IPv4 address: octet {octet} exceeds 255"
        return True, None

    # Check for IPv6 address (simplified check)
    if ':' in hostname:
        # Basic IPv6 validation
        ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'
        if re.match(ipv6_pattern, hostname) or hostname == "::1":
            return True, None
        return False, "Invalid IPv6 address format"

    # Check for valid hostname (RFC 1123)
    # Hostname can contain alphanumeric characters, hyphens, and dots
    # Cannot start or end with hyphen or dot
    # Each label must be 1-63 characters
    # Total length must be <= 253 characters

    if len(hostname) > 253:
        return False, "Hostname exceeds maximum length of 253 characters"

    # Check basic hostname format (don't enforce length here, do it per-label below)
    hostname_pattern = r'^(?!-)[a-zA-Z0-9-]+(?<!-)(\.[a-zA-Z0-9-]+(?<!-))*$'
    if not re.match(hostname_pattern, hostname):
        return False, "Invalid hostname format. Must contain only alphanumeric characters, hyphens, and dots"

    # Check each label
    labels = hostname.split('.')
    for label in labels:
        if len(label) > 63:
            return False, f"Hostname label '{label}' exceeds maximum length of 63 characters (has {len(label)})"
        if label.startswith('-') or label.endswith('-'):
            return False, f"Hostname label '{label}' cannot start or end with hyphen"

    return True, None


def validate_email(email: str) -> Tuple[bool, str | None]:
    """
    Validate email address format.

    Uses a regex pattern to validate basic email format.
    Does not verify that the email actually exists.

    Args:
        email: Email address string

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Examples:
        >>> validate_email("user@example.com")
        (True, None)
        >>> validate_email("invalid.email")
        (False, "Invalid email format")
    """
    if not email or not isinstance(email, str):
        return False, "Email cannot be empty"

    # Basic email regex pattern
    # Allows: alphanumeric, dots, hyphens, underscores, plus signs
    # Requires @ symbol
    # Requires domain with at least one dot
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(email_pattern, email):
        return False, "Invalid email format"

    # Additional checks
    local_part, domain = email.rsplit('@', 1)

    if len(local_part) > 64:
        return False, "Email local part (before @) exceeds maximum length of 64 characters"

    if len(domain) > 253:
        return False, "Email domain exceeds maximum length of 253 characters"

    # Check for consecutive dots
    if '..' in email:
        return False, "Email cannot contain consecutive dots"

    # Check local part doesn't start or end with dot
    if local_part.startswith('.') or local_part.endswith('.'):
        return False, "Email local part cannot start or end with a dot"

    return True, None


def validate_path(path: str, must_exist: bool = False) -> Tuple[bool, str | None]:
    """
    Validate file or directory path.

    Args:
        path: File or directory path string
        must_exist: If True, verify that the path exists

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Examples:
        >>> validate_path("/tmp/test.txt")
        (True, None)
        >>> validate_path("/tmp/test.txt", must_exist=True)
        (False, "Path does not exist: /tmp/test.txt")
    """
    if not path or not isinstance(path, str):
        return False, "Path cannot be empty"

    # Basic path validation
    try:
        path_obj = Path(path)
    except Exception as e:
        return False, f"Invalid path format: {str(e)}"

    # Check if path exists (if required)
    if must_exist:
        if not path_obj.exists():
            return False, f"Path does not exist: {path}"
    else:
        # For absolute paths, check if parent directory exists
        # For relative paths, don't validate parent (they're relative to CWD)
        if path_obj.is_absolute():
            parent = path_obj.parent
            if parent != path_obj and not parent.exists():
                return False, f"Parent directory does not exist: {parent}"

    return True, None


def validate_jwt_key(path: str, key_type: str) -> Tuple[bool, str | None]:
    """
    Validate JWT key file.

    Validates that the file:
    - Exists and is readable
    - Contains valid PEM format
    - Is the correct key type (private or public)
    - For EC keys, validates the proper key format

    Args:
        path: Path to the JWT key file
        key_type: Type of key ("private" or "public")

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Examples:
        >>> validate_jwt_key("/path/to/private.pem", "private")
        (True, None)
        >>> validate_jwt_key("/path/to/public.pem", "public")
        (True, None)
    """
    if not path or not isinstance(path, str):
        return False, "Key path cannot be empty"

    if key_type not in ["private", "public"]:
        return False, f"Invalid key type: {key_type}. Must be 'private' or 'public'"

    # Check if file exists
    path_obj = Path(path)
    if not path_obj.exists():
        return False, f"Key file does not exist: {path}"

    if not path_obj.is_file():
        return False, f"Key path is not a file: {path}"

    # Check if file is readable
    try:
        with open(path, 'r') as f:
            content = f.read()
    except PermissionError:
        return False, f"Key file is not readable: {path}"
    except Exception as e:
        return False, f"Error reading key file: {str(e)}"

    # Validate PEM format
    if not content.strip():
        return False, "Key file is empty"

    # Check for PEM headers/footers
    if key_type == "private":
        # Check for EC private key
        if "-----BEGIN EC PRIVATE KEY-----" in content and "-----END EC PRIVATE KEY-----" in content:
            # Valid EC private key format
            pass
        elif "-----BEGIN PRIVATE KEY-----" in content and "-----END PRIVATE KEY-----" in content:
            # Valid PKCS#8 private key format
            pass
        elif "-----BEGIN RSA PRIVATE KEY-----" in content and "-----END RSA PRIVATE KEY-----" in content:
            # Valid RSA private key format (for compatibility)
            pass
        else:
            return False, "Invalid private key format. Expected PEM format with proper BEGIN/END markers"

    elif key_type == "public":
        # Check for EC public key
        if "-----BEGIN PUBLIC KEY-----" in content and "-----END PUBLIC KEY-----" in content:
            # Valid public key format
            pass
        elif "-----BEGIN EC PUBLIC KEY-----" in content and "-----END EC PUBLIC KEY-----" in content:
            # Valid EC public key format (alternate)
            pass
        else:
            return False, "Invalid public key format. Expected PEM format with proper BEGIN/END markers"

    # Basic validation of PEM content (should be base64)
    lines = content.strip().split('\n')
    for line in lines:
        if line.startswith('-----'):
            continue
        # Check if line contains valid base64 characters
        if not re.match(r'^[A-Za-z0-9+/=\s]*$', line):
            return False, "Key file contains invalid characters (not valid base64)"

    return True, None


def validate_env_file(path: str) -> Tuple[bool, str | None]:
    """
    Validate .env file format and required variables.

    Checks:
    - File exists and is readable
    - Proper .env format (KEY=value)
    - No syntax errors
    - Returns list of issues if found

    Args:
        path: Path to the .env file

    Returns:
        Tuple of (is_valid, error_message)
        - (True, None) if valid
        - (False, error_message) if invalid

    Examples:
        >>> validate_env_file(".env")
        (True, None)
        >>> validate_env_file("missing.env")
        (False, "File does not exist: missing.env")
    """
    if not path or not isinstance(path, str):
        return False, "Env file path cannot be empty"

    # Check if file exists
    path_obj = Path(path)
    if not path_obj.exists():
        return False, f"File does not exist: {path}"

    if not path_obj.is_file():
        return False, f"Path is not a file: {path}"

    # Check if file is readable
    try:
        with open(path, 'r') as f:
            lines = f.readlines()
    except PermissionError:
        return False, f"File is not readable: {path}"
    except Exception as e:
        return False, f"Error reading file: {str(e)}"

    # Parse and validate .env format
    issues = []
    line_num = 0

    for line in lines:
        line_num += 1
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue

        # Check for valid KEY=value format
        if '=' not in line:
            issues.append(f"Line {line_num}: Missing '=' separator")
            continue

        # Split on first '=' only
        parts = line.split('=', 1)
        if len(parts) != 2:
            issues.append(f"Line {line_num}: Invalid format")
            continue

        key, value = parts
        key = key.strip()

        # Validate key format (must be valid identifier)
        if not key:
            issues.append(f"Line {line_num}: Empty variable name")
            continue

        # Key should be uppercase and contain only letters, numbers, and underscores
        if not re.match(r'^[A-Z_][A-Z0-9_]*$', key):
            issues.append(f"Line {line_num}: Invalid variable name '{key}'. Should be uppercase with underscores only")

    if issues:
        error_msg = "Env file validation issues:\n" + "\n".join(issues)
        return False, error_msg

    return True, None
