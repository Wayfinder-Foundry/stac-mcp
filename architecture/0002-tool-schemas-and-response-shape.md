# ADR 0002: Tool Schemas and Response Shape

Status: Accepted
Date: 2025-09-18

## Context
- Tools must be simple to discover and invoke across clients.
- Balance readability for humans with enough detail for follow-up calls.

## Decision
- Define four tools with concise JSON schemas:
  - Common optional catalog_url for catalog switching.
  - search_items supports collections, bbox, datetime, query, limit.
- Responses:
  - Human-readable text summaries containing IDs, bbox, datetime, and counts.
  - Truncate long descriptions; avoid overwhelming output.

## Consequences
- Good ergonomics for interactive exploration.
- Not yet machine-optimized for downstream parsing (JSON mode to be added).

## Alternatives considered
- JSON-only outputs (rejected initially; worse UX for chat discovery).
- Overly rich tool schemas (rejected; keep baseline minimal).
