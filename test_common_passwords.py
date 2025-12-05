#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/raphael/Programmation/PromptVault')

from src.config.auth_config import AuthConfig
from src.services.auth.password_service import PasswordService

config = AuthConfig()
service = PasswordService(config)

print("=" * 80)
print("TESTING COMMON PASSWORD DETECTION WITH VARIATIONS")
print("=" * 80)

passwords_to_test = [
    ("Password123", "Base common password"),
    ("Password123!", "With exclamation mark"),
    ("Password123!!!", "With multiple exclamation marks"),
    ("Password123@", "With @ symbol"),
    ("P@ssw0rd", "With substituted characters"),
    ("password123", "Lowercase variant"),
    ("MySecureP@ssw0rd123", "Genuinely unique password"),
    ("SecureP@ss123", "Different secure password"),
]

for password, description in passwords_to_test:
    is_valid, errors = service.validate_password_policy(password)
    common_check = service._is_common_password_variation(password)
    
    print(f"\nPassword: {password!r} ({description})")
    print(f"  Is Common: {common_check}")
    print(f"  Valid: {is_valid}")
    
    if errors:
        for error in errors:
            print(f"    - {error}")

print("\n" + "=" * 80)
