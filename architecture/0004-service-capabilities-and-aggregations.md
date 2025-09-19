# ADR 0004: Service Capabilities (Root, Conformance, Queryables) and Aggregations

Status: Proposed
Date: 2025-09-18

## Context
- Clients benefit from discovering service capabilities and queryable fields.
- Some APIs support Aggregations extension for counts/histograms.

## Decision
- Add tools:
  - get_root: id/title/description/links/conformance
  - get_conformance: list conformance classes; optional check param
  - get_queryables(collection_id optional): return queryable fields
  - get_aggregations: run a search and return aggregations (if supported)
- Fail gracefully when endpoints/extensions are not available.

## Consequences
- Better adaptability across catalogs and richer UX.
- Requires detection of conformance and conditional behavior.

## Alternatives considered
- Hard-code assumptions per catalog (rejected; brittle).
