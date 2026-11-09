# Contributing

Open an issue before substantial changes. Keep detectors deterministic and add tests for thresholds and boundary conditions. Never commit credentials, customer data, or production logs. Update docs when behavior changes.

Before submitting:

- [ ] Tests cover expected behavior and failure paths.
- [ ] `ruff check .` passes.
- [ ] `pytest -q` passes.
- [ ] API and operations docs match the implementation.
- [ ] No secrets or generated database files are included.

Use concise imperative commit messages such as `Add batch event validation`. Do not manufacture commit history; commits should represent work actually performed and reviewed.
