# Roadmap

Open issues for substantial milestones and mark items complete only after code, tests, and docs are merged.

## 1. Local core
- [x] Event ingestion and validation
- [x] SQLite persistence
- [x] Deterministic incident rules
- [x] Evidence-backed report
- [x] CI and local setup

## 2. API and data lifecycle
- [ ] Cursor pagination and idempotency keys
- [ ] Retention and deletion controls
- [ ] Database migrations
- [ ] PostgreSQL backend and contract tests
- [ ] Incident lifecycle and deduplication windows

## 3. Observability
- [ ] OpenTelemetry traces
- [ ] Prometheus metrics
- [ ] Structured JSON logs and request IDs
- [ ] Dashboards, alerts, and load-test baseline

## 4. AI assistance
- [ ] Summarizer interface with deterministic fallback
- [ ] Optional local model adapter
- [ ] Prompt-injection test corpus
- [ ] Evidence-ID validation and evaluation set

## 5. Delivery
- [ ] Kubernetes manifests and Helm chart
- [ ] SBOM, artifact signing, image scanning
- [ ] Backup/restore drill
- [ ] Threat model and deployment review
