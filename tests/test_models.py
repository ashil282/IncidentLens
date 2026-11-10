"""Tests for SQLAlchemy database models and constraints."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from incidentlens.config import Settings
from incidentlens.database import Database
from incidentlens.models import Base, Event, Incident, IncidentActivity


def test_event_creation_and_attributes(tmp_path) -> None:
    database = Database(Settings(database_path=tmp_path / "events.db"))

    try:
        Base.metadata.create_all(database.engine)

        with database.session_scope() as session:
            event = Event(
                service="checkout",
                environment="production",
                event_type="log",
                severity="error",
                message="Payment gateway timeout",
                timestamp=datetime.now(UTC),
                attributes={"status_code": 504, "gateway": "stripe"},
            )
            session.add(event)
            session.flush()

            event_id = event.id

        with database.session_factory() as session:
            saved = session.scalar(select(Event).where(Event.id == event_id))
            assert saved is not None
            assert saved.service == "checkout"
            assert saved.attributes["status_code"] == 504
            assert saved.attributes["gateway"] == "stripe"
    finally:
        database.dispose()


def test_incident_and_activity_relationship(tmp_path) -> None:
    database = Database(Settings(database_path=tmp_path / "incident.db"))

    try:
        Base.metadata.create_all(database.engine)

        fingerprint = uuid4().hex
        with database.session_scope() as session:
            incident = Incident(
                fingerprint=fingerprint,
                detector_id="http_5xx_rate",
                service="checkout",
                environment="production",
                title="Elevated HTTP errors",
                severity="high",
                summary="HTTP 5xx rate exceeded threshold",
            )
            incident.activity.append(
                IncidentActivity(
                    action="INCIDENT_OPENED",
                    actor="system",
                    details={"detector_id": "http_5xx_rate"},
                )
            )
            session.add(incident)
            session.flush()
            incident_id = incident.id

        with database.session_factory() as session:
            saved = session.scalar(select(Incident).where(Incident.id == incident_id))
            assert saved is not None
            assert saved.fingerprint == fingerprint
            assert len(saved.activity) == 1
            assert saved.activity[0].action == "INCIDENT_OPENED"
            assert saved.activity[0].details["detector_id"] == "http_5xx_rate"
    finally:
        database.dispose()


def test_active_incident_fingerprint_must_be_unique(tmp_path) -> None:
    database = Database(Settings(database_path=tmp_path / "unique.db"))

    try:
        Base.metadata.create_all(database.engine)

        fingerprint = uuid4().hex
        with database.session_scope() as session:
            incident_one = Incident(
                fingerprint=fingerprint,
                detector_id="detector_a",
                service="checkout",
                environment="production",
                title="First incident",
                severity="high",
                summary="First summary",
            )
            session.add(incident_one)

        with database.session_scope() as session:
            incident_two = Incident(
                fingerprint=fingerprint,
                detector_id="detector_b",
                service="checkout",
                environment="production",
                title="Second incident",
                severity="medium",
                summary="Second summary",
            )
            session.add(incident_two)
            with pytest.raises(IntegrityError):
                session.flush()
    finally:
        database.dispose()


def test_resolved_incident_does_not_block_new_active_incident(tmp_path) -> None:
    database = Database(Settings(database_path=tmp_path / "resolved.db"))

    try:
        Base.metadata.create_all(database.engine)

        fingerprint = uuid4().hex
        with database.session_scope() as session:
            incident_one = Incident(
                fingerprint=fingerprint,
                detector_id="detector_a",
                service="checkout",
                environment="production",
                title="Original incident",
                severity="high",
                summary="Original summary",
                status="OPEN",
            )
            session.add(incident_one)
            session.flush()
            incident_one_id = incident_one.id

        with database.session_scope() as session:
            saved = session.scalar(select(Incident).where(Incident.id == incident_one_id))
            saved.status = "RESOLVED"
            saved.resolved_at = datetime.now(UTC)

        with database.session_scope() as session:
            incident_two = Incident(
                fingerprint=fingerprint,
                detector_id="detector_a",
                service="checkout",
                environment="production",
                title="New active incident",
                severity="high",
                summary="New summary",
                status="OPEN",
            )
            session.add(incident_two)
            session.flush()
            assert incident_two.id is not None
    finally:
        database.dispose()
