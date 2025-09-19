# ASR 1005: Performance Bounds for Search Operations

Status: Proposed
Date: 2025-09-18

## Context
Search operations can return large result sets. To maintain responsiveness, the server should enforce reasonable limits and provide pagination hints.

## Requirement
- Default `limit` for searches must be conservative (e.g., 10) and configurable by caller.
- Support `max_items` and `page_size` to control pagination.
- When available, include matched counts or next links in the response (JSON mode) to guide clients.

## Implications
- Tool schemas must include pagination-related parameters and response metadata.
- Tests should cover boundary cases (limit=0/1/large) and ensure no unbounded iteration.

## Alternatives considered
- Unlimited item iteration by default: rejected due to latency and memory risks.

## Addendums
- 2025-09-18: Proposed alongside ADR 0003.
