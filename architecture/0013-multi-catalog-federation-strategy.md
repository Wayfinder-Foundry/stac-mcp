# ADR 0013: Multi-Catalog Federation Strategy

Status: Proposed  
Date: 2025-09-26

## Context
Current implementation targets a single STAC API endpoint (default: Microsoft Planetary Computer) per server process. Users may need to query multiple catalogs (e.g., Planetary Computer, AWS Earth Search, internal/private catalogs) within a single MCP session for:
- Broader temporal or spatial coverage
- Redundancy / resilience when one catalog degrades
- Cross-provider product comparison and harmonization

Challenges:
- Variability in STAC API conformance and extensions between catalogs
- Different rate limits, latency characteristics, and error behaviors
- Potentially large aggregate search result sets impacting memory/performance constraints (ASRs 1005, 1006)
- Maintaining response stability (ADR 1003) while merging heterogeneous metadata

## Decision
Introduce an optional federation layer that executes parallel (or semi-parallel) searches across a configured set of catalog endpoints and merges results deterministically while preserving provenance.

Key elements:
1. Configuration
   - New environment variable `STAC_MCP_FEDERATED_CATALOGS` containing a comma-separated list of catalog URLs.
   - If unset or single URL, behavior remains current (backwards compatible).
   - Optional per-catalog alias mapping via `STAC_MCP_FEDERATION_ALIASES` (format: `alias1=url1;alias2=url2`).

2. Federation Execution Model
   - For supported search operations (`search_collections`, `search_items`), dispatch asynchronous queries to each catalog.
   - Apply a per-catalog timeout (default 8s, configurable via `STAC_MCP_FEDERATION_TIMEOUT_SECS`). Late/errored catalogs logged (per ADR 0012) but do not fail the entire response unless all fail.
   - Partial results flagged with a `federation_warnings` list in response `meta` (subject to ADR 0015 for meta contract stabilization).

3. Result Merging
   - Collections: merge by `id`; if duplicates with conflicting core fields (title, extents), keep the first responding catalog's version and record a conflict warning.
   - Items: concatenate then stable sort by datetime (descending) or user-specified sort key if later supported; annotate each item with a non-intrusive `stac_mcp:source_catalog` property (namespaced to avoid collisions) indicating alias or URL.
   - Enforce a global item cap (configurable `STAC_MCP_FEDERATION_MAX_ITEMS`, default 500) to remain within memory/performance bounds (ASR 1005/1006). Truncation noted in warnings.

4. Error Handling
   - If at least one catalog returns successfully, return HTTP 200-equivalent success semantics for the tool.
   - Provide per-catalog error summaries in warnings but avoid leaking raw stack traces.

5. Caching Interaction (ADR 0011)
   - Cache keyed by (tool, catalog_url, normalized_params). Federation builds composite responses from individual cached sub-results when available.
   - Cache TTL uniform; no cross-catalog invalidation coupling.

6. Observability (ADR 0012 Alignment)
   - Log per-catalog latency and aggregate merge duration.
   - Metrics: counters for `federated_searches_total` and `federated_partial_failures_total`.

7. Incremental Adoption
   - Phase 1: Implement internal federation utilities + item search.
   - Phase 2: Add collection search federation.
   - Phase 3: Optimization (concurrency limits, adaptive timeouts based on historical latencies).

## Consequences
Pros:
- Enables multi-source discovery without spinning separate MCP servers.
- Resilient to single-catalog degradation.
- Maintains backwards compatibility for single-catalog setups.

Cons / Trade-offs:
- Adds complexity (parallelism, merging, conflict resolution).
- Potential uneven result quality when catalogs differ in metadata completeness.
- Requires careful memory management for large combined result sets.

## Alternatives Considered
- Sequential fallback (try next only on failure): simpler but loses completeness.
- Client-side multi-catalog orchestration: offloads complexity but duplicates logic across clients.
- Full aggregation service with unified index: out of scope, high operational burden.

## Open Questions / Follow-ups
- Need policy on deterministic tie-breaking for conflicting collection metadata (could expose a preference order variable).
- Consider bloom filter or paging strategy if item sets exceed memory constraints.
- Evaluate adding per-catalog rate limiting to avoid thundering herd on high-frequency queries.

## Addendums
- None yet.
