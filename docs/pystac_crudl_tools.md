# PySTAC-based CRUDL Tools

## Overview

The STAC MCP Server provides a comprehensive set of PySTAC-based tools for managing STAC catalogs, collections, and items. These tools support both local filesystem operations and remote STAC server operations, enabling full Create, Read, Update, Delete, and List (CRUDL) capabilities.

## Key Features

- **Local Operations**: Manage STAC resources on the local filesystem
- **Remote Operations**: Interact with remote STAC servers via HTTP/HTTPS
- **API Key Authentication**: Support for authenticated requests using the `STAC_API_KEY` environment variable
- **Complementary to Transaction Tools**: These tools work alongside existing transaction tools without replacing them

## Comparison: PySTAC Tools vs Transaction Tools

| Feature | PySTAC CRUDL Tools | Transaction Tools |
|---------|-------------------|-------------------|
| Library | pystac | pystac-client |
| Local Files | ✅ Yes | ❌ No |
| Remote APIs | ✅ Yes | ✅ Yes |
| Operations | CRUDL (Create, Read, Update, Delete, List) | CUD (Create, Update, Delete) |
| Authentication | STAC_API_KEY env variable | Headers via catalog configuration |
| Use Case | Direct file/object management | API transactions |

## Authentication

For remote operations that require authentication, set the `STAC_API_KEY` environment variable:

```bash
export STAC_API_KEY=your-api-key-here
```

The API key will be automatically included in requests as a Bearer token in the Authorization header.

## Tools Reference

### Catalog Management

#### `pystac_create_catalog`

Create a new STAC Catalog.

**Parameters:**
- `path` (string, required): Path to save catalog (local file path or remote URL)
- `catalog_id` (string, required): Catalog identifier
- `description` (string, required): Catalog description
- `title` (string, optional): Catalog title (defaults to catalog_id)

**Example:**
```json
{
  "path": "/path/to/my-catalog/catalog.json",
  "catalog_id": "my-catalog",
  "description": "My STAC catalog",
  "title": "My Catalog"
}
```

**Remote Example:**
```json
{
  "path": "https://example.com/stac/catalogs",
  "catalog_id": "remote-catalog",
  "description": "Remote STAC catalog"
}
```

#### `pystac_read_catalog`

Read an existing STAC Catalog.

**Parameters:**
- `path` (string, required): Path to catalog (local file path or remote URL)

**Example:**
```json
{
  "path": "/path/to/my-catalog/catalog.json"
}
```

#### `pystac_update_catalog`

Update an existing STAC Catalog.

**Parameters:**
- `path` (string, required): Path to catalog
- `catalog` (object, required): Updated catalog dictionary following STAC Catalog specification

**Example:**
```json
{
  "path": "/path/to/my-catalog/catalog.json",
  "catalog": {
    "id": "my-catalog",
    "type": "Catalog",
    "stac_version": "1.0.0",
    "description": "Updated description",
    "links": []
  }
}
```

#### `pystac_delete_catalog`

Delete a STAC Catalog.

**Parameters:**
- `path` (string, required): Path to catalog

**Example:**
```json
{
  "path": "/path/to/my-catalog/catalog.json"
}
```

#### `pystac_list_catalogs`

List STAC Catalogs in a directory or remote endpoint.

**Parameters:**
- `base_path` (string, required): Base path to search (local directory or remote URL)

**Example:**
```json
{
  "base_path": "/path/to/catalogs"
}
```

### Collection Management

#### `pystac_create_collection`

Create a new STAC Collection.

**Parameters:**
- `path` (string, required): Path to save collection
- `collection` (object, required): Collection dictionary following STAC Collection specification

**Example:**
```json
{
  "path": "/path/to/my-collection/collection.json",
  "collection": {
    "type": "Collection",
    "id": "my-collection",
    "stac_version": "1.0.0",
    "description": "My collection",
    "license": "MIT",
    "extent": {
      "spatial": {"bbox": [[-180, -90, 180, 90]]},
      "temporal": {"interval": [[null, null]]}
    },
    "links": []
  }
}
```

#### `pystac_read_collection`

Read an existing STAC Collection.

**Parameters:**
- `path` (string, required): Path to collection

**Example:**
```json
{
  "path": "/path/to/my-collection/collection.json"
}
```

#### `pystac_update_collection`

Update an existing STAC Collection.

**Parameters:**
- `path` (string, required): Path to collection
- `collection` (object, required): Updated collection dictionary

#### `pystac_delete_collection`

Delete a STAC Collection.

**Parameters:**
- `path` (string, required): Path to collection

#### `pystac_list_collections`

List STAC Collections in a directory or remote endpoint.

**Parameters:**
- `base_path` (string, required): Base path to search

**Example:**
```json
{
  "base_path": "/path/to/collections"
}
```

### Item Management

#### `pystac_create_item`

Create a new STAC Item.

**Parameters:**
- `path` (string, required): Path to save item
- `item` (object, required): Item dictionary following STAC Item specification

**Example:**
```json
{
  "path": "/path/to/my-item/item.json",
  "item": {
    "type": "Feature",
    "stac_version": "1.0.0",
    "id": "my-item",
    "properties": {
      "datetime": "2023-01-01T00:00:00Z"
    },
    "geometry": {
      "type": "Point",
      "coordinates": [0.0, 0.0]
    },
    "links": [],
    "assets": {}
  }
}
```

#### `pystac_read_item`

Read an existing STAC Item.

**Parameters:**
- `path` (string, required): Path to item

**Example:**
```json
{
  "path": "/path/to/my-item/item.json"
}
```

#### `pystac_update_item`

Update an existing STAC Item.

**Parameters:**
- `path` (string, required): Path to item
- `item` (object, required): Updated item dictionary

#### `pystac_delete_item`

Delete a STAC Item.

**Parameters:**
- `path` (string, required): Path to item

#### `pystac_list_items`

List STAC Items in a directory or remote endpoint.

**Parameters:**
- `base_path` (string, required): Base path to search

**Example:**
```json
{
  "base_path": "/path/to/items"
}
```

## Usage Examples

### Local Filesystem Operations

```python
import asyncio
from stac_mcp.tools.pystac_management import PySTACManager

async def main():
    manager = PySTACManager()
    
    # Create a catalog
    catalog = await manager.create_catalog(
        path="/data/stac/my-catalog/catalog.json",
        catalog_id="my-catalog",
        description="My STAC catalog"
    )
    
    # List catalogs in directory
    catalogs = await manager.list_catalogs("/data/stac")
    
    # Read a collection
    collection = await manager.read_collection(
        path="/data/stac/my-collection/collection.json"
    )

asyncio.run(main())
```

### Remote Operations with Authentication

```bash
# Set API key
export STAC_API_KEY=your-secret-key

# Run operations
python -c "
from stac_mcp.tools.pystac_management import PySTACManager

manager = PySTACManager()  # Will use STAC_API_KEY from environment

# Create remote catalog
result = manager.create_catalog(
    path='https://api.example.com/stac/catalogs',
    catalog_id='remote-catalog',
    description='Remote catalog'
)
print(result)
"
```

### Using MCP Tools

```python
import asyncio
from mcp.types import CallToolRequest, CallToolRequestParams

async def call_pystac_tool():
    # Create a catalog
    result = await call_tool(
        "pystac_create_catalog",
        {
            "path": "/path/to/catalog.json",
            "catalog_id": "example",
            "description": "Example catalog"
        }
    )
    return result

asyncio.run(call_pystac_tool())
```

## Best Practices

1. **Local vs Remote**: Use local operations for filesystem-based catalogs and remote operations for API-based catalogs.

2. **Authentication**: Store API keys securely and use environment variables rather than hardcoding them.

3. **Error Handling**: Both local and remote operations can raise exceptions. Always wrap calls in try-except blocks.

4. **Path Format**: 
   - Local: Use absolute or relative file paths (`/path/to/file.json`)
   - Remote: Use full URLs (`https://example.com/stac/resource`)

5. **Validation**: Ensure STAC objects follow the STAC specification before creating or updating them.

## Error Handling

Common errors and solutions:

- **ImportError**: pystac library not installed
  - Solution: `pip install pystac`

- **FileNotFoundError**: Local file path doesn't exist
  - Solution: Ensure parent directories exist or use absolute paths

- **URLError**: Remote endpoint not accessible
  - Solution: Check network connectivity and URL

- **Authentication Error (401)**: API key invalid or missing
  - Solution: Verify STAC_API_KEY environment variable is set correctly

## See Also

- [STAC Specification](https://stacspec.org/)
- [pystac Documentation](https://pystac.readthedocs.io/)
- [Transaction Tools](../README.md#transaction-operations) (for API-based operations)
- [Example Scripts](../examples/pystac_management_example.py)
