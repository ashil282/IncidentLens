"""Persistent incident lifecycle and append-only activity history."""
import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

VALID_STATES = {"OPEN", "ACKNOWLEDGED", "RESOLVED"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}

def utcnow():
    return datetime.now(UTC).isoformat()

class IncidentLifecycleStore:
    def __init__(self, database_path: Path):
        self.database_path = database_path

    def _connect(self):
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.database_path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def initialize(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS incidents (
                    id TEXT PRIMARY KEY,
                    fingerprint TEXT NOT NULL,
                    detector_id TEXT NOT NULL,
                    service TEXT NOT NULL,
                    environment TEXT NOT NULL,
                    title TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    assignee TEXT,
                    resolution_note TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    acknowledged_at TEXT,
                    resolved_at TEXT
                );
                CREATE UNIQUE INDEX IF NOT EXISTS idx_incidents_active_fingerprint
                    ON incidents(fingerprint) WHERE status != 'RESOLVED';
                CREATE INDEX IF NOT EXISTS idx_incidents_status_updated
                    ON incidents(status, updated_at DESC);
                CREATE INDEX IF NOT EXISTS idx_incidents_service
                    ON incidents(service, environment);
                CREATE TABLE IF NOT EXISTS incident_activity (
                    id TEXT PRIMARY KEY,
                    incident_id TEXT NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
                    action TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_activity_incident_time
                    ON incident_activity(incident_id, created_at);
            """)

    @staticmethod
    def fingerprint(service, environment, detector_id):
        raw = f"{service.lower()}|{environment.lower()}|{detector_id.lower()}"
        return hashlib.sha256(raw.encode()).hexdigest()

    @staticmethod
    def _incident(row):
        return dict(row) if row else None

    def open_or_get(self, *, detector_id, service, environment, title, severity, summary, actor):
        fingerprint = self.fingerprint(service, environment, detector_id)
        now = utcnow()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM incidents WHERE fingerprint = ? AND status != 'RESOLVED'",
                (fingerprint,)
            ).fetchone()
            if row:
                incident_id = row["id"]
                conn.execute(
                    "UPDATE incidents SET updated_at = ?, summary = ?, severity = ? WHERE id = ?",
                    (now, summary, severity, incident_id),
                )
                action = "EVENTS_CORRELATED"
                details = {"summary": summary, "severity": severity}
            else:
                incident_id = str(uuid4())
                conn.execute("""
                    INSERT INTO incidents
                    (id, fingerprint, detector_id, service, environment, title, severity,
                     status, summary, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?, ?)
                """, (incident_id, fingerprint, detector_id, service, environment,
                      title, severity, summary, now, now))
                action = "INCIDENT_OPENED"
                details = {"detector_id": detector_id, "severity": severity}

            conn.execute("""
                INSERT INTO incident_activity
                (id, incident_id, action, actor, details_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(uuid4()), incident_id, action, actor,
                  json.dumps(details, sort_keys=True), now))
            return self.get(incident_id, conn=conn)

    def get(self, incident_id, conn=None):
        if conn is not None:
            row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
            return self._incident(row)
        with self._connect() as connection:
            return self.get(incident_id, conn=connection)

    def list(self, status=None, service=None, limit=100):
        query, params, clauses = "SELECT * FROM incidents", [], []
        if status:
            clauses.append("status = ?")
            params.append(status)
        if service:
            clauses.append("service = ?")
            params.append(service)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            return [dict(row) for row in conn.execute(query, params).fetchall()]

    def activity(self, incident_id):
        with self._connect() as conn:
            return [dict(row) | {"details": json.loads(row["details_json"])}
                    for row in conn.execute(
                        "SELECT * FROM incident_activity WHERE incident_id = ? ORDER BY created_at",
                        (incident_id,)).fetchall()]

    def update(self, incident_id, *, actor, status=None, severity=None,
               assignee=None, resolution_note=None):
        now = utcnow()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM incidents WHERE id = ?", (incident_id,)).fetchone()
            if not row:
                return None
            changes, details = [], {}
            if status is not None and status != row["status"]:
                if row["status"] == "RESOLVED" and status != "OPEN":
                    raise ValueError("resolved incidents can only be reopened to OPEN")
                changes.extend(["status = ?", "updated_at = ?"])
                values = [status, now]
                details["status"] = {"from": row["status"], "to": status}
                if status == "ACKNOWLEDGED":
                    changes.append("acknowledged_at = ?")
                    values.append(now)
                if status == "RESOLVED":
                    changes.append("resolved_at = ?")
                    values.append(now)
                if status == "OPEN":
                    changes.extend(["resolved_at = NULL"])
                conn.execute("UPDATE incidents SET " + ", ".join(changes) +
                             " WHERE id = ?", values + [incident_id])
                changes = []
            if severity is not None and severity != row["severity"]:
                conn.execute("UPDATE incidents SET severity = ?, updated_at = ? WHERE id = ?",
                           (severity, now, incident_id))
                details["severity"] = {"from": row["severity"], "to": severity}
            if assignee is not None and assignee != row["assignee"]:
                conn.execute("UPDATE incidents SET assignee = ?, updated_at = ? WHERE id = ?",
                           (assignee, now, incident_id))
                details["assignee"] = {"from": row["assignee"], "to": assignee}
            if resolution_note is not None:
                conn.execute(
                    "UPDATE incidents SET resolution_note = ?, updated_at = ? "
                    "WHERE id = ?",
                    (resolution_note, now, incident_id),
                )
                details["resolution_note"] = "updated"
            if details:
                conn.execute("""
                    INSERT INTO incident_activity
                    (id, incident_id, action, actor, details_json, created_at)
                    VALUES (?, ?, 'INCIDENT_UPDATED', ?, ?, ?)
                """, (str(uuid4()), incident_id, actor,
                      json.dumps(details, sort_keys=True), now))
            return self.get(incident_id, conn=conn)
