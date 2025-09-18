# STAC MCP Server

An MCP (Model Context Protocol) Server that provides access to STAC (SpatioTemporal Asset Catalog) APIs for geospatial data discovery and access.

## Overview

This MCP server enables AI assistants and applications to interact with STAC catalogs to:
- Search and browse STAC collections
- Find geospatial datasets (satellite imagery, weather data, etc.)
- Access metadata and asset information
- Perform spatial and temporal queries

## Features

### Available Tools

- **`search_collections`**: List and search available STAC collections
- **`get_collection`**: Get detailed information about a specific collection
- **`search_items`**: Search for STAC items with spatial, temporal, and attribute filters
- **`get_item`**: Get detailed information about a specific STAC item

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

The STAC MCP server is available as a secure distroless container image with semantic versioning:

```bash
# Pull the latest stable version
docker pull ghcr.io/bnjam/stac-mcp:latest

# Pull a specific version (recommended for production)
docker pull ghcr.io/bnjam/stac-mcp:0.1.0

# Run the container (uses stdio transport for MCP)
docker run --rm -i ghcr.io/bnjam/stac-mcp:latest
```

Container images are tagged with semantic versions:
- `ghcr.io/bnjam/stac-mcp:1.2.3` (exact version)
- `ghcr.io/bnjam/stac-mcp:1.2` (major.minor)
- `ghcr.io/bnjam/stac-mcp:1` (major)
- `ghcr.io/bnjam/stac-mcp:latest` (latest stable)

#### Building the Container

To build the container locally using the provided Containerfile:

```bash
# Build with Docker
docker build -f Containerfile -t stac-mcp .

# Or build with Podman  
podman build -f Containerfile -t stac-mcp .
```

The container uses a multi-stage build with:
- **Builder stage**: Python 3.12 slim image for building dependencies
- **Runtime stage**: Distroless Python image for security and minimal size
- **Security**: Runs as non-root user, minimal attack surface
- **Transport**: Uses stdio for MCP protocol communication

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

### Command Line

#### Native Installation

```bash
stac-mcp
```

#### Container Usage

```bash
# With Docker
docker run --rm -i ghcr.io/bnjam/stac-mcp:latest

# With Podman
podman run --rm -i ghcr.io/bnjam/stac-mcp:latest
```

### Examples

#### Search Collections
```python
# Find all available collections
search_collections(limit=20)

# Search collections from a different catalog
search_collections(catalog_url="https://earth-search.aws.element84.com/v1", limit=10)
```

#### Search Items
```python
# Search for Landsat data over San Francisco
search_items(
    collections=["landsat-c2l2-sr"],
    bbox=[-122.5, 37.7, -122.3, 37.8],
    datetime="2023-01-01/2023-12-31",
    limit=10
)

# Search with additional query parameters
search_items(
    collections=["sentinel-2-l2a"],
    bbox=[-74.1, 40.6, -73.9, 40.8],  # New York area
    query={"eo:cloud_cover": {"lt": 10}},
    limit=5
)
```

#### Get Collection Details
```python
# Get information about a specific collection
get_collection("landsat-c2l2-sr")
```

#### Get Item Details
```python
# Get detailed information about a specific item
get_item("landsat-c2l2-sr", "LC08_L2SR_044034_20230815_02_T1")
```

## Development

### Setup

```bash
git clone https://github.com/BnJam/stac-mcp.git
cd stac-mcp
pip install -e ".[dev]"
```

### Testing

```bash
pytest
```

### Linting

```bash
black stac_mcp/
ruff check stac_mcp/
```

### Version Management

The project uses semantic versioning (SemVer) with automated version management based on branch naming:

#### Branch-Based Automatic Versioning
When PRs are merged to main, versions are automatically incremented based on branch prefixes:
- **hotfix/** branches → patch increment (0.1.0 → 0.1.1) for bug fixes
- **feature/** branches → minor increment (0.1.0 → 0.2.0) for new features  
- **release/** branches → major increment (0.1.0 → 1.0.0) for breaking changes

#### Manual Version Management
You can also manually manage versions using the version script:

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

The Containerfile uses a secure multi-stage build approach:
- **Distroless base**: Minimal attack surface with no shell or package manager
- **Non-root user**: Container runs as unprivileged user
- **Minimal dependencies**: Only runtime dependencies included in final image
- **Build optimization**: Dependencies built in separate stage and copied over
- **Production ready**: Includes resource limits and security best practices

## STAC Resources

- [STAC Specification](https://stacspec.org/)
- [pystac-client Documentation](https://pystac-client.readthedocs.io/)
- [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/)
- [AWS Earth Search](https://earth-search.aws.element84.com/v1)

## License

Apache 2.0 - see [LICENSE](LICENSE) file for details.