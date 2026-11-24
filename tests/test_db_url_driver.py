# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the PostgreSQL driver selection (issues #126, #127).

PromptVault ships psycopg v3. ``DatabaseSettings.sqlalchemy_url`` makes the
driver explicit (and maps the legacy ``+psycopg2`` form), while ``libpq_url``
strips it again for ``pg_dump``/``psql``.
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.engine import make_url

from src.db.config import DatabaseSettings
from src.services.backup_dump_strategy import PostgresDumpStrategy


def _settings(url: str) -> DatabaseSettings:
    return DatabaseSettings(DATABASE_URL=url)


class TestSqlalchemyUrl:
    def test_bare_postgresql_resolves_to_psycopg3(self):
        url = _settings("postgresql://u:p@db:5432/pv").sqlalchemy_url

        assert url == "postgresql+psycopg://u:p@db:5432/pv"
        assert make_url(url).get_dialect().driver == "psycopg"

    def test_legacy_psycopg2_url_is_mapped_to_psycopg3(self):
        """Existing .env files that say +psycopg2 keep working (psycopg2 is gone)."""
        url = _settings("postgresql+psycopg2://u:p@db/pv").sqlalchemy_url

        assert url == "postgresql+psycopg://u:p@db/pv"

    def test_driver_is_importable(self):
        """The resolved dialect's DBAPI is installed (the #126 failure mode)."""
        dialect = make_url(_settings("postgresql://u:p@h/d").sqlalchemy_url)
        assert dialect.get_dialect().import_dbapi().__name__ == "psycopg"

    @pytest.mark.parametrize(
        "url",
        [
            "postgresql+psycopg://u:p@db/pv",
            "postgresql+asyncpg://u:p@db/pv",
            "sqlite:///./data/promptvault.db",
            "sqlite:///:memory:",
        ],
    )
    def test_other_urls_unchanged(self, url):
        assert _settings(url).sqlalchemy_url == url

    def test_database_url_itself_is_not_rewritten(self):
        settings = _settings("postgresql://u:p@db/pv")

        assert settings.DATABASE_URL == "postgresql://u:p@db/pv"
        assert settings.is_postgresql

    def test_password_containing_scheme_text_is_preserved(self):
        url = _settings("postgresql://u:postgresql%3A%2F%2F@db/pv").sqlalchemy_url

        assert url == "postgresql+psycopg://u:postgresql%3A%2F%2F@db/pv"


class TestLibpqUrl:
    @pytest.mark.parametrize(
        "url, expected",
        [
            ("postgresql://u:p@db/pv", "postgresql://u:p@db/pv"),
            ("postgresql+psycopg2://u:p@db/pv", "postgresql://u:p@db/pv"),
            ("postgresql+psycopg://u:p@db/pv", "postgresql://u:p@db/pv"),
            ("sqlite:///./x.db", "sqlite:///./x.db"),
        ],
    )
    def test_driver_suffix_removed(self, url, expected):
        assert _settings(url).libpq_url == expected


class TestDumpStrategyUsesLibpqUrl:
    def _run(self, method, *args):
        settings = _settings("postgresql+psycopg://u:p@db/pv")
        with (
            patch("src.services.backup_dump_strategy.db_settings", settings),
            patch(
                "src.services.backup_dump_strategy.subprocess.run",
                return_value=MagicMock(),
            ) as run,
        ):
            method(PostgresDumpStrategy(), *args)
        return run.call_args.args[0]

    def test_dump_passes_plain_uri_to_pg_dump(self):
        cmd = self._run(PostgresDumpStrategy.dump, "/tmp/out.sql")

        assert cmd[0] == "pg_dump"
        assert cmd[-1] == "postgresql://u:p@db/pv"

    def test_restore_passes_plain_uri_to_psql(self):
        cmd = self._run(PostgresDumpStrategy.restore, "bk1", "/tmp/in.sql")

        assert cmd[0] == "psql"
        assert cmd[-1] == "postgresql://u:p@db/pv"
