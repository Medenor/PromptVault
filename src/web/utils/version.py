# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Application version lookup for display purposes (e.g. footer)."""

import tomllib
from functools import lru_cache
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

PYPROJECT_PATH = Path(__file__).parent.parent.parent.parent / "pyproject.toml"


@lru_cache(maxsize=1)
def get_app_version() -> str:
    """Return the PromptVault version from pyproject.toml, falling back to
    installed package metadata, or 'dev' if neither is available."""
    try:
        with open(PYPROJECT_PATH, "rb") as file:
            return tomllib.load(file)["project"]["version"]
    except (OSError, KeyError, tomllib.TOMLDecodeError):
        pass

    try:
        return version("promptvault")
    except PackageNotFoundError:
        return "dev"
