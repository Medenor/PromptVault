#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Validation script for rate limiting middleware.

This script validates that the rate limiting middleware is properly
installed and can be imported without errors.

Usage:
    python validate_rate_limit.py
"""

import sys
from typing import List, Tuple

def validate_imports() -> List[Tuple[str, bool, str]]:
    """Validate all rate limiting imports.

    Returns:
        List of tuples (module_name, success, error_message)
    """
    results = []

    # Test 1: Import core module
    try:
        from src.web.middleware.rate_limit import (
            limiter,
            get_rate_limit_key,
            create_limiter,
            create_redis_client,
        )
        results.append(("src.web.middleware.rate_limit (core)", True, "OK"))
    except Exception as e:
        results.append(("src.web.middleware.rate_limit (core)", False, str(e)))

    # Test 2: Import rate limit functions
    try:
        from src.web.middleware.rate_limit import (
            auth_login_limit,
            auth_register_limit,
            password_reset_limit,
            api_limit,
            admin_limit,
        )
        results.append(("src.web.middleware.rate_limit (limits)", True, "OK"))
    except Exception as e:
        results.append(("src.web.middleware.rate_limit (limits)", False, str(e)))

    # Test 3: Import exception handler
    try:
        from src.web.middleware.rate_limit import (
            rate_limit_exceeded_handler,
            add_rate_limit_headers,
        )
        results.append(("src.web.middleware.rate_limit (handlers)", True, "OK"))
    except Exception as e:
        results.append(("src.web.middleware.rate_limit (handlers)", False, str(e)))

    # Test 4: Import from package
    try:
        from src.web.middleware import (
            limiter,
            auth_login_limit,
            rate_limit_exceeded_handler,
        )
        results.append(("src.web.middleware (package)", True, "OK"))
    except Exception as e:
        results.append(("src.web.middleware (package)", False, str(e)))

    # Test 5: Import configuration
    try:
        from src.config.auth_config import auth_settings
        redis_url = auth_settings.redis_url
        results.append(("src.config.auth_config (redis)", True, f"Redis URL: {redis_url}"))
    except Exception as e:
        results.append(("src.config.auth_config (redis)", False, str(e)))

    # Test 6: Import exceptions
    try:
        from src.services.exceptions import RateLimitExceededError
        results.append(("src.services.exceptions (rate limit)", True, "OK"))
    except Exception as e:
        results.append(("src.services.exceptions (rate limit)", False, str(e)))

    return results


def validate_functionality() -> List[Tuple[str, bool, str]]:
    """Validate rate limiting functionality.

    Returns:
        List of tuples (test_name, success, message)
    """
    results = []

    # Test 1: Create limiter
    try:
        from src.web.middleware.rate_limit import create_limiter
        limiter = create_limiter()
        results.append(("Create limiter", True, f"Limiter created: {type(limiter).__name__}"))
    except Exception as e:
        results.append(("Create limiter", False, str(e)))

    # Test 2: Get rate limit strings
    try:
        from src.web.middleware.rate_limit import (
            auth_login_limit,
            auth_register_limit,
            password_reset_limit,
        )
        login_limit = auth_login_limit()
        register_limit = auth_register_limit()
        reset_limit = password_reset_limit()
        results.append(
            ("Get rate limit strings", True,
             f"Login: {login_limit}, Register: {register_limit}, Reset: {reset_limit}")
        )
    except Exception as e:
        results.append(("Get rate limit strings", False, str(e)))

    # Test 3: Redis client creation (may fail if Redis not running)
    try:
        from src.web.middleware.rate_limit import create_redis_client
        redis_client = create_redis_client()
        if redis_client:
            results.append(("Create Redis client", True, "Redis connected"))
        else:
            results.append(("Create Redis client", True, "Redis not available (graceful fallback)"))
    except Exception as e:
        results.append(("Create Redis client", False, str(e)))

    # Test 4: Rate limit key generation
    try:
        from src.web.middleware.rate_limit import get_rate_limit_key
        from unittest.mock import Mock

        # Test with IP address
        request = Mock()
        request.state = Mock()
        request.state.user = None
        request.headers = {}
        request.client = Mock()
        request.client.host = "192.168.1.100"

        # We need to patch get_remote_address for this test
        from unittest.mock import patch
        with patch("src.web.middleware.rate_limit.get_remote_address") as mock_get_ip:
            mock_get_ip.return_value = "192.168.1.100"
            key = get_rate_limit_key(request)
            results.append(("Rate limit key generation", True, f"Key: {key}"))
    except Exception as e:
        results.append(("Rate limit key generation", False, str(e)))

    return results


def print_results(results: List[Tuple[str, bool, str]], title: str):
    """Print validation results."""
    print(f"\n{title}")
    print("=" * 80)

    success_count = sum(1 for _, success, _ in results if success)
    total_count = len(results)

    for name, success, message in results:
        status = "✓" if success else "✗"
        print(f"{status} {name:50s} {message}")

    print("=" * 80)
    print(f"Results: {success_count}/{total_count} tests passed")

    return success_count == total_count


def main():
    """Run all validation tests."""
    print("Rate Limiting Middleware Validation")
    print("=" * 80)
    print("This script validates the rate limiting middleware installation.")

    # Run import validation
    import_results = validate_imports()
    imports_ok = print_results(import_results, "Import Validation")

    # Run functionality validation
    func_results = validate_functionality()
    funcs_ok = print_results(func_results, "Functionality Validation")

    # Print summary
    print("\n" + "=" * 80)
    if imports_ok and funcs_ok:
        print("✓ ALL VALIDATIONS PASSED")
        print("\nThe rate limiting middleware is properly installed and ready to use.")
        print("\nNext steps:")
        print("1. Integrate with FastAPI app (see INTEGRATION.md)")
        print("2. Configure Redis connection in .env")
        print("3. Apply rate limits to authentication endpoints")
        print("4. Test with example app: python examples/rate_limit_example.py")
        return 0
    else:
        print("✗ SOME VALIDATIONS FAILED")
        print("\nPlease fix the errors above before using the rate limiting middleware.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
