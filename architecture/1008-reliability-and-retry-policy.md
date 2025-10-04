# ASR 1008: Reliability & Retry Policy

Status: Proposed  
Date: 2025-09-26

## Context
Existing ADRs/ASRs address performance bounds (1005), error handling (1004), caching (0011), and observability (0012 – proposed). A formal reliability requirement is needed to:
- Define measurable expectations for tool availability under transient network faults.
- Standardize retry, timeout, and backoff behavior across STAC operations.
- Prevent unbounded latency inflation due to aggressive retries.

Without codified targets, future optimizations or regressions cannot be objectively evaluated.

## Requirement
Provide predictable reliability behavior for network-dependent tools (`search_items`, `search_collections`, `get_item`, `get_collection`, `get_root`, `get_queryables`, `get_conformance`, `get_aggregations`, `estimate_data_size`) under transient failure scenarios.

### Measurable Criteria
1. Success Ratio: Under simulated transient fault rate of 20% (random 5xx / connection resets), the effective successful completion ratio for each tool must be ≥ 95% within a single invocation (with internal retries) across 200 sampled invocations.
2. Latency Budget: p95 added latency due to retries must not exceed +35% of baseline p95 (baseline measured with 0% injected faults, same dataset).
3. Max Wall Time per Invocation: Hard cap (timeout) per tool request: 15 seconds (configurable via env `STAC_MCP_TOOL_TIMEOUT_SECS`, default 15). Exceeding cap triggers graceful abort with timeout error classification.
4. Retry Boundedness: No more than 3 retry attempts (1 initial + up to 2 retries) for idempotent operations; non-idempotent future tools (if any) must opt-in explicitly.
5. Backoff Strategy: Exponential backoff with jitter: base 0.4s, multiplier 2.0, full jitter max per attempt (0.4s, ≤0.8s, ≤1.6s). Cumulative backoff must remain < 3 seconds typical path.

### Scope of Reliability Mechanisms
- Retriable Error Classes: network timeouts, connection errors, 5xx remote server responses (excluding 501/505), throttling (429) with respect of `Retry-After` header if present (capped at 5s).
- Non-Retriable: 4xx validation errors, schema parsing errors, local argument validation, item not found (404), permission errors (401/403).

### Observability Coupling (ADR 0012)
- Expose counters: `retries_attempted_total{tool_name}`, `timeouts_total{tool_name}`, `retry_exhausted_total{tool_name}`.
- Log structured events: `retry_attempt`, `retry_give_up`, `timeout_abort` with correlation IDs.

### Failure Mode Behavior
- On final failure after retries, return error promptly (do not silently succeed with partial data unless explicitly designed, e.g., federation ADR 0013 context).
- Cache entries are not written for failed responses.

### Test & Validation Strategy
- Add fault injection harness (mock client raising configured transient exceptions at controlled probability).
- Automated test asserting success ratio and retry attempt ceilings.
- Benchmark test measuring baseline vs. injected fault latency deltas.

## Implications
- Introduces consistent user experience across tools for transient failures.
- Slight additional complexity in tool execution wrapper (shared retry logic).
- Increases code paths to test but bounded by uniform policy layer.

## Alternatives Considered
- Unlimited linear retries: rejected (unbounded latency, risk of cascading failure).
- No retries (delegate to caller): rejected (clients vary; central policy reduces burden and increases reliability SLO adherence).
- Circuit breaker: deferred (future if upstream instability patterns emerge; requires metrics maturity first).

## Open Questions / Follow-ups
- Introduce per-catalog adaptive backoff (depends on metrics trending)?
- Consider circuit breaker thresholds if consecutive failure streaks exceed N.
- Add SLO reporting tool after metrics mature.

## Addendums
- None yet.
