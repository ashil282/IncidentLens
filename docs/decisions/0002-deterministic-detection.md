# ADR 0002: Keep incident detection deterministic

- Status: Accepted
- Date: 2026-11-09

## Context

An incident system must make it possible to inspect why an event triggered a report. Model-generated reasoning can be inconsistent and may invent causal explanations.

## Decision

Use explicit rules for the initial detectors. Reports include evidence records and limitations. A future language model may summarize evidence but will not be the authority for detection or remediation.

## Consequences

The first release is cheap, reproducible, and testable. It does not provide semantic correlation or root-cause analysis. Future model-backed summaries require a test corpus and source-reference validation.
