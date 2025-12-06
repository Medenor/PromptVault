# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Configuration module for PromptVault.

This module provides centralized configuration management for all aspects
of the application including authentication, database, and general settings.

Available configurations:
    - auth_settings: Authentication and security configuration
    - AuthConfig: Authentication configuration class
"""

from src.config.auth_config import AuthConfig, auth_settings

__all__ = ["AuthConfig", "auth_settings"]
