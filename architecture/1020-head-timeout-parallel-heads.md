# ADR 1020: Configurable HEAD timeouts and parallel HEAD probing

Status: Accepted
Date: 2025-10-22

## Context

The `estimate_data_size` tool needs to compute asset sizes when metadata is missing. Naive sequential HTTP HEAD requests against many assets can cause the tool to block for long periods, which is unacceptable for agent-driven workflows that expect predictable response times.

Existing approaches (odc.stac, zarr inspection) may also be slow or network-dependent.

## Decision

- Add a per-request HEAD timeout configurable via `STAC_MCP_HEAD_TIMEOUT_SECONDS` (default 20s).
- Parallelize HEAD requests using a small thread pool, configurable via `STAC_MCP_HEAD_MAX_WORKERS` (default 4).
- Provide a `force_metadata_only` flag on `estimate_data_size` to bypass HEAD/zarr inspection entirely.

## Consequences

- Agents may tune timeouts/concurrency to match their latency requirements (fast agents should set smaller timeouts).
- Parallel HEADs reduce wall-clock time but increase concurrent outbound connections; keep defaults conservative.
- The implementation uses a dedicated requests.Session to allow the global default timeout wrapper to apply consistently.

## Alternatives considered

- Synchronous sequential HEADs (too slow in worst-case). 
- Fully asynchronous HTTP client (aiohttp) — rejected to keep the rest of the codebase synchronous and avoid adding an async runtime dependency inside the fallback path.

## Related

- ASR 1021 (Performance requirement for agent workflows)
