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
- **`code-catalog-connect`**: Generate Python code snippet to connect to a STAC catalog
- **`code-catalog-search`**: Generate Python code snippet for stackstac.query operation with given AOI and timeseries

### Supported STAC Catalogs

By default, the server connects to Microsoft Planetary Computer STAC API, but it can be configured to work with any STAC-compliant catalog.

The server now includes **StackSTAC code generation tools** that produce ready-to-use Python snippets for connecting to catalogs and creating stackstac queries.

## Installation

```bash
pip install stac-mcp
```

Or for development:

```bash
git clone https://github.com/BnJam/stac-mcp.git
cd stac-mcp
pip install -e .
```

## Usage

### As an MCP Server

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

### Command Line

You can also run the server directly:

```bash
stac-mcp
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

#### Generate StackSTAC Code

##### Connect to Catalog
```python
# Generate code to connect to default catalog (Microsoft Planetary Computer)
code-catalog-connect()

# Generate code to connect to custom catalog
code-catalog-connect(
    catalog_url="https://earth-search.aws.element84.com/v1",
    variable_name="aws_catalog"
)
```

##### StackSTAC Query Operations
```python
# Generate stackstac query code for Landsat data over San Francisco
code-catalog-search(
    collections=["landsat-c2l2-sr"],
    bbox=[-122.5, 37.7, -122.3, 37.8],
    datetime="2023-01-01/2023-12-31",
    variable_name="sf_landsat"
)

# Generate stackstac query code with cloud filtering
code-catalog-search(
    collections=["sentinel-2-l2a"],
    bbox=[-74.1, 40.6, -73.9, 40.8],  # New York area
    query={"eo:cloud_cover": {"lt": 10}},
    limit=50
)
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

## STAC Resources

- [STAC Specification](https://stacspec.org/)
- [pystac-client Documentation](https://pystac-client.readthedocs.io/)
- [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com/)
- [AWS Earth Search](https://earth-search.aws.element84.com/v1)

## License

Apache 2.0 - see [LICENSE](LICENSE) file for details.