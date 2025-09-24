# ASR 1007: Offline Mock STAC Server for Testing

Status: Proposed
Date: 2025-09-23

## Context
To expand feature coverage (pagination, CQL2 filters, capabilities endpoints, aggregations) we need richer test scenarios than simple method patching while still preserving offline, fast execution (ASR 1001). A minimal in‑process mock STAC service (data served from static JSON fixtures) enables deterministic tests for new tools (ADR 0003, ADR 0004) without real network calls.

## Requirement
* Provide a mock STAC API layer exposing endpoints: `/`, `/collections`, `/collections/{id}`, `/search`, `/conformance`, `/collections/{id}/queryables`, and optional `/aggregations` (namespaced if needed) returning static or parameter‑aware JSON.
* Must run fully in‑process (no actual sockets) using a lightweight ASGI app or simple function dispatcher; tests call it through a custom `StacApiIO` adapter or by monkeypatching `Client.open`.
* Response variants needed for tests:
  - Pagination (next links, matched counts)
  - Aggregations (histogram shell)
  - Error cases (4xx/5xx) to validate error mapping layer
* Include fixtures under `tests/fixtures/mock_stac/` with minimal, valid STAC JSON fragments.
* Execution time per test set < 50 ms (aggregate overhead minimal).
* Deterministic: no reliance on clock except for fixed timestamps in fixtures.

## Implications
* Simplifies implementing and validating future ADRs before acceptance.
* Slight maintenance cost to update fixture shape when STAC spec evolves; keep scope narrow (only necessary fields).
* Encourages earlier detection of pagination / filter regressions.

## Alternatives considered
* Live network calls to public STAC APIs — rejected (non‑deterministic, potential rate limits).
* Large recorded cassettes (e.g., via VCR) — heavier to curate and version; simpler handcrafted fixtures suffice for current scope.

## Addendums
* Future: Add dynamic query evaluation (CQL2 parsing) if/when ADR 0003 is accepted and implemented.
