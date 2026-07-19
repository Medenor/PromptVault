# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Vite manifest loader for production builds."""

import json
from pathlib import Path
from typing import Any, Dict, Optional

MANIFEST_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "dist"
    / "static"
    / ".vite"
    / "manifest.json"
)
DIST_PATH = Path(__file__).parent.parent.parent.parent / "dist" / "static"

_manifest_cache: Dict[str, Any] = {}
_manifest_mtime: Optional[float] = None


def load_manifest() -> Dict[str, Any]:
    """Load Vite manifest file for production builds."""
    global _manifest_cache, _manifest_mtime
    if not MANIFEST_PATH.exists():
        _manifest_cache = {}
        _manifest_mtime = None
        return {}

    current_mtime = MANIFEST_PATH.stat().st_mtime
    if _manifest_mtime is not None and _manifest_mtime == current_mtime:
        return _manifest_cache

    try:
        with open(MANIFEST_PATH, encoding="utf-8") as file:
            _manifest_cache = json.load(file)
            _manifest_mtime = current_mtime
            return _manifest_cache
    except json.JSONDecodeError, OSError:
        _manifest_cache = {}
        _manifest_mtime = None
        return {}


def get_asset_path(entry: str) -> str:
    """Get the hashed asset path for a given entry point."""
    manifest = load_manifest()
    if entry in manifest:
        return manifest[entry].get("file", entry)
    return entry


def is_production() -> bool:
    """Check if running in production mode (built assets exist)."""
    return DIST_PATH.exists() and MANIFEST_PATH.exists()


def clear_manifest_cache() -> None:
    """Clear the cached manifest (useful for hot reload)."""
    global _manifest_cache, _manifest_mtime
    _manifest_cache = {}
    _manifest_mtime = None
