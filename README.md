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

## Usage

### MCP Protocol / Server Configuration

The server implements the [Model Context Protocol (MCP)](https://github.com/Model-Context-Protocol/MCP) for standardized communication.

```json
{
  "stac": {
    "command": "uvx",
    "args": [
      "--from",
      "git+https://github.com/wayfinder-foundry/stac-mcp",
      "stac-mcp"
    ],
    "transport": "stdio",
  }
}
```

##### Published Image

```bash
# With Docker
docker run --rm -i ghcr.io/wayfinder-foundry/stac-mcp:latest

# With Podman
podman run --rm -i ghcr.io/wayfinder-foundry/stac-mcp:latest
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

#### Local Development

```bash
git clone https://github.com/wayfinder-foundry/stac-mcp.git
cd stac-mcp
pip install -e ".[dev]"
```

For local development with containers, you can use VS Code's Remote Containers extension with the provided `.devcontainer` configuration.

### Testing

```bash
pytest -v
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
1. `ruff format stac_mcp/ tests/`
2. `ruff check stac_mcp/ tests/ --fix`
3. `coverage run -m pytest -q`
4. `coverage report -m` (ensure no unexpected drops)

### Linting

```bash
ruff format stac_mcp/ tests/
ruff check stac_mcp/ tests/ --fix --no-cache
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

## Documentation

### FastMCP Guidelines and Architecture

STAC MCP includes comprehensive documentation for FastMCP patterns and agentic geospatial reasoning:

- **[FastMCP Documentation](docs/)**: Complete guide to MCP decorators, resources, tools, and prompts for STAC workflows
  - [DECORATORS.md](docs/fastmcp/DECORATORS.md): Choosing the right decorator for STAC operations
  - [GUIDELINES.md](docs/fastmcp/GUIDELINES.md): FastMCP architecture and usage patterns
  - [PROMPTS.md](docs/fastmcp/PROMPTS.md): Agentic STAC search reasoning and methodology
  - [RESOURCES.md](docs/fastmcp/RESOURCES.md): STAC catalog discovery and metadata patterns
  - [CONTEXT.md](docs/fastmcp/CONTEXT.md): Context usage for logging and progress tracking

These documents provide guidance for:
- AI agents reasoning about STAC catalog searches
- Developers implementing STAC MCP features
- Understanding the planned FastMCP integration (issues #69, #78)

### Additional Documentation

- [Test Coverage Strategy](docs/TEST_COVERAGE_STRATEGY.md): Testing approach and coverage goals

## STAC Resources

- [STAC Specification](https://stacspec.org/)
- [pystac-client Documentation](https://pystac-client.readthedocs.io/)
- [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/)
- [AWS Earth Search](https://earth-search.aws.element84.com/v1)

## License

Apache 2.0 - see [LICENSE](LICENSE) file for details.

