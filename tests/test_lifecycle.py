def incident_payload(**overrides):
    data = {
        "detector_id": "http-server-error",
        "service": "checkout",
        "environment": "test",
        "title": "HTTP server errors",
        "severity": "high",
        "summary": "Three requests returned 503",
        "actor": "test-suite",
    }
    data.update(overrides)
    return data

def test_open_and_deduplicate_incident(client):
    first = client.post("/v1/lifecycle/incidents", json=incident_payload())
    second = client.post("/v1/lifecycle/incidents", json=incident_payload(summary="Five requests returned 503"))
    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["summary"] == "Five requests returned 503"

def test_acknowledge_assign_and_resolve(client):
    opened = client.post("/v1/lifecycle/incidents", json=incident_payload()).json()
    incident_id = opened["id"]
    response = client.patch(f"/v1/lifecycle/incidents/{incident_id}", json={
        "status": "ACKNOWLEDGED", "assignee": "on-call", "actor": "operator"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "ACKNOWLEDGED"
    resolved = client.patch(f"/v1/lifecycle/incidents/{incident_id}", json={
        "status": "RESOLVED", "resolution_note": "Upstream provider recovered",
        "actor": "operator"
    })
    assert resolved.json()["status"] == "RESOLVED"
    detail = client.get(f"/v1/lifecycle/incidents/{incident_id}").json()
    assert len(detail["activity"]) >= 3

def test_resolved_incident_reopens_as_new_record(client):
    first = client.post("/v1/lifecycle/incidents", json=incident_payload()).json()
    client.patch(f"/v1/lifecycle/incidents/{first['id']}", json={"status": "RESOLVED"})
    second = client.post("/v1/lifecycle/incidents", json=incident_payload()).json()
    assert second["id"] != first["id"]
    assert second["status"] == "OPEN"

def test_invalid_transition_rejected(client):
    opened = client.post("/v1/lifecycle/incidents", json=incident_payload()).json()
    client.patch(f"/v1/lifecycle/incidents/{opened['id']}", json={"status": "RESOLVED"})
    response = client.patch(f"/v1/lifecycle/incidents/{opened['id']}", json={"status": "ACKNOWLEDGED"})
    assert response.status_code == 409

def test_filter_by_status(client):
    client.post("/v1/lifecycle/incidents", json=incident_payload())
    assert len(client.get("/v1/lifecycle/incidents?status=OPEN").json()) == 1
    assert client.get("/v1/lifecycle/incidents?status=RESOLVED").json() == []
