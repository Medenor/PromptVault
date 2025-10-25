#!/usr/bin/env python3
"""
Startup script for PromptVault Web
"""
import os
import uvicorn
from src.web.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "src.web.app:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
