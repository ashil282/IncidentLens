# Incident lifecycle

The lifecycle API stores operational incidents separately from the event stream. Repeated opens with the same service, environment, and detector key update the active incident rather than creating duplicate rows. A resolved incident is not silently reopened; a subsequent matching signal creates a new record.

## State model

- `OPEN`: detected and awaiting ownership or response.
- `ACKNOWLEDGED`: an operator has accepted responsibility.
- `RESOLVED`: an operator has recorded resolution.

A resolved incident can be explicitly reopened to `OPEN`. Other transitions out of `RESOLVED` are rejected. Every material update appends an activity record with an actor and structured details.

## Endpoints

- `POST /v1/lifecycle/incidents`: open or correlate an incident.
- `GET /v1/lifecycle/incidents`: list, optionally filtered by status and service.
- `GET /v1/lifecycle/incidents/{id}`: incident and activity history.
- `PATCH /v1/lifecycle/incidents/{id}`: change status, severity, assignee, or resolution note.

Example:

```bash
curl -X POST http://127.0.0.1:8000/v1/lifecycle/incidents \
  -H 'Content-Type: application/json' \
  -d '{"detector_id":"http-server-error","service":"checkout","environment":"local","title":"HTTP server errors","severity":"high","summary":"Payment endpoint returned 503","actor":"demo"}'
```

This initial local implementation does not authenticate actors. The `actor` field is an audit label supplied by the caller, not a verified identity. Do not expose these routes to untrusted networks until authentication, authorization, tenant isolation, and rate limiting are implemented.
