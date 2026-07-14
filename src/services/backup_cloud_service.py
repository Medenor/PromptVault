# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Backup cloud storage service for PromptVault.

Provides S3-compatible cloud storage upload/download for backup files
using boto3. Supports AWS S3, MinIO, Backblaze B2, and other
S3-compatible providers.
"""

import base64
import ipaddress
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from argon2.low_level import hash_secret_raw, Type

from src.db.session import get_db_session
from src.db.models.backup_storage_provider import BackupStorageProvider
from src.db.repositories.backup_storage_provider_repository import (
    BackupStorageProviderRepository,
)
from src.services.backup_encryption_service import (
    BackupEncryptionService,
    ARGON2_TIME_COST,
    ARGON2_MEMORY_COST,
    ARGON2_PARALLELISM,
    ARGON2_HASH_LEN,
)

logger = logging.getLogger(__name__)

def _get_credentials_passphrase() -> str:
    """Return the passphrase for cloud credential encryption.

    Raises:
        RuntimeError: If PROMPTVAULT_CLOUD_CREDS_PASSPHRASE is not set.
    """
    passphrase = os.environ.get("PROMPTVAULT_CLOUD_CREDS_PASSPHRASE")
    if not passphrase:
        raise RuntimeError(
            "PROMPTVAULT_CLOUD_CREDS_PASSPHRASE environment variable is not set. "
            "Set it to a long random secret before using cloud backup storage."
        )
    return passphrase


def _validate_endpoint_url(endpoint_url: str) -> None:
    """Validate a user-supplied S3 endpoint URL to prevent SSRF.

    Rejects non-https schemes and hosts that are IP literals resolving
    to loopback, link-local (incl. cloud metadata services), private,
    or otherwise non-public IP ranges. Hostnames are not DNS-resolved
    here (to keep validation fast and avoid a TOCTOU/DNS-rebinding
    false sense of safety); botocore will still fail closed if a
    resolved address becomes unreachable at request time.

    Raises:
        ValueError: If the endpoint URL is invalid or targets a
            disallowed network range.
    """
    parsed = urlparse(endpoint_url)
    if parsed.scheme != "https":
        raise ValueError("endpoint_url must use https://")
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("endpoint_url must include a valid host")

    if hostname == "localhost":
        raise ValueError("endpoint_url must not target localhost")

    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        return

    if (
        ip.is_loopback
        or ip.is_link_local
        or ip.is_private
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        raise ValueError(
            f"endpoint_url targets a disallowed address ({ip}); public hosts only"
        )


class BackupCloudService:
    """Service for cloud storage operations on backup files.

    Uses boto3 to interact with S3-compatible storage providers.
    Credentials are encrypted at rest using AES-256-GCM.
    """

    def upload(
        self,
        backup_path: str,
        provider: BackupStorageProvider,
        remote_key: str,
    ) -> str:
        """Upload a backup file to cloud storage.

        Args:
            backup_path: Local path to the backup file
            provider: Storage provider configuration
            remote_key: Remote object key in the bucket

        Returns:
            The remote path/key string
        """
        creds = self._decrypt_credentials(provider)
        client = self._get_client(provider, creds)

        full_key = f"{provider.prefix}{remote_key}" if provider.prefix else remote_key

        with open(backup_path, "rb") as f:
            client.upload_fileobj(f, provider.bucket_name, full_key)

        return full_key

    def download(
        self,
        provider: BackupStorageProvider,
        remote_key: str,
        dest_path: str,
    ) -> None:
        """Download a backup file from cloud storage.

        Args:
            provider: Storage provider configuration
            remote_key: Remote object key in the bucket
            dest_path: Local destination path
        """
        creds = self._decrypt_credentials(provider)
        client = self._get_client(provider, creds)

        with open(dest_path, "wb") as f:
            client.download_fileobj(provider.bucket_name, remote_key, f)

    def upload_backup_by_id(
        self,
        backup_service,
        backup_id: str,
        provider_id: str,
        log_prefix: str = "backup",
    ) -> bool:
        """Upload an existing local backup to a configured cloud provider.

        Looks up the backup's local storage path via `backup_service`,
        uploads it, and records the cloud location on the Backup row.
        Failures are logged but not raised — the local backup already
        exists and callers should not fail the overall operation because
        of a cloud upload issue.

        Args:
            backup_service: BackupService instance used to resolve backup metadata
            backup_id: ID of the already-created local backup
            provider_id: Storage provider ID to upload to
            log_prefix: Event name prefix for log messages (e.g. "backup.scheduled")

        Returns:
            True if the upload succeeded, False otherwise
        """
        try:
            from src.db.models.backup import Backup

            info = backup_service.get_backup_info(backup_id)
            if not info or not info.get("storage_path"):
                logger.warning(
                    "Cannot upload backup: metadata or storage_path missing",
                    extra={"event": f"{log_prefix}.upload_skipped", "backup_id": backup_id},
                )
                return False

            with get_db_session() as session:
                provider_repo = BackupStorageProviderRepository(session)
                provider = provider_repo.get_by_id(provider_id)
                if not provider or not provider.enabled:
                    logger.warning(
                        "Cannot upload backup: cloud provider not found or disabled",
                        extra={
                            "event": f"{log_prefix}.upload_skipped",
                            "backup_id": backup_id,
                            "provider_id": provider_id,
                        },
                    )
                    return False

                remote_key = self.upload(info["storage_path"], provider, info["filename"])

                backup = session.query(Backup).filter_by(id=backup_id).first()
                if backup:
                    backup.cloud_provider_id = provider_id
                    backup.cloud_path = remote_key
                    backup.cloud_uploaded_at = datetime.now(timezone.utc)
                    session.commit()

            logger.info(
                "Backup uploaded to cloud storage",
                extra={
                    "event": f"{log_prefix}.upload_success",
                    "backup_id": backup_id,
                    "provider_id": provider_id,
                },
            )
            return True

        except Exception as exc:
            logger.error(
                "Failed to upload backup to cloud storage",
                extra={
                    "event": f"{log_prefix}.upload_failure",
                    "backup_id": backup_id,
                    "provider_id": provider_id,
                },
                exc_info=exc,
            )
            return False

    def test_connectivity(self, provider: BackupStorageProvider) -> Dict[str, Any]:
        """Test connectivity to the cloud storage provider.

        Args:
            provider: Storage provider configuration

        Returns:
            Dict with 'success' and 'message' keys
        """
        try:
            creds = self._decrypt_credentials(provider)
            client = self._get_client(provider, creds)
            client.head_bucket(Bucket=provider.bucket_name)
            return {
                "success": True,
                "message": f"Connected to bucket '{provider.bucket_name}'",
            }
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "Unknown")
            return {"success": False, "message": f"S3 error: {error_code}"}
        except EndpointConnectionError:
            return {"success": False, "message": "Cannot reach endpoint"}
        except Exception as exc:
            return {"success": False, "message": str(exc)}

    def create_provider(
        self,
        name: str,
        provider_type: str,
        bucket_name: str,
        access_key: str,
        secret_key: str,
        endpoint_url: Optional[str] = None,
        prefix: str = "",
        region: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new storage provider with encrypted credentials.

        Args:
            name: Display name
            provider_type: 's3'
            bucket_name: S3 bucket name
            access_key: AWS access key ID
            secret_key: AWS secret access key
            endpoint_url: Custom endpoint for S3-compatible providers
            prefix: Key prefix within bucket
            region: AWS region

        Returns:
            Provider dict (without credentials)
        """
        supported = {"s3"}
        if provider_type not in supported:
            raise ValueError(
                f"Unsupported provider_type '{provider_type}'. "
                "Currently supported: s3 (AWS S3, MinIO, Backblaze B2, Cloudflare R2, etc.). "
                "Google Drive and Dropbox support is planned for a future release."
            )

        if endpoint_url:
            _validate_endpoint_url(endpoint_url)

        passphrase = _get_credentials_passphrase()

        creds_json = json.dumps({"access_key": access_key, "secret_key": secret_key})
        salt, nonce, encrypted_creds = self._encrypt_credentials(creds_json, passphrase)

        with get_db_session() as session:
            repo = BackupStorageProviderRepository(session)
            provider = repo.create(
                id=str(uuid.uuid4()),
                name=name,
                provider_type=provider_type,
                endpoint_url=endpoint_url,
                bucket_name=bucket_name,
                prefix=prefix,
                region=region,
                credentials_encrypted=encrypted_creds,
                credentials_salt=salt,
                credentials_nonce=nonce,
                enabled=True,
            )
            session.commit()
            return self._serialize_provider(provider)

    def list_providers(self) -> list:
        """List all configured storage providers.

        Returns:
            List of provider dicts (without credentials)
        """
        with get_db_session() as session:
            repo = BackupStorageProviderRepository(session)
            providers = repo.list_all()
            return [self._serialize_provider(p) for p in providers]

    def delete_provider(self, provider_id: str) -> bool:
        """Delete a storage provider.

        Args:
            provider_id: Provider ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If provider is referenced by backups
        """
        with get_db_session() as session:
            from src.db.models import Backup
            ref_count = session.query(Backup).filter_by(cloud_provider_id=provider_id).count()
            if ref_count > 0:
                raise ValueError(
                    f"Cannot delete provider: {ref_count} backup(s) reference it"
                )

            repo = BackupStorageProviderRepository(session)
            deleted = repo.delete(provider_id)
            session.commit()
            return deleted

    def _decrypt_credentials(self, provider: BackupStorageProvider) -> Dict[str, str]:
        """Decrypt stored credentials for a provider.

        Args:
            provider: Storage provider with encrypted credentials

        Returns:
            Dict with 'access_key' and 'secret_key'
        """
        passphrase = _get_credentials_passphrase()
        salt = bytes.fromhex(provider.credentials_salt)
        nonce = bytes.fromhex(provider.credentials_nonce)
        ciphertext = base64.b64decode(provider.credentials_encrypted)

        key = hash_secret_raw(
            secret=passphrase.encode("utf-8"),
            salt=salt,
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
            hash_len=ARGON2_HASH_LEN,
            type=Type.ID,
        )
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return json.loads(plaintext.decode("utf-8"))

    @staticmethod
    def _encrypt_credentials(creds_json: str, passphrase: str) -> tuple:
        """Encrypt credentials JSON with Argon2id + AES-256-GCM.

        Returns:
            Tuple of (salt_hex, nonce_hex, base64_ciphertext)
        """
        salt = os.urandom(16)
        nonce = os.urandom(12)
        key = hash_secret_raw(
            secret=passphrase.encode("utf-8"),
            salt=salt,
            time_cost=ARGON2_TIME_COST,
            memory_cost=ARGON2_MEMORY_COST,
            parallelism=ARGON2_PARALLELISM,
            hash_len=ARGON2_HASH_LEN,
            type=Type.ID,
        )
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, creds_json.encode("utf-8"), None)
        return salt.hex(), nonce.hex(), base64.b64encode(ciphertext).decode("utf-8")

    @staticmethod
    def _get_client(provider: BackupStorageProvider, creds: Dict[str, str]):
        """Create a boto3 S3 client for the provider.

        Args:
            provider: Storage provider configuration
            creds: Decrypted credentials dict

        Returns:
            boto3 S3 client
        """
        kwargs: Dict[str, Any] = {
            "aws_access_key_id": creds["access_key"],
            "aws_secret_access_key": creds["secret_key"],
        }
        if provider.endpoint_url:
            kwargs["endpoint_url"] = provider.endpoint_url
        if provider.region:
            kwargs["region_name"] = provider.region

        return boto3.client("s3", **kwargs)

    @staticmethod
    def _serialize_provider(provider: BackupStorageProvider) -> Dict[str, Any]:
        """Serialize a provider to dict (never includes credentials)."""
        return {
            "id": provider.id,
            "name": provider.name,
            "provider_type": provider.provider_type,
            "endpoint_url": provider.endpoint_url,
            "bucket_name": provider.bucket_name,
            "prefix": provider.prefix,
            "region": provider.region,
            "enabled": provider.enabled,
        }
