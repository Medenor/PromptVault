# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Prompt import/export API routes.

Extracted from the original ``app.py`` god-file. Contains:

- ``POST /export``              export prompts to csv/markdown/json
- ``POST /import``              import prompts from an uploaded file
- ``GET  /import-export/stats`` current import/export statistics

Route paths, methods, response shapes, and status codes are unchanged. The
router is mounted under ``/api`` by ``routing_setup``, yielding the original
``/api/export``, ``/api/import``, and ``/api/import-export/stats`` paths.

Service objects (``data_service``, ``import_export_service``, ``backup_service``)
and ``record_validation_event`` are read lazily from ``src.web.app`` per request,
mirroring the other legacy routers so test fixtures that reconfigure services at
runtime are honored.
"""

import json
import os
from datetime import datetime

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import ValidationError

from src.db.repositories.prompt_repository import PromptRepository
from src.db.repositories.sharing_repository import SharingRepository
from src.db.session import get_db_session
from src.services.logging_service import logging_service
from src.web.middleware.rate_limit import expensive_limit, limiter
from src.web.models import ExportFormat, ExportRequest, ImportMode, ImportRequest
from src.web.validators import (
    create_secure_temp_file,
    get_file_extension_from_format,
    sanitize_filename,
    validate_upload_file,
)

router = APIRouter(tags=["Legacy"])

SKILLS_EXCLUDED_HEADER = "X-Skills-Excluded"


def _count_skills() -> int:
    """Return how many skills exist; bulk import/export never touch them (FR-024a)."""
    with get_db_session() as session:
        return PromptRepository(session).count(item_type="skill")


def _app():
    from src.web import app as web_app

    return web_app


# ---------------------------------------------------------------------------
# Import ingestion helpers (Extract Method from the original import_prompts)
# ---------------------------------------------------------------------------


def _parse_import_file(temp_file_path: str, filename: str) -> list[dict]:
    """Parse an uploaded import file into a list of prompt-data dicts.

    Supports CSV, Markdown, and JSON payloads. JSON may be a PromptVault export
    envelope (``{"prompts": {...}}``), a bare list, or a bare object.
    """
    import_export_service = _app().import_export_service

    filename = filename.lower()
    if filename.endswith(".csv"):
        return import_export_service.import_from_csv(temp_file_path)
    if filename.endswith((".md", ".markdown")):
        return import_export_service.import_from_markdown(temp_file_path)
    if filename.endswith(".json"):
        imported_prompts: list[dict] = []
        with open(temp_file_path, encoding="utf-8") as f:
            data = json.load(f)
            if "prompts" in data:
                for _, prompt_info in data["prompts"].items():
                    imported_prompts.append(prompt_info["data"])
            else:
                if isinstance(data, list):
                    imported_prompts = data
                elif isinstance(data, dict):
                    imported_prompts = [data]
                else:
                    raise ValueError("Invalid JSON format: expected array or object")
        return imported_prompts
    return []


def _filter_valid_prompts(imported_prompts: list[dict]) -> list[dict]:
    """Keep only prompts that have both a title and a prompt body."""
    valid_prompts = []
    for prompt in imported_prompts:
        if prompt.get("title") and prompt.get("prompt"):
            valid_prompts.append(prompt)
    return valid_prompts


def _ingest_prompts(imported_prompts: list[dict], mode: ImportMode) -> int:
    """Persist imported prompts according to the requested import mode.

    Returns the number of prompts actually added. In REPLACE mode an automatic
    pre-import backup is created and existing prompts are cleared first.
    """
    web_app = _app()
    data_service = web_app.data_service
    backup_service = web_app.backup_service
    audit_logger = logging_service.get_audit_logger()

    added_count = 0
    if mode == ImportMode.REPLACE:
        backup_id = backup_service.create_backup("pre_replace_import")
        if backup_id:
            audit_logger.info(
                "Automatic backup created before replace import",
                extra={
                    "event": "backup.auto",
                    "action": "backup_before_replace_import",
                    "resource_id": "import",
                    "backup_id": backup_id,
                },
            )

        with get_db_session() as session:
            active_shares_count = SharingRepository(session).count_all()

        if active_shares_count:
            logging_service.log_audit_event(
                action="prompt.shares.destroyed_by_replace_import",
                resource_type="prompt_share",
                resource_id="all",
                active_shares_count=active_shares_count,
            )

        data_service.clear_all_prompts()

    for prompt_data in imported_prompts:
        if mode == ImportMode.MERGE:
            existing_prompts = data_service.load_prompts()
            exists = any(
                p.get("data", {}).get("title") == prompt_data.get("title")
                for p in existing_prompts.values()
            )
            if not exists:
                data_service.create_prompt(prompt_data)
                added_count += 1
        elif mode == ImportMode.REPLACE:
            data_service.create_prompt(prompt_data)
            added_count += 1
        else:
            data_service.create_prompt(prompt_data)
            added_count += 1

    return added_count


@router.post("/export", responses={429: {"description": "Rate limit exceeded"}})
@limiter.limit(expensive_limit)
async def export_prompts(
    request: Request,
    format: str = Form(...),
    filename: str = Form("promptvault_export"),
    include_favorites: bool = Form(False),
    include_metadata: bool = Form(True),
):
    """Export prompts in specified format with validation and secure file handling."""
    web_app = _app()
    data_service = web_app.data_service
    import_export_service = web_app.import_export_service
    record_validation_event = web_app.record_validation_event

    temp_file = None
    try:
        try:
            format_enum = ExportFormat(format.lower())
        except ValueError:
            record_validation_event(
                endpoint="/api/export",
                success=False,
                errors=[f"Invalid format '{format}'"],
            )
            return JSONResponse(
                status_code=422,
                content={
                    "error": "Validation failed",
                    "details": [
                        f"Invalid format '{format}'. Must be one of: csv, markdown, json"
                    ],
                },
            )

        validated_data = ExportRequest(
            format=format_enum,
            filename=filename,
            include_favorites=include_favorites,
            include_metadata=include_metadata,
        )

        prompts = data_service.load_prompts()  # prompts only: skills are excluded
        skills_excluded = _count_skills()
        if validated_data.include_favorites:
            prompts = {
                k: v
                for k, v in prompts.items()
                if v.get("data", {}).get("favorite", False)
            }

        prompt_list: list[tuple[int, dict]] = [(int(k), v) for k, v in prompts.items()]

        safe_filename = sanitize_filename(validated_data.filename)
        file_extension = get_file_extension_from_format(validated_data.format.value)
        final_filename = f"{safe_filename}{file_extension}"

        temp_file = create_secure_temp_file(final_filename)

        success = False
        if validated_data.format == ExportFormat.CSV:
            success = import_export_service.export_to_csv(temp_file, prompt_list)
        elif validated_data.format == ExportFormat.MARKDOWN:
            success = import_export_service.export_to_markdown(temp_file, prompt_list)
        elif validated_data.format == ExportFormat.JSON:
            export_data = {
                "export_timestamp": datetime.now().isoformat(),
                "total_prompts": len(prompt_list),
                "skills_excluded": skills_excluded,
                "prompts": {k: v for k, v in prompt_list},
            }
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            success = True

        if success:
            logging_service.log_audit_event(
                action="export.prompts",
                resource_type="export",
                resource_id=final_filename,
                format=validated_data.format.value,
                prompt_count=len(prompt_list),
                include_favorites=validated_data.include_favorites,
                include_metadata=validated_data.include_metadata,
                skills_excluded=skills_excluded,
            )
            record_validation_event(endpoint="/api/export", success=True)
            return FileResponse(
                temp_file,
                media_type="application/octet-stream",
                filename=final_filename,
                headers={SKILLS_EXCLUDED_HEADER: str(skills_excluded)},
            )

        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        return JSONResponse(
            status_code=400,
            content={
                "error": f"Failed to export in {validated_data.format.value} format"
            },
        )

    except ValidationError as e:
        record_validation_event(
            endpoint="/api/export",
            success=False,
            errors=[err.get("msg", "") for err in e.errors()],
        )
        return JSONResponse(
            status_code=422,
            content={"error": "Validation failed", "details": e.errors()},
        )
    except Exception as e:
        if temp_file and os.path.exists(temp_file):
            os.remove(temp_file)
        return JSONResponse(
            status_code=500, content={"error": f"Export failed: {str(e)}"}
        )


@router.post("/import", responses={429: {"description": "Rate limit exceeded"}})
@limiter.limit(expensive_limit)
async def import_prompts(
    request: Request,
    file: UploadFile = File(...),
    mode: str = Form("append"),
    validate_data: bool = Form(True),
):
    """Import prompts from uploaded file with comprehensive security validation."""
    record_validation_event = _app().record_validation_event

    temp_file_path = None
    try:
        validated_params = ImportRequest(
            mode=ImportMode(mode.lower()),
            validate_data=validate_data,
        )

        is_valid, error_message = await validate_upload_file(file)
        if not is_valid:
            record_validation_event(
                endpoint="/api/import",
                success=False,
                errors=[error_message],
            )
            return JSONResponse(
                status_code=400,
                content={"error": error_message},
            )

        # validate_upload_file() above already rejects a missing filename.
        assert file.filename is not None
        temp_file_path = create_secure_temp_file(file.filename)

        content = await file.read()
        with open(temp_file_path, "wb") as buffer:
            buffer.write(content)

        imported_prompts = _parse_import_file(temp_file_path, file.filename)

        if validated_params.validate_data:
            imported_prompts = _filter_valid_prompts(imported_prompts)

        added_count = _ingest_prompts(imported_prompts, validated_params.mode)

        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)

        record_validation_event(
            endpoint="/api/import",
            success=True,
        )
        logging_service.log_audit_event(
            action="import.prompts",
            resource_type="import",
            resource_id="import",
            imported_count=len(imported_prompts),
            added_count=added_count,
            mode=validated_params.mode.value,
        )

        return JSONResponse(
            content={
                "success": True,
                "imported_count": len(imported_prompts),
                "added_count": added_count,
                "mode": validated_params.mode.value,
            }
        )

    except ValidationError as e:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        record_validation_event(
            endpoint="/api/import",
            success=False,
            errors=[err.get("msg", "") for err in e.errors()],
        )
        return JSONResponse(
            status_code=422,
            content={"error": "Validation failed", "details": e.errors()},
        )
    except Exception as e:
        if temp_file_path and os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        return JSONResponse(
            status_code=500, content={"error": f"Import failed: {str(e)}"}
        )


@router.get("/import-export/stats")
async def get_import_export_stats():
    """Get current import/export statistics"""
    data_service = _app().data_service
    try:
        prompts = data_service.load_prompts()

        total_prompts = len(prompts)
        favorite_prompts = 0
        unique_categories = set()
        all_tags = set()

        for prompt_info in prompts.values():
            prompt_data = prompt_info["data"] if "data" in prompt_info else prompt_info
            if prompt_data.get("favorite", False):
                favorite_prompts += 1
            unique_categories.add(prompt_data.get("category", "No category"))
            prompt_tags = prompt_data.get("tags", [])
            if isinstance(prompt_tags, list):
                all_tags.update(prompt_tags)

        with get_db_session() as session:
            active_shares_count = SharingRepository(session).count_all()
            skill_count = PromptRepository(session).count(item_type="skill")

        return JSONResponse(
            content={
                "total_prompts": total_prompts,
                "skill_count": skill_count,
                "favorite_prompts": favorite_prompts,
                "total_categories": len(unique_categories),
                "total_tags": len(all_tags),
                "categories": list(unique_categories),
                "tags": list(all_tags),
                "active_shares_count": active_shares_count,
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500, content={"error": f"Failed to get statistics: {str(e)}"}
        )
