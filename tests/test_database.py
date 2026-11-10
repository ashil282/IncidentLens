"""Tests for database engine and session configuration."""

from pathlib import Path

from sqlalchemy import text

from incidentlens.config import Settings
from incidentlens.database import Database, build_database_url


def test_default_configuration_uses_sqlite(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("INCIDENTLENS_DATABASE_URL", raising=False)
    settings = Settings(database_path=tmp_path / "test.db")
    url = build_database_url(settings)
    assert url.drivername.startswith("sqlite")


def test_database_connection_and_foreign_keys(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("INCIDENTLENS_DATABASE_URL", raising=False)
    database = Database(Settings(database_path=tmp_path / "test.db"))

    try:
        assert database.check_connection()

        with database.engine.connect() as connection:
            if database.engine.dialect.name == "sqlite":
                result = connection.execute(text("PRAGMA foreign_keys")).scalar_one()
                assert result == 1
    finally:
        database.dispose()


def test_session_scope_rolls_back_failed_transaction(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("INCIDENTLENS_DATABASE_URL", raising=False)
    database = Database(Settings(database_path=tmp_path / "test.db"))

    try:
        with database.engine.begin() as connection:
            connection.execute(text("CREATE TABLE IF NOT EXISTS transaction_test (value INTEGER)"))

        try:
            with database.session_scope() as session:
                session.execute(text("INSERT INTO transaction_test (value) VALUES (42)"))
                raise RuntimeError("Force rollback")
        except RuntimeError:
            pass

        with database.session_factory() as session:
            count = session.execute(text("SELECT count(*) FROM transaction_test")).scalar_one()
            assert count == 0
    finally:
        database.dispose()
