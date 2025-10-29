# PySTAC Tools Quick Start Guide

## Overview

The STAC MCP Server now includes 15 PySTAC-based CRUDL (Create, Read, Update, Delete, List) tools for managing STAC catalogs, collections, and items on both local filesystems and remote servers.

## Quick Comparison

### When to Use PySTAC Tools vs Transaction Tools

**Use PySTAC Tools when:**
- Managing STAC resources on local filesystems
- Need List operations to discover existing resources
- Want unified interface for local and remote operations
- Working with STAC object files directly
- Building local STAC catalogs

**Use Transaction Tools when:**
- Only working with remote STAC APIs
- Using pystac-client-based workflows
- Need conformance checking before operations
- Following STAC Transaction API specification

## Getting Started

### 1. Local Filesystem Example

```python
#!/usr/bin/env python3
"""Simple local STAC catalog creation."""

from stac_mcp.tools.pystac_management import PySTACManager

# Initialize manager (no API key needed for local)
manager = PySTACManager()

# Create a catalog
catalog = manager.create_catalog(
    path="/data/stac/my-catalog/catalog.json",
    catalog_id="my-catalog",
    description="My first STAC catalog",
    title="My Catalog"
)

print(f"Created catalog: {catalog['id']}")

# List all catalogs in a directory
catalogs = manager.list_catalogs("/data/stac")
print(f"Found {len(catalogs)} catalogs")
```

### 2. Remote API Example

```bash
# Set API key for authentication
export STAC_API_KEY=your-secret-api-key
```

```python
#!/usr/bin/env python3
"""Remote STAC server interaction."""

from stac_mcp.tools.pystac_management import PySTACManager

# Initialize manager (will use STAC_API_KEY from environment)
manager = PySTACManager()

# Create a remote catalog
catalog = manager.create_catalog(
    path="https://api.example.com/stac/catalogs",
    catalog_id="remote-catalog",
    description="Remote catalog"
)

# List remote catalogs
catalogs = manager.list_catalogs("https://api.example.com/stac/catalogs")
```

### 3. MCP Tool Usage

```python
#!/usr/bin/env python3
"""Using tools through MCP server."""

import asyncio
from mcp.types import CallToolRequest, CallToolRequestParams

async def create_catalog():
    result = await call_tool(
        "pystac_create_catalog",
        {
            "path": "/data/stac/catalog.json",
            "catalog_id": "example",
            "description": "Example catalog"
        }
    )
    return result

asyncio.run(create_catalog())
```

## All Available Tools

### Catalog Operations

| Tool | Description | Local | Remote |
|------|-------------|-------|--------|
| `pystac_create_catalog` | Create new catalog | ✅ | ✅ |
| `pystac_read_catalog` | Read existing catalog | ✅ | ✅ |
| `pystac_update_catalog` | Update catalog | ✅ | ✅ |
| `pystac_delete_catalog` | Delete catalog | ✅ | ✅ |
| `pystac_list_catalogs` | List catalogs | ✅ | ✅ |

### Collection Operations

| Tool | Description | Local | Remote |
|------|-------------|-------|--------|
| `pystac_create_collection` | Create new collection | ✅ | ✅ |
| `pystac_read_collection` | Read existing collection | ✅ | ✅ |
| `pystac_update_collection` | Update collection | ✅ | ✅ |
| `pystac_delete_collection` | Delete collection | ✅ | ✅ |
| `pystac_list_collections` | List collections | ✅ | ✅ |

### Item Operations

| Tool | Description | Local | Remote |
|------|-------------|-------|--------|
| `pystac_create_item` | Create new item | ✅ | ✅ |
| `pystac_read_item` | Read existing item | ✅ | ✅ |
| `pystac_update_item` | Update item | ✅ | ✅ |
| `pystac_delete_item` | Delete item | ✅ | ✅ |
| `pystac_list_items` | List items | ✅ | ✅ |

## Common Use Cases

### Use Case 1: Building a Local STAC Catalog

```python
from stac_mcp.tools.pystac_management import PySTACManager

manager = PySTACManager()

# Step 1: Create catalog
catalog = manager.create_catalog(
    path="/data/stac/catalog.json",
    catalog_id="earth-obs",
    description="Earth observation data catalog"
)

# Step 2: Create collection
collection = manager.create_collection(
    path="/data/stac/collections/sentinel2.json",
    collection={
        "type": "Collection",
        "id": "sentinel2",
        "stac_version": "1.0.0",
        "description": "Sentinel-2 data",
        "license": "proprietary",
        "extent": {
            "spatial": {"bbox": [[-180, -90, 180, 90]]},
            "temporal": {"interval": [[None, None]]}
        },
        "links": []
    }
)

# Step 3: Add items
item = manager.create_item(
    path="/data/stac/items/S2A_20230101.json",
    item={
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": "S2A_20230101",
        "properties": {"datetime": "2023-01-01T00:00:00Z"},
        "geometry": {"type": "Point", "coordinates": [0, 0]},
        "links": [],
        "assets": {}
    }
)
```

### Use Case 2: Syncing Local to Remote

```python
from stac_mcp.tools.pystac_management import PySTACManager
import os

# Set up authenticated manager
os.environ["STAC_API_KEY"] = "your-api-key"
manager = PySTACManager()

# Read local catalog
local_catalog = manager.read_catalog("/data/stac/catalog.json")

# Push to remote
remote_catalog = manager.create_catalog(
    path="https://api.example.com/stac/catalogs",
    catalog_id=local_catalog["id"],
    description=local_catalog["description"]
)

print("Synced to remote!")
```

### Use Case 3: Batch Operations

```python
from stac_mcp.tools.pystac_management import PySTACManager
from pathlib import Path

manager = PySTACManager()

# List all items in a collection
items = manager.list_items("/data/stac/collections/sentinel2/items")

# Update each item
for item in items:
    # Modify item
    item["properties"]["processed"] = True
    
    # Update back to disk
    item_path = f"/data/stac/items/{item['id']}.json"
    manager.update_item(item_path, item)

print(f"Updated {len(items)} items")
```

### Use Case 4: Catalog Validation

```python
from stac_mcp.tools.pystac_management import PySTACManager

manager = PySTACManager()

# List and validate all catalogs
catalogs = manager.list_catalogs("/data/stac")

for catalog in catalogs:
    print(f"Catalog: {catalog['id']}")
    print(f"  Description: {catalog.get('description', 'N/A')}")
    print(f"  Links: {len(catalog.get('links', []))}")
```

## Authentication Guide

### Environment Variable (Recommended)

```bash
export STAC_API_KEY=your-api-key
```

### Programmatic

```python
from stac_mcp.tools.pystac_management import PySTACManager

manager = PySTACManager(api_key="your-api-key")
```

### Verifying Authentication

```python
manager = PySTACManager(api_key="test-key")
headers = manager._get_headers()

if "Authorization" in headers:
    print("✓ Authentication configured")
else:
    print("✗ No authentication")
```

## Error Handling

### Import Errors

```python
try:
    from stac_mcp.tools.pystac_management import PySTACManager
    manager = PySTACManager()
except ImportError as e:
    print(f"Error: {e}")
    print("Install pystac: pip install pystac")
```

### File Not Found

```python
try:
    catalog = manager.read_catalog("/nonexistent/catalog.json")
except FileNotFoundError:
    print("Catalog file not found")
```

### Remote API Errors

```python
try:
    catalog = manager.create_catalog(
        path="https://api.example.com/catalogs",
        catalog_id="test",
        description="Test"
    )
except urllib.error.HTTPError as e:
    if e.code == 401:
        print("Authentication failed - check STAC_API_KEY")
    elif e.code == 404:
        print("Endpoint not found")
    else:
        print(f"HTTP error: {e.code}")
```

## Testing

Run the test suite:

```bash
# Run all pystac tests
pytest tests/test_pystac_management.py tests/test_pystac_handlers.py -v

# Run specific test
pytest tests/test_pystac_management.py::test_create_catalog_local -v

# Run with coverage
pytest tests/test_pystac_*.py --cov=stac_mcp.tools.pystac_management
```

## Examples

See complete examples in:
- `examples/pystac_management_example.py` - Comprehensive demonstration
- `docs/pystac_crudl_tools.md` - Detailed API reference

## Troubleshooting

### Issue: "pystac is required for catalog management operations"

**Solution:** Install pystac:
```bash
pip install pystac
```

### Issue: Authentication fails on remote operations

**Solution:** Verify API key is set:
```bash
echo $STAC_API_KEY
```

### Issue: Files created in wrong location

**Solution:** Use absolute paths:
```python
from pathlib import Path

base_path = Path("/data/stac").absolute()
catalog_path = base_path / "catalog.json"
```

### Issue: Remote endpoint returns 404

**Solution:** Verify endpoint URL and ensure it exists:
```python
# Check if endpoint is correct
print(f"Creating at: {url}")
```

## Best Practices

1. **Use absolute paths** for local operations
2. **Set STAC_API_KEY via environment** rather than code
3. **Validate STAC objects** before writing
4. **Handle errors gracefully** with try-except blocks
5. **Use list operations** to discover existing resources
6. **Separate local and remote concerns** in your code

## Next Steps

- Read the [complete documentation](pystac_crudl_tools.md)
- Review [ADR 0017](../architecture/0017-pystac-based-crudl-tools.md)
- Try the [example script](../examples/pystac_management_example.py)
- Check existing [transaction tools](../README.md#transaction-operations)

## Support

For issues or questions:
- GitHub Issues: [Wayfinder-Foundry/stac-mcp](https://github.com/Wayfinder-Foundry/stac-mcp/issues)
- STAC Spec: [stacspec.org](https://stacspec.org/)
- pystac Docs: [pystac.readthedocs.io](https://pystac.readthedocs.io/)
