# IncidentLens

IncidentLens is a local-first incident investigation service for platform teams. It accepts structured service events, detects common reliability signals, groups matching events, and produces reports linked to recorded evidence.

The initial release uses deterministic rules rather than an LLM. Core behavior is reproducible, free to run, and testable on a laptop. This is a working engineering foundation, not a claim of certified production readiness.

## Quick start — Ubuntu

Requirements: Python 3.11+, Git. Docker is optional.

```bash
./scripts/dev-setup.sh
source .venv/bin/activate
uvicorn incidentlens.main:app --reload
```

In another terminal:

```bash
python scripts/send_demo_events.py
curl -s http://127.0.0.1:8000/v1/incidents | python -m json.tool
```

Open http://127.0.0.1:8000/docs.

## Tests

```bash
source .venv/bin/activate
ruff check .
pytest -q
```

## Docker

```bash
docker compose up --build
```

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Process health |
| GET | `/ready` | Storage readiness |
| POST | `/v1/events` | Ingest one event |
| POST | `/v1/events/batch` | Ingest a batch |
| GET | `/v1/events` | List recent events |
| GET | `/v1/incidents` | List incident groups |
| GET | `/v1/incidents/{incident_id}` | Report with evidence |

Example event:

```json
{
  "service": "checkout",
  "environment": "local",
  "event_type": "http_request",
  "severity": "error",
  "message": "payment provider returned 503",
  "timestamp": "2026-01-15T10:00:00Z",
  "attributes": {"status_code": 503, "duration_ms": 850}
}
```

## Layout

- `incidentlens/`: API, settings, schemas, persistence, detectors.
- `tests/`: API and detector tests.
- `scripts/`: local setup and sample event sender.
- `docs/`: architecture, operations, threat model, readiness review.
- `.github/workflows/`: CI and dependency audit.
- `Dockerfile`, `compose.yaml`: local container setup.

## Design principles

1. Reports link back to stored evidence.
2. Detection stays deterministic and testable.
3. Inputs are validated before persistence.
4. Local development requires no cloud credentials or paid APIs.
5. Production limitations are documented explicitly.

Before exposing the service to untrusted traffic, add authentication, rate limits, migrations, retention controls, and tested backup/restore. See `docs/production-readiness.md`.

## License

MIT. See `LICENSE`.
