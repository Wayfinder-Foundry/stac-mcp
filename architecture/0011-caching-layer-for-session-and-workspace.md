# ADR 0011: Caching Layer for Session & Workspace Reuse

Status: Proposed
Date: 2025-09-23

## Context
Repeated queries (especially overlapping spatial/temporal filters) can cause redundant network calls and re‑serialization overhead. A lightweight cache keyed by semantic query parameters and (optionally) by a workspace / working directory context can improve responsiveness and reduce API pressure. The cache must remain optional and bounded to honor performance requirements (ASR 1001) and avoid stale data hazards.

## Decision
Implement a pluggable cache abstraction:
* In‑memory default (LRU) with size bound expressed in *entries* (e.g., 256) and optional TTL.
* Optional persistent layer (directory) when `STAC_MCP_CACHE_DIR` is set, storing JSON for STAC collections and item search results (NOT large asset contents) keyed by a hash of: tool name + normalized arguments + catalog URL + server version.
* Workspace scoping: If a deterministic workspace root (e.g., current working directory) is provided by caller environment, incorporate it into the cache key to isolate parallel projects.
* API: `cache.get(key) -> value | None`, `cache.set(key, value, meta)`, `cache.invalidate(predicate)`.
* Metrics (debug logging only): hits, misses, evictions.

Invalidation Strategy:
* Time‑based expiry if TTL configured (env var, e.g., `STAC_MCP_CACHE_TTL_SECONDS`).
* Manual invalidation endpoint/tool (future) or on version bump (different `server_version` invalidates naturally via key composition).

Security & Integrity:
* Do not cache error responses.
* Limit per‑entry serialized size (e.g., 1 MB) to prevent runaway memory usage.

## Consequences
* Adds a small layer of complexity; must ensure thread/async safety (simple asyncio lock or rely on single‑thread event loop semantics).
* Facilitates batching & conversation continuity.
* Persisted cache introduces file I/O; keep optional and skip silently if directory unusable.

## Alternatives considered
* Rely solely on HTTP caching headers (delegated to underlying client) — insufficient for higher‑level aggregation and argument normalization.
* Full distributed cache (Redis) — unjustified for current scope.

## Addendums
* Future: Add cache stats tool if demanded by users.
