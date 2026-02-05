"""
Utility functions for setup scripts.
"""

from .validators import (
    validate_database_url,
    validate_password_strength,
    validate_port,
    validate_hostname,
    validate_email,
    validate_path,
    validate_jwt_key,
    validate_env_file,
)

from .config_parser import (
    parse_env_file,
    parse_yaml_config,
    merge_configs,
    substitute_env_vars,
    load_env_template,
    write_env_file,
)

from .docker_utils import (
    check_docker_installed,
    check_docker_running,
    check_docker_compose_installed,
    check_port_available,
    run_docker_compose,
    get_container_status,
    wait_for_healthy,
    get_container_logs,
    check_image_exists,
)

__all__ = [
    "validate_database_url",
    "validate_password_strength",
    "validate_port",
    "validate_hostname",
    "validate_email",
    "validate_path",
    "validate_jwt_key",
    "validate_env_file",
    "parse_env_file",
    "parse_yaml_config",
    "merge_configs",
    "substitute_env_vars",
    "load_env_template",
    "write_env_file",
    "check_docker_installed",
    "check_docker_running",
    "check_docker_compose_installed",
    "check_port_available",
    "run_docker_compose",
    "get_container_status",
    "wait_for_healthy",
    "get_container_logs",
    "check_image_exists",
]
