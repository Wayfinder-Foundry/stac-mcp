# ADR 0008: Testing and Release Strategy

Status: Accepted
Date: 2025-09-18

## Context
- The repo defines strict dev workflow and release automation.
- Tests must run quickly and without network.

## Decision
- Follow repository guide:
  - pip install -e ".[dev]" (timeout 120s), black, ruff --fix, pytest -v (timeout 30s)
  - Validate example script and 5s MCP timeout behavior
- Tests:
  - Mock all network I/O; assert parameter pass-through and graceful errors
  - Add cases for new params (intersects, ids, sortby, fields, CQL2, pagination)
  - Add JSON mode golden tests; optional PC signing path with monkeypatch
- Releases:
  - Semantic versioning via scripts/version.py
  - Branch prefixes trigger version bumps; containers tagged automatically

## Consequences
- Predictable CI outcomes and fast feedback.
- Clear upgrade path aligned with SemVer.

## Alternatives considered
- Live network tests (rejected; flaky, slow).

## Addendums
- 2025-09-18: See ASR 1001 (Fast, Offline, Deterministic Validation and Tests) for enforced timing and offline constraints.
