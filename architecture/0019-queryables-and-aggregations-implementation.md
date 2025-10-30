# ADR 0019: Queryables and Aggregations Implementation

Status: Proposed
Date: 2025-10-29

## Context
The `get_queryables` and `get_aggregations` tools are not fully implemented and lack robustness. This ADR documents the decisions to make them functional and align with the expanded search capabilities outlined in ADR-0003.

## Decision
- **`get_queryables`**:
  - The tool will fetch queryable properties for a specific collection or for the entire STAC API.
  - URL construction will be made more robust to handle different catalog URL formats.
  - The tool will gracefully handle cases where queryables are not available or the endpoint is not found.
- **`get_aggregations`**:
  - The tool will be updated to accept all search parameters from ADR-0003, including `intersects`, `ids`, `sortby`, `fields`, and `filter`.
  - The request body sent to the STAC API's `/search` endpoint will be updated to include these new parameters.
  - The tool will check for the `aggregation` conformance class and fail gracefully if the API does not support it.

## Consequences
- `get_queryables` and `get_aggregations` will be fully functional and provide more powerful search capabilities.
- The tools will be more resilient to different STAC API implementations and error conditions.
- New integration tests will be required to validate the new functionality.

## Alternatives considered
- Leaving the tools in their current, partially implemented state was rejected as it does not meet user needs.
