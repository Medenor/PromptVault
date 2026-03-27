# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

#!/usr/bin/env python3
"""
Startup script for PromptVault Web
"""
import os
import uvicorn
from src.web.app import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8003))
    reload_enabled = os.environ.get("UVICORN_RELOAD", "true").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    uvicorn.run(
        "src.web.app:app",
        host="0.0.0.0",
        port=port,
        reload=reload_enabled,
        log_level="info",
    )
