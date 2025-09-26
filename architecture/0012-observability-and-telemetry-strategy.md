# ADR 0012: Observability & Telemetry Strategy

Status: Proposed  
Date: 2025-09-26

## Context
Prior ADRs define protocol stability (0002, 0006, 1003), performance bounds (1005), memory/nodata handling (1006), caching (0011), and graceful network/error handling (0007, 1004). We currently lack a formal, consistent approach to:
- Structured logging (levels, correlation IDs, redaction rules)
- Minimal metrics (latency, errors, cache effectiveness)
- Trace context propagation across tool executions and underlying STAC client calls
- Measuring adherence to existing performance and resource ASRs
- Providing optional hooks for downstream embedding into larger AI assistant runtimes or MCP clients

Without an agreed design, ad-hoc logging risks instability (log format churn), noisy output on stdio (interfering with MCP protocol), and missing data for future optimization or regression detection.

## Decision
Adopt a lightweight, layered observability approach:

1. Logging
   - Use Python `logging` with a single library logger namespace: `stac_mcp`.
   - Default level: WARNING (end users), elevated to INFO/DEBUG via env var `STAC_MCP_LOG_LEVEL`.
   - Emit structured JSON lines when `STAC_MCP_LOG_FORMAT=json`; otherwise concise text.
   - Never write logs to stdout that could interleave with MCP protocol; use stderr exclusively.
   - Standard JSON log fields: `timestamp` (UTC ISO8601), `level`, `event`, `tool_name` (if applicable), `duration_ms` (if applicable), `error_type`, `correlation_id`, `cache_hit` (bool/none), `catalog_url`.
   - Correlation ID: generate per MCP request (UUID4), propagate to nested logs, and (optionally, experimental) return inside response `meta` (future ADR will formalize if stabilized).

2. Metrics (in-process only)
   - Maintain internal counters/gauges:
     - `tool_invocations_total{tool_name}`
     - `tool_errors_total{tool_name,error_type}`
     - `tool_latency_ms_bucketed{tool_name}` (power-of-two buckets or streaming p50/p95 estimator)
     - `cache_requests_total`, `cache_hits_total` (from ADR 0011 integration)
   - Provide an internal function to snapshot metrics (dict) for tests.
   - Do NOT expose via MCP tool yet (avoid premature surface expansion).

3. Tracing (future-ready no-op abstraction)
   - Introduce `trace_span(name: str, **attrs)` context manager (no-op by default) to enable optional OpenTelemetry instrumentation without core dependency.
   - Wrap: request root, STAC network call, cache lookup.

4. Error Taxonomy
   - Normalize `error_type` for logs/metrics: `NetworkError`, `TimeoutError`, `ValidationError`, `RemoteAPIError`, `UnknownError`.
   - Map internal exceptions to taxonomy without altering external error payloads (preserves JSON output stability—ADR 1003).

5. Configuration Precedence
   - Environment variables only (for now):
     - `STAC_MCP_LOG_LEVEL` (e.g., INFO, DEBUG)
     - `STAC_MCP_LOG_FORMAT` ("text" | "json")
     - `STAC_MCP_ENABLE_METRICS` (default true)
     - `STAC_MCP_ENABLE_TRACE` (default false)
   - Future ADR may add config file layering (out of scope).

6. Testing & Validation
   - Add tests asserting:
     - Unique correlation ID per tool invocation.
     - Metrics counters increment appropriately (success + error).
     - Cache hit flag logged when cache used.
     - JSON logs are parseable when json mode enabled.
     - No stdout leakage (capture and assert empty for logs).

7. Non-Goals
   - No external metrics backend (Prometheus/OTLP) in core.
   - No MCP metrics exposure yet.
   - No guarantee of meta field stability (needs future ADR if exposed consistently).
   - No distributed tracing export.

## Consequences
Pros:
- Enables measurement of performance, error rates, cache efficacy.
- Reduces risk of protocol contamination by enforcing stderr-only logs.
- Facilitates future integration with OpenTelemetry or custom dashboards.
- Simplifies debugging with correlation IDs.

Cons / Trade-offs:
- Slight overhead (timers, counter increments).
- Additional complexity in test harness.
- Need disciplined evolution of log schema.

## Alternatives Considered
- Immediate adoption of OpenTelemetry: rejected (dependency & config overhead for minimal initial needs).
- Human-readable only logs: rejected (less machine-friendly for automated tooling / regression detection).
- Early metrics MCP tool: deferred (surface area vs. immediate necessity).
- Rely solely on client-side instrumentation: insufficient (cache internals invisible externally).

## Incremental Rollout Plan
1. Implement stderr logger + correlation IDs (Phase 1)
2. Add timing + metrics registry (Phase 2)
3. JSON formatting + env toggles (Phase 3)
4. Introduce `trace_span` no-op wrapper (Phase 4)
5. Tests & docs update (Phase 5)

## Open Questions / Follow-ups
- Formalize inclusion of `meta.correlation_id` in tool responses? (Would require schema extension ADR.)
- Add SLO-oriented ASR for latency distribution once metrics baseline established?
- Provide optional metrics export tool or /metrics endpoint alternative? (Noting stdio transport constraints.)

## Addendums
- None yet.
