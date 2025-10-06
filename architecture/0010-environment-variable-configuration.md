# ADR 0010: Environment Variable Based Configuration

Status: Proposed
Date: 2025-09-23

## Context
The server currently relies only on per‑call parameters. Some behavioral toggles (defaults, caps, experimental features) would benefit from centralized, override‑friendly configuration without expanding every tool schema. To avoid collisions with arbitrary user environment variables we will use a reserved prefix.

## Decision
Introduce optional configuration via environment variables prefixed `STAC_MCP_`. Initial set (scoped to currently implemented or near‑term features):
* `STAC_MCP_DEFAULT_CATALOG` — override default catalog URL.
* `STAC_MCP_SEARCH_DEFAULT_LIMIT` — baseline limit for searches (fallback when not supplied).
* `STAC_MCP_SEARCH_MAX_LIMIT` — hard safety ceiling (schema `maximum` should align at runtime).
* `STAC_MCP_ENABLE_JSON_MODE` — feature flag ("1"/"0") to enable early JSON mode before full acceptance of ADR 0006 (guard experimental usage).
* `STAC_MCP_DATASIZE_MAX_LIMIT` — ceiling for `estimate_data_size` limit parameter.
* `STAC_MCP_LOG_LEVEL` — logging verbosity (INFO by default).
* `STAC_MCP_NODATA_SAMPLE_PIXELS`, `STAC_MCP_NODATA_MAX_ASSETS` — sampling controls (see ASR 1006).
* `STAC_MCP_CACHE_DIR` — path for optional on‑disk cache (see ADR 0011) when persistence desired.
* `STAC_MCP_SSL_INSECURE_FALLBACK` — when set to `1`, allows a one-time insecure (certificate verification disabled) retry for read-only metadata endpoints (`/conformance` or root) if an SSL certificate verification error occurs. This is safer than globally disabling SSL and intended only for diagnostic or constrained corporate proxy environments. Prefer providing a valid CA bundle via `STAC_MCP_CA_BUNDLE` instead.

Behavior:
1. Add a lightweight config loader (`config.py`) that reads env vars once at import and exposes a typed object/dict.
2. Tool handlers consult config defaults only when explicit arguments are absent.
3. Environment variable parsing is defensive: invalid values → logged warning → fallback to safe default.
4. Future additions require updating central config (single source of truth) and documenting in README.

## Consequences
* Reduces need to modify every tool for new global defaults / feature flags.
* Adds minimal complexity; config module must remain dependency‑free apart from stdlib.
* Encourages reproducibility: users can snapshot environment for consistent behavior.

## Alternatives considered
* Global Python module constants only — rejected (less flexible, harder to override in containerized CI).
* CLI arguments — outside current MCP stdio flow, increases surface area.

## Addendums
* Future: may add `STAC_MCP_CACHE_TTL_SECONDS` aligned with ADR 0011.
* 2025-10-06: Added `STAC_MCP_SSL_INSECURE_FALLBACK` for limited, read-only retry on SSL verification failure to reduce friction in environments with intercepting proxies.
