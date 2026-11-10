"""Alembic migration environment for IncidentLens."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from incidentlens.config import get_settings
from incidentlens.database import build_database_url
from incidentlens.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Require an explicit database URL for schema migrations."""
    settings = get_settings()

    if not settings.database_url:
        raise RuntimeError(
            "Set INCIDENTLENS_DATABASE_URL explicitly before running "
            "Alembic migrations. The default application SQLite database "
            "is a legacy database and must not be migrated automatically."
        )

    url = build_database_url(settings)
    return (
        url.render_as_string(hide_password=False) if hasattr(url, "render_as_string") else str(url)
    )


def run_migrations_offline() -> None:
    """Run migrations without creating a database connection."""
    context.configure(
        url=get_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations using a live database connection."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
                compare_server_default=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
