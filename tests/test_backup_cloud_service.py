# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for BackupCloudService."""

import json
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from src.services.backup_cloud_service import BackupCloudService, _get_credentials_passphrase
from src.services.backup_encryption_service import BackupEncryptionService


class TestGetCredentialsPassphrase:
    def test_raises_when_env_not_set(self, monkeypatch):
        monkeypatch.delenv("PROMPTVAULT_CLOUD_CREDS_PASSPHRASE", raising=False)
        with pytest.raises(RuntimeError, match="PROMPTVAULT_CLOUD_CREDS_PASSPHRASE"):
            _get_credentials_passphrase()

    def test_returns_env_value(self, monkeypatch):
        monkeypatch.setenv("PROMPTVAULT_CLOUD_CREDS_PASSPHRASE", "my-secret")
        assert _get_credentials_passphrase() == "my-secret"


class TestCreateProvider:
    def test_create_s3_provider(self, cloud_service):
        result = cloud_service.create_provider(
            name="Test S3",
            provider_type="s3",
            bucket_name="my-bucket",
            access_key="AKIAIOSF000000000",
            secret_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            endpoint_url="https://s3.example.com",
            prefix="backups/",
            region="us-east-1",
        )
        assert result["name"] == "Test S3"
        assert result["provider_type"] == "s3"
        assert result["bucket_name"] == "my-bucket"
        assert result["endpoint_url"] == "https://s3.example.com"
        assert result["prefix"] == "backups/"
        assert result["region"] == "us-east-1"
        assert result["enabled"] is True
        assert "credentials_encrypted" not in result
        assert "credentials_salt" not in result

    def test_create_provider_unsupported_type(self, cloud_service):
        with pytest.raises(ValueError, match="Unsupported provider_type"):
            cloud_service.create_provider(
                name="GDrive",
                provider_type="google_drive",
                bucket_name="bucket",
                access_key="key",
                secret_key="secret",
            )

    def test_create_provider_without_optional_fields(self, cloud_service):
        result = cloud_service.create_provider(
            name="Minimal",
            provider_type="s3",
            bucket_name="bucket",
            access_key="AK",
            secret_key="SK",
        )
        assert result["endpoint_url"] is None
        assert result["region"] is None
        assert result["prefix"] == ""

    @pytest.mark.parametrize(
        "endpoint_url",
        [
            "http://s3.example.com",
            "http://169.254.169.254/latest/meta-data/",
            "https://169.254.169.254/",
            "https://127.0.0.1:9000",
            "https://localhost",
            "https://10.0.0.5",
            "https://192.168.1.1",
            "https://[::1]",
        ],
    )
    def test_create_provider_rejects_ssrf_endpoint(self, cloud_service, endpoint_url):
        with pytest.raises(ValueError):
            cloud_service.create_provider(
                name="Malicious",
                provider_type="s3",
                bucket_name="bucket",
                access_key="AK",
                secret_key="SK",
                endpoint_url=endpoint_url,
            )

    def test_create_provider_allows_public_https_endpoint(self, cloud_service):
        result = cloud_service.create_provider(
            name="Public",
            provider_type="s3",
            bucket_name="bucket",
            access_key="AK",
            secret_key="SK",
            endpoint_url="https://s3.example.com",
        )
        assert result["endpoint_url"] == "https://s3.example.com"


class TestListProviders:
    def test_list_empty(self, cloud_service):
        assert cloud_service.list_providers() == []

    def test_list_after_create(self, cloud_service):
        cloud_service.create_provider(
            name="P1", provider_type="s3", bucket_name="b1",
            access_key="ak1", secret_key="sk1",
        )
        cloud_service.create_provider(
            name="P2", provider_type="s3", bucket_name="b2",
            access_key="ak2", secret_key="sk2",
        )
        providers = cloud_service.list_providers()
        assert len(providers) == 2
        names = {p["name"] for p in providers}
        assert names == {"P1", "P2"}

    def test_list_never_includes_credentials(self, cloud_service):
        cloud_service.create_provider(
            name="P1", provider_type="s3", bucket_name="b1",
            access_key="ak1", secret_key="sk1",
        )
        for p in cloud_service.list_providers():
            assert "credentials_encrypted" not in p
            assert "credentials_salt" not in p
            assert "credentials_nonce" not in p


class TestDeleteProvider:
    def test_delete_existing_provider(self, cloud_service):
        result = cloud_service.create_provider(
            name="ToDelete", provider_type="s3", bucket_name="b",
            access_key="ak", secret_key="sk",
        )
        deleted = cloud_service.delete_provider(result["id"])
        assert deleted is True
        assert cloud_service.list_providers() == []

    def test_delete_nonexistent_provider(self, cloud_service):
        deleted = cloud_service.delete_provider("nonexistent-id")
        assert deleted is False

    def test_delete_provider_referenced_by_backup_raises(self, cloud_service, patched_db_session):
        from src.db.models import Backup

        result = cloud_service.create_provider(
            name="InUse", provider_type="s3", bucket_name="b",
            access_key="ak", secret_key="sk",
        )
        with patched_db_session() as session:
            backup = Backup(
                id="backup-ref-test",
                backup_type="sqlite_copy",
                filename="test.db",
                storage_path="/tmp/test.db",
                cloud_provider_id=result["id"],
            )
            session.add(backup)
            session.commit()

        with pytest.raises(ValueError, match="Cannot delete provider"):
            cloud_service.delete_provider(result["id"])


class TestEncryptDecryptCredentials:
    def test_roundtrip(self, monkeypatch):
        passphrase = "test-passphrase"
        creds = json.dumps({"access_key": "AK", "secret_key": "SK"})
        salt, nonce, encrypted = BackupCloudService._encrypt_credentials(creds, passphrase)

        from argon2.low_level import hash_secret_raw, Type
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import base64

        key = hash_secret_raw(
            secret=passphrase.encode("utf-8"),
            salt=bytes.fromhex(salt),
            time_cost=3,
            memory_cost=65536,
            parallelism=1,
            hash_len=32,
            type=Type.ID,
        )
        plaintext = AESGCM(key).decrypt(bytes.fromhex(nonce), base64.b64decode(encrypted), None)
        assert json.loads(plaintext.decode("utf-8")) == {"access_key": "AK", "secret_key": "SK"}


class TestUpload:
    def test_upload_success(self, cloud_service):
        provider = MagicMock()
        provider.prefix = "backups/"
        provider.bucket_name = "my-bucket"
        provider.endpoint_url = None
        provider.region = None
        provider.credentials_salt = None
        provider.credentials_nonce = None
        provider.credentials_encrypted = None

        tmpdir = tempfile.mkdtemp()
        backup_path = os.path.join(tmpdir, "backup.db")
        with open(backup_path, "wb") as f:
            f.write(b"backup data")

        mock_client = MagicMock()
        with patch.object(cloud_service, "_decrypt_credentials", return_value={"access_key": "ak", "secret_key": "sk"}):
            with patch.object(BackupCloudService, "_get_client", return_value=mock_client):
                full_key = cloud_service.upload(backup_path, provider, "backup_20240101.db")

        mock_client.upload_fileobj.assert_called_once()
        call_args = mock_client.upload_fileobj.call_args
        assert call_args[0][1] == "my-bucket"
        assert call_args[0][2] == "backups/backup_20240101.db"
        assert full_key == "backups/backup_20240101.db"
        shutil.rmtree(tmpdir, ignore_errors=True)

    def test_upload_without_prefix(self, cloud_service):
        provider = MagicMock()
        provider.prefix = ""
        provider.bucket_name = "bucket"
        provider.endpoint_url = None
        provider.region = None

        tmpdir = tempfile.mkdtemp()
        backup_path = os.path.join(tmpdir, "backup.db")
        with open(backup_path, "wb") as f:
            f.write(b"data")

        mock_client = MagicMock()
        with patch.object(cloud_service, "_decrypt_credentials", return_value={"access_key": "ak", "secret_key": "sk"}):
            with patch.object(BackupCloudService, "_get_client", return_value=mock_client):
                full_key = cloud_service.upload(backup_path, provider, "file.db")

        assert full_key == "file.db"
        shutil.rmtree(tmpdir, ignore_errors=True)


class TestDownload:
    def test_download_success(self, cloud_service):
        provider = MagicMock()
        provider.bucket_name = "my-bucket"
        provider.endpoint_url = None
        provider.region = None

        tmpdir = tempfile.mkdtemp()
        dest_path = os.path.join(tmpdir, "downloaded.db")

        mock_client = MagicMock()
        with patch.object(cloud_service, "_decrypt_credentials", return_value={"access_key": "ak", "secret_key": "sk"}):
            with patch.object(BackupCloudService, "_get_client", return_value=mock_client):
                cloud_service.download(provider, "remote/key.db", dest_path)

        mock_client.download_fileobj.assert_called_once()
        call_args = mock_client.download_fileobj.call_args
        assert call_args[0][0] == "my-bucket"
        assert call_args[0][1] == "remote/key.db"
        shutil.rmtree(tmpdir, ignore_errors=True)


class TestTestConnectivity:
    def test_connectivity_success(self, cloud_service):
        provider = MagicMock()
        provider.bucket_name = "my-bucket"
        provider.endpoint_url = None
        provider.region = None

        mock_client = MagicMock()
        mock_client.head_bucket.return_value = {}

        with patch.object(cloud_service, "_decrypt_credentials", return_value={"access_key": "ak", "secret_key": "sk"}):
            with patch.object(BackupCloudService, "_get_client", return_value=mock_client):
                result = cloud_service.test_connectivity(provider)

        assert result["success"] is True
        assert "my-bucket" in result["message"]

    def test_connectivity_client_error(self, cloud_service):
        provider = MagicMock()
        provider.bucket_name = "my-bucket"
        provider.endpoint_url = None
        provider.region = None

        mock_client = MagicMock()
        error_response = {"Error": {"Code": "403", "Message": "Forbidden"}}
        mock_client.head_bucket.side_effect = ClientError(error_response, "HeadBucket")

        with patch.object(cloud_service, "_decrypt_credentials", return_value={"access_key": "ak", "secret_key": "sk"}):
            with patch.object(BackupCloudService, "_get_client", return_value=mock_client):
                result = cloud_service.test_connectivity(provider)

        assert result["success"] is False
        assert "403" in result["message"]

    def test_connectivity_endpoint_error(self, cloud_service):
        provider = MagicMock()
        provider.bucket_name = "my-bucket"
        provider.endpoint_url = "https://bad-endpoint.example.com"
        provider.region = None

        mock_client = MagicMock()
        mock_client.head_bucket.side_effect = EndpointConnectionError(endpoint_url="https://bad-endpoint.example.com")

        with patch.object(cloud_service, "_decrypt_credentials", return_value={"access_key": "ak", "secret_key": "sk"}):
            with patch.object(BackupCloudService, "_get_client", return_value=mock_client):
                result = cloud_service.test_connectivity(provider)

        assert result["success"] is False
        assert "Cannot reach endpoint" in result["message"]

    def test_connectivity_generic_error(self, cloud_service):
        provider = MagicMock()
        provider.bucket_name = "my-bucket"
        provider.endpoint_url = None
        provider.region = None

        mock_client = MagicMock()
        mock_client.head_bucket.side_effect = RuntimeError("unexpected")

        with patch.object(cloud_service, "_decrypt_credentials", return_value={"access_key": "ak", "secret_key": "sk"}):
            with patch.object(BackupCloudService, "_get_client", return_value=mock_client):
                result = cloud_service.test_connectivity(provider)

        assert result["success"] is False
        assert "unexpected" in result["message"]


class TestGetClient:
    def test_get_client_with_all_options(self):
        provider = MagicMock()
        provider.endpoint_url = "https://minio.example.com"
        provider.region = "eu-west-1"
        creds = {"access_key": "AK", "secret_key": "SK"}

        with patch("boto3.client") as mock_boto:
            mock_boto.return_value = MagicMock()
            BackupCloudService._get_client(provider, creds)
            mock_boto.assert_called_once_with(
                "s3",
                aws_access_key_id="AK",
                aws_secret_access_key="SK",
                endpoint_url="https://minio.example.com",
                region_name="eu-west-1",
            )

    def test_get_client_minimal(self):
        provider = MagicMock()
        provider.endpoint_url = None
        provider.region = None
        creds = {"access_key": "AK", "secret_key": "SK"}

        with patch("boto3.client") as mock_boto:
            mock_boto.return_value = MagicMock()
            BackupCloudService._get_client(provider, creds)
            mock_boto.assert_called_once_with(
                "s3",
                aws_access_key_id="AK",
                aws_secret_access_key="SK",
            )


class TestSerializeProvider:
    def test_serialize_never_includes_credentials(self):
        provider = MagicMock()
        provider.id = "p-1"
        provider.name = "Test"
        provider.provider_type = "s3"
        provider.endpoint_url = None
        provider.bucket_name = "b"
        provider.prefix = ""
        provider.region = None
        provider.enabled = True
        provider.credentials_encrypted = "secret-data"
        provider.credentials_salt = "salt"
        provider.credentials_nonce = "nonce"

        result = BackupCloudService._serialize_provider(provider)
        assert "credentials_encrypted" not in result
        assert "credentials_salt" not in result
        assert "credentials_nonce" not in result
        assert result["id"] == "p-1"
        assert result["name"] == "Test"
