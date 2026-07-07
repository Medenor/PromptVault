# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Backup management API endpoints.

Provides REST API routes for backup CRUD, scheduling, encryption,
cloud storage, restore preview, monitoring, and audit operations.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import JSONResponse

from src.db.models.user import User
from src.web.dependencies.auth import get_current_user_or_none
from src.web.models import BackupCreateRequest, BackupCompressRequest
from src.web.monitoring import ValidationMonitor

router = APIRouter(tags=["backups"])

_backup_service = None
_validation_monitor = None
_record_validation_event = None


def init_backup_router(backup_service, validation_monitor=None, record_validation_event=None):
    """Initialize the backup router with service dependencies.

    Args:
        backup_service: BackupService instance
        validation_monitor: Optional ValidationMonitor instance
        record_validation_event: Optional validation recording function
    """
    global _backup_service, _validation_monitor, _record_validation_event
    _backup_service = backup_service
    _validation_monitor = validation_monitor
    _record_validation_event = record_validation_event


def _get_backup_service():
    if _backup_service is None:
        raise HTTPException(status_code=503, detail="Backup service not initialized")
    return _backup_service


@router.get("/api/backups")
async def get_backups(
    tag: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    kind: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user: Optional[User] = Depends(get_current_user_or_none),
):
    """Get list of all backups with optional filters."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    service = _get_backup_service()
    backups = service.list_backups()

    if tag:
        backups = [b for b in backups if tag in (b.get("tags") or [])]
    if kind:
        backups = [b for b in backups if b.get("backup_kind", "full") == kind]
    if start_date:
        backups = [b for b in backups if (b.get("timestamp") or "") >= start_date]
    if end_date:
        backups = [b for b in backups if (b.get("timestamp") or "") <= end_date]

    total = len(backups)
    backups = backups[offset:offset + limit]

    return {"backups": backups, "total": total}


@router.post("/api/backups")
async def create_manual_backup(
    name: str = Form(None),
    current_user: Optional[User] = Depends(get_current_user_or_none),
):
    """Create a manual backup with validation."""
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    service = _get_backup_service()
    try:
        validated_data = BackupCreateRequest(name=name)

        backup_id = service.create_backup(
            validated_data.name,
            created_by=current_user.username if current_user else "anonymous",
        )
        if backup_id:
            if _record_validation_event:
                _record_validation_event(endpoint="/api/backups", success=True)
            return {"success": True, "backup_id": backup_id}
        else:
            return JSONResponse(
                status_code=500, content={"error": "Failed to create backup"}
            )

    except Exception as e:
        from pydantic import ValidationError

        if isinstance(e, ValidationError):
            if _record_validation_event:
                _record_validation_event(
                    endpoint="/api/backups",
                    success=False,
                    errors=[err.get("msg", "") for err in e.errors()],
                )
            return JSONResponse(
                status_code=422,
                content={"error": "Validation failed", "details": e.errors()},
            )
        raise


@router.post("/api/backups/{backup_id}/restore-preview")
async def restore_preview(
    backup_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_or_none),
):
    """Preview what would change if this backup were restored."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})

    service = _get_backup_service()
    body = await request.json()
    passphrase = body.get("passphrase")

    from src.services.exceptions import BackupError
    try:
        diff = service.compute_restore_diff(backup_id, passphrase=passphrase)
        return diff
    except BackupError as exc:
        return JSONResponse(status_code=exc.http_status or 400, content={"error": str(exc)})


@router.post("/api/backups/{backup_id}/restore")
async def restore_backup(
    backup_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_or_none),
):
    """Restore from a specific backup. Supports selective restore via prompt_ids."""
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    service = _get_backup_service()
    from src.services.exceptions import BackupError

    body = await request.json()
    prompt_ids = body.get("prompt_ids", [])
    passphrase = body.get("passphrase")

    if prompt_ids:
        try:
            result = service.selective_restore(
                backup_id,
                prompt_ids=prompt_ids,
                created_by=current_user.username if current_user else "anonymous",
                passphrase=passphrase,
            )
            return result
        except BackupError as exc:
            status_code = exc.http_status or 500
            request_id = str(uuid.uuid4())
            return JSONResponse(
                status_code=status_code,
                content={"error": str(exc), "request_id": request_id},
                headers={"x-request-id": request_id},
            )

    success = False
    try:
        success = service.restore_backup(
            backup_id,
            created_by=current_user.username if current_user else "anonymous",
            passphrase=passphrase,
        )
    except BackupError as exc:
        status_code = exc.http_status or 500
        request_id = str(uuid.uuid4())
        return JSONResponse(
            status_code=status_code,
            content={"error": str(exc), "request_id": request_id},
            headers={"x-request-id": request_id},
        )
    if success:
        return {"success": True}
    return JSONResponse(status_code=500, content={"error": "Failed to restore backup"})


@router.delete("/api/backups/{backup_id}")
async def delete_backup(
    backup_id: str,
    current_user: Optional[User] = Depends(get_current_user_or_none),
):
    """Delete a specific backup."""
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    service = _get_backup_service()
    try:
        backup_info = service.get_backup_info(backup_id)
        deleted = service.delete_backup(backup_id)
        if deleted:
            return {"success": True}

        if backup_info:
            return JSONResponse(
                status_code=500, content={"error": "Failed to delete backup"}
            )
        return JSONResponse(status_code=404, content={"error": "Backup not found"})

    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"Failed to delete backup: {str(e)}"}
        )


@router.post("/api/backups/compress")
async def compress_backups(
    days_threshold: int = Form(7),
    current_user: Optional[User] = Depends(get_current_user_or_none),
):
    """Compress old backups with validation."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    service = _get_backup_service()
    try:
        validated_data = BackupCompressRequest(days_threshold=days_threshold)

        compressed_count = service.compress_old_backups(validated_data.days_threshold)
        if _record_validation_event:
            _record_validation_event(endpoint="/api/backups/compress", success=True)
        return {"success": True, "compressed_count": compressed_count}

    except Exception as e:
        from pydantic import ValidationError

        if isinstance(e, ValidationError):
            if _record_validation_event:
                _record_validation_event(
                    endpoint="/api/backups/compress",
                    success=False,
                    errors=[err.get("msg", "") for err in e.errors()],
                )
            return JSONResponse(
                status_code=422,
                content={"error": "Validation failed", "details": e.errors()},
            )
        raise


@router.get("/api/backups/stats")
async def get_backup_stats(
    current_user: Optional[User] = Depends(get_current_user_or_none),
):
    """Get backup statistics."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    service = _get_backup_service()
    stats = service.get_backup_stats()
    return stats


@router.get("/api/backup-schedule")
async def get_backup_schedule():
    """Get current backup schedule configuration."""
    from src.services.backup_scheduler_service import BackupSchedulerService

    service = BackupSchedulerService(backup_service=_backup_service)
    schedule = service.get_schedule()
    if schedule is None:
        return JSONResponse(status_code=404, content={"error": "No schedule configured"})
    return schedule


@router.put("/api/backup-schedule")
async def update_backup_schedule(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_or_none),
):
    """Create or update the backup schedule."""
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from src.services.backup_scheduler_service import BackupSchedulerService

    body = await request.json()

    frequency = body.get("frequency")
    if frequency not in ("daily", "weekly", "monthly"):
        raise HTTPException(status_code=422, detail="frequency must be daily, weekly, or monthly")

    hour = body.get("hour")
    if hour is None or not (0 <= hour <= 23):
        raise HTTPException(status_code=422, detail="hour must be 0-23")

    minute = body.get("minute", 0)
    if not (0 <= minute <= 59):
        raise HTTPException(status_code=422, detail="minute must be 0-59")

    if frequency == "weekly":
        day_of_week = body.get("day_of_week")
        if day_of_week is None or not (0 <= day_of_week <= 6):
            raise HTTPException(status_code=422, detail="day_of_week must be 0-6 for weekly")

    if frequency == "monthly":
        day_of_month = body.get("day_of_month")
        if day_of_month is None or not (1 <= day_of_month <= 31):
            raise HTTPException(status_code=422, detail="day_of_month must be 1-31 for monthly")

    kwargs = {
        "enabled": body.get("enabled", False),
        "frequency": frequency,
        "hour": hour,
        "minute": minute,
        "day_of_week": body.get("day_of_week"),
        "day_of_month": body.get("day_of_month"),
        "retention_daily_count": body.get("retention_daily_count", 7),
        "retention_weekly_count": body.get("retention_weekly_count", 4),
        "retention_monthly_count": body.get("retention_monthly_count", 12),
        "encrypt_scheduled_backups": body.get("encrypt_scheduled_backups", False),
        "cloud_provider_id": body.get("cloud_provider_id"),
    }

    service = BackupSchedulerService(backup_service=_backup_service)
    result = service.upsert_schedule(**kwargs)
    return result


@router.get("/api/backup-encryption")
async def get_encryption_config():
    """Get encryption configuration (never returns passphrase)."""
    from src.services.backup_encryption_service import BackupEncryptionService

    service = BackupEncryptionService()
    config = service.get_config()
    if config is None:
        return {"is_enabled": False, "algorithm": "AES-256-GCM", "kdf": "argon2id", "key_version": 1, "rotated_at": None}
    return config


@router.put("/api/backup-encryption")
async def update_encryption_config(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_or_none),
):
    """Enable/disable encryption or rotate key."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})

    from src.services.backup_encryption_service import BackupEncryptionService

    body = await request.json()
    service = BackupEncryptionService()

    if body.get("rotate_key"):
        old_passphrase = body.get("old_passphrase", "")
        new_passphrase = body.get("new_passphrase", "")
        if not old_passphrase or not new_passphrase:
            raise HTTPException(status_code=422, detail="old_passphrase and new_passphrase required for key rotation")
        return service.rotate_key(old_passphrase, new_passphrase)

    is_enabled = body.get("is_enabled", False)
    if is_enabled:
        passphrase = body.get("passphrase", "")
        if not passphrase:
            raise HTTPException(status_code=422, detail="passphrase required to enable encryption")
        return service.enable(passphrase)
    else:
        result = service.disable()
        if result is None:
            return {"is_enabled": False, "algorithm": "AES-256-GCM", "kdf": "argon2id", "key_version": 1, "rotated_at": None}
        return result


@router.get("/api/backup-providers")
async def list_backup_providers():
    """List configured cloud storage providers."""
    from src.services.backup_cloud_service import BackupCloudService
    service = BackupCloudService()
    providers = service.list_providers()
    return {"providers": providers}


@router.post("/api/backup-providers", status_code=201)
async def create_backup_provider(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_or_none),
):
    """Configure a new cloud storage provider."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})

    from src.services.backup_cloud_service import BackupCloudService
    body = await request.json()

    required = ["name", "provider_type", "bucket_name", "access_key", "secret_key"]
    for field in required:
        if field not in body or not body[field]:
            raise HTTPException(status_code=422, detail=f"{field} is required")

    service = BackupCloudService()
    try:
        return service.create_provider(
            name=body["name"],
            provider_type=body["provider_type"],
            bucket_name=body["bucket_name"],
            access_key=body["access_key"],
            secret_key=body["secret_key"],
            endpoint_url=body.get("endpoint_url"),
            prefix=body.get("prefix", ""),
            region=body.get("region"),
            credentials_passphrase=body.get("credentials_passphrase"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/api/backup-providers/{provider_id}")
async def delete_backup_provider(
    provider_id: str,
    current_user: Optional[User] = Depends(get_current_user_or_none),
):
    """Remove a cloud storage provider."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})

    from src.services.backup_cloud_service import BackupCloudService
    service = BackupCloudService()
    try:
        deleted = service.delete_provider(provider_id)
        if deleted:
            return {"deleted": True}
        return JSONResponse(status_code=404, content={"error": "Provider not found"})
    except ValueError as exc:
        return JSONResponse(status_code=409, content={"error": str(exc)})


@router.post("/api/backup-providers/{provider_id}/test")
async def test_backup_provider(
    provider_id: str,
    current_user: Optional[User] = Depends(get_current_user_or_none),
):
    """Test connectivity to a cloud storage provider."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})

    from src.services.backup_cloud_service import BackupCloudService
    from src.db.session import get_db_session
    from src.db.models.backup_storage_provider import BackupStorageProvider

    with get_db_session() as session:
        provider = session.query(BackupStorageProvider).filter_by(id=provider_id).first()
        if not provider:
            return JSONResponse(status_code=404, content={"error": "Provider not found"})

        service = BackupCloudService()
        return service.test_connectivity(provider)


@router.get("/api/backup-monitoring")
async def get_backup_monitoring():
    """Get backup monitoring dashboard statistics."""
    from src.services.backup_audit_service import BackupAuditService
    service = BackupAuditService()
    return service.get_dashboard_stats()


@router.get("/api/backup-audit-log")
async def get_backup_audit_log(
    operation: Optional[str] = None,
    outcome: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """Get paginated backup audit log entries."""
    from src.services.backup_audit_service import BackupAuditService
    service = BackupAuditService()
    return service.get_log(operation=operation, outcome=outcome, limit=limit, offset=offset)


@router.post("/api/backups/{backup_id}/verify")
async def verify_backup(
    backup_id: str,
    current_user: Optional[User] = Depends(get_current_user_or_none),
):
    """Verify backup integrity by recomputing SHA-256 checksum."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})

    import hashlib
    from datetime import datetime, timezone
    from src.db.session import get_db_session
    from src.db.models import Backup

    service = _get_backup_service()
    metadata = service.get_backup_info(backup_id)
    if not metadata:
        return JSONResponse(status_code=404, content={"error": "Backup not found"})

    storage_path = metadata.get("storage_path")
    if not storage_path or not __import__('os').path.exists(storage_path):
        return JSONResponse(status_code=404, content={"error": "Backup file not found"})

    sha256 = hashlib.sha256()
    with open(storage_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    actual_checksum = sha256.hexdigest()

    with get_db_session() as session:
        backup = session.query(Backup).filter_by(id=backup_id).first()
        stored_checksum = backup.checksum if backup else metadata.get("checksum")

        if stored_checksum and stored_checksum == actual_checksum:
            if backup:
                backup.integrity_verified_at = datetime.now(timezone.utc)
                session.commit()
            return {"valid": True, "checksum": actual_checksum, "verified_at": datetime.now(timezone.utc).isoformat()}
        elif stored_checksum:
            return {"valid": False, "expected": stored_checksum, "actual": actual_checksum, "verified_at": datetime.now(timezone.utc).isoformat()}
        else:
            if backup:
                backup.checksum = actual_checksum
                backup.integrity_verified_at = datetime.now(timezone.utc)
                session.commit()
            return {"valid": True, "checksum": actual_checksum, "verified_at": datetime.now(timezone.utc).isoformat()}


@router.post("/api/backups/{backup_id}/tags")
async def update_backup_tags(
    backup_id: str,
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_or_none),
):
    """Add or replace tags on a backup."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})

    from src.db.session import get_db_session
    from src.db.models import Backup

    body = await request.json()
    tags = body.get("tags", [])

    if not isinstance(tags, list):
        raise HTTPException(status_code=422, detail="tags must be a list")
    if len(tags) > 20:
        raise HTTPException(status_code=422, detail="Maximum 20 tags per backup")
    for tag in tags:
        if not isinstance(tag, str) or len(tag) > 64:
            raise HTTPException(status_code=422, detail="Each tag must be a string of max 64 characters")

    with get_db_session() as session:
        backup = session.query(Backup).filter_by(id=backup_id).first()
        if not backup:
            return JSONResponse(status_code=404, content={"error": "Backup not found"})
        backup.tags = tags
        session.commit()
        return {"tags": tags}


@router.post("/api/backups/cleanup")
async def cleanup_backups_retention(
    request: Request,
    current_user: Optional[User] = Depends(get_current_user_or_none),
):
    """Run retention cleanup (or dry-run) based on schedule retention policy."""
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"})
    body = await request.json()
    dry_run = body.get("dry_run", True)

    service = _get_backup_service()
    from src.db.session import get_db_session
    from src.db.repositories.backup_schedule_repository import BackupScheduleRepository

    with get_db_session() as session:
        repo = BackupScheduleRepository(session)
        schedule = repo.get_active()

    if not schedule:
        return {"dry_run": dry_run, "would_delete": [], "deleted": []}

    backups = service.list_backups()
    would_delete = []

    daily_backups = [b for b in backups if b.get("timestamp")]
    daily_backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    keep_count = schedule.retention_daily_count + schedule.retention_weekly_count + schedule.retention_monthly_count
    to_delete = daily_backups[keep_count:] if len(daily_backups) > keep_count else []
    would_delete = [b["backup_id"] for b in to_delete]

    if dry_run:
        return {"dry_run": True, "would_delete": would_delete, "deleted": []}

    deleted = []
    for backup_id in would_delete:
        try:
            service.delete_backup(backup_id)
            deleted.append(backup_id)
        except Exception:
            pass

    return {"dry_run": False, "would_delete": would_delete, "deleted": deleted}
