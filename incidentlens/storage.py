"""SQLAlchemy-backed event persistence."""

from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select

from incidentlens.database import Database
from incidentlens.models import Base, Event
from incidentlens.schemas import EventIn, EventRecord


def _as_utc(value: datetime) -> datetime:
    """Normalize database datetimes to timezone-aware UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class EventStore:
    def __init__(self, database_path_or_db: Database | str | Path):
        if isinstance(database_path_or_db, Database):
            self.database = database_path_or_db
        else:
            from incidentlens.config import Settings

            self.database = Database(Settings(database_path=database_path_or_db))

    def initialize(self) -> None:
        """Drop and recreate database tables to ensure a clean state."""
        Base.metadata.drop_all(self.database.engine)
        Base.metadata.create_all(self.database.engine)

    def insert_many(self, events: Iterable[EventIn]) -> list[EventRecord]:
        records = [EventRecord.model_validate(event.model_dump()) for event in events]

        if not records:
            return []

        with self.database.session_scope() as session:
            session.add_all(
                [
                    Event(
                        id=record.id,
                        service=record.service,
                        environment=record.environment,
                        event_type=record.event_type,
                        severity=record.severity,
                        message=record.message,
                        timestamp=record.timestamp,
                        ingested_at=record.ingested_at,
                        attributes=record.attributes,
                    )
                    for record in records
                ]
            )

        return records

    @staticmethod
    def _to_record(event: Event) -> EventRecord:
        return EventRecord(
            id=event.id,
            service=event.service,
            environment=event.environment,
            event_type=event.event_type,
            severity=event.severity,
            message=event.message,
            timestamp=_as_utc(event.timestamp),
            ingested_at=_as_utc(event.ingested_at),
            attributes=event.attributes or {},
        )

    def list_events(self, limit: int = 100, service: str | None = None) -> list[EventRecord]:
        statement = select(Event)

        if service:
            statement = statement.where(Event.service == service)

        statement = statement.order_by(Event.timestamp.desc(), Event.id.asc()).limit(limit)

        with self.database.session_factory() as session:
            events = session.scalars(statement).all()
            return [self._to_record(event) for event in events]

    def get_event_count(self) -> int:
        with self.database.session_factory() as session:
            count = session.scalar(select(func.count()).select_from(Event))
            return int(count or 0)
