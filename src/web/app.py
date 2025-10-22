from fastapi import FastAPI, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import sys
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
    return {"prompts": prompts}

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
