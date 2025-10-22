# ASR 1021: Agent performance bounds for estimation tools

Status: Proposed
Date: 2025-10-22

## Requirement

Agent-driven invocations of `estimate_data_size` should return a best-effort result within a configurable wall-clock bound. The system should provide tunable knobs to manage latency vs completeness tradeoffs.

Measurable criteria:
- Default worst-case per-asset probe timeout: 20 seconds (configurable via `STAC_MCP_HEAD_TIMEOUT_SECONDS`).
- Default parallelism for probes: 4 workers (configurable via `STAC_MCP_HEAD_MAX_WORKERS`).

## Implications

- The client must support per-request timeouts and batched probing.
- Agents must set appropriate env vars for their desired latency profiles.
- The project must include tests that simulate slow endpoints to validate behavior.

## Acceptance

- Unit tests demonstrating that slow HEAD endpoints time out and do not block the estimator indefinitely.
- Documentation in README and ROADMAP describing the knobs and recommended defaults.
