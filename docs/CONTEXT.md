# FastMCP Context Usage Guide for STAC MCP

**Status**: Technical Guide  
**Last Updated**: 2025-10-18  
**Purpose**: How to use the FastMCP `Context` object in STAC MCP tools, resources, and prompts

---

## Overview

This guide describes how STAC MCP uses (or will use) the FastMCP `Context` object and how to keep logging and orchestration consistent across STAC tools, resources, and shared modules.

---

## 1. Where Context Lives

### Current Architecture (MCP 1.0)

STAC MCP currently uses the `mcp` package directly without FastMCP's `Context` object. Tools receive parameters directly:

```python
async def execute_tool(tool_name: str, arguments: dict):
    """Current tool execution pattern."""
    if tool_name == "search_items":
        return await handle_search_items(arguments)
```

### Future FastMCP Architecture

When migrating to FastMCP (issues #69, #78), `Context` will be injected:

- **Entry points**: `Context` will be injected into MCP tools, resources, and prompts in `stac_mcp/tools/`, `stac_mcp/resources/` (future), and `stac_mcp/prompts/` (future)
- **Shared helpers**: Modules under `stac_mcp/tools/client.py` and future shared utilities will accept `ctx: Context | None` but remain silent unless the caller explicitly opts in

This keeps shared STAC logic reusable outside MCP and avoids duplicate logging.

---

## 2. Allowed Operations

When using `Context` in STAC MCP, limit usage to:

### Logging
```python
await ctx.info("Searching STAC catalog for items")
await ctx.debug(f"Using bbox: {bbox}, datetime: {datetime}")
await ctx.warning("Collection not found, trying fallback")
await ctx.error("STAC API connection failed")
```

### Progress Reporting
```python
# For long-running operations like size estimation
await ctx.report_progress(processed_items, total_items, "Estimating data size...")
```

### Resource Access
```python
# Read STAC catalog metadata from resources
catalog_info = await ctx.read_resource("catalog://root")
collections = await ctx.read_resource("catalog://collections")
```

### Request Metadata
```python
# Access request identifiers for correlation
request_id = ctx.request_id
client_id = ctx.client_id
```

### State Management
```python
# Manage per-request scratch state (e.g., search cache)
ctx.set_state("last_search_params", search_params)
last_params = ctx.get_state("last_search_params")
```

### LLM Sampling (Advanced)
```python
# Optional: When a tool needs on-the-fly assistance
collection_advice = await ctx.sample(
    "Which STAC collection is best for vegetation monitoring?"
)
```

---

## 3. Prohibited Operations

Avoid the following to prevent `Context` from becoming a god object:

❌ **Don't persist state across requests**
```python
# BAD: Global state mutation
ctx.set_state("all_searches", global_search_list)
```

❌ **Don't embed business logic in Context**
```python
# BAD: Context-dependent decisions
if ctx.is_admin():  # Wrong approach
    return sensitive_data
```

❌ **Don't transport large datasets**
```python
# BAD: Large binary data in context
ctx.set_state("full_stac_items", huge_item_list)
```

❌ **Don't perform blocking I/O**
```python
# BAD: Blocking operations in context wrappers
def helper(ctx):
    time.sleep(10)  # Blocks event loop
```

---

## 4. Logging Patterns for STAC

### Log at the Boundary

Entry points announce start/end, key milestones, and recoverable errors:

```python
@mcp.tool()
async def search_items(
    collections: list[str],
    bbox: list[float] | None = None,
    datetime: str | None = None,
    limit: int = 10,
    ctx: Context | None = None
) -> dict:
    """Search STAC catalog for items."""
    if ctx:
        await ctx.info(f"[search_items] Starting search in {collections}")
    
    try:
        results = await stac_client.search(
            collections=collections,
            bbox=bbox,
            datetime=datetime,
            limit=limit
        )
        
        if ctx:
            await ctx.info(f"[search_items] Found {len(results)} items")
        
        return format_results(results)
        
    except Exception as e:
        if ctx:
            await ctx.error(f"[search_items] Search failed: {str(e)}")
        raise
```

### No Duplicate Logging

Shared helpers remain silent by default:

```python
# stac_mcp/tools/client.py
class STACClient:
    async def search(
        self,
        collections: list[str],
        bbox: list[float] | None = None,
        ctx: Context | None = None
    ):
        """Shared STAC search logic - silent by default."""
        # Only log if ctx is provided AND caller opts in
        if ctx:
            await ctx.debug(f"[STACClient] Executing search")
        
        # Core logic without logging
        return await self._execute_search(collections, bbox)
```

### Consistency with Prefixes

Prefix messages so log consumers can filter quickly:

```python
await ctx.info("[search_items] Starting search")
await ctx.info("[estimate_data_size] Processing 50 items")
await ctx.debug("[STACClient] Making API request")
await ctx.warning("[get_collection] Collection not found in cache")
```

### Signal Over Noise

Prefer progress updates over repetitive info messages:

```python
# GOOD: Progress updates in loops
for i, item in enumerate(items):
    if i % 10 == 0 and ctx:
        await ctx.report_progress(i, len(items), f"Processing item {i}/{len(items)}")
    process_item(item)

# BAD: Info message in tight loop
for item in items:
    await ctx.info(f"Processing {item.id}")  # Too noisy
```

---

## 5. Passing Context to STAC Helpers

When helpers need logging or progress reporting, pass `ctx` explicitly:

### Example: Size Estimation with Progress

```python
# Entry point (tool)
@mcp.tool()
async def estimate_data_size(
    collections: list[str],
    bbox: list[float] | None = None,
    limit: int = 50,
    ctx: Context | None = None
) -> dict:
    """Estimate data size with progress tracking."""
    if ctx:
        await ctx.info("[estimate_data_size] Starting")
    
    # Pass ctx to helper
    items = await search_items_helper(collections, bbox, limit, ctx=ctx)
    
    # Helper uses ctx for progress
    size_estimate = await calculate_size_with_progress(items, ctx=ctx)
    
    return {
        "estimated_bytes": size_estimate,
        "item_count": len(items)
    }

# Helper function
async def calculate_size_with_progress(
    items: list,
    ctx: Context | None = None
) -> int:
    """Calculate size with optional progress reporting."""
    total_size = 0
    
    for i, item in enumerate(items):
        if ctx and i % 10 == 0:
            await ctx.report_progress(i, len(items), "Calculating size...")
        
        total_size += get_item_size(item)
    
    return total_size
```

### Example: STAC Search with Logging

```python
# Entry point (tool)
@mcp.tool()
async def search_collections(
    query: str | None = None,
    ctx: Context | None = None
) -> dict:
    """Search STAC collections."""
    if ctx:
        await ctx.info(f"[search_collections] Query: {query}")
    
    # Call helper with ctx
    collections = await stac_client.get_collections(query=query, ctx=ctx)
    
    return format_collections(collections)

# Helper in STACClient
async def get_collections(
    self,
    query: str | None = None,
    ctx: Context | None = None
):
    """Get collections with optional logging."""
    if ctx:
        await ctx.debug(f"[STACClient] Fetching collections: {query}")
    
    # Core logic
    response = await self._http_get("/collections")
    return response.get("collections", [])
```

---

## 6. STAC-Specific Context Patterns

### Pattern 1: Multi-Step STAC Workflow

```python
@mcp.tool()
async def comprehensive_stac_search(
    data_type: str,
    region: str,
    time_period: str,
    ctx: Context | None = None
) -> dict:
    """Multi-step STAC search with context tracking."""
    
    # Step 1: Read collection info from resource
    if ctx:
        await ctx.info("[comprehensive_search] Step 1: Reading collections")
        collections_resource = await ctx.read_resource("catalog://collections")
    
    # Step 2: Select appropriate collection
    if ctx:
        await ctx.info("[comprehensive_search] Step 2: Selecting collection")
    selected_collection = choose_collection(data_type, collections_resource)
    
    # Step 3: Execute search with progress
    if ctx:
        await ctx.info(f"[comprehensive_search] Step 3: Searching {selected_collection}")
    items = await search_items(
        collections=[selected_collection],
        bbox=parse_region(region),
        datetime=parse_time_period(time_period),
        ctx=ctx
    )
    
    # Step 4: Validate results
    if ctx:
        await ctx.info(f"[comprehensive_search] Step 4: Validating {len(items)} items")
    
    return {"items": items, "collection": selected_collection}
```

### Pattern 2: Retry with Logging

```python
@mcp.tool()
async def resilient_stac_search(
    collections: list[str],
    bbox: list[float],
    ctx: Context | None = None
) -> dict:
    """STAC search with retry and logging."""
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            if ctx:
                await ctx.info(f"[resilient_search] Attempt {attempt + 1}/{max_retries}")
            
            results = await stac_client.search(
                collections=collections,
                bbox=bbox,
                ctx=ctx
            )
            
            if ctx:
                await ctx.info(f"[resilient_search] Success on attempt {attempt + 1}")
            
            return {"items": results}
            
        except Exception as e:
            if ctx:
                await ctx.warning(
                    f"[resilient_search] Attempt {attempt + 1} failed: {str(e)}"
                )
            
            if attempt == max_retries - 1:
                if ctx:
                    await ctx.error("[resilient_search] All attempts failed")
                raise
            
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Pattern 3: Size Estimation with Progress

```python
@mcp.tool()
async def estimate_data_size(
    collections: list[str],
    bbox: list[float] | None = None,
    limit: int = 50,
    ctx: Context | None = None
) -> dict:
    """Estimate size with detailed progress."""
    
    # Phase 1: Search
    if ctx:
        await ctx.info("[estimate_size] Phase 1/3: Searching for items")
    
    items = await search_items(collections, bbox, limit=limit, ctx=ctx)
    
    # Phase 2: Load metadata
    if ctx:
        await ctx.info(f"[estimate_size] Phase 2/3: Loading metadata for {len(items)} items")
    
    total_size = 0
    for i, item in enumerate(items):
        if ctx and i % 10 == 0:
            await ctx.report_progress(i, len(items), "Calculating size...")
        
        total_size += calculate_item_size(item)
    
    # Phase 3: Format results
    if ctx:
        await ctx.info("[estimate_size] Phase 3/3: Formatting results")
    
    return {
        "estimated_bytes": total_size,
        "item_count": len(items),
        "average_bytes_per_item": total_size // len(items) if items else 0
    }
```

---

## 7. Review Checklist

Before merging changes that use Context:

- [ ] Logging occurs only at entry points or deliberately opted-in helpers
- [ ] All `ctx.` usage appears in modules cleared for orchestration responsibilities
- [ ] Shared modules accept `ctx: Context | None` but do not require it
- [ ] No business logic or configuration lives inside context helper functions
- [ ] Progress updates used for long-running operations (>5 seconds)
- [ ] Error logging includes actionable information
- [ ] Log messages are prefixed with component name `[component]`
- [ ] No duplicate logging between entry points and helpers
- [ ] Context state used only for per-request scratch data
- [ ] No blocking I/O inside context operations

---

## 8. Migration Guide: Current → FastMCP

### Current State (v1.2.0)

```python
# Current: No context, direct execution
async def handle_search_items(arguments: dict):
    """Execute STAC search without context."""
    results = await stac_client.search(
        collections=arguments["collections"],
        bbox=arguments.get("bbox"),
        datetime=arguments.get("datetime")
    )
    return format_results(results)
```

### Future with FastMCP

```python
# Future: With Context support
@mcp.tool()
async def search_items(
    collections: list[str],
    bbox: list[float] | None = None,
    datetime: str | None = None,
    ctx: Context | None = None
) -> dict:
    """Search STAC catalog for items."""
    if ctx:
        await ctx.info(f"[search_items] Searching {collections}")
    
    results = await stac_client.search(
        collections=collections,
        bbox=bbox,
        datetime=datetime,
        ctx=ctx
    )
    
    if ctx:
        await ctx.info(f"[search_items] Found {len(results)} items")
    
    return format_results(results)
```

---

## 9. Examples by Tool Category

### STAC Search Tools

```python
@mcp.tool()
async def search_items(
    collections: list[str],
    bbox: list[float] | None = None,
    ctx: Context | None = None
) -> dict:
    if ctx:
        await ctx.info(f"[search_items] Searching {', '.join(collections)}")
    # Implementation...
```

### PySTAC CRUDL Tools

```python
@mcp.tool()
async def pystac_create_collection(
    collection_id: str,
    title: str,
    output_path: str,
    ctx: Context | None = None
) -> dict:
    if ctx:
        await ctx.info(f"[pystac_create_collection] Creating {collection_id}")
    
    collection = create_collection(collection_id, title)
    collection.save_object(output_path)
    
    if ctx:
        await ctx.info(f"[pystac_create_collection] Saved to {output_path}")
    
    return {"id": collection_id, "path": output_path}
```

### Data Analysis Tools

```python
@mcp.tool()
async def estimate_data_size(
    collections: list[str],
    limit: int = 50,
    ctx: Context | None = None
) -> dict:
    if ctx:
        await ctx.info("[estimate_data_size] Starting estimation")
    
    items = await search_items(collections, limit=limit, ctx=ctx)
    
    size = 0
    for i, item in enumerate(items):
        if ctx and i % 10 == 0:
            await ctx.report_progress(i, len(items))
        size += calculate_size(item)
    
    return {"estimated_bytes": size}
```

---

## 10. Environment Variable Integration

Context can access environment-based configuration:

```python
@mcp.tool()
async def configure_catalog(
    catalog_url: str | None = None,
    ctx: Context | None = None
) -> dict:
    """Configure STAC catalog with logging."""
    # Use env var if not provided
    url = catalog_url or os.getenv("STAC_CATALOG_URL")
    
    if ctx:
        await ctx.info(f"[configure_catalog] Using catalog: {url}")
    
    # Configure client
    stac_client.configure(url)
    
    if ctx:
        await ctx.info("[configure_catalog] Configuration complete")
    
    return {"catalog_url": url, "status": "configured"}
```

---

## Conclusion

This Context usage policy:

- Keeps MCP logs meaningful with boundary-based logging
- Maintains clean separation between control flow and domain logic
- Preserves the ability to reuse STAC shared modules outside MCP
- Enables progress tracking for long-running STAC operations
- Supports future FastMCP migration without major refactoring

By following these guidelines, STAC MCP will have consistent, helpful logging and orchestration when integrated with FastMCP.

---

## References

- **FastMCP Documentation**: [Context Guide](https://github.com/jlowin/fastmcp)
- **GUIDELINES.md**: Overall FastMCP usage in STAC MCP
- **Issue #69**: FastMCP integration
- **Issue #78**: FastMCP doc/architecture implementation

---

**Last Updated**: 2025-10-18  
**Related Docs**: [GUIDELINES.md](./GUIDELINES.md), [DECORATORS.md](./DECORATORS.md), [PROMPTS.md](./PROMPTS.md), [RESOURCES.md](./RESOURCES.md)
