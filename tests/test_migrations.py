"""Regression tests for database migrations and PostgreSQL DDL."""

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

from incidentlens.config import get_settings
from incidentlens.models import Base


@pytest.fixture
def migration_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Use an isolated SQLite database for each migration test."""
    database_path = tmp_path / "migration-test.db"
    database_url = f"sqlite+pysqlite:///{database_path}"

    monkeypatch.setenv("INCIDENTLENS_DATABASE_URL", database_url)
    get_settings.cache_clear()

    project_root = Path(__file__).resolve().parents[1]
    config = Config(str(project_root / "alembic.ini"))
    config.set_main_option("script_location", str(project_root / "migrations"))

    yield config

    get_settings.cache_clear()


def test_migration_upgrade_downgrade_and_reupgrade(migration_config: Config) -> None:
    """A fresh database can migrate up, down, and up again."""
    command.upgrade(migration_config, "head")

    from incidentlens.database import build_database_url

    database_url = build_database_url(get_settings()).render_as_string(
        hide_password=False,
    )

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)

        assert {"events", "incidents", "incident_activity"}.issubset(
            set(inspector.get_table_names())
        )

        expected_indexes = {
            "events": {"idx_events_service", "idx_events_time"},
            "incidents": {
                "idx_incidents_active_fingerprint",
                "idx_incidents_service",
                "idx_incidents_status_updated",
            },
            "incident_activity": {"idx_activity_incident_time"},
        }

        for table_name, expected in expected_indexes.items():
            actual = {index["name"] for index in inspector.get_indexes(table_name)}
            assert expected.issubset(actual)

        foreign_keys = inspector.get_foreign_keys("incident_activity")
        assert any(
            foreign_key["referred_table"] == "incidents"
            and foreign_key["constrained_columns"] == ["incident_id"]
            and foreign_key["options"].get("ondelete") == "CASCADE"
            for foreign_key in foreign_keys
        )
    finally:
        engine.dispose()

    command.downgrade(migration_config, "base")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        remaining_tables = set(inspector.get_table_names())

        assert not {
            "events",
            "incidents",
            "incident_activity",
        }.intersection(remaining_tables)
    finally:
        engine.dispose()

    command.upgrade(migration_config, "head")

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        assert {"events", "incidents", "incident_activity"}.issubset(
            set(inspector.get_table_names())
        )
    finally:
        engine.dispose()


def test_models_compile_to_postgresql_ddl() -> None:
    """Models produce PostgreSQL DDL with JSONB and partial uniqueness."""
    dialect = postgresql.dialect()

    table_ddl = {
        table.name: str(CreateTable(table).compile(dialect=dialect))
        for table in Base.metadata.sorted_tables
    }

    assert "JSONB" in table_ddl["events"]
    assert "JSONB" in table_ddl["incident_activity"]

    index_ddl = {
        index.name: str(CreateIndex(index).compile(dialect=dialect))
        for table in Base.metadata.sorted_tables
        for index in table.indexes
    }

    active_fingerprint_ddl = index_ddl["idx_incidents_active_fingerprint"]

    assert "CREATE UNIQUE INDEX" in active_fingerprint_ddl
    assert "WHERE status != 'RESOLVED'" in active_fingerprint_ddl
