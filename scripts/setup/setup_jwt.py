#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""
Enhanced JWT Key Setup Script

This script generates, validates, and manages ES256 (ECDSA P-256) key pairs
for JWT token signing with comprehensive CLI options and validation.

Features:
- Generate ES256 key pairs with proper permissions
- Validate existing keys by testing sign/verify operations
- Backup existing keys before regeneration
- Idempotent operation (skip if valid keys exist)
- Non-interactive mode for automation
- Verify .gitignore configuration

Usage:
    python scripts/setup/setup_jwt.py
    python scripts/setup/setup_jwt.py --force
    python scripts/setup/setup_jwt.py --validate-only
    python scripts/setup/setup_jwt.py --backup --force
    python scripts/setup/setup_jwt.py --output-dir custom/path --non-interactive
"""

import os
import sys
import shutil
import datetime
from pathlib import Path
from typing import Tuple, Optional

import click
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key

# Add scripts directory to path to import SetupConsole
script_dir = Path(__file__).resolve().parent
setup_utils_dir = script_dir / "utils"
sys.path.insert(0, str(setup_utils_dir))

from console import SetupConsole


def generate_key_pair() -> Tuple[bytes, bytes]:
    """
    Generate an ES256 (ECDSA P-256) key pair.

    Returns:
        A tuple of (private_key_pem, public_key_pem) as bytes.
    """
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

    return private_pem, public_pem


def validate_key_pair(private_path: Path, public_path: Path, console: SetupConsole) -> bool:
    """
    Validate that a key pair can successfully sign and verify a JWT token.

    Args:
        private_path: Path to the private key file.
        public_path: Path to the public key file.
        console: SetupConsole instance for output.

    Returns:
        True if the key pair is valid, False otherwise.
    """
    try:
        # Check if files exist
        if not private_path.exists():
            console.error(f"Private key not found: {private_path}")
            return False
        if not public_path.exists():
            console.error(f"Public key not found: {public_path}")
            return False

        # Load the private key
        with open(private_path, 'rb') as f:
            private_key = load_pem_private_key(f.read(), password=None, backend=default_backend())

        # Load the public key
        with open(public_path, 'rb') as f:
            public_key_pem = f.read()

        # Create a test JWT payload
        test_payload = {
            'test': True,
            'timestamp': datetime.datetime.utcnow().isoformat(),
            'purpose': 'validation'
        }

        # Sign a test token with the private key
        token = jwt.encode(test_payload, private_key, algorithm='ES256')

        # Verify the token with the public key
        decoded = jwt.decode(token, public_key_pem, algorithms=['ES256'])

        # Verify the payload matches
        if decoded.get('test') != True or decoded.get('purpose') != 'validation':
            console.error("Key validation failed: Decoded payload doesn't match")
            return False

        return True

    except Exception as e:
        console.error(f"Key validation failed: {str(e)}")
        return False


def backup_keys(output_dir: Path, console: SetupConsole) -> Optional[Path]:
    """
    Backup existing key files to a timestamped directory.

    Args:
        output_dir: Directory containing the keys to backup.
        console: SetupConsole instance for output.

    Returns:
        Path to the backup directory, or None if no keys to backup.
    """
    private_key_path = output_dir / "private_key.pem"
    public_key_path = output_dir / "public_key.pem"

    # Check if any keys exist
    if not private_key_path.exists() and not public_key_path.exists():
        return None

    # Create backup directory with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = output_dir / f"backup_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Backup existing keys
    files_backed_up = []
    if private_key_path.exists():
        shutil.copy2(private_key_path, backup_dir / "private_key.pem")
        files_backed_up.append("private_key.pem")

    if public_key_path.exists():
        shutil.copy2(public_key_path, backup_dir / "public_key.pem")
        files_backed_up.append("public_key.pem")

    if files_backed_up:
        console.success(f"Backed up {', '.join(files_backed_up)} to {backup_dir}")
        return backup_dir

    return None


def ensure_gitignore(secrets_dir: Path, console: SetupConsole) -> None:
    """
    Ensure the secrets directory is listed in .gitignore.

    Args:
        secrets_dir: Path to the secrets directory.
        console: SetupConsole instance for output.
    """
    # Find the project root (where .gitignore should be)
    project_root = secrets_dir
    while project_root.parent != project_root:
        if (project_root / ".gitignore").exists():
            break
        project_root = project_root.parent
    else:
        # Reached filesystem root without finding .gitignore
        console.warning("Could not find .gitignore file")
        return

    gitignore_path = project_root / ".gitignore"

    # Read existing .gitignore
    try:
        with open(gitignore_path, 'r') as f:
            gitignore_content = f.read()
    except Exception as e:
        console.warning(f"Could not read .gitignore: {e}")
        return

    # Check if secrets/ is already in .gitignore
    if 'secrets/' in gitignore_content:
        console.info(".gitignore already includes secrets/ directory")
        return

    console.warning("secrets/ directory not found in .gitignore")
    console.info("Please ensure 'secrets/' is added to your .gitignore file")


def set_file_permissions(private_path: Path, public_path: Path, console: SetupConsole) -> None:
    """
    Set appropriate file permissions for key files.

    Args:
        private_path: Path to the private key file.
        public_path: Path to the public key file.
        console: SetupConsole instance for output.
    """
    try:
        # Private key: 600 (read/write for owner only)
        os.chmod(private_path, 0o600)
        # Public key: 644 (read/write for owner, read for others)
        os.chmod(public_path, 0o644)
        console.info("File permissions set: private key (600), public key (644)")
    except Exception as e:
        console.warning(f"Could not set file permissions: {e}")


def write_keys(output_dir: Path, private_pem: bytes, public_pem: bytes, console: SetupConsole) -> Tuple[Path, Path]:
    """
    Write key files to the output directory.

    Args:
        output_dir: Directory to write the keys to.
        private_pem: Private key in PEM format.
        public_pem: Public key in PEM format.
        console: SetupConsole instance for output.

    Returns:
        Tuple of (private_key_path, public_key_path).
    """
    private_key_path = output_dir / "private_key.pem"
    public_key_path = output_dir / "public_key.pem"

    # Write private key
    with open(private_key_path, "wb") as f:
        f.write(private_pem)

    # Write public key
    with open(public_key_path, "wb") as f:
        f.write(public_pem)

    # Set permissions
    set_file_permissions(private_key_path, public_key_path, console)

    return private_key_path, public_key_path


@click.command()
@click.option(
    '--output-dir',
    type=click.Path(),
    default='secrets/jwt',
    help='Directory for JWT keys (default: secrets/jwt)'
)
@click.option(
    '--force',
    is_flag=True,
    help='Force regeneration even if valid keys exist'
)
@click.option(
    '--validate-only',
    is_flag=True,
    help='Only validate existing keys without generating new ones'
)
@click.option(
    '--backup',
    is_flag=True,
    help='Backup existing keys before regeneration'
)
@click.option(
    '--non-interactive',
    is_flag=True,
    help='Run without prompts, use defaults'
)
def main(output_dir: str, force: bool, validate_only: bool, backup: bool, non_interactive: bool):
    """
    Enhanced JWT Key Setup Script.

    Generate, validate, and manage ES256 key pairs for JWT token signing.
    """
    console = SetupConsole()

    # Display header
    console.header(
        "JWT ES256 Key Setup",
        "Generate and manage ECDSA P-256 keys for JWT signing"
    )

    # Resolve output directory to absolute path
    project_root = Path(__file__).resolve().parent.parent.parent
    output_path = Path(output_dir)
    if not output_path.is_absolute():
        output_path = project_root / output_path

    private_key_path = output_path / "private_key.pem"
    public_key_path = output_path / "public_key.pem"

    # VALIDATE-ONLY mode
    if validate_only:
        console.step(1, 1, "Validating existing keys")
        if validate_key_pair(private_key_path, public_key_path, console):
            console.success("Key validation successful")
            console.info(f"Private key: {private_key_path}")
            console.info(f"Public key: {public_key_path}")
            sys.exit(0)
        else:
            console.error("Key validation failed")
            sys.exit(1)

    # Check if keys already exist
    keys_exist = private_key_path.exists() or public_key_path.exists()

    if keys_exist and not force:
        console.info("JWT keys already exist")
        console.info(f"Private key: {private_key_path}")
        console.info(f"Public key: {public_key_path}")

        # Validate existing keys
        console.step(1, 2, "Validating existing keys")
        if validate_key_pair(private_key_path, public_key_path, console):
            console.success("Existing keys are valid")
            console.info("Use --force to regenerate keys")
            sys.exit(0)
        else:
            console.warning("Existing keys are invalid")
            if not non_interactive:
                if not console.confirm("Do you want to regenerate the keys?", default=True):
                    console.info("Keeping existing keys. Exiting.")
                    sys.exit(0)
            else:
                console.info("Non-interactive mode: regenerating invalid keys")

    # If force mode and keys exist, ask for confirmation (unless non-interactive)
    if keys_exist and force and not non_interactive:
        console.warning("Force mode: This will overwrite existing keys")
        if not console.confirm("Are you sure you want to regenerate keys?", default=False):
            console.info("Operation cancelled")
            sys.exit(0)

    # Backup existing keys if requested
    if backup and keys_exist:
        console.step(1, 4, "Backing up existing keys")
        backup_dir = backup_keys(output_path, console)
        if backup_dir:
            console.success(f"Backup created: {backup_dir}")
    else:
        console.step(1, 3, "Preparing to generate keys")

    # Create output directory with proper permissions
    step_num = 2 if backup else 2
    total_steps = 4 if backup else 3
    console.step(step_num, total_steps, "Creating output directory")

    try:
        output_path.mkdir(parents=True, exist_ok=True)
        # Set directory permissions to 700 (owner only)
        os.chmod(output_path, 0o700)
        console.success(f"Output directory ready: {output_path}")
    except Exception as e:
        console.error(f"Failed to create output directory: {e}")
        sys.exit(1)

    # Generate key pair
    step_num += 1
    console.step(step_num, total_steps, "Generating ES256 key pair")

    try:
        with console.spinner("Generating keys..."):
            private_pem, public_pem = generate_key_pair()
        console.success("Key pair generated successfully")
    except Exception as e:
        console.error(f"Failed to generate key pair: {e}")
        sys.exit(1)

    # Write keys to files
    try:
        private_path, public_path = write_keys(output_path, private_pem, public_pem, console)
        console.success(f"Private key written: {private_path}")
        console.success(f"Public key written: {public_path}")
    except Exception as e:
        console.error(f"Failed to write key files: {e}")
        sys.exit(1)

    # Validate the generated keys
    step_num += 1
    console.step(step_num, total_steps, "Validating generated keys")

    if validate_key_pair(private_path, public_path, console):
        console.success("Key validation successful")
    else:
        console.error("Generated keys failed validation")
        sys.exit(1)

    # Check .gitignore
    ensure_gitignore(output_path, console)

    # Success summary
    console.console.print()
    console.console.print("[bold green]Setup completed successfully![/bold green]")
    console.console.print()
    console.warning("IMPORTANT: Keep the private key secure and never commit it to version control")
    console.console.print()

    sys.exit(0)


if __name__ == "__main__":
    main()
