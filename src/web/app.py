from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add the parent directory to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

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
        "tags": tags.split(",") if tags else []
    }

    prompt_id = data_service.create_prompt(prompt_data)
    data_service.save_prompts()  # Save to disk
    return {"success": True, "prompt_id": prompt_id}

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
    tags: str = Form("")
):
    """Update a prompt"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})

    prompt_data = {
        "title": title,
        "prompt": prompt,
        "category": category,
        "tags": tags.split(",") if tags else []
    }

    success = data_service.update_prompt(prompt_id_int, prompt_data)
    if success:
        data_service.save_prompts()  # Save to disk
    return {"success": success}

@app.delete("/api/prompts/{prompt_id}")
async def delete_prompt(prompt_id: str):
    """Delete a prompt"""
    try:
        prompt_id_int = int(prompt_id)
    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Invalid prompt ID"})

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
    validate: bool = Form(True)
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
                    # Handle direct JSON format
                    imported_prompts = data

        # Validate if requested
        if validate:
            valid_prompts = []
            for prompt in imported_prompts:
                if prompt.get('title') and prompt.get('prompt'):
                    valid_prompts.append(prompt)
            imported_prompts = valid_prompts

        # Import based on mode
        added_count = 0
        if mode == "replace":
            # Clear existing data
            data_service.clear_all_prompts()
            added_count = len(imported_prompts)

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
            else:
                # Append mode
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
