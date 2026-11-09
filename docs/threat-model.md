# Threat model

## Assets
Ingested messages and attributes, event integrity, incident reports, and API availability.

## Trust boundaries
HTTP clients, event contents, CI dependencies, and any future model provider are untrusted boundaries.

## Current mitigations
Schema validation, bounded strings, rejected unknown top-level fields, parameterized SQL, non-root container, local loopback binding in the documented workflow.

## Known gaps
No authentication, tenant isolation, rate limiting, application-level total attribute-size limit, redaction, or retention policy. Dependency auditing does not replace code review or runtime scanning.

## Abuse cases to test
1. Send an oversized batch and verify rejection before persistence.
2. Send malformed timestamps and deeply nested attributes.
3. Query a nonexistent incident ID.
4. Verify production logs do not echo sensitive event payloads.
5. If AI is added, place prompt-injection strings in messages and prove they cannot invoke tools or actions.
