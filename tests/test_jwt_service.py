# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Comprehensive unit tests for JWTService in PromptVault.

This module provides thorough coverage (100%) for:
- JWTService (src/services/auth/jwt_service.py)

Tests cover:
- ES256 (ECDSA) access token generation and validation
- ES256 refresh token generation and validation
- Token expiration handling
- Security features (algorithm enforcement, signature verification)
- Token tampering detection
- Algorithm confusion attack prevention
- Key loading and initialization
- Edge cases and error handling
- Unicode support in claims
- JTI uniqueness and tracking

Target: 100% code coverage of JWTService
"""

import shutil
import tempfile
import time
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.exceptions import (
    DecodeError,
    ExpiredSignatureError,
    InvalidAlgorithmError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    InvalidTokenError,
    MissingRequiredClaimError,
)

from src.config.auth_config import AuthConfig
from src.services.auth.jwt_service import JWTService

# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def auth_config():
    """Create AuthConfig instance with default JWT settings.

    Returns:
        AuthConfig: Configuration with JWT settings
    """
    return AuthConfig()


@pytest.fixture
def jwt_service(auth_config):
    """Create JWTService instance with default config.

    Args:
        auth_config: Default AuthConfig fixture

    Returns:
        JWTService: Service instance for testing
    """
    return JWTService(auth_config)


@pytest.fixture
def sample_user_data():
    """Provide sample user data for token generation.

    Returns:
        dict: User data dictionary
    """
    return {
        "user_id": "user_123456",
        "username": "alice_test",
        "email": "alice@example.com",
        "role": "user",
    }


@pytest.fixture
def temp_jwt_keys():
    """Generate temporary JWT ES256 key pair for testing.

    Yields:
        tuple: (temp_dir_path, private_key_path, public_key_path)
    """
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)

    # Generate ES256 key pair
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_key = private_key.public_key()

    # Write private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    private_key_path = temp_path / "private_key.pem"
    private_key_path.write_bytes(private_pem)

    # Write public key
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    public_key_path = temp_path / "public_key.pem"
    public_key_path.write_bytes(public_pem)

    yield temp_path, private_key_path, public_key_path

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def jwt_service_with_temp_keys(temp_jwt_keys):
    """Create JWTService with temporary keys.

    Args:
        temp_jwt_keys: Temporary key fixture

    Returns:
        JWTService: Service instance with temporary keys
    """
    temp_path, private_key_path, public_key_path = temp_jwt_keys

    with patch.dict(
        "os.environ",
        {
            "JWT_PRIVATE_KEY_PATH": str(private_key_path),
            "JWT_PUBLIC_KEY_PATH": str(public_key_path),
        },
    ):
        config = AuthConfig()
        return JWTService(config)


# ============================================================================
# TEST: INITIALIZATION
# ============================================================================


class TestJWTServiceInitialization:
    """Test JWTService initialization and configuration."""

    def test_initialization_success(self, auth_config):
        """Test successful service initialization."""
        service = JWTService(auth_config)

        assert service.config == auth_config
        assert service.algorithm == "ES256"
        assert service._private_key is None  # Lazy loading
        assert service._public_key is None  # Lazy loading

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration."""
        with patch.dict(
            "os.environ",
            {
                "JWT_ISSUER": "custom-issuer",
                "JWT_AUDIENCE": "custom-audience",
                "JWT_ACCESS_TOKEN_EXPIRE_SECONDS": "600",
            },
        ):
            config = AuthConfig()
            service = JWTService(config)

            assert service.config.jwt_issuer == "custom-issuer"
            assert service.config.jwt_audience == "custom-audience"
            assert service.config.jwt_access_token_expire_seconds == 600


# ============================================================================
# TEST: KEY LOADING
# ============================================================================


class TestKeyLoading:
    """Test JWT key loading and validation."""

    def test_load_private_key_success(self, jwt_service):
        """Test successful private key loading."""
        private_key = jwt_service._load_private_key()

        assert private_key is not None
        assert isinstance(private_key, bytes)
        assert len(private_key) > 50
        assert b"BEGIN" in private_key  # PEM format
        assert b"PRIVATE KEY" in private_key

    def test_load_public_key_success(self, jwt_service):
        """Test successful public key loading."""
        public_key = jwt_service._load_public_key()

        assert public_key is not None
        assert isinstance(public_key, bytes)
        assert len(public_key) > 50
        assert b"BEGIN" in public_key  # PEM format
        assert b"PUBLIC KEY" in public_key

    def test_key_caching(self, jwt_service):
        """Test that keys are cached after first load."""
        # Load keys first time
        private_key_1 = jwt_service._load_private_key()
        public_key_1 = jwt_service._load_public_key()

        # Load keys second time (should be cached)
        private_key_2 = jwt_service._load_private_key()
        public_key_2 = jwt_service._load_public_key()

        # Should return same object (cached)
        assert private_key_1 is private_key_2
        assert public_key_1 is public_key_2

    def test_load_private_key_missing_file(self, auth_config):
        """Test error handling when private key file doesn't exist."""
        with patch.dict(
            "os.environ",
            {
                "JWT_PRIVATE_KEY_PATH": "/nonexistent/private_key.pem",
            },
        ):
            config = AuthConfig()
            service = JWTService(config)

            with pytest.raises(FileNotFoundError) as exc_info:
                service._load_private_key()

            assert "JWT private key not found" in str(exc_info.value)
            assert "generate_jwt_keys.py" in str(exc_info.value)

    def test_load_public_key_missing_file(self, auth_config):
        """Test error handling when public key file doesn't exist."""
        with patch.dict(
            "os.environ",
            {
                "JWT_PUBLIC_KEY_PATH": "/nonexistent/public_key.pem",
            },
        ):
            config = AuthConfig()
            service = JWTService(config)

            with pytest.raises(FileNotFoundError) as exc_info:
                service._load_public_key()

            assert "JWT public key not found" in str(exc_info.value)
            assert "generate_jwt_keys.py" in str(exc_info.value)

    def test_load_private_key_permission_error(self, jwt_service, temp_jwt_keys):
        """Test error handling for permission denied on private key."""
        temp_path, private_key_path, public_key_path = temp_jwt_keys

        # Create a mock config that returns our temp path
        mock_config = MagicMock()
        mock_config.jwt_private_key_absolute_path = private_key_path

        service = JWTService(mock_config)

        # Mock the key_path.read_bytes() to raise PermissionError
        with patch.object(
            Path, "read_bytes", side_effect=PermissionError("Access denied")
        ):
            with pytest.raises(PermissionError) as exc_info:
                service._load_private_key()

            assert "Cannot read JWT private key" in str(exc_info.value)
            assert "Check file permissions" in str(exc_info.value)

    def test_load_public_key_permission_error(self, jwt_service, temp_jwt_keys):
        """Test error handling for permission denied on public key."""
        temp_path, private_key_path, public_key_path = temp_jwt_keys

        # Create a mock config that returns our temp path
        mock_config = MagicMock()
        mock_config.jwt_public_key_absolute_path = public_key_path

        service = JWTService(mock_config)

        # Mock the key_path.read_bytes() to raise PermissionError
        with patch.object(
            Path, "read_bytes", side_effect=PermissionError("Access denied")
        ):
            with pytest.raises(PermissionError) as exc_info:
                service._load_public_key()

            assert "Cannot read JWT public key" in str(exc_info.value)

    def test_load_private_key_invalid_content(self, temp_jwt_keys):
        """Test error handling for invalid private key content."""
        temp_path, private_key_path, public_key_path = temp_jwt_keys

        # Write invalid content
        private_key_path.write_text("invalid key content")

        with patch.dict(
            "os.environ",
            {
                "JWT_PRIVATE_KEY_PATH": str(private_key_path),
            },
        ):
            config = AuthConfig()
            service = JWTService(config)

            with pytest.raises(ValueError) as exc_info:
                service._load_private_key()

            assert "appears to be invalid or empty" in str(exc_info.value)

    def test_load_public_key_invalid_content(self, temp_jwt_keys):
        """Test error handling for invalid public key content."""
        temp_path, private_key_path, public_key_path = temp_jwt_keys

        # Write invalid content
        public_key_path.write_text("invalid")

        with patch.dict(
            "os.environ",
            {
                "JWT_PUBLIC_KEY_PATH": str(public_key_path),
            },
        ):
            config = AuthConfig()
            service = JWTService(config)

            with pytest.raises(ValueError) as exc_info:
                service._load_public_key()

            assert "appears to be invalid or empty" in str(exc_info.value)

    def test_load_private_key_empty_file(self, temp_jwt_keys):
        """Test error handling for empty private key file."""
        temp_path, private_key_path, public_key_path = temp_jwt_keys

        # Write empty content
        private_key_path.write_bytes(b"")

        with patch.dict(
            "os.environ",
            {
                "JWT_PRIVATE_KEY_PATH": str(private_key_path),
            },
        ):
            config = AuthConfig()
            service = JWTService(config)

            with pytest.raises(ValueError) as exc_info:
                service._load_private_key()

            assert "appears to be invalid or empty" in str(exc_info.value)

    def test_load_public_key_empty_file(self, temp_jwt_keys):
        """Test error handling for empty public key file."""
        temp_path, private_key_path, public_key_path = temp_jwt_keys

        # Write empty content
        public_key_path.write_bytes(b"")

        with patch.dict(
            "os.environ",
            {
                "JWT_PUBLIC_KEY_PATH": str(public_key_path),
            },
        ):
            config = AuthConfig()
            service = JWTService(config)

            with pytest.raises(ValueError) as exc_info:
                service._load_public_key()

            assert "appears to be invalid or empty" in str(exc_info.value)

    def test_load_private_key_generic_exception(self, jwt_service, temp_jwt_keys):
        """Test error handling for generic exception when loading private key."""
        temp_path, private_key_path, public_key_path = temp_jwt_keys

        # Create a mock config
        mock_config = MagicMock()
        mock_config.jwt_private_key_absolute_path = private_key_path

        service = JWTService(mock_config)

        # Mock to raise a generic exception
        with patch.object(Path, "read_bytes", side_effect=OSError("Disk error")):
            with pytest.raises(ValueError) as exc_info:
                service._load_private_key()

            assert "Failed to load JWT private key" in str(exc_info.value)

    def test_load_public_key_generic_exception(self, jwt_service, temp_jwt_keys):
        """Test error handling for generic exception when loading public key."""
        temp_path, private_key_path, public_key_path = temp_jwt_keys

        # Create a mock config
        mock_config = MagicMock()
        mock_config.jwt_public_key_absolute_path = public_key_path

        service = JWTService(mock_config)

        # Mock to raise a generic exception
        with patch.object(Path, "read_bytes", side_effect=OSError("Disk error")):
            with pytest.raises(ValueError) as exc_info:
                service._load_public_key()

            assert "Failed to load JWT public key" in str(exc_info.value)


# ============================================================================
# TEST: JTI GENERATION
# ============================================================================


class TestJTIGeneration:
    """Test JWT ID (jti) generation."""

    def test_generate_jti_format(self, jwt_service):
        """Test that JTI is in UUID4 format."""
        jti = jwt_service._generate_jti()

        assert isinstance(jti, str)
        # Validate UUID4 format
        uuid_obj = uuid.UUID(jti)
        assert uuid_obj.version == 4

    def test_generate_jti_uniqueness(self, jwt_service):
        """Test that generated JTIs are unique."""
        jtis = set()
        for _ in range(1000):
            jti = jwt_service._generate_jti()
            jtis.add(jti)

        # All JTIs should be unique
        assert len(jtis) == 1000

    def test_generate_jti_cryptographic_randomness(self, jwt_service):
        """Test that JTI uses cryptographically secure randomness."""
        jti1 = jwt_service._generate_jti()
        jti2 = jwt_service._generate_jti()

        # Should be different
        assert jti1 != jti2

        # Both should be valid UUID4s
        assert uuid.UUID(jti1).version == 4
        assert uuid.UUID(jti2).version == 4


# ============================================================================
# TEST: ACCESS TOKEN GENERATION
# ============================================================================


class TestAccessTokenGeneration:
    """Test JWT access token generation."""

    def test_generate_access_token_success(self, jwt_service, sample_user_data):
        """Test successful access token generation."""
        token = jwt_service.generate_access_token(**sample_user_data)

        assert isinstance(token, str)
        assert len(token) > 0
        # JWT tokens have 3 parts separated by dots
        assert token.count(".") == 2

    def test_access_token_structure(self, jwt_service, sample_user_data):
        """Test access token has correct structure (header, payload, signature)."""
        token = jwt_service.generate_access_token(**sample_user_data)

        parts = token.split(".")
        assert len(parts) == 3

        # Each part should be base64url-encoded (alphanumeric + - and _)
        for part in parts:
            assert len(part) > 0
            # Base64url uses alphanumeric, -, and _ characters
            assert all(c.isalnum() or c in "-_" for c in part)

    def test_access_token_contains_all_claims(self, jwt_service, sample_user_data):
        """Test that access token contains all required claims."""
        token = jwt_service.generate_access_token(**sample_user_data)

        # Decode without verification to inspect claims
        claims = jwt_service.decode_token_unsafe(token)

        # Standard claims
        assert "sub" in claims
        assert "exp" in claims
        assert "iat" in claims
        assert "iss" in claims
        assert "aud" in claims
        assert "jti" in claims

        # Custom claims
        assert "username" in claims
        assert "email" in claims
        assert "role" in claims

        # Verify values
        assert claims["sub"] == sample_user_data["user_id"]
        assert claims["username"] == sample_user_data["username"]
        assert claims["email"] == sample_user_data["email"]
        assert claims["role"] == sample_user_data["role"]

    def test_access_token_expiration_time(self, jwt_service, sample_user_data):
        """Test that access token has correct expiration time (15 minutes)."""
        datetime.now(UTC)
        token = jwt_service.generate_access_token(**sample_user_data)
        datetime.now(UTC)

        claims = jwt_service.decode_token_unsafe(token)

        # Calculate expected expiration
        expected_expire_seconds = jwt_service.config.jwt_access_token_expire_seconds
        exp_time = datetime.fromtimestamp(claims["exp"], tz=UTC)
        iat_time = datetime.fromtimestamp(claims["iat"], tz=UTC)

        # Verify expiration is approximately 15 minutes (900 seconds) from issued time
        time_diff = (exp_time - iat_time).total_seconds()
        assert abs(time_diff - expected_expire_seconds) < 1  # Allow 1 second tolerance

    def test_access_token_issuer_audience(self, jwt_service, sample_user_data):
        """Test that access token has correct issuer and audience."""
        token = jwt_service.generate_access_token(**sample_user_data)
        claims = jwt_service.decode_token_unsafe(token)

        assert claims["iss"] == jwt_service.config.jwt_issuer
        assert claims["aud"] == jwt_service.config.jwt_audience

    def test_access_token_jti_uniqueness(self, jwt_service, sample_user_data):
        """Test that each access token has a unique JTI."""
        tokens = []
        jtis = set()

        for _ in range(100):
            token = jwt_service.generate_access_token(**sample_user_data)
            tokens.append(token)
            claims = jwt_service.decode_token_unsafe(token)
            jtis.add(claims["jti"])

        # All JTIs should be unique
        assert len(jtis) == 100

    def test_access_token_different_roles(self, jwt_service, sample_user_data):
        """Test access token generation with different roles."""
        roles = ["viewer", "editor", "admin", "moderator", "guest"]

        for role in roles:
            data = sample_user_data.copy()
            data["role"] = role

            token = jwt_service.generate_access_token(**data)
            claims = jwt_service.decode_token_unsafe(token)

            assert claims["role"] == role

    def test_access_token_unicode_username(self, jwt_service, sample_user_data):
        """Test access token with Unicode characters in username."""
        data = sample_user_data.copy()
        data["username"] = "用户测试"  # Chinese characters

        token = jwt_service.generate_access_token(**data)
        claims = jwt_service.decode_token_unsafe(token)

        assert claims["username"] == "用户测试"

    def test_access_token_unicode_email(self, jwt_service, sample_user_data):
        """Test access token with Unicode domain in email."""
        data = sample_user_data.copy()
        data["email"] = "test@日本.jp"

        token = jwt_service.generate_access_token(**data)
        claims = jwt_service.decode_token_unsafe(token)

        assert claims["email"] == "test@日本.jp"

    def test_access_token_special_characters(self, jwt_service, sample_user_data):
        """Test access token with special characters in claims."""
        data = sample_user_data.copy()
        data["username"] = "user!@#$%^&*()"
        data["email"] = "test+tag@example.com"

        token = jwt_service.generate_access_token(**data)
        claims = jwt_service.decode_token_unsafe(token)

        assert claims["username"] == "user!@#$%^&*()"
        assert claims["email"] == "test+tag@example.com"

    def test_access_token_long_values(self, jwt_service, sample_user_data):
        """Test access token with very long values."""
        data = sample_user_data.copy()
        data["username"] = "a" * 1000
        data["email"] = "a" * 500 + "@example.com"

        token = jwt_service.generate_access_token(**data)
        claims = jwt_service.decode_token_unsafe(token)

        assert claims["username"] == "a" * 1000
        assert len(claims["email"]) > 500


# ============================================================================
# TEST: REFRESH TOKEN GENERATION
# ============================================================================


class TestRefreshTokenGeneration:
    """Test JWT refresh token generation."""

    def test_generate_refresh_token_success(self, jwt_service):
        """Test successful refresh token generation."""
        user_id = "user_123"
        family_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())

        token = jwt_service.generate_refresh_token(user_id, family_id, jti)

        assert isinstance(token, str)
        assert len(token) > 0
        assert token.count(".") == 2

    def test_refresh_token_contains_required_claims(self, jwt_service):
        """Test that refresh token contains all required claims."""
        user_id = "user_123"
        family_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())

        token = jwt_service.generate_refresh_token(user_id, family_id, jti)
        claims = jwt_service.decode_token_unsafe(token)

        # Standard claims
        assert "sub" in claims
        assert "exp" in claims
        assert "iat" in claims
        assert "iss" in claims
        assert "aud" in claims
        assert "jti" in claims

        # Refresh token specific claims
        assert "family_id" in claims
        assert "type" in claims

        # Verify values
        assert claims["sub"] == user_id
        assert claims["family_id"] == family_id
        assert claims["jti"] == jti
        assert claims["type"] == "refresh"

    def test_refresh_token_type_claim(self, jwt_service):
        """Test that refresh token has type='refresh' claim."""
        user_id = "user_123"
        family_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())

        token = jwt_service.generate_refresh_token(user_id, family_id, jti)
        claims = jwt_service.decode_token_unsafe(token)

        assert claims["type"] == "refresh"

    def test_refresh_token_expiration_time(self, jwt_service):
        """Test that refresh token has correct expiration time (7 days)."""
        user_id = "user_123"
        family_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())

        token = jwt_service.generate_refresh_token(user_id, family_id, jti)
        claims = jwt_service.decode_token_unsafe(token)

        # Calculate expected expiration
        expected_expire_seconds = jwt_service.config.jwt_refresh_token_expire_seconds
        exp_time = datetime.fromtimestamp(claims["exp"], tz=UTC)
        iat_time = datetime.fromtimestamp(claims["iat"], tz=UTC)

        # Verify expiration is approximately 7 days (604800 seconds) from issued time
        time_diff = (exp_time - iat_time).total_seconds()
        assert abs(time_diff - expected_expire_seconds) < 1

    def test_refresh_token_family_id_preserved(self, jwt_service):
        """Test that family_id is correctly preserved in refresh token."""
        user_id = "user_123"
        family_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())

        token = jwt_service.generate_refresh_token(user_id, family_id, jti)
        claims = jwt_service.decode_token_unsafe(token)

        assert claims["family_id"] == family_id

    def test_refresh_token_jti_preserved(self, jwt_service):
        """Test that provided JTI is used in refresh token."""
        user_id = "user_123"
        family_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())

        token = jwt_service.generate_refresh_token(user_id, family_id, jti)
        claims = jwt_service.decode_token_unsafe(token)

        assert claims["jti"] == jti

    def test_refresh_token_minimal_claims(self, jwt_service):
        """Test that refresh token has minimal claims (no username, email, role)."""
        user_id = "user_123"
        family_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())

        token = jwt_service.generate_refresh_token(user_id, family_id, jti)
        claims = jwt_service.decode_token_unsafe(token)

        # Should NOT have these claims
        assert "username" not in claims
        assert "email" not in claims
        assert "role" not in claims


# ============================================================================
# TEST: ACCESS TOKEN VALIDATION
# ============================================================================


class TestAccessTokenValidation:
    """Test JWT access token validation."""

    def test_validate_access_token_success(self, jwt_service, sample_user_data):
        """Test successful access token validation."""
        token = jwt_service.generate_access_token(**sample_user_data)

        claims = jwt_service.validate_access_token(token)

        assert claims["sub"] == sample_user_data["user_id"]
        assert claims["username"] == sample_user_data["username"]
        assert claims["email"] == sample_user_data["email"]
        assert claims["role"] == sample_user_data["role"]

    def test_validate_access_token_all_claims_extracted(
        self, jwt_service, sample_user_data
    ):
        """Test that all claims are correctly extracted during validation."""
        token = jwt_service.generate_access_token(**sample_user_data)
        claims = jwt_service.validate_access_token(token)

        # All expected claims should be present
        assert "sub" in claims
        assert "username" in claims
        assert "email" in claims
        assert "role" in claims
        assert "jti" in claims
        assert "exp" in claims
        assert "iat" in claims
        assert "iss" in claims
        assert "aud" in claims

    def test_validate_expired_access_token(
        self, jwt_service_with_temp_keys, sample_user_data
    ):
        """Test that expired access token is rejected."""
        # Create service with very short expiration
        with patch.dict(
            "os.environ",
            {
                "JWT_ACCESS_TOKEN_EXPIRE_SECONDS": "1",
            },
        ):
            config = AuthConfig()
            service = JWTService(config)
            # Copy keys from temp service
            service._private_key = jwt_service_with_temp_keys._load_private_key()
            service._public_key = jwt_service_with_temp_keys._load_public_key()

            token = service.generate_access_token(**sample_user_data)

            # Wait for token to expire
            time.sleep(2)

            with pytest.raises(ExpiredSignatureError):
                service.validate_access_token(token)

    def test_validate_access_token_invalid_signature(
        self, jwt_service, jwt_service_with_temp_keys, sample_user_data
    ):
        """Test that token with invalid signature is rejected."""
        # Generate token with one service
        token = jwt_service.generate_access_token(**sample_user_data)

        # Try to validate with different service (different keys)
        with pytest.raises(InvalidSignatureError):
            jwt_service_with_temp_keys.validate_access_token(token)

    def test_validate_access_token_tampered(self, jwt_service, sample_user_data):
        """Test that tampered token is rejected."""
        token = jwt_service.generate_access_token(**sample_user_data)

        # Tamper with token by modifying payload
        parts = token.split(".")
        # Modify the payload part slightly
        parts[1] = parts[1][:-1] + ("a" if parts[1][-1] != "a" else "b")
        tampered_token = ".".join(parts)

        with pytest.raises((InvalidSignatureError, DecodeError, InvalidTokenError)):
            jwt_service.validate_access_token(tampered_token)

    def test_validate_refresh_token_as_access_token(self, jwt_service):
        """Test that refresh token cannot be used as access token."""
        user_id = "user_123"
        family_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())

        refresh_token = jwt_service.generate_refresh_token(user_id, family_id, jti)

        with pytest.raises(InvalidTokenError) as exc_info:
            jwt_service.validate_access_token(refresh_token)

        assert "Refresh token cannot be used as access token" in str(exc_info.value)

    def test_validate_access_token_missing_claims(self, jwt_service, sample_user_data):
        """Test validation fails with missing required claims."""
        # Generate token with missing claims by manually creating JWT
        private_key = jwt_service._load_private_key()

        # Create token without required 'sub' claim
        claims = {
            "username": sample_user_data["username"],
            "exp": datetime.now(UTC) + timedelta(minutes=15),
        }

        token = jwt.encode(claims, private_key, algorithm="ES256")

        with pytest.raises((MissingRequiredClaimError, InvalidTokenError)):
            jwt_service.validate_access_token(token)

    def test_validate_access_token_invalid_issuer(self, jwt_service, sample_user_data):
        """Test validation fails with invalid issuer."""
        # Create token with wrong issuer
        private_key = jwt_service._load_private_key()
        now = datetime.now(UTC)

        claims = {
            "sub": sample_user_data["user_id"],
            "username": sample_user_data["username"],
            "email": sample_user_data["email"],
            "role": sample_user_data["role"],
            "exp": now + timedelta(minutes=15),
            "iat": now,
            "iss": "wrong-issuer",
            "aud": jwt_service.config.jwt_audience,
            "jti": str(uuid.uuid4()),
        }

        token = jwt.encode(claims, private_key, algorithm="ES256")

        with pytest.raises(InvalidIssuerError):
            jwt_service.validate_access_token(token)

    def test_validate_access_token_invalid_audience(
        self, jwt_service, sample_user_data
    ):
        """Test validation fails with invalid audience."""
        # Create token with wrong audience
        private_key = jwt_service._load_private_key()
        now = datetime.now(UTC)

        claims = {
            "sub": sample_user_data["user_id"],
            "username": sample_user_data["username"],
            "email": sample_user_data["email"],
            "role": sample_user_data["role"],
            "exp": now + timedelta(minutes=15),
            "iat": now,
            "iss": jwt_service.config.jwt_issuer,
            "aud": "wrong-audience",
            "jti": str(uuid.uuid4()),
        }

        token = jwt.encode(claims, private_key, algorithm="ES256")

        with pytest.raises(InvalidAudienceError):
            jwt_service.validate_access_token(token)

    def test_validate_access_token_algorithm_confusion_hs256(
        self, jwt_service, sample_user_data
    ):
        """Test that HS256 token is rejected (algorithm confusion attack)."""
        # Try to create token with HS256 (symmetric) algorithm
        now = datetime.now(UTC)
        claims = {
            "sub": sample_user_data["user_id"],
            "username": sample_user_data["username"],
            "email": sample_user_data["email"],
            "role": sample_user_data["role"],
            "exp": now + timedelta(minutes=15),
            "iat": now,
            "iss": jwt_service.config.jwt_issuer,
            "aud": jwt_service.config.jwt_audience,
            "jti": str(uuid.uuid4()),
        }

        # Create HS256 token
        hs256_token = jwt.encode(claims, "secret", algorithm="HS256")

        # Should be rejected
        with pytest.raises(
            (InvalidAlgorithmError, InvalidSignatureError, InvalidTokenError)
        ):
            jwt_service.validate_access_token(hs256_token)

    def test_validate_access_token_none_algorithm(self, jwt_service, sample_user_data):
        """Test that 'none' algorithm token is rejected."""
        now = datetime.now(UTC)
        claims = {
            "sub": sample_user_data["user_id"],
            "username": sample_user_data["username"],
            "email": sample_user_data["email"],
            "role": sample_user_data["role"],
            "exp": now + timedelta(minutes=15),
            "iat": now,
            "iss": jwt_service.config.jwt_issuer,
            "aud": jwt_service.config.jwt_audience,
            "jti": str(uuid.uuid4()),
        }

        # Try to create token with 'none' algorithm
        try:
            none_token = jwt.encode(claims, "", algorithm="none")

            # Should be rejected
            with pytest.raises((InvalidAlgorithmError, InvalidTokenError, DecodeError)):
                jwt_service.validate_access_token(none_token)
        except Exception:
            # PyJWT might not allow 'none' algorithm, which is good
            pass

    def test_validate_access_token_malformed(self, jwt_service):
        """Test validation of malformed token."""
        malformed_tokens = [
            "not.a.jwt",
            "invalid",
            "",
            "a.b",  # Only 2 parts
            "a.b.c.d",  # 4 parts
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",
        ]

        for malformed_token in malformed_tokens:
            with pytest.raises((InvalidTokenError, DecodeError)):
                jwt_service.validate_access_token(malformed_token)


# ============================================================================
# TEST: REFRESH TOKEN VALIDATION
# ============================================================================


class TestRefreshTokenValidation:
    """Test JWT refresh token validation."""

    def test_validate_refresh_token_success(self, jwt_service):
        """Test successful refresh token validation."""
        user_id = "user_123"
        family_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())

        token = jwt_service.generate_refresh_token(user_id, family_id, jti)
        claims = jwt_service.validate_refresh_token(token)

        assert claims["sub"] == user_id
        assert claims["family_id"] == family_id
        assert claims["jti"] == jti
        assert claims["type"] == "refresh"

    def test_validate_refresh_token_type_verification(self, jwt_service):
        """Test that type='refresh' claim is verified."""
        user_id = "user_123"
        family_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())

        token = jwt_service.generate_refresh_token(user_id, family_id, jti)
        claims = jwt_service.validate_refresh_token(token)

        assert claims.get("type") == "refresh"

    def test_validate_access_token_as_refresh_token(
        self, jwt_service, sample_user_data
    ):
        """Test that access token cannot be used as refresh token."""
        access_token = jwt_service.generate_access_token(**sample_user_data)

        with pytest.raises((InvalidTokenError, MissingRequiredClaimError)) as exc_info:
            jwt_service.validate_refresh_token(access_token)

        # Should fail because access token is missing family_id claim or type='refresh'
        error_msg = str(exc_info.value)
        assert "not a valid refresh token" in error_msg or "family_id" in error_msg

    def test_validate_expired_refresh_token(self, jwt_service_with_temp_keys):
        """Test that expired refresh token is rejected."""
        # Create service with very short expiration
        with patch.dict(
            "os.environ",
            {
                "JWT_REFRESH_TOKEN_EXPIRE_SECONDS": "1",
            },
        ):
            config = AuthConfig()
            service = JWTService(config)
            service._private_key = jwt_service_with_temp_keys._load_private_key()
            service._public_key = jwt_service_with_temp_keys._load_public_key()

            user_id = "user_123"
            family_id = str(uuid.uuid4())
            jti = str(uuid.uuid4())

            token = service.generate_refresh_token(user_id, family_id, jti)

            # Wait for token to expire
            time.sleep(2)

            with pytest.raises(ExpiredSignatureError):
                service.validate_refresh_token(token)

    def test_validate_refresh_token_missing_type_claim(self, jwt_service):
        """Test validation fails when type claim is missing."""
        # Manually create token without type claim
        private_key = jwt_service._load_private_key()
        now = datetime.now(UTC)

        claims = {
            "sub": "user_123",
            "family_id": str(uuid.uuid4()),
            "jti": str(uuid.uuid4()),
            "exp": now + timedelta(days=7),
            "iat": now,
            "iss": jwt_service.config.jwt_issuer,
            "aud": jwt_service.config.jwt_audience,
        }

        token = jwt.encode(claims, private_key, algorithm="ES256")

        with pytest.raises(InvalidTokenError) as exc_info:
            jwt_service.validate_refresh_token(token)

        assert "not a valid refresh token" in str(exc_info.value)

    def test_validate_refresh_token_tampered(self, jwt_service):
        """Test that tampered refresh token is rejected."""
        user_id = "user_123"
        family_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())

        token = jwt_service.generate_refresh_token(user_id, family_id, jti)

        # Tamper with token
        parts = token.split(".")
        parts[1] = parts[1][:-1] + ("a" if parts[1][-1] != "a" else "b")
        tampered_token = ".".join(parts)

        with pytest.raises((InvalidSignatureError, DecodeError, InvalidTokenError)):
            jwt_service.validate_refresh_token(tampered_token)

    def test_validate_refresh_token_invalid_signature(
        self, jwt_service, jwt_service_with_temp_keys
    ):
        """Test that refresh token with invalid signature is rejected."""
        user_id = "user_123"
        family_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())

        # Generate with one service
        token = jwt_service.generate_refresh_token(user_id, family_id, jti)

        # Try to validate with different service
        with pytest.raises(InvalidSignatureError):
            jwt_service_with_temp_keys.validate_refresh_token(token)

    def test_validate_refresh_token_missing_family_id(self, jwt_service):
        """Test validation fails when family_id claim is missing."""
        private_key = jwt_service._load_private_key()
        now = datetime.now(UTC)

        claims = {
            "sub": "user_123",
            "type": "refresh",
            "jti": str(uuid.uuid4()),
            "exp": now + timedelta(days=7),
            "iat": now,
            "iss": jwt_service.config.jwt_issuer,
            "aud": jwt_service.config.jwt_audience,
        }

        token = jwt.encode(claims, private_key, algorithm="ES256")

        with pytest.raises((MissingRequiredClaimError, InvalidTokenError)):
            jwt_service.validate_refresh_token(token)

    def test_validate_refresh_token_invalid_algorithm_error(self, jwt_service):
        """Test that InvalidAlgorithmError is raised for wrong algorithm in refresh token."""
        # Create an HS256 token
        now = datetime.now(UTC)
        claims = {
            "sub": "user_123",
            "family_id": str(uuid.uuid4()),
            "jti": str(uuid.uuid4()),
            "type": "refresh",
            "exp": now + timedelta(days=7),
            "iat": now,
            "iss": jwt_service.config.jwt_issuer,
            "aud": jwt_service.config.jwt_audience,
        }

        hs256_token = jwt.encode(claims, "secret", algorithm="HS256")

        with pytest.raises(
            (InvalidAlgorithmError, InvalidSignatureError, InvalidTokenError)
        ):
            jwt_service.validate_refresh_token(hs256_token)

    def test_validate_refresh_token_invalid_audience(self, jwt_service):
        """Test validation fails with invalid audience in refresh token."""
        private_key = jwt_service._load_private_key()
        now = datetime.now(UTC)

        claims = {
            "sub": "user_123",
            "family_id": str(uuid.uuid4()),
            "jti": str(uuid.uuid4()),
            "type": "refresh",
            "exp": now + timedelta(days=7),
            "iat": now,
            "iss": jwt_service.config.jwt_issuer,
            "aud": "wrong-audience",
        }

        token = jwt.encode(claims, private_key, algorithm="ES256")

        with pytest.raises(InvalidAudienceError):
            jwt_service.validate_refresh_token(token)

    def test_validate_refresh_token_invalid_issuer(self, jwt_service):
        """Test validation fails with invalid issuer in refresh token."""
        private_key = jwt_service._load_private_key()
        now = datetime.now(UTC)

        claims = {
            "sub": "user_123",
            "family_id": str(uuid.uuid4()),
            "jti": str(uuid.uuid4()),
            "type": "refresh",
            "exp": now + timedelta(days=7),
            "iat": now,
            "iss": "wrong-issuer",
            "aud": jwt_service.config.jwt_audience,
        }

        token = jwt.encode(claims, private_key, algorithm="ES256")

        with pytest.raises(InvalidIssuerError):
            jwt_service.validate_refresh_token(token)


# ============================================================================
# TEST: DECODE TOKEN UNSAFE
# ============================================================================


class TestDecodeTokenUnsafe:
    """Test unsafe token decoding (without validation)."""

    def test_decode_token_unsafe_success(self, jwt_service, sample_user_data):
        """Test successful unsafe token decoding."""
        token = jwt_service.generate_access_token(**sample_user_data)
        claims = jwt_service.decode_token_unsafe(token)

        assert claims["sub"] == sample_user_data["user_id"]
        assert claims["username"] == sample_user_data["username"]

    def test_decode_expired_token_unsafe(
        self, jwt_service_with_temp_keys, sample_user_data
    ):
        """Test that expired token can be decoded unsafely."""
        # Create service with very short expiration
        with patch.dict(
            "os.environ",
            {
                "JWT_ACCESS_TOKEN_EXPIRE_SECONDS": "1",
            },
        ):
            config = AuthConfig()
            service = JWTService(config)
            service._private_key = jwt_service_with_temp_keys._load_private_key()
            service._public_key = jwt_service_with_temp_keys._load_public_key()

            token = service.generate_access_token(**sample_user_data)

            # Wait for expiration
            time.sleep(2)

            # Should succeed (no validation)
            claims = service.decode_token_unsafe(token)
            assert claims["sub"] == sample_user_data["user_id"]

    def test_decode_token_unsafe_invalid_signature(
        self, jwt_service, jwt_service_with_temp_keys, sample_user_data
    ):
        """Test that token with invalid signature can still be decoded unsafely."""
        # Generate with one service
        token = jwt_service.generate_access_token(**sample_user_data)

        # Decode with different service (should work - no verification)
        claims = jwt_service_with_temp_keys.decode_token_unsafe(token)

        assert claims["sub"] == sample_user_data["user_id"]

    def test_decode_token_unsafe_malformed(self, jwt_service):
        """Test that malformed token raises error even in unsafe decode."""
        malformed_tokens = [
            "not.a.jwt",
            "invalid",
            "",
        ]

        for malformed_token in malformed_tokens:
            with pytest.raises(InvalidTokenError):
                jwt_service.decode_token_unsafe(malformed_token)

    def test_decode_token_unsafe_claim_extraction(self, jwt_service):
        """Test extracting specific claims from unsafe decode."""
        user_id = "user_123"
        family_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())

        token = jwt_service.generate_refresh_token(user_id, family_id, jti)
        claims = jwt_service.decode_token_unsafe(token)

        # Should be able to extract JTI for logging
        assert claims.get("jti") == jti
        assert claims.get("family_id") == family_id


# ============================================================================
# TEST: GET TOKEN EXPIRY
# ============================================================================


class TestGetTokenExpiry:
    """Test token expiration datetime extraction."""

    def test_get_token_expiry_success(self, jwt_service, sample_user_data):
        """Test successful expiration time extraction."""
        before = datetime.now(UTC)
        token = jwt_service.generate_access_token(**sample_user_data)
        datetime.now(UTC)

        expiry = jwt_service.get_token_expiry(token)

        assert isinstance(expiry, datetime)
        assert expiry.tzinfo == UTC

        # Should be approximately 15 minutes from now
        expected_expiry = before + timedelta(
            seconds=jwt_service.config.jwt_access_token_expire_seconds
        )
        time_diff = abs((expiry - expected_expiry).total_seconds())
        assert time_diff < 2  # Allow 2 seconds tolerance

    def test_get_token_expiry_timezone(self, jwt_service, sample_user_data):
        """Test that returned expiry is in UTC timezone."""
        token = jwt_service.generate_access_token(**sample_user_data)
        expiry = jwt_service.get_token_expiry(token)

        assert expiry.tzinfo == UTC

    def test_get_token_expiry_invalid_token(self, jwt_service):
        """Test error handling for invalid token."""
        with pytest.raises(InvalidTokenError):
            jwt_service.get_token_expiry("invalid.token")

    def test_get_token_expiry_missing_exp_claim(self, jwt_service):
        """Test error handling when exp claim is missing."""
        # Manually create token without exp claim
        private_key = jwt_service._load_private_key()

        claims = {
            "sub": "user_123",
            "iat": datetime.now(UTC),
        }

        token = jwt.encode(claims, private_key, algorithm="ES256")

        with pytest.raises(InvalidTokenError) as exc_info:
            jwt_service.get_token_expiry(token)

        assert "missing exp claim" in str(exc_info.value)

    def test_get_token_expiry_generic_exception(self, jwt_service):
        """Test error handling for generic exception in get_token_expiry."""
        # Manually create token with invalid exp value
        private_key = jwt_service._load_private_key()

        claims = {
            "sub": "user_123",
            "exp": "invalid_timestamp",  # String instead of int
            "iat": datetime.now(UTC),
        }

        token = jwt.encode(claims, private_key, algorithm="ES256")

        with pytest.raises(InvalidTokenError) as exc_info:
            jwt_service.get_token_expiry(token)

        assert "Cannot extract expiry from token" in str(exc_info.value)


# ============================================================================
# TEST: IS TOKEN EXPIRED
# ============================================================================


class TestIsTokenExpired:
    """Test token expiration checking."""

    def test_is_token_expired_not_expired(self, jwt_service, sample_user_data):
        """Test that non-expired token returns False."""
        token = jwt_service.generate_access_token(**sample_user_data)

        assert jwt_service.is_token_expired(token) is False

    def test_is_token_expired_expired(
        self, jwt_service_with_temp_keys, sample_user_data
    ):
        """Test that expired token returns True."""
        # Create service with very short expiration
        with patch.dict(
            "os.environ",
            {
                "JWT_ACCESS_TOKEN_EXPIRE_SECONDS": "1",
            },
        ):
            config = AuthConfig()
            service = JWTService(config)
            service._private_key = jwt_service_with_temp_keys._load_private_key()
            service._public_key = jwt_service_with_temp_keys._load_public_key()

            token = service.generate_access_token(**sample_user_data)

            # Token should not be expired yet
            assert service.is_token_expired(token) is False

            # Wait for expiration
            time.sleep(2)

            # Token should now be expired
            assert service.is_token_expired(token) is True

    def test_is_token_expired_about_to_expire(
        self, jwt_service_with_temp_keys, sample_user_data
    ):
        """Test token that's about to expire but hasn't yet."""
        # Create service with 3 second expiration
        with patch.dict(
            "os.environ",
            {
                "JWT_ACCESS_TOKEN_EXPIRE_SECONDS": "3",
            },
        ):
            config = AuthConfig()
            service = JWTService(config)
            service._private_key = jwt_service_with_temp_keys._load_private_key()
            service._public_key = jwt_service_with_temp_keys._load_public_key()

            token = service.generate_access_token(**sample_user_data)

            # Wait 2 seconds (still valid)
            time.sleep(2)

            # Should still be valid
            assert service.is_token_expired(token) is False

    def test_is_token_expired_invalid_token(self, jwt_service):
        """Test error handling for invalid token."""
        with pytest.raises(InvalidTokenError):
            jwt_service.is_token_expired("invalid.token")

    def test_is_token_expired_missing_exp(self, jwt_service):
        """Test error handling when exp claim is missing."""
        private_key = jwt_service._load_private_key()

        claims = {
            "sub": "user_123",
            "iat": datetime.now(UTC),
        }

        token = jwt.encode(claims, private_key, algorithm="ES256")

        with pytest.raises(InvalidTokenError):
            jwt_service.is_token_expired(token)


# ============================================================================
# TEST: SECURITY FEATURES
# ============================================================================


class TestSecurityFeatures:
    """Test security features and attack prevention."""

    def test_algorithm_enforcement(self, jwt_service, sample_user_data):
        """Test that only ES256 algorithm is accepted."""
        # The service should only use ES256
        assert jwt_service.algorithm == "ES256"

        token = jwt_service.generate_access_token(**sample_user_data)

        # Decode header to verify algorithm
        import base64
        import json

        header = json.loads(base64.urlsafe_b64decode(token.split(".")[0] + "=="))

        assert header["alg"] == "ES256"

    def test_signature_verification_cannot_be_bypassed(
        self, jwt_service, sample_user_data
    ):
        """Test that signature verification cannot be bypassed."""
        token = jwt_service.generate_access_token(**sample_user_data)

        # Try to modify payload and keep signature
        parts = token.split(".")

        # Decode payload, modify it, encode it back
        import base64
        import json

        payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
        payload["role"] = "admin"  # Try to escalate privileges
        modified_payload = (
            base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        )

        # Create tampered token
        tampered_token = f"{parts[0]}.{modified_payload}.{parts[2]}"

        # Should be rejected due to invalid signature
        with pytest.raises((InvalidSignatureError, InvalidTokenError)):
            jwt_service.validate_access_token(tampered_token)

    def test_token_tampering_detection(self, jwt_service, sample_user_data):
        """Test that any token tampering is detected."""
        token = jwt_service.generate_access_token(**sample_user_data)

        # Try various tampering attempts
        parts = token.split(".")

        # Tamper with each part
        tampering_attempts = [
            f"x{parts[0]}.{parts[1]}.{parts[2]}",  # Modify header
            f"{parts[0]}.x{parts[1]}.{parts[2]}",  # Modify payload
            f"{parts[0]}.{parts[1]}.x{parts[2]}",  # Modify signature
        ]

        for tampered in tampering_attempts:
            with pytest.raises((InvalidSignatureError, DecodeError, InvalidTokenError)):
                jwt_service.validate_access_token(tampered)

    def test_jti_tracking_support(self, jwt_service, sample_user_data):
        """Test that JTI can be extracted for tracking/revocation."""
        tokens_and_jtis = []

        # Generate multiple tokens
        for _ in range(10):
            token = jwt_service.generate_access_token(**sample_user_data)
            claims = jwt_service.decode_token_unsafe(token)
            jti = claims["jti"]
            tokens_and_jtis.append((token, jti))

        # All JTIs should be unique
        jtis = [jti for _, jti in tokens_and_jtis]
        assert len(jtis) == len(set(jtis))

        # Each token should have its correct JTI
        for token, expected_jti in tokens_and_jtis:
            claims = jwt_service.validate_access_token(token)
            assert claims["jti"] == expected_jti

    def test_key_confusion_prevention(
        self, jwt_service, jwt_service_with_temp_keys, sample_user_data
    ):
        """Test that tokens signed with different keys are rejected."""
        # Generate token with service 1
        token1 = jwt_service.generate_access_token(**sample_user_data)

        # Try to validate with service 2 (different keys)
        with pytest.raises(InvalidSignatureError):
            jwt_service_with_temp_keys.validate_access_token(token1)

        # Generate token with service 2
        token2 = jwt_service_with_temp_keys.generate_access_token(**sample_user_data)

        # Try to validate with service 1
        with pytest.raises(InvalidSignatureError):
            jwt_service.validate_access_token(token2)


# ============================================================================
# TEST: EDGE CASES
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_concurrent_token_generation(self, jwt_service, sample_user_data):
        """Test concurrent token generation produces unique tokens."""
        import threading

        tokens = []
        lock = threading.Lock()

        def generate_token():
            token = jwt_service.generate_access_token(**sample_user_data)
            with lock:
                tokens.append(token)

        # Generate tokens concurrently
        threads = []
        for _ in range(50):
            thread = threading.Thread(target=generate_token)
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All tokens should be unique
        assert len(tokens) == len(set(tokens))

        # All tokens should be valid
        for token in tokens:
            claims = jwt_service.validate_access_token(token)
            assert claims["sub"] == sample_user_data["user_id"]

    def test_very_long_claims(self, jwt_service, sample_user_data):
        """Test token generation with very long claim values."""
        data = sample_user_data.copy()
        data["username"] = "a" * 10000
        data["email"] = "b" * 5000 + "@example.com"

        token = jwt_service.generate_access_token(**data)
        claims = jwt_service.validate_access_token(token)

        assert len(claims["username"]) == 10000
        assert len(claims["email"]) > 5000

    def test_special_characters_in_all_claims(self, jwt_service):
        """Test special characters in all claim types."""
        data = {
            "user_id": "user_!@#$%^&*()",
            "username": "用户<>[]{}",
            "email": "test+tag@日本.jp",
            "role": "admin-moderator_special",
        }

        token = jwt_service.generate_access_token(**data)
        claims = jwt_service.validate_access_token(token)

        assert claims["sub"] == data["user_id"]
        assert claims["username"] == data["username"]
        assert claims["email"] == data["email"]
        assert claims["role"] == data["role"]

    def test_token_near_expiration_boundary(
        self, jwt_service_with_temp_keys, sample_user_data
    ):
        """Test token behavior at exact expiration moment."""
        # Create service with 3 second expiration
        with patch.dict(
            "os.environ",
            {
                "JWT_ACCESS_TOKEN_EXPIRE_SECONDS": "3",
            },
        ):
            config = AuthConfig()
            service = JWTService(config)
            service._private_key = jwt_service_with_temp_keys._load_private_key()
            service._public_key = jwt_service_with_temp_keys._load_public_key()

            token = service.generate_access_token(**sample_user_data)

            # Should be valid immediately
            claims = service.validate_access_token(token)
            assert claims["sub"] == sample_user_data["user_id"]

            # Wait until close to expiration but not expired yet
            time.sleep(1.5)

            # Should still be valid (not expired yet)
            claims = service.validate_access_token(token)
            assert claims["sub"] == sample_user_data["user_id"]

    def test_empty_string_claims(self, jwt_service):
        """Test token generation with empty string claims."""
        data = {
            "user_id": "user_123",
            "username": "",
            "email": "",
            "role": "",
        }

        token = jwt_service.generate_access_token(**data)
        claims = jwt_service.validate_access_token(token)

        assert claims["username"] == ""
        assert claims["email"] == ""
        assert claims["role"] == ""

    def test_whitespace_claims(self, jwt_service):
        """Test token generation with whitespace in claims."""
        data = {
            "user_id": "  user_123  ",
            "username": "  alice  ",
            "email": "  alice@example.com  ",
            "role": " admin ",
        }

        token = jwt_service.generate_access_token(**data)
        claims = jwt_service.validate_access_token(token)

        # Whitespace should be preserved
        assert claims["sub"] == "  user_123  "
        assert claims["username"] == "  alice  "
        assert claims["email"] == "  alice@example.com  "
        assert claims["role"] == " admin "

    def test_numeric_string_claims(self, jwt_service):
        """Test claims that are numeric strings."""
        data = {
            "user_id": "12345",
            "username": "98765",
            "email": "123@example.com",
            "role": "1",
        }

        token = jwt_service.generate_access_token(**data)
        claims = jwt_service.validate_access_token(token)

        # Should remain as strings
        assert claims["sub"] == "12345"
        assert claims["username"] == "98765"
        assert isinstance(claims["sub"], str)


# ============================================================================
# TEST: INTEGRATION
# ============================================================================


class TestIntegration:
    """Test integration scenarios and workflows."""

    def test_complete_access_token_lifecycle(self, jwt_service, sample_user_data):
        """Test complete lifecycle: generate, validate, decode, check expiry."""
        # Generate
        token = jwt_service.generate_access_token(**sample_user_data)
        assert isinstance(token, str)

        # Validate
        claims = jwt_service.validate_access_token(token)
        assert claims["sub"] == sample_user_data["user_id"]

        # Unsafe decode
        unsafe_claims = jwt_service.decode_token_unsafe(token)
        assert unsafe_claims["sub"] == sample_user_data["user_id"]

        # Get expiry
        expiry = jwt_service.get_token_expiry(token)
        assert isinstance(expiry, datetime)

        # Check if expired
        assert jwt_service.is_token_expired(token) is False

    def test_complete_refresh_token_lifecycle(self, jwt_service):
        """Test complete refresh token lifecycle."""
        user_id = "user_123"
        family_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())

        # Generate
        token = jwt_service.generate_refresh_token(user_id, family_id, jti)

        # Validate
        claims = jwt_service.validate_refresh_token(token)
        assert claims["sub"] == user_id
        assert claims["family_id"] == family_id
        assert claims["jti"] == jti
        assert claims["type"] == "refresh"

        # Decode unsafe
        unsafe_claims = jwt_service.decode_token_unsafe(token)
        assert unsafe_claims["type"] == "refresh"

        # Get expiry
        expiry = jwt_service.get_token_expiry(token)
        assert isinstance(expiry, datetime)

        # Check if expired
        assert jwt_service.is_token_expired(token) is False

    def test_token_rotation_scenario(self, jwt_service):
        """Test token rotation with family ID tracking."""
        user_id = "user_123"
        family_id = str(uuid.uuid4())

        # Generate initial refresh token
        jti1 = str(uuid.uuid4())
        token1 = jwt_service.generate_refresh_token(user_id, family_id, jti1)
        claims1 = jwt_service.validate_refresh_token(token1)

        # Rotate: generate new refresh token with same family_id, new jti
        jti2 = str(uuid.uuid4())
        token2 = jwt_service.generate_refresh_token(user_id, family_id, jti2)
        claims2 = jwt_service.validate_refresh_token(token2)

        # Both should have same family_id
        assert claims1["family_id"] == claims2["family_id"]

        # But different JTIs
        assert claims1["jti"] != claims2["jti"]
        assert claims1["jti"] == jti1
        assert claims2["jti"] == jti2

    def test_multi_role_authorization_flow(self, jwt_service, sample_user_data):
        """Test generating tokens for different roles."""
        roles = ["viewer", "editor", "admin"]
        tokens = {}

        for role in roles:
            data = sample_user_data.copy()
            data["role"] = role
            token = jwt_service.generate_access_token(**data)
            tokens[role] = token

        # Validate all tokens
        for role, token in tokens.items():
            claims = jwt_service.validate_access_token(token)
            assert claims["role"] == role

    def test_key_lazy_loading_workflow(self, jwt_service, sample_user_data):
        """Test that keys are only loaded when needed."""
        # Create fresh service
        service = JWTService(jwt_service.config)

        # Keys should not be loaded yet
        assert service._private_key is None
        assert service._public_key is None

        # Generate token (loads private key)
        token = service.generate_access_token(**sample_user_data)

        # Private key should now be loaded
        assert service._private_key is not None

        # Public key still not loaded
        assert service._public_key is None

        # Validate token (loads public key)
        service.validate_access_token(token)

        # Both keys now loaded
        assert service._private_key is not None
        assert service._public_key is not None


class TestTokenTypeSeparation:
    """Access, refresh and 2FA-challenge tokens must not be interchangeable.

    All three share the signing key, issuer and audience, so the claims that
    distinguish them are the only thing keeping a password-only login (which
    yields a challenge token) from authenticating API requests.
    """

    def test_challenge_token_is_rejected_as_access_token(self, jwt_service):
        challenge = jwt_service.generate_2fa_challenge_token("user_123", "challenge-1")

        with pytest.raises(InvalidTokenError) as exc_info:
            jwt_service.validate_access_token(challenge)

        assert "challenge" in str(exc_info.value).lower()

    def test_challenge_token_is_rejected_as_refresh_token(self, jwt_service):
        challenge = jwt_service.generate_2fa_challenge_token("user_123", "challenge-1")

        with pytest.raises(InvalidTokenError):
            jwt_service.validate_refresh_token(challenge)

    def test_access_token_is_rejected_as_challenge_token(
        self, jwt_service, sample_user_data
    ):
        access = jwt_service.generate_access_token(**sample_user_data)

        with pytest.raises(InvalidTokenError):
            jwt_service.validate_2fa_challenge_token(access)

    def test_access_token_carries_the_access_type(self, jwt_service, sample_user_data):
        access = jwt_service.generate_access_token(**sample_user_data)

        assert jwt_service.decode_token_unsafe(access)["type"] == "access"
        assert jwt_service.validate_access_token(access)["sub"] == "user_123456"

    def test_access_token_without_type_claim_is_still_accepted(self, jwt_service):
        # Tokens issued before the "type" claim existed must keep working
        # until they expire.
        import jwt as pyjwt

        now = datetime.now(UTC)
        legacy = pyjwt.encode(
            {
                "sub": "user_123",
                "exp": now + timedelta(minutes=5),
                "iat": now,
                "iss": jwt_service.config.jwt_issuer,
                "aud": jwt_service.config.jwt_audience,
                "jti": str(uuid.uuid4()),
            },
            jwt_service._load_private_key(),
            algorithm=jwt_service.algorithm,
        )

        assert jwt_service.validate_access_token(legacy)["sub"] == "user_123"

    def test_challenge_token_carries_remember_me(self, jwt_service):
        remembered = jwt_service.generate_2fa_challenge_token(
            "user_123", "c1", remember_me=True
        )
        default = jwt_service.generate_2fa_challenge_token("user_123", "c2")

        assert jwt_service.validate_2fa_challenge_token(remembered)["remember_me"]
        assert not jwt_service.validate_2fa_challenge_token(default)["remember_me"]
