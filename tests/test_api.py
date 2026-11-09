def payload(**overrides):
    data = {
        "service": "checkout",
        "environment": "test",
        "event_type": "http_request",
        "severity": "error",
        "message": "provider returned 503",
        "timestamp": "2026-01-15T10:00:00Z",
        "attributes": {"status_code": 503, "duration_ms": 850},
    }
    data.update(overrides)
    return data


def test_health_and_ready(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/ready").json()["event_count"] == 0


def test_ingest_and_list(client):
    response = client.post("/v1/events", json=payload())
    assert response.status_code == 201
    assert response.json()["accepted"] == 1
    assert client.get("/v1/events").json()[0]["service"] == "checkout"


def test_naive_timestamp_rejected(client):
    assert (
        client.post("/v1/events", json=payload(timestamp="2026-01-15T10:00:00")).status_code == 422
    )


def test_unknown_field_rejected(client):
    assert client.post("/v1/events", json=payload(unexpected="no")).status_code == 422


def test_batch(client):
    response = client.post(
        "/v1/events/batch", json={"events": [payload(), payload(message="second")]}
    )
    assert response.status_code == 201
    assert response.json()["accepted"] == 2


def test_service_filter(client):
    client.post("/v1/events", json=payload())
    client.post("/v1/events", json=payload(service="catalog", severity="info"))
    result = client.get("/v1/events?service=catalog").json()
    assert len(result) == 1
    assert result[0]["service"] == "catalog"


def test_incident_report_contains_evidence(client):
    client.post("/v1/events", json=payload())
    reports = client.get("/v1/incidents").json()
    assert reports[0]["evidence"][0]["service"] == "checkout"
    assert reports[0]["limitations"]
