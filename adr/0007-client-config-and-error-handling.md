# ADR 0007: Client Configuration and Error Handling

Status: Proposed
Date: 2025-09-18

## Context
- Some deployments require custom headers, user agents, or timeouts.
- Need consistent error mapping for better UX.

## Decision
- Add optional client configuration at call level:
  - headers (dict[str, str]), timeout (seconds)
- Pass configuration to pystac-client via StacApiIO when feasible.
- Error handling:
  - Map timeouts/connection errors to concise messages.
  - Preserve APIError details; avoid swallowing context.
  - Log at error level; no prints.

## Consequences
- More robust behavior in varied environments.
- Slight increase in configuration complexity.

## Alternatives considered
- Global env-only configuration (rejected; less explicit, harder to test).

## Addendums
- 2025-09-18: See ASR 1004 (Graceful Network Error Handling) for non-functional error-handling guarantees and testing guidance.
