"""Incident lifecycle store supporting PostgreSQL and SQLite backends."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select

from incidentlens.database import Database
from incidentlens.models import Incident, IncidentActivity


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


VALID_TRANSITIONS = {
    "OPEN": {"ACKNOWLEDGED", "RESOLVED"},
    "ACKNOWLEDGED": {"RESOLVED", "OPEN"},
    "RESOLVED": {"OPEN"},
}


class IncidentLifecycleStore:
    def __init__(self, database_or_path: Database | str | Path):
        if isinstance(database_or_path, Database):
            self.database = database_or_path
        else:
            from incidentlens.config import Settings

            self.database = Database(Settings(database_path=database_or_path))

    def open_or_get(
        self,
        detector_id: str,
        service: str,
        environment: str,
        title: str,
        severity: str,
        summary: str,
        actor: str,
    ) -> Incident:
        with self.database.session_scope() as session:
            statement = select(Incident).where(
                Incident.detector_id == detector_id,
                Incident.service == service,
                Incident.environment == environment,
                Incident.status.in_(["OPEN", "ACKNOWLEDGED"]),
            )
            existing = session.scalars(statement).first()

            if existing:
                existing.summary = summary
                existing.updated_at = datetime.now(UTC)
                session.flush()
                session.refresh(existing)
                return existing

            now = datetime.now(UTC)
            incident = Incident(
                fingerprint=uuid4().hex,
                detector_id=detector_id,
                service=service,
                environment=environment,
                title=title,
                severity=severity,
                summary=summary,
                status="OPEN",
                created_at=now,
                updated_at=now,
            )
            session.add(incident)
            session.flush()

            activity = IncidentActivity(
                incident_id=incident.id,
                actor=actor,
                action="opened",
                details={"summary": summary},
            )
            session.add(activity)
            session.flush()
            session.refresh(incident)
            return incident

    def get(self, incident_id: str) -> Incident | None:
        with self.database.session_factory() as session:
            return session.get(Incident, incident_id)

    def activity(self, incident_id: str) -> list[IncidentActivity]:
        with self.database.session_factory() as session:
            statement = (
                select(IncidentActivity)
                .where(IncidentActivity.incident_id == incident_id)
                .order_by(IncidentActivity.id.asc())
            )
            return list(session.scalars(statement).all())

    def update(
        self,
        incident_id: str,
        status: str | None = None,
        assignee: str | None = None,
        resolution_note: str | None = None,
        actor: str = "operator",
        details: dict[Any, Any] | None = None,
    ) -> Incident | None:
        with self.database.session_scope() as session:
            incident = session.get(Incident, incident_id)
            if not incident:
                return None

            current_status = incident.status
            target_status = status
            if resolution_note is not None and target_status is None:
                target_status = "RESOLVED"

            if target_status is not None and target_status != current_status:
                allowed = VALID_TRANSITIONS.get(current_status, set())
                if target_status not in allowed:
                    raise HTTPException(
                        status_code=409,
                        detail=f"Invalid transition from {current_status} to {target_status}",
                    )
                incident.status = target_status

            if assignee is not None:
                incident.assignee = assignee

            if resolution_note is not None:
                incident.resolution_note = resolution_note
                incident.resolved_at = datetime.now(UTC)

            incident.updated_at = datetime.now(UTC)
            session.flush()

            activity_action = incident.status.lower()
            activity = IncidentActivity(
                incident_id=incident.id,
                actor=actor,
                action=activity_action,
                details=details or {"assignee": assignee, "resolution_note": resolution_note},
            )
            session.add(activity)
            session.flush()
            session.refresh(incident)
            return incident

    def list(
        self,
        status: str | None = None,
        service: str | None = None,
        limit: int = 100,
    ) -> list[Incident]:
        with self.database.session_factory() as session:
            statement = select(Incident)
            if status:
                statement = statement.where(Incident.status == status)
            if service:
                statement = statement.where(Incident.service == service)
            statement = statement.order_by(Incident.created_at.desc()).limit(limit)
            return list(session.scalars(statement).all())
