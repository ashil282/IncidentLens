from datetime import UTC, datetime

from incidentlens.detection import detect_incidents
from incidentlens.schemas import EventRecord


def make_event(event_id, **overrides):
    data = {
        "id": event_id,
        "service": "checkout",
        "environment": "test",
        "event_type": "http_request",
        "severity": "info",
        "message": "request completed",
        "timestamp": datetime(2026, 1, 15, 10, 0, tzinfo=UTC),
        "attributes": {"status_code": 200, "duration_ms": 100},
    }
    data.update(overrides)
    return EventRecord(**data)


def test_high_latency_detected():
    reports = detect_incidents([make_event("123456789abc", attributes={"duration_ms": 1200})])
    assert reports[0].detector == "high-request-latency"


def test_normal_event_ignored():
    assert detect_incidents([make_event("123456789abd")]) == []


def test_deployment_detected():
    reports = detect_incidents([make_event("123456789abe", event_type="deployment")])
    assert reports[0].detector == "deployment-event"


def test_critical_severity_preserved():
    reports = detect_incidents([make_event("123456789abf", severity="critical")])
    assert reports[0].severity == "critical"
