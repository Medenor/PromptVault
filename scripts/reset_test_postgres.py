#!/usr/bin/env python3
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Reset the ``public`` schema of a *test* PostgreSQL database.

``make test-postgres`` runs each PostgreSQL test file against the same database
and calls this script between files, because the migration tests leave tables
behind that break the next file's fixtures.

This is destructive, so it refuses to run unless the database name in
``DATABASE_URL`` contains ``test``.
"""

import os
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from src.db.config import DatabaseSettings


def main() -> int:
    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url.startswith("postgresql"):
        print("DATABASE_URL must be a postgresql:// URL.", file=sys.stderr)
        return 2

    settings = DatabaseSettings(DATABASE_URL=raw_url)
    url = make_url(settings.sqlalchemy_url)
    if "test" not in (url.database or "").lower():
        print(
            f"Refusing to reset database '{url.database}': its name must contain 'test'.",
            file=sys.stderr,
        )
        return 2

    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
