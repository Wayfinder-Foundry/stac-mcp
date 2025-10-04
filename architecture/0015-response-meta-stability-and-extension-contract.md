# ADR 0015: Response Meta Stability & Extension Contract

Status: Proposed  
Date: 2025-09-26

## Context
Tool responses today focus on core payloads (collections, items, etc.) with stable JSON shapes per ADRs 0002 and 1003. Emerging needs (observability correlation IDs, federation warnings, cache indicators) require attaching auxiliary metadata without destabilizing existing consumers or encouraging ad-hoc, undocumented fields.

A formal contract is needed to:
- Provide a reserved location for non-primary payload metadata.
- Guarantee backwards-compatible evolution rules.
- Prevent name collisions and inconsistent semantics across future enhancements (federation, observability, retry policy surfacing, experimental flags).

## Decision
Introduce an optional top-level `meta` object in all successful and error tool responses with a governed namespace and evolution policy.

### Contract Summary
- Presence: Optional. Absence implies no supplemental metadata.
- Stability Tiering:
  1. Stable Fields: versioned & guaranteed backwards-compatible addition-only changes.
  2. Experimental Fields: prefixed with `_exp_`; may change or disappear across minor versions.
  3. Vendor / Plugin Fields: prefixed with `x_` (plugins or deployments). Out of stability scope.

### Initial Stable Fields
- `schema_version`: semantic version string for the meta schema subset (initial `1.0`)
- `correlation_id`: UUID (if observability enabled; from ADR 0012)

### Initial Experimental Fields
- `_exp_federation_warnings`: array of strings describing partial failures or truncation (ADR 0013)
- `_exp_cache_hit`: boolean for cache usage (ADR 0011 integration)
- `_exp_retry_attempts`: integer number of retry attempts performed (ASR 1008)

### Evolution Rules
- Stable fields may be added; never removed or repurposed in same major server version.
- Experimental fields may change naming or semantics; promotion path: `_exp_*` -> stable upon new minor version after documentation update + deprecation notice spanning at least one minor release cycle.
- Plugins must not define fields colliding with stable or experimental prefixes (validation warning logged if they do).

### Error Responses
- Error responses may include `meta` with `correlation_id` and `_exp_retry_attempts`; never required.

### Validation & Enforcement
- Central response construction helper ensures:
  - Meta object inserted or merged last.
  - Experimental fields gated by feature flags/environments where applicable.
  - Field prefix policy enforced; violations logged (warning) and field stripped if unsafe.

### Documentation
- README + AGENTS guide sections enumerating current stable vs experimental fields and promotion policy.
- CHANGELOG (future) records promotions or removals of experimental fields.

## Consequences
Pros:
- Predictable place for auxiliary data without bloating primary payloads.
- Shields clients from churn by clearly labeling unstable fields.
- Enables incremental feature rollout (federation, observability) with reduced break risk.

Cons / Trade-offs:
- Slight response size increase.
- Requires governance discipline to avoid misuse of experimental bucket.

## Alternatives Considered
- Embedding metadata inside primary objects (items/collections): rejected (pollutes STAC domain objects with transport-specific concerns).
- Multiple top-level namespaces (e.g., `debug`, `diagnostics`): rejected for simplicity; could be emulated with nested meta keys later.
- No experimental distinction: higher break risk for early adopters.

## Open Questions / Follow-ups
- Should we provide a programmatic meta schema endpoint/tool? (Deferred.)
- Promotion cadence policy specifics (time-based vs usage-based)?
- Need for a deprecation notice mechanism surfaced through meta itself?

## Addendums
- None yet.
