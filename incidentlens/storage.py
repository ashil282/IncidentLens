import json
import sqlite3
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

from incidentlens.schemas import EventIn, EventRecord


class EventStore:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    def _connect(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    def initialize(self):
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    service TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    ingested_at TEXT NOT NULL,
                    attributes_json TEXT NOT NULL
                )
            """)
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_time "
                "ON events(timestamp DESC)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_events_service "
                "ON events(service, environment)"
            )

    def insert_many(self, events: Iterable[EventIn]) -> list[EventRecord]:
        records = [
            EventRecord.model_validate(event.model_dump())
            for event in events
        ]
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO events (
                    id, service, environment, event_type,
                    severity, message, timestamp,
                    ingested_at, attributes_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        e.id,
                        e.service,
                        e.environment,
                        e.event_type,
                        e.severity,
                        e.message,
                        e.timestamp.isoformat(),
                        e.ingested_at.isoformat(),
                        json.dumps(
                            e.attributes,
                            separators=(",", ":"),
                            sort_keys=True,
                        ),
                    )
                    for e in records
                ],
            )
        return records

    @staticmethod
    def _row_to_record(row):
        return EventRecord(
            id=row["id"],
            service=row["service"],
            environment=row["environment"],
            event_type=row["event_type"],
            severity=row["severity"],
            message=row["message"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            ingested_at=datetime.fromisoformat(row["ingested_at"]),
            attributes=json.loads(row["attributes_json"]),
        )

    def list_events(
        self, limit: int = 100, service: str | None = None
    ) -> list[EventRecord]:
        query, params = "SELECT * FROM events", []
        if service:
            query += " WHERE service = ?"
            params.append(service)
        query += " ORDER BY timestamp DESC, id ASC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_event_count(self) -> int:
        with self._connect() as connection:
            cursor = connection.execute("SELECT COUNT(*) FROM events")
            return int(cursor.fetchone()[0])
