# Local operations runbook

Start:

```bash
source .venv/bin/activate
uvicorn incidentlens.main:app --host 127.0.0.1 --port 8000
```

Check:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/ready
```

Send demo events and inspect reports:

```bash
python scripts/send_demo_events.py
curl -fsS http://127.0.0.1:8000/v1/incidents | python -m json.tool
```

Common failures:
- Port in use: start with `--port 8001` and update the demo script URL.
- Readiness 503: check logs and ensure the database directory is writable.
- 422: timestamps need timezone information and fields must match the schema.
- No incidents: inspect `/v1/events`; normal events do not trigger a detector.

To reset data, stop the service and remove the configured SQLite database plus its `-wal` and `-shm` companions. This permanently deletes local events.
