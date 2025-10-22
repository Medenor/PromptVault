#!/usr/bin/env python3
"""
Startup script for PromptVault Web
"""
import uvicorn
from src.web.app import app

if __name__ == "__main__":
    uvicorn.run(
        "src.web.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
