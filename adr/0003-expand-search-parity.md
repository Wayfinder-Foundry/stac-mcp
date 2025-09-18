# ADR 0003: Expand Search to Parity with pystac-client

Status: Proposed
Date: 2025-09-18

## Context
- pystac-client exposes rich search capabilities used by advanced users.
- Current tool surface omits common filters and pagination controls.

## Decision
- Extend search_items arguments (optional, backward compatible):
  - intersects (GeoJSON geometry)
  - ids (explicit item IDs)
  - sortby ([{field, direction}])
  - fields (include/exclude)
  - filter, filter_lang (CQL2)
  - page_size, max_items (total across pages)
- Surface pagination metadata:
  - matched count from context (when provided)
  - first/next links if available (for JSON mode)
- Add helpers:
  - get_items_by_ids(ids, collections?)
  - get_collection_items(collection_id, same search params)

## Consequences
- Closer parity with pystac-client; enables precise queries.
- Requires schema updates, parameter pass-through, and tests for each option.

## Alternatives considered
- Keep minimal search surface (rejected; limits serious use).
