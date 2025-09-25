# STAC MCP Server

[![PyPI Version](https://img.shields.io/pypi/v/stac-mcp?style=flat-square&logo=pypi)](https://pypi.org/project/stac-mcp/)
[![Build Status](https://img.shields.io/github/actions/workflow/status/BnJam/stac-mcp/container.yml?branch=main&style=flat-square&logo=github)](https://github.com/BnJam/stac-mcp/actions/workflows/container.yml)
[![Container](https://img.shields.io/badge/container-ghcr.io-blue?style=flat-square&logo=docker)](https://github.com/BnJam/stac-mcp/pkgs/container/stac-mcp)
[![Python](https://img.shields.io/pypi/pyversions/stac-mcp?style=flat-square&logo=python)](https://pypi.org/project/stac-mcp/)
[![License](https://img.shields.io/github/license/BnJam/stac-mcp?style=flat-square)](https://github.com/BnJam/stac-mcp/blob/main/LICENSE)
[![PyPI Downloads](https://static.pepy.tech/personalized-badge/stac-mcp?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/stac-mcp)

An MCP (Model Context Protocol) Server that provides access to STAC (SpatioTemporal Asset Catalog) APIs for geospatial data discovery and access. Supports dual output modes (`text` and structured `json`) for all tools.

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

```bash
git clone https://github.com/BnJam/stac-mcp.git
cd stac-mcp
pip install -e ".[dev]"
```

### Testing

```bash
pytest -v
python examples/example_usage.py  # MCP stdio smoke test
```

### Linting

```bash
black stac_mcp/
ruff check stac_mcp/
```

### Version Management

The project uses semantic versioning (SemVer) with automated version management based on branch naming, implemented in `.github/workflows/container.yml`:

#### Branch-Based Automatic Versioning
When PRs are merged to `main`, the workflow inspects the merged branch name (via the PR head ref) and increments the version if it matches a prefix:
- **hotfix/** branches → patch increment (0.1.0 → 0.1.1) for bug fixes
- **feature/** branches → minor increment (0.1.0 → 0.2.0) for new features  
- **release/** branches → major increment (0.1.0 → 1.0.0) for breaking changes

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
