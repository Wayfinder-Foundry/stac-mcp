# ASR 1001: Fast, Offline, Deterministic Validation and Tests

Status: Accepted
Date: 2025-09-18

## Context
Reliable contributor experience and CI require fast feedback and zero reliance on external networks. The repository already documents timing expectations and offline behavior for development and validation.

## Requirement
- Install step: `pip install -e ".[dev]"` completes within 120 seconds under typical conditions.
- Formatting and linting:
  - `ruff format stac_mcp/ tests/ examples/` ~0.2 seconds.
  - `ruff check stac_mcp/ tests/ examples/ --fix` ~0.02 seconds (auto-fixable issues).
- Tests: `pytest -v` completes within 30 seconds and does not require Internet; all network I/O must be mocked.
- Example usage: `python examples/example_usage.py` runs in ~0.6 seconds.
- MCP server manual timeout: `timeout 5s stac-mcp || true` exits with code 124 after ~5 seconds, proving the server starts and blocks awaiting MCP input.

## Implications
- All tests must mock network interactions; no live STAC calls in the test suite.
- Keep the validation steps deterministic and documented in README and contributor docs.
- Avoid long-running integration flows in CI; prefer targeted unit/integration tests using mocks.

## Alternatives considered
- Live network integration tests: rejected due to flakiness, non-determinism, and slow execution.

## Addendums
- 2025-09-18: Initial acceptance aligned with current repository guidance.
