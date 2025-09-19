# ADR 0001: Baseline MCP STAC Server

Status: Accepted
Date: 2025-09-18

## Context
- Provide an MCP server that exposes common STAC workflows to AI assistants.
- Use pystac-client for interoperability with STAC APIs (Planetary Computer by default).
- Keep tests fast and offline via mocking.

## Decision
- Implement a stdio MCP server with four tools:
  - search_collections, get_collection, search_items, get_item
- Default catalog: https://planetarycomputer.microsoft.com/api/stac/v1
- Wrap pystac-client Client for API calls.
- Text-first responses optimized for chat UX.
- Logging via standard logging; graceful error logging for APIError.

## Consequences
- Minimal, reliable baseline with broad catalog compatibility.
- Does not yet expose all pystac-client features (filters, sorting, pagination, etc.).
- Tests mock network; example script validates end-to-end behavior.

## Alternatives considered
- Direct STAC API via requests (rejected: reinvents client features).
- HTTP transport for MCP (rejected: stdio is the standard baseline).
