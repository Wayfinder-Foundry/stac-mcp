# STAC MCP Server

[![PyPI Version](https://img.shields.io/pypi/v/stac-mcp?style=flat-square&logo=pypi)](https://pypi.org/project/stac-mcp/)
[![Build Status](https://img.shields.io/github/actions/workflow/status/BnJam/stac-mcp/container.yml?branch=main&style=flat-square&logo=github)](https://github.com/BnJam/stac-mcp/actions/workflows/container.yml)
[![CI](https://img.shields.io/github/actions/workflow/status/BnJam/stac-mcp/ci.yml?branch=main&label=ci&style=flat-square)](https://github.com/BnJam/stac-mcp/actions/workflows/ci.yml)
[![Coverage](./coverage-badge.svg)](#test-coverage)
[![Container](https://img.shields.io/badge/container-ghcr.io-blue?style=flat-square&logo=docker)](https://github.com/BnJam/stac-mcp/pkgs/container/stac-mcp)
[![Python](https://img.shields.io/pypi/pyversions/stac-mcp?style=flat-square&logo=python)](https://pypi.org/project/stac-mcp/)
[![License](https://img.shields.io/github/license/BnJam/stac-mcp?style=flat-square)](https://github.com/BnJam/stac-mcp/blob/main/LICENSE)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/stac-mcp?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/stac-mcp)
[![Ruff](https://img.shields.io/badge/lint-ruff-e57300?style=flat-square)](https://github.com/astral-sh/ruff)



An MCP (Model Context Protocol) Server that provides access to STAC (SpatioTemporal Asset Catalog) APIs for geospatial data discovery and access. Supports dual output modes (`text` and structured `json`) for all tools.

> The coverage badge is updated automatically on pushes to `main` by the CI workflow.

## Overview

This MCP server enables AI assistants and applications to interact with STAC catalogs to:
- Search and browse STAC collections
- Find geospatial datasets (satellite imagery, weather data, etc.)
- Access metadata and asset information
- Perform spatial and temporal queries

## Features

### Available Tools

All tools accept an optional `output_format` parameter (`"text"` default, or `"json"`). JSON mode returns a single MCP `TextContent` whose `text` field is a compact JSON envelope: `{ "mode": "json", "data": { ... } }` (or `{ "mode": "text_fallback", "content": ["..."] }` if a handler lacks a JSON branch). This preserves backward compatibility while enabling structured consumption (see ADR 0006 and ASR 1003).

- **`get_root`**: Fetch root document (id/title/description/links/conformance subset)
- **`get_conformance`**: List all conformance classes; optionally verify specific URIs
- **`get_queryables`**: Retrieve queryable fields (global or per collection) when supported
- **`get_aggregations`**: Execute a search requesting aggregations (count/stats) if supported
- **`search_collections`**: List and search available STAC collections
- **`get_collection`**: Get detailed information about a specific collection
- **`search_items`**: Search for STAC items with spatial, temporal, and attribute filters
- **`get_item`**: Get detailed information about a specific STAC item
- **`estimate_data_size`**: Estimate data size for STAC items using lazy loading (XArray + odc.stac)

### Capability Discovery & Aggregations

The new capability tools (ADR 0004) allow adaptive client behavior:

- Graceful fallbacks: Missing `/conformance`, `/queryables`, or aggregation support returns structured JSON with `supported:false` instead of hard errors.
- `get_conformance` falls back to the root document's `conformsTo` array when the dedicated endpoint is absent.
- `get_queryables` returns an empty set with a message if the endpoint is not implemented by the catalog.
- `get_aggregations` constructs a STAC Search request with an `aggregations` object; if unsupported (HTTP 400/404), it returns a descriptive message while preserving original search parameters.

### Data Size Estimation

The `estimate_data_size` tool provides accurate size estimates for geospatial datasets without downloading the actual data:

- **Lazy Loading**: Uses odc.stac to load STAC items into xarray datasets without downloading
- **AOI Clipping**: Automatically clips to the smallest area when both bbox and AOI GeoJSON are provided
- **Fallback Estimation**: Provides size estimates even when odc.stac fails
- **Detailed Metadata**: Returns information about data variables, spatial dimensions, and individual assets
- **Batch Support**: Retains structured metadata for efficient batch processing

Example usage:
```json
{
  "collections": ["landsat-c2l2-sr"],
  "bbox": [-122.5, 37.7, -122.3, 37.8],
  "datetime": "2023-01-01/2023-01-31",
  "aoi_geojson": {
    "type": "Polygon",
    "coordinates": [[...]]
  },
  "limit": 50
}
```

### Supported STAC Catalogs

By default, the server connects to Microsoft Planetary Computer STAC API, but it can be configured to work with any STAC-compliant catalog.

## Installation

### PyPI Package

```bash
pip install stac-mcp
```

### Development Installation

```bash
git clone https://github.com/BnJam/stac-mcp.git
cd stac-mcp
pip install -e .
```

### Container

The STAC MCP server publishes multi-arch container images (linux/amd64, linux/arm64) via GitHub Actions workflow (`.github/workflows/container.yml`). The current build uses a Python 3.12 slim Debian base (not distroless) with GDAL-related libs for raster IO and odc-stac compatibility.

```bash
# Pull the latest stable version
docker pull ghcr.io/bnjam/stac-mcp:latest

# Pull a specific version (recommended for production)
docker pull ghcr.io/bnjam/stac-mcp:0.2.0

# Run the container (uses stdio transport for MCP)
docker run --rm -i ghcr.io/bnjam/stac-mcp:latest
```

Container images are tagged with semantic versions when version bumps occur on `main`:
- `ghcr.io/bnjam/stac-mcp:X.Y.Z` (exact version)
- `ghcr.io/bnjam/stac-mcp:X.Y` (major.minor convenience tag)
- `ghcr.io/bnjam/stac-mcp:X` (major convenience tag)
- `ghcr.io/bnjam/stac-mcp:latest` (points at current main version)
Pull request builds (without version bump) also produce ephemeral PR/ref tags via the metadata action.

#### Building the Container

To build the container locally using the provided Containerfile:

```bash
# Build with Docker
docker build -f Containerfile -t stac-mcp .

# Or build with Podman  
podman build -f Containerfile -t stac-mcp .
```

The Containerfile currently performs a single-stage build based on `python:3.12-slim` (future optimization could reintroduce a distroless runtime stage). It installs system GDAL/PROJ dependencies and then installs the package.

## Usage

### As an MCP Server

#### Native Installation

Configure your MCP client to connect to this server:

```json
{
  "mcpServers": {
    "stac": {
      "command": "stac-mcp"
    }
  }
}
```

#### Container Usage

To use the containerized version with an MCP client:

```json
{
  "mcpServers": {
    "stac": {
      "command": "docker",
      "args": ["run", "--rm", "-i", "ghcr.io/bnjam/stac-mcp:latest"]
    }
  }
}
```

Or with Podman:

```json
{
  "mcpServers": {
    "stac": {
      "command": "podman", 
      "args": ["run", "--rm", "-i", "ghcr.io/bnjam/stac-mcp:latest"]
    }
  }
}
```

docker run --rm -i ghcr.io/bnjam/stac-mcp:latest
### Command Line

#### Native Installation

```bash
stac-mcp
```

Each invocation starts an MCP stdio server; it waits for protocol messages (see `examples/example_usage.py`).

#### Container Usage

```bash
# With Docker
docker run --rm -i ghcr.io/bnjam/stac-mcp:latest

# With Podman
podman run --rm -i ghcr.io/bnjam/stac-mcp:latest
```

### Examples

#### Example: JSON Output Mode
Below is an illustrative (client-side) pseudo-call showing `output_format` usage through an MCP client message:

```jsonc
{
  "method": "tools/call",
  "params": {
    "name": "search_items",
    "arguments": {
      "collections": ["landsat-c2l2-sr"],
      "bbox": [-122.5, 37.7, -122.3, 37.8],
      "datetime": "2023-01-01/2023-01-31",
      "limit": 5,
      "output_format": "json"
    }
  }
}
```

The server responds with a single `TextContent` whose text is a JSON string like:
```json
{"mode":"json","data":{"type":"item_list","count":5,"items":[{"id":"..."}]}}
```
This wrapping keeps the MCP content type stable while enabling machine-readable chaining.

## Development

### Setup

#### GitHub Codespaces (Recommended)

The fastest way to get started is with GitHub Codespaces, which provides a fully configured development environment in your browser:

1. Click the green "Code" button on the GitHub repository
2. Select the "Codespaces" tab
3. Click "Create codespace on main"

The devcontainer will automatically:
- Set up Python 3.12 with all dependencies
- Install GDAL/PROJ system libraries
- Configure VS Code with recommended extensions
- Install the project in development mode

See [`.devcontainer/README.md`](.devcontainer/README.md) for more details.

#### Local Development

```bash
git clone https://github.com/BnJam/stac-mcp.git
cd stac-mcp
pip install -e ".[dev]"
```

For local development with containers, you can use VS Code's Remote Containers extension with the provided `.devcontainer` configuration.

### Testing

```bash
pytest -v
python examples/example_usage.py  # MCP stdio smoke test
```

#### Test Coverage
The project uses `coverage.py` (already a dependency was added) for measuring statement and branch coverage.

Quick run (terminal):
```bash
coverage run -m pytest -q
coverage report -m
```
Example output (illustrative):
```
Name                                Stmts   Miss Branch BrMiss  Cover
---------------------------------------------------------------------
stac_mcp/observability.py             185      4     42      3    96%
stac_mcp/tools/execution.py            68      2     18      1    94%
... (others) ...
---------------------------------------------------------------------
TOTAL                                 620     20    140      9    96%
```

Generate an HTML report (optional):
```bash
coverage html
open htmlcov/index.html  # macOS
```

Configuration: `.coveragerc` enforces `branch = True` and omits `tests/*` and `scripts/version.py`. Update omit patterns only when necessary to keep metrics honest.

Recommended workflow before opening a PR:
1. `ruff format stac_mcp/ tests/ examples/`
2. `ruff check stac_mcp/ tests/ examples/ --fix`
3. `coverage run -m pytest -q`
4. `coverage report -m` (ensure no unexpected drops)

### SSL / TLS Troubleshooting

If you encounter an SSL certificate verification error (e.g., `SSLCertVerificationError` or a message about a *self-signed certificate in certificate chain*) when the server accesses a STAC endpoint:

1. Confirm the endpoint is reachable with a standard tool (e.g., `curl https://.../stac/v1/conformance`).
2. Ensure your system trust store is up to date (on macOS, some Python installs provide an `Install Certificates.command`).
3. Behind a corporate proxy / MITM device: export a custom CA bundle.

The client now supports two environment variables (see ADR notes / security guidance):

| Variable | Purpose | Security Impact |
|----------|---------|-----------------|
| `STAC_MCP_CA_BUNDLE` | Path to a PEM file with additional / custom root CAs. If present and readable it will be used to build the SSL context. | Low (extends trust roots intentionally). |
| `STAC_MCP_UNSAFE_DISABLE_SSL` | If set to `1`, disables certificate verification entirely (hostname + chain). For diagnostics only. | High (vulnerable to MITM). Never use in production. |

Example (custom CA):
```bash
export STAC_MCP_CA_BUNDLE=/etc/ssl/certs/internal-proxy.pem
stac-mcp
```

Temporary diagnostic bypass (NOT recommended):
```bash
export STAC_MCP_UNSAFE_DISABLE_SSL=1
stac-mcp
```

When an SSL failure occurs you will receive a structured `SSLVerificationError` message with remediation guidance instead of a low-level `urllib.error.URLError`.

#### Container vs Local/Virtual Environment (Why `get_conformance` May Differ)

The published Docker/Podman images generally succeed with `get_conformance` against public STAC APIs even when a locally installed Python environment fails. Reasons:

- The container base image (`python:3.12-slim`) ships with a current CA trust store.  
- Some local macOS / Homebrew / pyenv environments have an out-of-date or un-initialized certificate bundle until you run the platform's certificate installation script.  
- Corporate proxies can inject custom CAs that exist in system Keychain but are not automatically propagated to the Python cert store.

Typical symptom: Local invocation of the `get_conformance` tool returns a structured `SSLVerificationError`, while running the same command via the container (e.g. `docker run --rm -i ghcr.io/bnjam/stac-mcp:latest`) succeeds.

Mitigations (ordered):
1. Update local certificates (macOS framework Python: run the `Install Certificates.command` script found in the Python application folder).  
2. Export a custom CA bundle path: `export STAC_MCP_CA_BUNDLE=/path/to/ca.pem`.  
3. (Last resort, diagnostics only) Temporarily disable verification with `STAC_MCP_UNSAFE_DISABLE_SSL=1` and immediately revert once the root cause is identified.  

If the container also fails, the remote endpoint may genuinely present an invalid or mismatched certificate—collect the structured error details (they include hostname and failing reason) and investigate network or proxy layers.

Planned future enhancements (pending ADRs): add retry/federation logic and corresponding tests; coverage thresholds may be introduced once feature set stabilizes.

### Linting

```bash
ruff format stac_mcp/ tests/ examples/
ruff check stac_mcp/ tests/ examples/
```

### Version Management

The project uses semantic versioning (SemVer) with automated version management based on PR labels or branch naming, implemented in `.github/workflows/container.yml`.

#### Automatic Versioning

When PRs are merged to `main`, the workflow determines the version increment using either PR labels or branch prefixes:

**PR Labels (Recommended for Automated Tools)**

Labels take priority over branch prefixes. Add one of these labels to your PR:
- **bump:patch** or **bump:hotfix** → patch increment (0.1.0 → 0.1.1) for bug fixes
- **bump:minor** or **bump:feature** → minor increment (0.1.0 → 0.2.0) for new features
- **bump:major** or **bump:release** → major increment (0.1.0 → 1.0.0) for breaking changes

**Branch Prefixes (For Human Contributors)**

If no version bump label is present, the workflow falls back to branch prefix detection:
- **hotfix/**, **fix/**, **copilot/fix-**, or **copilot/hotfix/** branches → patch increment (0.1.0 → 0.1.1) for bug fixes
- **feature/** or **copilot/feature/** branches → minor increment (0.1.0 → 0.2.0) for new features  
- **release/** or **copilot/release/** branches → major increment (0.1.0 → 1.0.0) for breaking changes

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines on version bumping.

#### Manual Version Management
You can also manually manage versions using the version script (should normally not be needed unless doing a coordinated release):

```bash
# Show current version
python scripts/version.py current

# Increment version based on change type
python scripts/version.py patch    # Bug fixes (0.1.0 -> 0.1.1)
python scripts/version.py minor    # New features (0.1.0 -> 0.2.0)  
python scripts/version.py major    # Breaking changes (0.1.0 -> 1.0.0)

# Set specific version
python scripts/version.py set 1.2.3
```

The version system maintains consistency across:
- `pyproject.toml` (project version)
- `stac_mcp/__init__.py` (__version__)
- `stac_mcp/server.py` (server_version in MCP initialization)

### Container Development

To develop with containers:

```bash
# Build development image
docker build -f Containerfile -t stac-mcp:dev .

# Test the container
docker run --rm -i stac-mcp:dev

# Using docker-compose for development
docker-compose up --build

# For debugging, use an interactive shell (requires modifying Containerfile)
# docker run --rm -it --entrypoint=/bin/sh stac-mcp:dev
```

Current Containerfile (single-stage) notes:
- Based on `python:3.12-slim` for broad wheel compatibility (rasterio, shapely, etc.)
- Installs GDAL/PROJ system libraries needed by rasterio/odc-stac
- Installs the package with `pip install .`
- Entrypoint: `python -m stac_mcp.server` (stdio MCP transport)
- Multi-stage/distroless hardening can be reintroduced later (tracked by potential future ADR)

## STAC Resources

- [STAC Specification](https://stacspec.org/)
- [pystac-client Documentation](https://pystac-client.readthedocs.io/)
- [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/)
- [AWS Earth Search](https://earth-search.aws.element84.com/v1)

## License

Apache 2.0 - see [LICENSE](LICENSE) file for details.

## Architecture Overview

The project maintains Architecture Decision Records (ADRs) and Architecture Significant Requirements (ASRs) under `architecture/`.
Core recent decisions:

- Observability & Telemetry (ADR 0012): structured logging (stderr only), metrics counters, correlation IDs, future-ready tracing hooks.
- Multi-Catalog Federation (ADR 0013): optional parallel search across multiple STAC endpoints with deterministic merging and provenance.
- Pluggable Tool Extension Model (ADR 0014): entry point / directory-based plugin registration with collision protection.
- Response Meta Stability (ADR 0015): introduces `meta` object with stable vs experimental field tiering.
- Security & Credential Isolation (ADR 0016): alias-scoped credentials, redaction and least-privilege injection.

Notable earlier foundations:
- Output format & JSON envelope (ADR 0006) and JSON stability (ASR 1003)
- Capability & aggregation support (ADR 0004)
- Data size estimation tool (ADR 0009) with nodata efficiency requirement (ASR 1006)
- Caching layer (ADR 0011)
- Offline deterministic validation (ASR 1001)
- Graceful network error handling (ASR 1004)
- Performance bounds for search (ASR 1005)
- Reliability & Retry Policy (ASR 1008)

See individual ADR/ASR markdown files for full context, rationale, and evolution notes.

## Service Level Objectives (SLO) & Requirements Summary

The following summarizes measurable targets defined in ASRs (and related ADR enforcement points). These are engineering **goals**; enforcement is via tests, benchmarks, and observability counters.

| Area | Reference | Objective |
|------|-----------|-----------|
| Offline Dev & Tests | ASR 1001 | Install <=120s, tests <=30s, example script ~0.6s, no live network |
| JSON Output Stability | ASR 1003 | Backwards-compatible JSON schemas within major version; golden tests guard |
| Network Error Handling | ASR 1004 | All network faults mapped to structured errors; server never crashes |
| Search Performance Bounds | ASR 1005 | Conservative default limit (10); pagination controls; no unbounded iteration |
| NoData & Memory Efficiency | ASR 1006 | Optional adjusted size reporting with `adjust_for_nodata`; always provide raw & adjusted bytes |
| Reliability & Retries | ASR 1008 | >=95% success under 20% transient fault injection; p95 retry overhead <= +35%; max invocation 15s; ≤2 retries (3 attempts total) |
| Meta Stability | ADR 0015 | Stable vs `_exp_` field tiering; no breaking removal of stable fields within major version |
| Observability | ADR 0012 | Structured JSON logs (opt-in), correlation IDs per request, metrics counters (latency, errors, cache, retries) |
| Federation | ADR 0013 | Partial catalog failures produce warnings not total failure when at least one succeeds |
| Plugin Safety | ADR 0014 | Tool name collision prevention; load failures isolated; optional strict mode |
| Credential Isolation | ADR 0016 | Per-alias credential scoping; automatic redaction; plugin access opt-in |

### Experimental Meta Fields (Subject to Change)
Defined in ADR 0015; current experimental keys returned (when features enabled):

- `_exp_federation_warnings`: array of partial-failure or truncation notices
- `_exp_cache_hit`: boolean indicating cache usage
- `_exp_retry_attempts`: integer number of retry attempts performed

Promotion of experimental fields to stable requires an ADR update and minor version release; consumers should treat `_exp_*` names as best-effort hints.

### Operational Notes
- Logging never uses stdout to avoid MCP protocol interference (ADR 0012).
- Federation item merging adds provenance via a namespaced property (`stac_mcp:source_catalog`) (ADR 0013).
- Retry logic applies only to idempotent read tools; future write-type tools must opt in explicitly (ASR 1008).
- Nodata adjustment is off by default to preserve raw size semantics (ASR 1006).

### Roadmap Candidates (Future ADRs)
- Metrics exposure tool or external exporter integration
- Circuit breaker & adaptive backoff extensions to reliability policy
- Plugin capability introspection tool
- OAuth / token refresh flows for credential layer

For contributions impacting architecture, add or update an ADR/ASR following `AGENTS.md` guidelines.

## Client Configuration (ADR 0007)

The STAC client implementation supports flexible configuration options for varied deployment scenarios (corporate proxies, slow networks, custom authentication).

### Per-Call Configuration (Programmatic API)

When using the `STACClient` class directly (e.g., in custom tools or extensions), you can configure requests at call time:

#### Timeout Configuration

All STAC API requests support an optional `timeout` parameter (in seconds):

```python
from stac_mcp.tools.client import STACClient

client = STACClient("https://planetarycomputer.microsoft.com/api/stac/v1")

# Use custom timeout (60 seconds instead of default 30)
result = client._http_json("/conformance", timeout=60)

# Disable timeout (wait indefinitely)
result = client._http_json("/conformance", timeout=0)
```

**Default**: 30 seconds if not specified

**Use cases**:
- Slow networks or high-latency connections: increase timeout
- Large catalog queries: increase timeout to prevent premature failures
- Testing/diagnostics: adjust timeout to isolate performance issues

#### Headers Configuration

Custom headers can be provided at two levels:

1. **Instance-level** (applies to all requests from that client):
```python
client = STACClient(
    "https://example.com/stac/v1",
    headers={"X-API-Key": "your-key", "User-Agent": "MyApp/1.0"}
)
```

2. **Per-call** (merges with or overrides instance headers):
```python
# Override specific header for this call only
result = client._http_json("/search", headers={"X-API-Key": "different-key"})
```

**Behavior**: Per-call headers are merged with instance headers, with per-call values taking precedence for duplicate keys. The `Accept: application/json` header is always set automatically.

**Note**: These configuration options are for programmatic use. MCP tool calls use the default client configuration.

### Error Handling

The client provides structured error types with actionable guidance:

#### Timeout Errors

When requests exceed the timeout threshold, a `STACTimeoutError` is raised with context:

```
Request to https://example.com/stac/v1/search timed out after 30s (attempted 3 times).
Consider increasing timeout parameter or checking network connectivity.
```

**Automatic retries**: Timeout errors are retried 3 times with exponential backoff before failing.

#### Connection Errors

Connection failures are mapped to specific, actionable messages via `ConnectionFailedError`:

- **DNS failures**: "DNS lookup failed for [url]. Check the catalog URL and network connectivity."
- **Connection refused**: "Connection refused by [url]. The server may be down or the URL may be incorrect."
- **Network unreachable**: "Network unreachable for [url]. Check network connectivity and firewall settings."
- **Generic errors**: Includes the underlying error reason with remediation guidance

**Automatic retries**: Connection errors are retried 3 times with exponential backoff (0.2s, 0.4s, 0.8s delays).

#### SSL/TLS Errors

SSL certificate verification failures raise `SSLVerificationError` with detailed remediation steps. See the [SSL / TLS Troubleshooting](#ssl--tls-troubleshooting) section for environment variables and configuration options.

### Error Logging

Network errors are logged at ERROR level (not EXCEPTION level) to preserve context without excessive stack traces:

```
ERROR stac_mcp.tools.client: Connection failed after 3 attempts: DNS lookup failed for ...
```

This follows ADR 0007 guidance: "Log at error level; no prints."

## Observability Configuration (ADR 0012)

Environment variables controlling telemetry:

| Variable | Default | Description |
|----------|---------|-------------|
| `STAC_MCP_LOG_LEVEL` | `WARNING` | Logging level (`DEBUG`, `INFO`, etc.) |
| `STAC_MCP_LOG_FORMAT` | `text` | Set to `json` for structured single-line JSON logs |
| `STAC_MCP_ENABLE_METRICS` | `true` | Disable (`false`) to skip counter increments |
| `STAC_MCP_ENABLE_TRACE` | `false` | Enable lightweight span timing debug logs |

All logs are emitted to stderr only; stdout is reserved strictly for MCP protocol traffic. JSON logs include fields: `timestamp`, `level`, `message`, plus optional `event`, `tool_name`, `duration_ms`, `error_type`, `correlation_id`, `cache_hit`, `catalog_url`.

