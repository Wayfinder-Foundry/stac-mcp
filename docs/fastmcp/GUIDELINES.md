---
type: product_context
title: FastMCP Guidelines for STAC MCP
tags: [fastmcp, mcp, guidelines, stac]
---

# FastMCP: A Pythonic Framework for STAC Model Context Protocol

## What is FastMCP?

FastMCP is a high-level, Pythonic framework for building servers and clients that implement the **Model Context Protocol (MCP)**. MCP is a standard that allows large language models (LLMs) to access external data and functions through structured endpoints.

FastMCP simplifies MCP implementation by handling protocol specifics—such as JSON-RPC message handling, schema generation, error reporting, and transport management—so developers can focus on business logic.

The **FastMCP 2.0** release is the actively maintained version. It provides a comprehensive toolkit that goes beyond the core protocol, including:

- Deployment tools
- Authentication
- Dynamic tool rewriting
- REST-API integration
- Testing utilities

FastMCP's goal is to be **fast, simple, Pythonic, and complete**, giving you an easy path from development to production.

> **Website:** [gofastmcp.com](https://gofastmcp.com)

---

## STAC MCP Server Architecture

The STAC MCP server is built on the Model Context Protocol (MCP) standard, currently using the `mcp` package directly. Future integration with FastMCP is planned (tracked in issues #69 and #78).

### Current Architecture (MCP 1.0)

```python
from mcp.server import Server
from mcp.server.stdio import stdio_server

server = Server("stac-mcp")

@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available STAC tools."""
    return definitions.get_tool_definitions()

@server.call_tool()
async def handle_call_tool(tool_name: str, arguments: dict):
    """Execute STAC tool."""
    return await execution.execute_tool(tool_name, arguments)
```

### Planned FastMCP Integration

When migrating to FastMCP (issues #69, #78), the architecture will adopt:

```python
from fastmcp import FastMCP

mcp = FastMCP("STAC MCP Server")

@mcp.tool()
async def search_items(
    collections: list[str],
    bbox: list[float] | None = None,
    datetime: str | None = None,
    limit: int = 10
) -> dict:
    """Search STAC catalog for items."""
    return await stac_client.search(...)

@mcp.resource("catalog://collections")
def list_collections() -> dict:
    """List available STAC collections."""
    return {"collections": [...]}

@mcp.prompt()
def stac_search_guide(region: str, data_type: str) -> str:
    """Guide STAC search planning."""
    return f"Search strategy for {data_type} in {region}..."
```

---

## Installation and Versioning

### Current STAC MCP Installation

```bash
# Via pip
pip install stac-mcp

# From source
git clone https://github.com/Wayfinder-Foundry/stac-mcp.git
cd stac-mcp
pip install -e ".[dev]"

# Via container
docker pull ghcr.io/bnjam/stac-mcp:latest
```

### FastMCP Installation (for Future Integration)

```bash
# Recommended if using uv to manage dependencies
uv add fastmcp

# Alternative uv-based pip installation
uv pip install fastmcp

# Standard pip installation
pip install fastmcp
```

After installation, verify the FastMCP version:

```bash
fastmcp version
```

---

## Running and Transport Modes

### Current STAC MCP Server

The STAC MCP server currently uses **stdio** transport exclusively:

```bash
# Run as MCP server (stdio transport)
stac-mcp

# Via container
docker run --rm -i ghcr.io/bnjam/stac-mcp:latest
```

### FastMCP Transport Options (Future)

FastMCP supports multiple transport modes:

| Transport | Description                                                                 |
| --------- | --------------------------------------------------------------------------- |
| **stdio** | Default. Ideal for local development, each client gets a dedicated process. |
| **http**  | Exposes your server over HTTP for network access.                           |
| **sse**   | Server-Sent Events transport for legacy streaming clients.                  |

```bash
# Future FastMCP integration examples
fastmcp run stac_server.py:mcp

# HTTP transport
fastmcp run stac_server.py:mcp --transport http --port 8000
```

---

## Tools

**Tools** are functions exposed to LLMs for executing STAC operations.

### STAC Tool Categories

The STAC MCP server provides several categories of tools:

#### 1. STAC API Discovery
- **`get_root`**: Fetch catalog root document
- **`get_conformance`**: Check API conformance classes
- **`get_queryables`**: Retrieve queryable fields

#### 2. STAC Search and Retrieval
- **`search_collections`**: List/search STAC collections
- **`get_collection`**: Get collection details
- **`search_items`**: Search for STAC items (bbox, datetime, filters)
- **`get_item`**: Get item details

#### 3. Data Analysis
- **`estimate_data_size`**: Estimate dataset size using lazy loading
- **`get_aggregations`**: Execute aggregation queries

#### 4. PySTAC CRUDL Operations
- **Catalog**: create, read, update, delete, list
- **Collection**: create, read, update, delete, list
- **Item**: create, read, update, delete, list

### Tool Design Principles

**Current Implementation (delegated pattern):**
```python
# Tools are defined in stac_mcp/tools/definitions.py
# Execution is handled in stac_mcp/tools/execution.py

async def execute_tool(tool_name: str, arguments: dict):
    """Central tool execution dispatcher."""
    if tool_name == "search_items":
        return await handle_search_items(arguments)
    # ... other tools
```

**Future FastMCP Pattern:**
```python
@mcp.tool()
async def search_items(
    collections: list[str],
    bbox: list[float] | None = None,
    datetime: str | None = None,
    limit: int = 10,
    output_format: str = "text",
    ctx: Context | None = None
) -> dict:
    """
    Search STAC catalog for items.
    
    USE WHEN: Need to find geospatial datasets by location/time
    REQUIRES: Valid STAC catalog connection
    OUTPUT: List of matching STAC items
    SIDE EFFECTS: None (read-only search)
    """
    if ctx:
        await ctx.info(f"Searching {collections} with bbox={bbox}")
    
    results = await stac_client.search(
        collections=collections,
        bbox=bbox,
        datetime=datetime,
        limit=limit
    )
    
    if output_format == "json":
        return {"mode": "json", "data": {"items": list(results)}}
    else:
        return format_text_output(results)
```

### Key Tool Concepts

* **Metadata:**
  - Name, description, and parameter schemas auto-generated
  - Tags for categorization: `{"stac", "search", "geospatial"}`
  - Safety hints: `readOnlyHint=True` for search operations

* **Async support:**
  - All STAC API operations use `async def`
  - Enables concurrent catalog searches

* **Output formats:**
  - **Text mode** (default): Human-readable descriptions
  - **JSON mode**: Structured data for programmatic consumption
  - Dual-mode pattern: `output_format` parameter

* **Error handling:**
  - Network errors wrapped in `STACTimeoutError`, `ConnectionFailedError`
  - SSL/TLS errors provide remediation guidance
  - Graceful degradation when catalogs unavailable

* **Context Access:**
  - Add `Context` parameter for logging and progress
  - Used for long-running operations (size estimation)

---

## Resources and Resource Templates

**Resources** are read-only STAC data endpoints for AI agents to gather context.

### STAC Resource Examples

**Current Implementation (planned for future):**

```python
# Catalog root information
@mcp.resource("catalog://root")
def get_catalog_root() -> dict:
    """STAC catalog root document."""
    return stac_client.get_root()

# Collection metadata
@mcp.resource("collection://{collection_id}/metadata")
def get_collection_info(collection_id: str) -> dict:
    """Collection details and extent."""
    return stac_client.get_collection(collection_id)

# STAC specification reference
@mcp.resource("reference://stac-extensions")
def get_extensions() -> dict:
    """STAC extension descriptions."""
    return {
        "eo": "Electro-Optical extension",
        "proj": "Projection extension",
        "raster": "Raster band metadata"
    }

# Queryable fields
@mcp.resource("catalog://queryables")
def get_queryables() -> dict:
    """Available query parameters."""
    return stac_client.get_queryables()
```

### Resource Design Principles

* **URI Schemes:** Hierarchical and descriptive
  - `catalog://` - Catalog-level resources
  - `collection://` - Collection-specific data
  - `item://` - Item-level resources
  - `reference://` - Static reference information

* **Caching:** Appropriate for static resources
* **Error Handling:** Return structured errors, not exceptions
* **Context:** Rich metadata about STAC resources

---

## Prompts

Prompts are reusable templates that guide AI agents in STAC reasoning.

### STAC Prompt Examples

**Planned for Future Implementation:**

```python
@mcp.prompt()
def stac_search_methodology(
    data_type: str,
    region: str,
    time_period: str
) -> str:
    """Guide STAC search planning."""
    return f"""
    STAC SEARCH STRATEGY: {data_type} in {region}
    
    Time period: {time_period}
    
    1. Identify appropriate STAC collections
    2. Define spatial extent (bbox) for {region}
    3. Parse temporal range to STAC datetime
    4. Apply filters (cloud cover, resolution)
    5. Start with small limit to validate
    6. Expand search if needed
    
    What collections and parameters will you use?
    """

@mcp.prompt()
def temporal_filter_guide(analysis_type: str) -> str:
    """Help choose temporal filtering strategy."""
    return f"""
    TEMPORAL FILTERING FOR: {analysis_type}
    
    STAC datetime formats:
    - Single: "2023-06-15T00:00:00Z"
    - Range: "2023-01-01/2023-12-31"
    - Open start: "../2023-12-31"
    - Open end: "2023-01-01/.."
    
    Choose format based on {analysis_type} needs.
    """
```

### Prompt Use Cases

* **Search strategy:** Guide collection selection and parameter tuning
* **Temporal filtering:** Help choose datetime formats and ranges
* **Spatial reasoning:** Bbox construction and coordinate systems
* **Workflow planning:** Multi-step STAC operations

---

## Context Capabilities

The `Context` object provides features for tools, resources, and prompts:

| Capability         | Description                                           | STAC Use Case |
| ------------------ | ----------------------------------------------------- | ------------- |
| Logging            | `ctx.info`, `ctx.debug`, `ctx.warning`, `ctx.error`   | Search progress |
| Progress Reporting | `await ctx.report_progress(progress, total)`          | Size estimation |
| Resource Access    | `await ctx.read_resource(uri)`                        | Read catalog metadata |
| Request Metadata   | `ctx.request_id`, `ctx.client_id`                     | Correlation IDs |
| State Management   | `ctx.set_state()`, `ctx.get_state()`                  | Session workspace |

### STAC-Specific Context Usage

```python
@mcp.tool()
async def estimate_data_size(
    collections: list[str],
    bbox: list[float],
    limit: int = 50,
    ctx: Context | None = None
) -> dict:
    """Estimate data size with progress tracking."""
    if ctx:
        await ctx.info(f"Searching {limit} items from {collections}")
    
    items = await search_items(collections, bbox, limit=limit)
    
    total_items = len(items)
    estimated_bytes = 0
    
    for i, item in enumerate(items):
        if ctx and i % 10 == 0:
            await ctx.report_progress(i, total_items)
        
        estimated_bytes += calculate_item_size(item)
    
    if ctx:
        await ctx.info(f"Total estimate: {estimated_bytes} bytes")
    
    return {"estimated_bytes": estimated_bytes, "item_count": total_items}
```

---

## STAC MCP Best Practices

### 1. Output Format Support

All tools should support dual output modes:

```python
async def search_items(..., output_format: str = "text") -> dict:
    results = await stac_client.search(...)
    
    if output_format == "json":
        return {
            "mode": "json",
            "data": {"type": "item_list", "items": list(results)}
        }
    else:
        return format_text_summary(results)
```

### 2. Network Error Handling

Gracefully handle STAC API failures:

```python
from stac_mcp.tools.client import STACTimeoutError, ConnectionFailedError

try:
    result = await stac_client.search(...)
except STACTimeoutError as e:
    return {"error": str(e), "suggestion": "Increase timeout or check network"}
except ConnectionFailedError as e:
    return {"error": str(e), "catalog_url": catalog_url}
```

### 3. Parameter Validation

Validate STAC-specific inputs:

```python
def validate_bbox(bbox: list[float]) -> None:
    """Validate bbox format [west, south, east, north]."""
    if len(bbox) != 4:
        raise ValueError("bbox must have 4 coordinates")
    if not (-180 <= bbox[0] <= 180 and -180 <= bbox[2] <= 180):
        raise ValueError("longitude must be between -180 and 180")
    if not (-90 <= bbox[1] <= 90 and -90 <= bbox[3] <= 90):
        raise ValueError("latitude must be between -90 and 90")
```

### 4. Lazy Loading and Memory Efficiency

Use lazy loading for large datasets:

```python
# Use odc.stac for lazy data loading
import odc.stac

def estimate_size_lazy(items: list) -> int:
    """Estimate size without downloading."""
    try:
        ds = odc.stac.load(items, chunks={})
        return ds.nbytes
    except Exception:
        # Fallback to asset size sum
        return sum_asset_sizes(items)
```

### 5. Catalog Configuration

Support multiple STAC catalogs:

```python
# Default catalog
DEFAULT_CATALOG = "https://planetarycomputer.microsoft.com/api/stac/v1"

# Allow catalog override
def get_catalog_client(catalog_url: str | None = None) -> STACClient:
    url = catalog_url or os.getenv("STAC_CATALOG_URL", DEFAULT_CATALOG)
    return STACClient(url)
```

---

## Environment Configuration

### STAC MCP Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `STAC_CATALOG_URL` | Planetary Computer | Default STAC catalog endpoint |
| `STAC_API_KEY` | None | API key for authenticated catalogs |
| `STAC_MCP_CA_BUNDLE` | None | Custom CA bundle for SSL |
| `STAC_MCP_UNSAFE_DISABLE_SSL` | False | Disable SSL verification (dev only) |
| `STAC_MCP_LOG_LEVEL` | `WARNING` | Logging level |
| `STAC_MCP_LOG_FORMAT` | `text` | Set to `json` for structured logs |
| `STAC_MCP_ENABLE_METRICS` | `true` | Enable metrics counters |

---

## Testing

### Current Test Structure

```bash
# Run all tests
pytest -v

# Run with coverage
coverage run -m pytest
coverage report -m

# Test specific module
pytest tests/test_server.py -v
```

### Test Categories

1. **MCP Protocol Tests** (`tests/test_mcp_protocol.py`)
   - Tool listing
   - Tool execution
   - Error handling

2. **Server Functionality** (`tests/test_server.py`)
   - STAC searches
   - Collection/item retrieval
   - PySTAC CRUDL operations

3. **Client Tests** (`tests/test_client.py`)
   - Network error handling
   - SSL/TLS verification
   - Retry logic

---

## Migration Path to FastMCP

### Current State (v1.2.0)

- Using `mcp` package directly
- Manual tool registration and execution
- Delegated pattern for tool definitions

### Planned Migration (Issues #69, #78)

1. **Phase 1: Add FastMCP dependency**
   ```bash
   pip install fastmcp
   ```

2. **Phase 2: Create FastMCP server instance**
   ```python
   from fastmcp import FastMCP
   mcp = FastMCP("STAC MCP Server")
   ```

3. **Phase 3: Convert tools to decorators**
   ```python
   @mcp.tool()
   async def search_items(...) -> dict:
       """Search STAC items."""
   ```

4. **Phase 4: Add resources and prompts**
   ```python
   @mcp.resource("catalog://collections")
   def list_collections() -> dict:
       """List collections."""
   
   @mcp.prompt()
   def search_guide(...) -> str:
       """Search guidance."""
   ```

5. **Phase 5: Update documentation and examples**

---

## Conclusion

STAC MCP provides an MCP-compliant interface to STAC catalogs, enabling AI agents to discover and access geospatial data. Future integration with FastMCP will enhance the developer experience through:

- **Simplified decorator-based API**
- **Automatic schema generation**
- **Built-in resource and prompt support**
- **Enhanced testing utilities**

By adopting FastMCP patterns while maintaining STAC-specific domain knowledge, the server will continue to evolve as a robust, production-ready geospatial data integration platform.

---

## References

- **STAC Specification**: [stacspec.org](https://stacspec.org/)
- **FastMCP**: [gofastmcp.com](https://gofastmcp.com)
- **MCP Protocol**: [Model Context Protocol Spec](https://spec.modelcontextprotocol.io/)
- **Issue #69**: FastMCP integration
- **Issue #78**: FastMCP doc/architecture implementation

---

**Last Updated**: 2025-10-18  
**Related Docs**: [DECORATORS.md](./DECORATORS.md), [PROMPTS.md](./PROMPTS.md), [RESOURCES.md](./RESOURCES.md), [CONTEXT.md](./CONTEXT.md)
