from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json
from datetime import datetime
from typing import List

from src.services.prompt_data_service import PromptDataService
from src.services.prompt_filter_service import PromptFilterService
from src.services.prompt_versioning_service import PromptVersioningService
from src.services.prompt_import_export_service import PromptImportExportService
from src.services.backup_service import BackupService

app = FastAPI(title="PromptVault Web", version="0.1.0")

# Mount static files
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

# Templates
templates = Jinja2Templates(directory="src/web/templates")

# Initialize services
data_service = PromptDataService()
filter_service = PromptFilterService()
versioning_service = PromptVersioningService()
import_export_service = PromptImportExportService()
backup_service = BackupService()


def _parse_tags_field(tags: str) -> List[str]:
    """
    Normalize a comma-delimited tag string into a list with trimmed entries.

    Args:
        tags (str): Raw tag field from the form submission.

    Returns:
        List[str]: Cleaned tags with whitespace removed and empty values filtered out.
    """
    if not tags:
        return []
    normalized_tags = []
    for tag in tags.split(","):
        cleaned = tag.strip()
        if cleaned:
            normalized_tags.append(cleaned)
    return normalized_tags

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main page"""
    prompts = data_service.load_prompts()
    categories = data_service.get_categories()
    tags = data_service.get_tags()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "prompts": prompts,
        "categories": categories,
        "tags": tags
    })

@app.get("/api/prompts")
async def get_prompts():
    """Get all prompts"""
    prompts = data_service.load_prompts()
    # Unwrap the data structure for frontend consumption
    unwrapped_prompts = {}
    for prompt_id, prompt_info in prompts.items():
        if 'data' in prompt_info:
            unwrapped_prompts[prompt_id] = prompt_info['data']
        else:
            # Fallback for prompts without 'data' wrapper
            unwrapped_prompts[prompt_id] = prompt_info
    return {"prompts": unwrapped_prompts}

@app.post("/api/prompts")
async def create_prompt(
    title: str = Form(...),
    prompt: str = Form(...),
    category: str = Form(""),
    tags: str = Form("")
):
    """Create a new prompt"""
    prompt_data = {
        "title": title,
        "prompt": prompt,
        "category": category,
        "tags": _parse_tags_field(tags)
    }

    prompt_id = data_service.create_prompt(prompt_data)
    data_service.save_prompts()  # Save to disk
    return {"success": True, "prompt_id": prompt_id}

@app.get("/api/prompts/search")
async def search_prompts(
    search: str = "",
    category: str = "",
    tag: str = "",
    favorites: bool = False,
    case_sensitive: bool = False
):
    """
    Search and filter prompts based on various criteria.

    Query parameters:
    - search: Text to search for in title, prompt content, or notes
    - category: Filter by specific category (empty string means no filter)
    - tag: Filter by specific tag (empty string means no filter)
    - favorites: Show only favorite prompts if true
    - case_sensitive: Enable case-sensitive search if true
    """
    try:
        # Load all prompts
        prompts = data_service.load_prompts()

        # Convert to the format expected by filter service
        # The filter service expects Dict[int, Dict[str, Any]] where inner dict has 'data' key
        filter_prompts = {}
        for prompt_id, prompt_info in prompts.items():
            if 'data' in prompt_info:
                filter_prompts[prompt_id] = prompt_info
            else:
                # Fallback for prompts without 'data' wrapper
                filter_prompts[prompt_id] = {'data': prompt_info}

        # Apply filters using the filter service
        filtered_prompts = filter_service.filter_prompts(
            prompts=filter_prompts,
            filter_category=category if category else None,
            filter_tag=tag if tag else None,
            search_term=search,
            filter_favorites=favorites,
            case_sensitive=case_sensitive
        )

        # Sort the results
        sorted_prompts = filter_service.sort_prompts(filtered_prompts)

        # Convert back to the format expected by frontend
        result = {}
        for prompt in sorted_prompts:
            prompt_id = prompt['id']
            # Remove the 'id' field that was added by filter service
            prompt_data = {k: v for k, v in prompt.items() if k != 'id'}
            result[str(prompt_id)] = prompt_data

        return {"prompts": result}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Search failed: {str(e)}"}
        )

@app.get("/api/prompts/{prompt_id}")
async def get_prompt(prompt_id: str):
    """Get a specific prompt"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=404, content={"error": "Invalid prompt ID"})

    prompts = data_service.load_prompts()
    prompt = prompts.get(prompt_id_int)
    if not prompt:
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    # Unwrap the data structure for frontend consumption
    if 'data' in prompt:
        return prompt['data']
    else:
        # Fallback for prompts without 'data' wrapper
        return prompt

@app.put("/api/prompts/{prompt_id}")
async def update_prompt(
    prompt_id: str,
    title: str = Form(...),
    prompt: str = Form(...),
    category: str = Form(""),
    tags: str = Form(""),
    commit_message: str = Form("Update")
):
    """Update a prompt"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})

    prompts = data_service.load_prompts()
    if prompt_id_int not in prompts:
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    prompt_data = {
        "title": title,
        "prompt": prompt,
        "category": category,
        "tags": _parse_tags_field(tags)
    }

    success = data_service.update_prompt(prompt_id_int, prompt_data, commit_message)
    if success:
        data_service.save_prompts()  # Save to disk
        return {"success": True}
    else:
        return JSONResponse(status_code=500, content={"error": "Failed to update prompt"})

@app.delete("/api/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """Delete a prompt"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})

    # Create automatic backup before deletion
    backup_id = backup_service.create_backup(f"pre_delete_prompt_{prompt_id}")
    if backup_id:
        print(f"Automatic backup created before deleting prompt {prompt_id}: {backup_id}")

    success = data_service.delete_prompt(prompt_id_int)
    if success:
        data_service.save_prompts()  # Save to disk
    return {"success": success}

@app.put("/api/prompts/{prompt_id}/favorite")
async def toggle_favorite(prompt_id: str):
    """Toggle favorite status of a prompt"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})

    # Get current prompt data
    prompt_data = data_service.get_prompt_data(prompt_id_int)
    if not prompt_data:
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    # Toggle favorite status
    current_favorite = prompt_data.get('favorite', False)
    prompt_data['favorite'] = not current_favorite

    # Update the prompt
    success = data_service.update_prompt(prompt_id_int, prompt_data, "Toggle favorite")
    if success:
        data_service.save_prompts()  # Save to disk
        return {"success": True, "favorite": prompt_data['favorite']}
    else:
        return JSONResponse(status_code=500, content={"error": "Failed to update favorite status"})

@app.get("/api/categories")
async def get_categories():
    """Get all categories"""
    categories = data_service.get_categories()
    return {"categories": categories}

@app.get("/api/tags")
async def get_tags():
    """Get all tags"""
    tags = data_service.get_tags()
    return {"tags": tags}

# Import/Export endpoints
@app.get("/import-export", response_class=HTMLResponse)
async def import_export_page(request: Request):
    """Import/Export management page"""
    prompts = data_service.load_prompts()
    categories = data_service.get_categories()
    tags = data_service.get_tags()

    # Calculate statistics
    total_prompts = len(prompts)
    favorite_prompts = sum(1 for p in prompts.values() if p.get('data', {}).get('favorite', False))
    unique_categories = len(set(p.get('data', {}).get('category', 'No category') for p in prompts.values()))
    all_tags = set()
    for p in prompts.values():
        all_tags.update(p.get('data', {}).get('tags', []))
    unique_tags = len(all_tags)

    return templates.TemplateResponse("import_export.html", {
        "request": request,
        "total_prompts": total_prompts,
        "favorite_prompts": favorite_prompts,
        "total_categories": unique_categories,
        "total_tags": unique_tags
    })

@app.post("/api/export")
async def export_prompts(
    format: str = Form(...),
    filename: str = Form("promptvault_export"),
    include_favorites: bool = Form(False),
    include_metadata: bool = Form(True)
):
    """Export prompts in specified format"""
    try:
        prompts = data_service.load_prompts()

        # Filter prompts if needed
        if include_favorites:
            prompts = {k: v for k, v in prompts.items() if v.get('data', {}).get('favorite', False)}

        # Convert to list format for export service
        prompt_list = [(int(k), v) for k, v in prompts.items()]

        # Generate filename with extension
        if not filename.endswith(f'.{format}'):
            filename = f"{filename}.{format}"

        # Create temporary file
        temp_file = f"/tmp/{filename}"

        success = False
        if format.lower() == 'csv':
            success = import_export_service.export_to_csv(temp_file, prompt_list)
        elif format.lower() == 'markdown':
            success = import_export_service.export_to_markdown(temp_file, prompt_list)
        elif format.lower() == 'json':
            # Export as JSON
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'total_prompts': len(prompt_list),
                'prompts': {k: v for k, v in prompt_list}
            }
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            success = True

        if success:
            # Return file for download
            return FileResponse(
                temp_file,
                media_type='application/octet-stream',
                filename=filename
            )
        else:
            return JSONResponse(
                status_code=400,
                content={"error": f"Failed to export in {format} format"}
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Export failed: {str(e)}"}
        )

@app.post("/api/import")
async def import_prompts(
    file: UploadFile = File(...),
    mode: str = Form("append"),
    validate_data: bool = Form(True)
):
    """Import prompts from uploaded file"""
    try:
        # Save uploaded file temporarily
        temp_file = f"/tmp/{file.filename}"
        with open(temp_file, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        imported_prompts = []

        # Determine format from filename
        filename = file.filename.lower()
        if filename.endswith('.csv'):
            imported_prompts = import_export_service.import_from_csv(temp_file)
        elif filename.endswith(('.md', '.markdown')):
            imported_prompts = import_export_service.import_from_markdown(temp_file)
        elif filename.endswith('.json'):
            # Import from JSON
            with open(temp_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'prompts' in data:
                    # Handle exported JSON format
                    for prompt_id, prompt_info in data['prompts'].items():
                        imported_prompts.append(prompt_info['data'])
                else:
                    # Handle direct JSON format - ensure it's a list
                    if isinstance(data, list):
                        imported_prompts = data
                    elif isinstance(data, dict):
                        # Single prompt object, wrap in list
                        imported_prompts = [data]
                    else:
                        raise ValueError("Invalid JSON format: expected array or object")

        # Validate if requested
        if validate_data:
            valid_prompts = []
            for prompt in imported_prompts:
                if prompt.get('title') and prompt.get('prompt'):
                    valid_prompts.append(prompt)
            imported_prompts = valid_prompts

        # Import based on mode
        added_count = 0
        if mode == "replace":
            # Create automatic backup before replacing all data
            backup_id = backup_service.create_backup("pre_replace_import")
            if backup_id:
                print(f"Automatic backup created before replace import: {backup_id}")

            # Clear existing data
            data_service.clear_all_prompts()

        for prompt_data in imported_prompts:
            if mode == "merge":
                # Check if prompt with same title exists
                existing_prompts = data_service.load_prompts()
                exists = any(
                    p.get('data', {}).get('title') == prompt_data.get('title')
                    for p in existing_prompts.values()
                )
                if not exists:
                    data_service.create_prompt(prompt_data)
                    added_count += 1
            elif mode == "replace":
                # Replace mode: add all prompts (existing data already cleared)
                data_service.create_prompt(prompt_data)
                added_count += 1
            else:
                # Append mode: add all prompts
                data_service.create_prompt(prompt_data)
                added_count += 1

        # Save changes
        data_service.save_prompts()

        # Clean up temp file
        if os.path.exists(temp_file):
            os.remove(temp_file)

        return JSONResponse(content={
            "success": True,
            "imported_count": len(imported_prompts),
            "added_count": added_count,
            "mode": mode
        })

    except Exception as e:
        # Clean up temp file on error
        if 'temp_file' in locals() and os.path.exists(temp_file):
            os.remove(temp_file)
        return JSONResponse(
            status_code=500,
            content={"error": f"Import failed: {str(e)}"}
        )

@app.get("/api/import-export/stats")
async def get_import_export_stats():
    """Get current import/export statistics"""
    try:
        prompts = data_service.load_prompts()
        categories = data_service.get_categories()
        tags = data_service.get_tags()

        # Calculate statistics - handle both wrapped and unwrapped structures
        total_prompts = len(prompts)
        favorite_prompts = 0
        unique_categories = set()
        all_tags = set()

        for prompt_info in prompts.values():
            # Handle both wrapped (with 'data') and unwrapped structures
            if 'data' in prompt_info:
                prompt_data = prompt_info['data']
            else:
                prompt_data = prompt_info

            # Count favorites
            if prompt_data.get('favorite', False):
                favorite_prompts += 1

            # Collect categories
            unique_categories.add(prompt_data.get('category', 'No category'))

            # Collect tags
            prompt_tags = prompt_data.get('tags', [])
            if isinstance(prompt_tags, list):
                all_tags.update(prompt_tags)

        return JSONResponse(content={
            "total_prompts": total_prompts,
            "favorite_prompts": favorite_prompts,
            "total_categories": len(unique_categories),
            "total_tags": len(all_tags),
            "categories": list(unique_categories),
            "tags": list(all_tags)
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get statistics: {str(e)}"}
        )


# Backup Management Endpoints
@app.get("/backup-management", response_class=HTMLResponse)
async def backup_management_page(request: Request):
    """Backup management page"""
    # Get backup statistics
    stats = backup_service.get_backup_stats()

    return templates.TemplateResponse("backup_management.html", {
        "request": request,
        "backup_stats": stats
    })

@app.get("/api/backups")
async def get_backups():
    """Get list of all backups"""
    backups = backup_service.list_backups()
    return {"backups": backups}

@app.post("/api/backups")
async def create_manual_backup(name: str = Form(None)):
    """Create a manual backup"""
    backup_id = backup_service.create_backup(name)
    if backup_id:
        return {"success": True, "backup_id": backup_id}
    else:
        return JSONResponse(status_code=500, content={"error": "Failed to create backup"})

@app.post("/api/backups/{backup_id}/restore")
async def restore_backup(backup_id: str):
    """Restore from a specific backup"""
    success = backup_service.restore_backup(backup_id)
    if success:
        return {"success": True}
    else:
        return JSONResponse(status_code=500, content={"error": "Failed to restore backup"})

@app.delete("/api/backups/{backup_id}")
async def delete_backup(backup_id: str):
    """Delete a specific backup"""
    try:
        backup_info = backup_service.get_backup_info(backup_id)
        if not backup_info:
            return JSONResponse(status_code=404, content={"error": "Backup not found"})

        if backup_service.delete_backup(backup_id):
            return {"success": True}
        else:
            return JSONResponse(status_code=500, content={"error": "Failed to delete backup"})

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to delete backup: {str(e)}"})

@app.post("/api/backups/cleanup")
async def cleanup_backups(retention_days: int = Form(30)):
    """Clean up old backups"""
    removed_count = backup_service.cleanup_old_backups(retention_days)
    return {"success": True, "removed_count": removed_count}

@app.post("/api/backups/compress")
async def compress_backups(days_threshold: int = Form(7)):
    """Compress old backups"""
    compressed_count = backup_service.compress_old_backups(days_threshold)
    return {"success": True, "compressed_count": compressed_count}

@app.get("/api/backups/stats")
async def get_backup_stats():
    """Get backup statistics"""
    stats = backup_service.get_backup_stats()
    return stats

# Version Control Endpoints
@app.get("/api/prompts/{prompt_id}/versions")
async def get_version_history(prompt_id: str):
    """Get version history for a specific prompt"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})

    prompts = data_service.load_prompts()
    if prompt_id_int not in prompts:
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    versions = data_service.get_prompt_versions(prompt_id_int)
    
    # Sort by timestamp (newest first)
    sorted_versions = sorted(versions, key=lambda v: v.get('timestamp', ''), reverse=True)
    
    # Return version metadata without full data to reduce payload
    version_list = []
    for version in sorted_versions:
        version_list.append({
            'version_id': version.get('version_id'),
            'timestamp': version.get('timestamp'),
            'author': version.get('author'),
            'message': version.get('message'),
            'parents': version.get('parents', [])
        })
    
    return JSONResponse(content={"versions": version_list})


@app.get("/api/prompts/{prompt_id}/versions/compare")
async def compare_versions(prompt_id: str, v1: str = None, v2: str = None):
    """Compare two versions of a prompt"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})

    if not v1 or not v2:
        return JSONResponse(status_code=400, content={"error": "Both v1 and v2 version IDs are required"})

    prompts = data_service.load_prompts()
    if prompt_id_int not in prompts:
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    versions = data_service.get_prompt_versions(prompt_id_int)
    
    # Find both versions
    version1 = None
    version2 = None
    for version in versions:
        if version.get('version_id') == v1:
            version1 = version
        if version.get('version_id') == v2:
            version2 = version
    
    if not version1 or not version2:
        return JSONResponse(status_code=404, content={"error": "One or both versions not found"})

    # Compare the data
    data1 = version1.get('data', {})
    data2 = version2.get('data', {})
    
    diff = {
        'v1_id': v1,
        'v2_id': v2,
        'changes': {}
    }
    
    # Compare each field
    fields = ['title', 'prompt', 'category', 'tags', 'note']
    for field in fields:
        val1 = data1.get(field)
        val2 = data2.get(field)
        if val1 != val2:
            diff['changes'][field] = {
                'old': val1,
                'new': val2
            }
    
    return JSONResponse(content=diff)


@app.get("/api/prompts/{prompt_id}/versions/{version_id}")
async def get_specific_version(prompt_id: str, version_id: str):
    """Get a specific version of a prompt"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})

    prompts = data_service.load_prompts()
    if prompt_id_int not in prompts:
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    versions = data_service.get_prompt_versions(prompt_id_int)
    
    # Find the specific version
    for version in versions:
        if version.get('version_id') == version_id:
            return JSONResponse(content=version)
    
    return JSONResponse(status_code=404, content={"error": "Version not found"})


@app.post("/api/prompts/{prompt_id}/versions/{version_id}/revert")
async def revert_to_version(prompt_id: str, version_id: str, commit_message: str = Form("Revert to previous version")):
    """Revert a prompt to a specific version"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})

    prompts = data_service.load_prompts()
    if prompt_id_int not in prompts:
        return JSONResponse(status_code=404, content={"error": "Prompt not found"})

    versions = data_service.get_prompt_versions(prompt_id_int)
    
    # Find the version to revert to
    version_to_revert = None
    for version in versions:
        if version.get('version_id') == version_id:
            version_to_revert = version
            break
    
    if not version_to_revert:
        return JSONResponse(status_code=404, content={"error": "Version not found"})

    # Get the data from the version to revert to
    reverted_data = version_to_revert.get('data', {}).copy()
    
    # Create a new version with the reverted data
    success = data_service.revert_prompt_to_version(prompt_id_int, reverted_data, commit_message)
    
    if success:
        data_service.save_prompts()
        new_versions = data_service.get_prompt_versions(prompt_id_int)
        new_version_id = new_versions[-1].get('version_id') if new_versions else None
        return JSONResponse(content={
            "success": True,
            "message": f"Reverted to version {version_id}",
            "new_version_id": new_version_id
        })
    else:
        return JSONResponse(status_code=500, content={"error": "Failed to revert version"})
