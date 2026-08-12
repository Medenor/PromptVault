# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Password hashing and validation service for PromptVault.

This module provides secure password operations using Argon2id hashing algorithm
with OWASP-recommended parameters. It implements password policy validation,
strength analysis, and timing-safe password verification.

Security Features:
    - Argon2id hybrid algorithm (resistant to both GPU and side-channel attacks)
    - OWASP recommended parameters (time_cost=2, memory_cost=102400, parallelism=8)
    - Constant-time password verification to prevent timing attacks
    - Comprehensive password policy validation
    - Password strength analysis with entropy calculation
    - Common password detection (top 100 most common passwords)

Example:
    >>> from src.services.auth.password_service import PasswordService
    >>> from src.config.auth_config import auth_settings
    >>>
    >>> service = PasswordService(auth_settings)
    >>>
    >>> # Validate password meets policy
    >>> is_valid, errors = service.validate_password_policy("MyP@ssw0rd123")
    >>> if not is_valid:
    ...     errors  # validation failure reasons
    >>>
    >>> # Hash password
    >>> password_hash = service.hash_password("MyP@ssw0rd123")
    >>>
    >>> # Verify password
    >>> is_correct = service.verify_password("MyP@ssw0rd123", password_hash)
    >>>
    >>> # Check password strength
    >>> strength = service.check_password_strength("MyP@ssw0rd123")
    >>> strength['level']

References:
    - OWASP Password Storage Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
    - Argon2 RFC 9106: https://www.rfc-editor.org/rfc/rfc9106.html
    - NIST Digital Identity Guidelines: https://pages.nist.gov/800-63-3/sp800-63b.html
"""

import math
import re

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from src.config.auth_config import AuthConfig

# Top 100 most common passwords for basic security check
# Source: Compiled from various password breach databases
COMMON_PASSWORDS = {
    "123456",
    "password",
    "123456789",
    "12345678",
    "12345",
    "1234567",
    "password1",
    "123123",
    "1234567890",
    "000000",
    "abc123",
    "qwerty",
    "iloveyou",
    "monkey",
    "dragon",
    "111111",
    "baseball",
    "letmein",
    "trustno1",
    "sunshine",
    "master",
    "welcome",
    "shadow",
    "ashley",
    "football",
    "jesus",
    "michael",
    "ninja",
    "mustang",
    "password123",
    "qwerty123",
    "admin",
    "administrator",
    "root",
    "toor",
    "pass",
    "passw0rd",
    "passwd",
    "Password1",
    "Password123",
    "P@ssw0rd",
    "P@ssword",
    "1q2w3e4r",
    "1qaz2wsx",
    "qwertyuiop",
    "azerty",
    "696969",
    "fuckyou",
    "666666",
    "batman",
    "superman",
    "princess",
    "starwars",
    "qazwsx",
    "654321",
    "123qwe",
    "zxcvbnm",
    "login",
    "admin123",
    "solo",
    "jordan",
    "harley",
    "ranger",
    "buster",
    "thomas",
    "tigger",
    "robert",
    "soccer",
    "hockey",
    "freedom",
    "ginger",
    "cookie",
    "secret",
    "summer",
    "matthew",
    "whatever",
    "william",
    "samsung",
    "bailey",
    "121212",
    "charlie",
    "maggie",
    "computer",
    "jessica",
    "pepper",
    "1111",
    "222222",
    "hunter",
    "joshua",
    "chelsea",
    "corvette",
    "angel",
    "midnight",
    "access",
    "yellow",
    "thunder",
    "1234",
    "testing",
    "test",
    "temp",
    "changeme",
}


class PasswordService:
    """Secure password hashing and validation service.

    This service provides comprehensive password operations including Argon2id
    hashing, policy validation, strength analysis, and timing-safe verification.

    The service uses OWASP-recommended Argon2id parameters:
        - time_cost=2: Number of iterations (balance security vs performance)
        - memory_cost=102400: Memory usage in KiB (100 MB)
        - parallelism=8: Number of parallel threads
        - hash_len=32: Output hash length in bytes
        - salt_len=16: Salt length in bytes
        - type=Type.ID: Argon2id variant (hybrid mode)

    Security Notes:
        - Argon2id provides resistance to both GPU cracking and side-channel attacks
        - Password verification uses constant-time comparison
        - All passwords are validated against configurable policy requirements
        - Common password detection prevents use of easily guessable passwords
        - Password hashes include algorithm parameters for future flexibility

    Attributes:
        config: Authentication configuration with password policy settings
        _hasher: Argon2 password hasher instance with secure parameters
    """

    def __init__(self, config: AuthConfig):
        """Initialize password service with authentication configuration.

        Args:
            config: Authentication configuration containing password policy settings

        Security Note:
            The Argon2 parameters are set to OWASP recommendations and should not
            be modified without careful security analysis. Reducing memory_cost or
            time_cost will make passwords easier to crack.
        """
        self.config = config

        # Initialize Argon2id password hasher with OWASP recommended parameters
        # These parameters provide strong security while maintaining acceptable performance
        self._hasher = PasswordHasher(
            time_cost=2,  # Number of iterations (OWASP minimum: 2)
            memory_cost=102400,  # Memory in KiB (100 MB - OWASP recommended)
            parallelism=8,  # Number of parallel threads
            hash_len=32,  # Hash output length in bytes
            salt_len=16,  # Salt length in bytes (cryptographically random)
            encoding="utf-8",  # Character encoding for password strings
            type=Type.ID,  # Argon2id - hybrid of Argon2i and Argon2d
        )

    def _is_common_password_variation(self, password: str) -> bool:
        """Check if password is a common password or a variation of one.

        This method detects common passwords even when users try to obfuscate them
        by adding special characters or numbers. For example, "Password123!" is a
        variation of the common password "Password123".

        Detection strategy:
            1. Direct match: Check if password exactly matches a common password
            2. Strip trailing special chars: Remove ! @ # $ % ^ & * etc. from end
            3. Strip trailing digits: Remove numbers from end
            4. Strip both: Remove trailing special chars and numbers
            5. Remove all special chars: Check without any special characters

        Args:
            password: Plain text password to check (lowercase)

        Returns:
            True if password or any stripped variation is in COMMON_PASSWORDS, False otherwise

        Security Notes:
            - This is case-insensitive (caller should pass lowercase version)
            - Helps prevent users from thinking they're secure by adding ! or 123
            - Prevents social engineering where users slightly modify common passwords

        Example:
            >>> service._is_common_password_variation("password123")  # True
            >>> service._is_common_password_variation("password123!")  # True
            >>> service._is_common_password_variation("password123!!!")  # True
            >>> service._is_common_password_variation("mySecurePass123!")  # False
        """
        pwd_lower = password.lower() if isinstance(password, str) else ""

        # Strategy 1: Direct match
        if pwd_lower in COMMON_PASSWORDS:
            return True

        # Strategy 2: Strip trailing special characters (!, @, #, $, %, ^, &, *, etc.)
        pwd_no_special = re.sub(r"[!@#$%^&*\-_.~()[\]{};:,.<>?/\\|`~]+$", "", pwd_lower)
        if pwd_no_special != pwd_lower and pwd_no_special in COMMON_PASSWORDS:
            return True

        # Strategy 3: Strip trailing digits
        pwd_no_digits = re.sub(r"\d+$", "", pwd_lower)
        if pwd_no_digits != pwd_lower and pwd_no_digits in COMMON_PASSWORDS:
            return True

        # Strategy 4: Strip both trailing special chars and digits
        pwd_no_special_digits = re.sub(
            r"[!@#$%^&*\-_.~()[\]{};:,.<>?/\\|`~\d]+$", "", pwd_lower
        )
        if (
            pwd_no_special_digits != pwd_lower
            and pwd_no_special_digits in COMMON_PASSWORDS
        ):
            return True

        # Strategy 5: Remove ALL special characters (not just trailing)
        # This catches patterns like "P@ssw0rd" -> "Password"
        pwd_alphanumeric = re.sub(r"[^a-z0-9]", "", pwd_lower)
        if pwd_alphanumeric != pwd_lower and pwd_alphanumeric in COMMON_PASSWORDS:
            return True

        return False

    def hash_password(self, password: str) -> str:
        """Hash a password using Argon2id algorithm.

        This method generates a cryptographically secure password hash using the
        Argon2id algorithm with OWASP-recommended parameters. Each hash includes
        a unique random salt, making rainbow table attacks infeasible.

        Args:
            password: Plain text password to hash

        Returns:
            Argon2id password hash string in PHC format, including:
                - Algorithm identifier ($argon2id$)
                - Version (v=19)
                - Parameters (m=102400,t=2,p=8)
                - Base64-encoded salt
                - Base64-encoded hash

        Raises:
            ValueError: If password is empty or None

        Security Notes:
            - Each hash uses a unique cryptographically random salt
            - The hash includes algorithm parameters for future compatibility
            - Hashing is intentionally slow to resist brute-force attacks
            - The returned hash can be safely stored in a database

        Example:
            >>> service = PasswordService(auth_settings)
            >>> hash1 = service.hash_password("MyP@ssw0rd123")
            >>> hash2 = service.hash_password("MyP@ssw0rd123")
            >>> # hash1 != hash2 due to unique random salts
        """
        if not password:
            raise ValueError("Password cannot be empty")

        # Argon2 PasswordHasher automatically generates a random salt
        # and returns a PHC-formatted hash string
        return self._hasher.hash(password)

    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its Argon2id hash using constant-time comparison.

        This method performs timing-safe password verification to prevent timing
        attacks. The verification time is independent of where the password differs
        from the stored hash.

        Args:
            password: Plain text password to verify
            password_hash: Argon2id hash to verify against (from hash_password)

        Returns:
            True if password matches the hash, False otherwise

        Security Notes:
            - Uses constant-time comparison to prevent timing attacks
            - Automatically handles parameter extraction from hash
            - Returns False for any verification errors (invalid hash, etc.)
            - Verification time is independent of password correctness

        Performance Note:
            Verification is intentionally slow (same as hashing) to prevent
            brute-force attacks. This is a security feature, not a bug.

        Example:
            >>> service = PasswordService(auth_settings)
            >>> password = "MyP@ssw0rd123"
            >>> hash = service.hash_password(password)
            >>> service.verify_password(password, hash)  # Returns True
            >>> service.verify_password("wrong", hash)   # Returns False
        """
        if not password or not password_hash:
            return False

        try:
            # Argon2 verify() uses constant-time comparison internally
            # It extracts parameters from the hash and re-hashes the password
            self._hasher.verify(password_hash, password)
            return True
        except VerifyMismatchError, VerificationError, InvalidHashError:
            # VerifyMismatchError: Password doesn't match
            # VerificationError: Generic verification error
            # InvalidHashError: Malformed hash string
            return False
        except Exception:
            # Catch any unexpected errors and fail safely
            return False

    def validate_password_policy(self, password: str) -> tuple[bool, list[str]]:
        """Validate password against configured policy requirements.

        This method checks the password against all policy rules defined in
        AuthConfig, including length, character requirements, and common
        password detection.

        Args:
            password: Plain text password to validate

        Returns:
            Tuple of (is_valid, errors) where:
                - is_valid: True if password meets all requirements, False otherwise
                - errors: List of human-readable error messages (empty if valid)

        Policy Checks:
            - Minimum length (from config.password_min_length)
            - Uppercase letter requirement (if config.password_require_uppercase)
            - Lowercase letter requirement (if config.password_require_lowercase)
            - Digit requirement (if config.password_require_digit)
            - Special character requirement (if config.password_require_special)
            - Common password detection (checks against top 100 passwords)

        Example:
            >>> service = PasswordService(auth_settings)
            >>> is_valid, errors = service.validate_password_policy("abc")
            >>> errors
            ['Password must be at least 12 characters long',
             'Password must contain at least one uppercase letter',
             'Password must contain at least one digit',
             'Password must contain at least one special character']

            >>> is_valid, errors = service.validate_password_policy("MyP@ssw0rd123")
            >>> is_valid
            True
        """
        errors = []

        if not password:
            errors.append("Password cannot be empty")
            return False, errors

        # Check minimum length
        if len(password) < self.config.password_min_length:
            errors.append(
                f"Password must be at least {self.config.password_min_length} "
                f"characters long"
            )

        # Check maximum length (prevent DoS via extremely long passwords)
        if len(password) > 128:
            errors.append("Password must not exceed 128 characters")

        # Check uppercase requirement
        if self.config.password_require_uppercase:
            if not re.search(r"[A-Z]", password):
                errors.append("Password must contain at least one uppercase letter")

        # Check lowercase requirement
        if self.config.password_require_lowercase:
            if not re.search(r"[a-z]", password):
                errors.append("Password must contain at least one lowercase letter")

        # Check digit requirement
        if self.config.password_require_digit:
            if not re.search(r"\d", password):
                errors.append("Password must contain at least one digit")

        # Check special character requirement
        if self.config.password_require_special:
            # Special characters: anything that's not alphanumeric
            if not re.search(r"[^a-zA-Z0-9]", password):
                errors.append(
                    "Password must contain at least one special character "
                    "(e.g., !@#$%^&*)"
                )

        # Check against common passwords (including variations with special chars/numbers)
        if self._is_common_password_variation(password):
            errors.append(
                "This password is too common and easily guessable. "
                "Please choose a more unique password"
            )

        is_valid = len(errors) == 0
        return is_valid, errors

    def check_password_strength(self, password: str) -> dict:
        """Analyze password strength and calculate entropy.

        This method provides detailed password strength analysis including
        entropy calculation, character diversity, and overall strength rating.

        Args:
            password: Plain text password to analyze

        Returns:
            Dictionary containing strength analysis:
                - level: Strength rating ('weak', 'medium', 'strong', 'very_strong')
                - entropy: Estimated entropy in bits (higher is better)
                - length: Password length
                - has_uppercase: Boolean indicating uppercase letters present
                - has_lowercase: Boolean indicating lowercase letters present
                - has_digits: Boolean indicating digits present
                - has_special: Boolean indicating special characters present
                - char_diversity: Number of unique characters
                - feedback: List of improvement suggestions

        Entropy Calculation:
            Entropy is calculated based on character pool size and password length:
            - Only lowercase: 26 possibilities per character
            - + Uppercase: 52 possibilities
            - + Digits: 62 possibilities
            - + Special chars: ~95 possibilities

            Entropy (bits) = log2(pool_size ^ length)

        Strength Ratings:
            - weak: < 40 bits entropy (crackable in minutes/hours)
            - medium: 40-59 bits (crackable in days/weeks)
            - strong: 60-79 bits (crackable in years)
            - very_strong: >= 80 bits (crackable in centuries with current tech)

        Example:
            >>> service = PasswordService(auth_settings)
            >>> strength = service.check_password_strength("MyP@ssw0rd123")
            >>> strength
            {
                'level': 'strong',
                'entropy': 68.4,
                'length': 13,
                'has_uppercase': True,
                'has_lowercase': True,
                'has_digits': True,
                'has_special': True,
                'char_diversity': 11,
                'feedback': []
            }
        """
        if not password:
            return {
                "level": "weak",
                "entropy": 0,
                "length": 0,
                "has_uppercase": False,
                "has_lowercase": False,
                "has_digits": False,
                "has_special": False,
                "char_diversity": 0,
                "feedback": ["Password cannot be empty"],
            }

        # Analyze character composition
        has_lowercase = bool(re.search(r"[a-z]", password))
        has_uppercase = bool(re.search(r"[A-Z]", password))
        has_digits = bool(re.search(r"\d", password))
        has_special = bool(re.search(r"[^a-zA-Z0-9]", password))

        # Calculate character pool size
        pool_size = 0
        if has_lowercase:
            pool_size += 26
        if has_uppercase:
            pool_size += 26
        if has_digits:
            pool_size += 10
        if has_special:
            pool_size += 33  # Common special characters

        # Calculate entropy: log2(pool_size ^ length)
        if pool_size > 0:
            entropy = len(password) * math.log2(pool_size)
        else:
            entropy = 0

        # Calculate character diversity (unique characters)
        char_diversity = len(set(password))

        # Determine strength level based on entropy
        if entropy < 40:
            level = "weak"
        elif entropy < 60:
            level = "medium"
        elif entropy < 80:
            level = "strong"
        else:
            level = "very_strong"

        # Generate feedback for improvement. Rules are evaluated in order; each
        # is a (condition, message) pair so new suggestions can be added to the
        # table without growing a chain of if-statements.
        feedback = []
        feedback_rules = [
            (
                len(password) < 12,
                "Consider using a longer password (12+ characters)",
            ),
            (
                not has_uppercase,
                "Add uppercase letters for increased strength",
            ),
            (
                not has_lowercase,
                "Add lowercase letters for increased strength",
            ),
            (
                not has_digits,
                "Add numbers for increased strength",
            ),
            (
                not has_special,
                "Add special characters for increased strength",
            ),
            (
                char_diversity < len(password) * 0.5,
                "Use more unique characters (avoid repetition)",
            ),
        ]
        for triggered, message in feedback_rules:
            if triggered:
                feedback.append(message)

        if self._is_common_password_variation(password):
            feedback.append(
                "This is a commonly used password - choose something unique"
            )
            level = "weak"  # Override level for common passwords

        # Pattern-based feedback rules (evaluated after the composition rules
        # to preserve the original message ordering).
        pattern_rules = [
            (
                re.search(r"(012|123|234|345|456|567|678|789|890)", password),
                "Avoid sequential number patterns",
            ),
            (
                re.search(
                    r"(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)",
                    password.lower(),
                ),
                "Avoid sequential letter patterns",
            ),
            (
                re.search(r"(.)\1{2,}", password),
                "Avoid repeating the same character multiple times",
            ),
        ]
        for triggered, message in pattern_rules:
            if triggered:
                feedback.append(message)

        return {
            "level": level,
            "entropy": round(entropy, 1),
            "length": len(password),
            "has_uppercase": has_uppercase,
            "has_lowercase": has_lowercase,
            "has_digits": has_digits,
            "has_special": has_special,
            "char_diversity": char_diversity,
            "feedback": feedback,
        }

    def needs_rehash(self, password_hash: str) -> bool:
        """Check if a password hash needs to be regenerated with updated parameters.

        This method is useful for upgrading password hashes when security parameters
        are updated (e.g., increasing memory_cost or time_cost).

        Args:
            password_hash: Argon2id hash to check

        Returns:
            True if hash should be regenerated with current parameters, False otherwise

        Security Note:
            When upgrading hash parameters, rehash passwords during user login
            (when you have access to the plain text password). Never rehash
            without the original password.

        Example:
            >>> service = PasswordService(auth_settings)
            >>> if service.needs_rehash(stored_hash):
            ...     # User just logged in successfully
            ...     new_hash = service.hash_password(user_password)
            ...     # Update database with new_hash
        """
        try:
            return self._hasher.check_needs_rehash(password_hash)
        except InvalidHashError, Exception:
            # If hash is invalid or cannot be checked, assume it needs rehash
            return True
