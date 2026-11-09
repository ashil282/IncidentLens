# Architecture

```text
Client -> FastAPI/Pydantic -> EventStore -> SQLite (WAL)
                                  |
                                  v
                         deterministic detectors
                                  |
                                  v
                       incident report + evidence
```

The API handles HTTP concerns and validation. Schemas define the event contract. EventStore owns persistence. Detection is deterministic and does not mutate records or make network calls.

SQLite keeps the project runnable without another service. It is suitable for local development and small single-process workloads, not multi-replica production. A production backend should use PostgreSQL, migrations, connection pooling, tested backup/restore, and a retention policy.

Incident IDs currently derive from the first matching event ID. This is not a durable incident lifecycle model. A later version should add persisted incident records, deduplication windows, acknowledgement, and resolution states.

The initial release makes no model calls. A future summarizer should phrase findings from selected evidence only, return source event IDs, and never control remediation actions.
