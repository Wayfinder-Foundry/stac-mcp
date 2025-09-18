# ADR 0006: Output Formats — Add JSON Mode

Status: Proposed
Date: 2025-09-18

## Context
- MCP clients sometimes need machine-readable results for chaining actions.
- Current responses are text-only.

## Decision
- Add output_format: "text" (default) | "json" to all tools.
- JSON mode returns:
  - For collections/items: compact dicts mirroring STAC fields used today.
  - For searches: items array plus pagination/conformance metadata when available.
- Keep text mode unchanged for backward compatibility.

## Consequences
- Enables programmatic consumption in workflows.
- Requires careful versioning of response schema and tests.

## Alternatives considered
- New parallel tools with -json suffix (rejected; duplicates surface).
