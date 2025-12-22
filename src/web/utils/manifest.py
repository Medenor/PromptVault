# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Vite manifest loader for production builds."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

MANIFEST_PATH = Path(__file__).parent.parent.parent.parent / "dist" / "static" / ".vite" / "manifest.json"
DIST_PATH = Path(__file__).parent.parent.parent.parent / "dist" / "static"


@lru_cache(maxsize=1)
def load_manifest() -> dict[str, Any]:
    """Load Vite manifest file for production builds."""
    if not MANIFEST_PATH.exists():
        return {}

    try:
        with open(MANIFEST_PATH, encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
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
    load_manifest.cache_clear()
