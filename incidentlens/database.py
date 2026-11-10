"""Shared SQLAlchemy database infrastructure."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from incidentlens.config import Settings


def build_database_url(settings: Settings) -> URL:
    """Build a SQLAlchemy URL from application settings."""
    if settings.database_url:
        url = make_url(settings.database_url)

        if url.drivername in {"postgres", "postgresql"}:
            url = url.set(drivername="postgresql+psycopg")

        if url.drivername not in {
            "sqlite",
            "sqlite+pysqlite",
            "postgresql+psycopg",
        }:
            raise ValueError("Unsupported database driver")

        return url

    return URL.create(
        drivername="sqlite+pysqlite",
        database=str(settings.database_path),
    )


def create_database_engine(settings: Settings) -> Engine:
    """Create an engine with backend-specific connection settings."""
    url = build_database_url(settings)

    if url.drivername.startswith("sqlite"):
        if url.database not in {None, "", ":memory:"}:
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)

        connect_args = {"timeout": 5}

        if url.database != ":memory:":
            connect_args["check_same_thread"] = False

        engine = create_engine(
            url,
            connect_args=connect_args,
            pool_pre_ping=True,
        )

        @event.listens_for(engine, "connect")
        def configure_sqlite_connection(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA busy_timeout = 5000")
            cursor.close()

        return engine

    return create_engine(
        url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_timeout=settings.database_pool_timeout,
        pool_pre_ping=True,
    )


class Database:
    """Owns the SQLAlchemy engine and session factory."""

    def __init__(self, settings: Settings):
        self.engine = create_database_engine(settings)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            autoflush=False,
            expire_on_commit=False,
        )

    @contextmanager
    def session_scope(self) -> Iterator[Session]:
        """Provide a session with automatic commit and rollback."""
        with self.session_factory.begin() as session:
            yield session

    def check_connection(self) -> bool:
        """Check whether the configured database is reachable."""
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True

    def dispose(self) -> None:
        """Close pooled database connections."""
        self.engine.dispose()
