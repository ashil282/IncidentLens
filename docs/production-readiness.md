# Production-readiness review

This is a runnable engineering foundation, not ready to expose directly to the public internet.

## Included

- Strict event schemas and timezone validation.
- Bounded list queries and configurable batch limit.
- Parameterized SQL and SQLite WAL.
- Liveness/readiness endpoints.
- Non-root container user and dropped Linux capabilities in Compose.
- CI tests, linting, and dependency audit.
- Evidence and explicit limitations in reports.
- No external model API or cloud credentials.

## Required before production

### Identity and data
- Authentication, authorization, tenant boundaries, and rate limiting.
- PostgreSQL, schema migrations, retention/deletion rules, redaction, encryption as required.
- Idempotency semantics and cursor pagination.
- Backup/restore drills and a documented recovery objective.

### Reliability and operations
- OpenTelemetry traces and metrics, structured logs, dashboards, and actionable alerts.
- Load tests and SLOs based on measured workload.
- Graceful shutdown, bounded retries, and tested failure behavior.
- TLS termination and deployment-specific secret management.

### Supply chain
- Pin GitHub Actions to immutable SHAs for hardened use.
- Generate an SBOM, sign artifacts, scan images, and review dependency updates.
- Perform a threat-model review before public deployment.

### If AI is added
- Treat logs and event messages as untrusted input.
- Validate structured output and source event IDs.
- Measure hallucination and missing-evidence rates.
- Do not grant the model shell access or direct remediation permissions.
- Keep a deterministic fallback and human approval for actions.

Do not call a release production-ready until the relevant controls are implemented, tested, documented, and reviewed for the actual deployment.
