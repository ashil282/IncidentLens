#!/usr/bin/env python3
import json
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta

url = "http://127.0.0.1:8000/v1/events/batch"
now = datetime.now(UTC)
events = [
    {
        "service": "checkout",
        "environment": "local",
        "event_type": "http_request",
        "severity": "error",
        "message": "payment provider returned 503",
        "timestamp": (now - timedelta(minutes=3)).isoformat(),
        "attributes": {"status_code": 503, "duration_ms": 850},
    },
    {
        "service": "checkout",
        "environment": "local",
        "event_type": "http_request",
        "severity": "info",
        "message": "request exceeded latency budget",
        "timestamp": (now - timedelta(minutes=2)).isoformat(),
        "attributes": {"status_code": 200, "duration_ms": 1450},
    },
    {
        "service": "catalog",
        "environment": "local",
        "event_type": "deployment",
        "severity": "info",
        "message": "release v1.4.2 deployed",
        "timestamp": (now - timedelta(minutes=1)).isoformat(),
        "attributes": {"version": "1.4.2", "change_id": "demo-42"},
    },
]
request = urllib.request.Request(
    url,
    data=json.dumps({"events": events}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
try:
    with urllib.request.urlopen(request, timeout=5) as response:
        print(response.read().decode())
except urllib.error.URLError as exc:
    raise SystemExit(f"Could not reach {url}. Start the API first. Details: {exc}") from exc
