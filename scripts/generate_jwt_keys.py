# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

# #!/usr/bin/env python3
"""
Generate ES256 JWT Keys

This script generates a private/public key pair using the ES256 algorithm
(ECDSA with SHA-256, using the P-256 curve) for JWT token signing.

ES256 is more secure than HS256 because it uses asymmetric encryption,
allowing the public key to verify tokens without exposing the signing key.

Usage:
    python scripts/generate_jwt_keys.py
"""

import os
import sys
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend


def generate_jwt_keys():
    """Generate ES256 key pair and save to secrets directory."""

    # Determine the project root directory
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    secrets_dir = project_root / "secrets" / "jwt"

    # Create secrets directory if it doesn't exist
    secrets_dir.mkdir(parents=True, exist_ok=True)

    print("Generating ES256 key pair...")

    # Generate private key using SECP256R1 (P-256) curve
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())

    # Serialize private key to PEM format (PKCS8, no encryption)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Extract public key from private key
    public_key = private_key.public_key()

    # Serialize public key to PEM format
    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Define file paths
    private_key_path = secrets_dir / "private_key.pem"
    public_key_path = secrets_dir / "public_key.pem"

    # Write private key to file
    with open(private_key_path, "wb") as f:
        f.write(private_pem)

    # Write public key to file
    with open(public_key_path, "wb") as f:
        f.write(public_pem)

    # Set appropriate file permissions
    # Private key: 600 (read/write for owner only)
    os.chmod(private_key_path, 0o600)

    # Public key: 644 (read/write for owner, read for others)
    os.chmod(public_key_path, 0o644)

    print(f"\n✓ Keys generated successfully!")
    print(f"  Private key: {private_key_path}")
    print(f"  Public key:  {public_key_path}")
    print(f"\n⚠️  IMPORTANT: Keep the private key secure and never commit it to version control!")
    print(f"  File permissions set:")
    print(f"    - Private key: 600 (owner read/write only)")
    print(f"    - Public key:  644 (owner read/write, others read)")

    return private_key_path, public_key_path


def verify_keys_exist():
    """Check if JWT keys already exist."""
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent
    secrets_dir = project_root / "secrets" / "jwt"

    private_key_path = secrets_dir / "private_key.pem"
    public_key_path = secrets_dir / "public_key.pem"

    if private_key_path.exists() or public_key_path.exists():
        return True, private_key_path, public_key_path
    return False, private_key_path, public_key_path


def main():
    """Main entry point."""
    print("=" * 60)
    print("JWT ES256 Key Generator")
    print("=" * 60)

    # Check if keys already exist
    keys_exist, private_path, public_path = verify_keys_exist()

    if keys_exist:
        print("\n⚠️  Warning: JWT keys already exist!")
        print(f"  Private key: {private_path}")
        print(f"  Public key:  {public_path}")

        response = input("\nDo you want to regenerate them? This will overwrite existing keys. (yes/no): ")
        if response.lower() not in ['yes', 'y']:
            print("\n✓ Keeping existing keys. Exiting.")
            sys.exit(0)
        print("\nRegenerating keys...")

    try:
        generate_jwt_keys()
        print("\n✓ Done!")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error generating keys: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
