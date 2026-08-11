# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Full-text search correctness tests (ranking, sort precedence, pagination).

Requires SQLite FTS5. If the interpreter's SQLite build lacks FTS5, the
whole module is skipped with a clear message rather than failing.
"""

import sqlite3

import pytest


def _sqlite_has_fts5() -> bool:
    conn = sqlite3.connect(":memory:")
    try:
        options = {row[0] for row in conn.execute("PRAGMA compile_options")}
        return any(opt.startswith("ENABLE_FTS5") for opt in options)
    finally:
        conn.close()


pytestmark = pytest.mark.skipif(
    not _sqlite_has_fts5(),
    reason="SQLite build does not have FTS5 compiled in (PRAGMA compile_options lacks ENABLE_FTS5)",
)
