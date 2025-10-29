# ADR 0017: PySTAC-based CRUDL Tools for Local and Remote STAC Management

Status: Implemented
Date: 2025-01-09

## Context

The STAC MCP server previously provided transaction tools for managing STAC resources on remote servers via pystac-client. However, there was no support for:

1. Managing STAC resources on local filesystems
2. Direct object manipulation using pystac
3. List operations for discovering existing resources
4. Unified interface for both local and remote operations

Users needed a way to programmatically manage STAC catalogs, collections, and items across different storage backends (filesystem and remote APIs) with full CRUDL (Create, Read, Update, Delete, List) capabilities.

## Decision

Implement a comprehensive set of PySTAC-based tools that provide CRUDL operations for STAC catalogs, collections, and items, supporting both local filesystem and remote HTTP/S endpoints.

### Key Design Decisions

1. **Separate Module**: Create `pystac_management.py` with `PySTACManager` class, distinct from existing transaction tools
2. **Dual Support**: Handle both local filesystem paths and remote URLs in a single interface
3. **API Key Authentication**: Support `STAC_API_KEY` environment variable for authenticated remote requests
4. **15 New Tools**: 5 operations (CRUDL) × 3 resource types (catalog, collection, item)
5. **Complementary Approach**: These tools complement rather than replace existing transaction tools

### Tool Categories

**Catalog Tools:**
- `pystac_create_catalog`: Create new catalog
- `pystac_read_catalog`: Read existing catalog
- `pystac_update_catalog`: Update catalog
- `pystac_delete_catalog`: Delete catalog
- `pystac_list_catalogs`: List catalogs in directory/endpoint

**Collection Tools:**
- `pystac_create_collection`: Create new collection
- `pystac_read_collection`: Read existing collection
- `pystac_update_collection`: Update collection
- `pystac_delete_collection`: Delete collection
- `pystac_list_collections`: List collections in directory/endpoint

**Item Tools:**
- `pystac_create_item`: Create new item
- `pystac_read_item`: Read existing item
- `pystac_update_item`: Update item
- `pystac_delete_item`: Delete item
- `pystac_list_items`: List items in directory/endpoint

## Implementation

### Core Components

1. **PySTACManager** (`stac_mcp/tools/pystac_management.py`):
   - Handles path detection (local vs remote)
   - Manages API key authentication
   - Implements all CRUDL operations
   - Uses pystac for object manipulation

2. **Handlers** (`stac_mcp/tools/pystac_handlers.py`):
   - 15 handler functions mapping tools to PySTACManager methods
   - Consistent signature: `handler(manager, arguments) -> dict`

3. **Tool Definitions** (`stac_mcp/tools/definitions.py`):
   - 15 MCP tool definitions with input schemas
   - Clear documentation of parameters

4. **Execution Integration** (`stac_mcp/tools/execution.py`):
   - Separate handler registry for pystac tools
   - Special handling in `execute_tool` function
   - Uses PySTACManager instead of STACClient

### Authentication

Remote operations support optional authentication via:
- `STAC_API_KEY` environment variable
- Automatically included as Bearer token in Authorization header
- No authentication required for local operations

### Path Resolution

The implementation automatically detects path type:
- Starts with `http://` or `https://`: Remote URL
- Otherwise: Local filesystem path

### Error Handling

- **ImportError**: If pystac not installed, provides clear error message
- **FileNotFoundError**: For missing local files
- **URLError**: For remote connection issues
- **HTTPError**: For API errors (401, 404, etc.)

## Consequences

### Positive

1. **Complete CRUDL**: All operations (including List) now available
2. **Dual Support**: Unified interface for local and remote operations
3. **Flexible Authentication**: Environment variable-based API key support
4. **Complementary**: Works alongside existing transaction tools
5. **Well Tested**: 50+ test cases covering all scenarios
6. **Documented**: Complete documentation and examples

### Negative

1. **Additional Dependency**: Requires pystac library (already in dependencies)
2. **Two APIs**: Users must choose between pystac tools and transaction tools
3. **Complexity**: More tools to learn and understand

### Neutral

1. **Different Patterns**: PySTAC tools use path-based addressing vs transaction tools using collection_id/item_id
2. **Separate Execution Path**: PySTAC tools bypass STACClient and use PySTACManager

## Comparison with Transaction Tools

| Aspect | PySTAC Tools | Transaction Tools |
|--------|-------------|-------------------|
| Library | pystac | pystac-client |
| Local Files | ✅ Yes | ❌ No |
| Remote APIs | ✅ Yes | ✅ Yes |
| Operations | CRUDL | CUD only |
| Authentication | STAC_API_KEY env | Headers in catalog config |
| Use Case | Direct management | API transactions |
| Path Format | File paths or URLs | Collection/Item IDs |

## Usage Examples

### Local Operations

```python
from stac_mcp.tools.pystac_management import PySTACManager

manager = PySTACManager()

# Create catalog
catalog = manager.create_catalog(
    path="/data/stac/my-catalog/catalog.json",
    catalog_id="my-catalog",
    description="My catalog"
)

# List catalogs
catalogs = manager.list_catalogs("/data/stac")
```

### Remote Operations

```bash
export STAC_API_KEY=your-api-key

python -c "
from stac_mcp.tools.pystac_management import PySTACManager

manager = PySTACManager()
result = manager.create_catalog(
    path='https://api.example.com/stac/catalogs',
    catalog_id='remote-catalog',
    description='Remote catalog'
)
"
```

## Testing

- **Unit Tests**: `tests/test_pystac_management.py` (30+ tests)
- **Handler Tests**: `tests/test_pystac_handlers.py` (15+ tests)
- **Example**: `examples/pystac_management_example.py`
- **Documentation**: `docs/pystac_crudl_tools.md`

## Future Enhancements

1. Batch operations for multiple resources
2. Transaction support for atomic operations
3. Validation of STAC objects before write
4. Progress callbacks for long-running operations
5. Caching layer for read operations
6. Support for additional authentication methods (OAuth, custom headers)

## Alternatives Considered

1. **Extend Transaction Tools**: Would have mixed local and remote concerns
2. **Separate Servers**: Too much overhead for related functionality
3. **CLI Tool**: MCP tools provide better integration with AI assistants
4. **Direct pystac Usage**: Tools provide consistent MCP interface

## References

- [STAC Specification](https://stacspec.org/)
- [pystac Documentation](https://pystac.readthedocs.io/)
- [ADR 1009: Transaction Extension](./1009-support-stac-api-transaction-extension.md)
- [Issue: Implement pystac-based tools for CRUDL management](https://github.com/Wayfinder-Foundry/stac-mcp/issues/XXX)
