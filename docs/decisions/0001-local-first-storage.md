# ADR 0001: Start with local-first storage

- Status: Accepted
- Date: 2026-11-09

## Context

The project must be runnable on a laptop with limited free memory and without paid services. Requiring a database container or cloud account would make first-run verification harder.

## Decision

Use SQLite with WAL for the initial local implementation. Keep persistence behind `EventStore` so a later PostgreSQL implementation can replace it.

## Consequences

The first version is easy to start and test. SQLite is not a substitute for a highly available multi-replica production data layer. PostgreSQL, migrations, pooling, retention, and backup/restore verification remain roadmap work.
