# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Enumeration types for API validation."""

from enum import Enum


class ExportFormat(str, Enum):
    """Allowed export formats."""

    CSV = "csv"
    MARKDOWN = "markdown"
    JSON = "json"


class ImportMode(str, Enum):
    """Import modes for handling existing data."""

    APPEND = "append"
    MERGE = "merge"
    REPLACE = "replace"
