from collections import defaultdict
from collections.abc import Iterable

from incidentlens.schemas import EventRecord, IncidentReport


def _number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def detect_incidents(events: Iterable[EventRecord]) -> list[IncidentReport]:
    groups = defaultdict(list)
    for event in events:
        status_code = _number(event.attributes.get("status_code"))
        duration = _number(event.attributes.get("duration_ms"))
        if event.severity in {"error", "critical"}:
            detector, title = "elevated-error-severity", "Elevated error severity"
        elif status_code is not None and status_code >= 500:
            detector, title = "http-server-error", "HTTP server errors"
        elif duration is not None and duration >= 1000:
            detector, title = "high-request-latency", "High request latency"
        elif event.event_type == "deployment":
            detector, title = "deployment-event", "Deployment observed"
        else:
            continue
        groups[(event.service, event.environment, detector, title)].append(event)

    reports = []
    for (service, environment, detector, title), matching in groups.items():
        matching.sort(key=lambda item: item.timestamp)
        first = matching[0]
        severity = (
            "critical"
            if any(e.severity == "critical" for e in matching)
            else (
                "high" if detector in {"http-server-error", "elevated-error-severity"} else "medium"
            )
        )
        findings = [
            f"{len(matching)} event(s) matched detector '{detector}'.",
            f"First matching event occurred at {first.timestamp.isoformat()}.",
        ]
        durations = [_number(e.attributes.get("duration_ms")) for e in matching]
        durations = [value for value in durations if value is not None]
        if durations:
            findings.append(
                f"Observed request duration range: {min(durations):.0f}–{max(durations):.0f} ms."
            )
        reports.append(
            IncidentReport(
                id=f"inc-{first.id[:12]}",
                service=service,
                environment=environment,
                title=title,
                severity=severity,
                started_at=first.timestamp,
                event_count=len(matching),
                detector=detector,
                evidence=matching[:50],
                findings=findings,
                limitations=[
                    "Correlation is rule-based and does not establish root cause.",
                    "Only events in the current query sample were considered.",
                    "No external telemetry backend or language model was queried.",
                ],
            )
        )
    return sorted(reports, key=lambda item: (item.started_at, item.id), reverse=True)
