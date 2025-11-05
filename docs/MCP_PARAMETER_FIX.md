

# MCP Parameter Serialization Issue Fix

## Problem Description

When Claude (or other MCP clients) call STAC MCP tools with array or object parameters, the parameters were being serialized as JSON strings instead of native types. For example:

```xml
<parameter name="bbox">[-123.27, 49.15, -123.0, 49.35]</parameter>
```

Was being received as the string `"[-123.27, 49.15, -123.0, 49.35]"` instead of a Python list `[-123.27, 49.15, -123.0, 49.35]`.

This caused FastMCP's schema validation to fail with:
```
Input validation error: '[-123.27, 49.15, -123.0, 49.35]' is not valid under any of the given schemas
```

## Root Cause

The MCP protocol (specifically Claude's implementation) serializes function parameters in XML format. When arrays and objects are passed as parameters, they can be serialized as JSON strings. FastMCP's auto-generated schema from Python type hints (e.g., `list[float]`) doesn't accept strings, causing validation to fail before the function is even called.

## Solution

We implemented a two-part fix:

### 1. Accept String Parameters in Function Signatures

Modified the type hints in `server.py` to accept both native types AND strings:

```python
# Before
async def search_items(
    collections: list[str],
    bbox: list[float] | None = None,
    query: dict[str, Any] | None = None,
    ...
)

# After
async def search_items(
    collections: list[str] | str,  # Accept string or list
    bbox: list[float] | str | None = None,  # Accept string or list
    query: dict[str, Any] | str | None = None,  # Accept string or dict
    ...
)
```

This allows FastMCP's schema validation to accept both formats.

### 2. Parameter Preprocessing

Created `stac_mcp/tools/params.py` with a `preprocess_parameters()` function that:
- Detects string parameters that should be arrays/objects
- Parses JSON strings and converts them to native Python types
- Preserves native types that don't need conversion
- Handles errors gracefully (preserves invalid input for downstream error handling)

The preprocessor is called in each tool function before passing arguments to `execution.execute_tool()`:

```python
async def search_items(...):
    arguments = preprocess_parameters({
        "collections": collections,
        "bbox": bbox,
        ...
    })
    return await execution.execute_tool("search_items", arguments=arguments, ...)
```

## Testing

Added comprehensive tests in `tests/test_params.py` to verify:
- String-to-list conversion for bbox and collections
- String-to-dict conversion for aoi_geojson and query
- Preservation of native types
- Handling of None values
- Error handling for invalid JSON

## Affected Tools

The following tools were updated to handle string parameters:
- `search_items`: collections, bbox, query
- `estimate_data_size`: collections, bbox, query, aoi_geojson

## Backward Compatibility

This change is fully backward compatible:
- Existing clients passing native types continue to work
- New clients passing JSON strings now work too
- The parameter preprocessing is transparent to downstream handlers

## Usage Example

Now both of these work:

```python
# Native types (existing behavior)
await search_items(
    collections=["sentinel-2-l2a"],
    bbox=[-123.27, 49.15, -123.0, 49.35],
    datetime="2025-10-23/2025-10-30"
)

# JSON strings (new behavior for MCP clients)
await search_items(
    collections='["sentinel-2-l2a"]',
    bbox="[-123.27, 49.15, -123.0, 49.35]",
    datetime="2025-10-23/2025-10-30"
)
```

## Files Changed

1. `stac_mcp/tools/params.py` (new)
   - Parameter preprocessing utilities

2. `stac_mcp/server.py` (modified)
   - Updated type hints for `search_items` and `estimate_data_size`
   - Added calls to `preprocess_parameters()`

3. `tests/test_params.py` (new)
   - Comprehensive tests for parameter preprocessing

## Future Considerations

If other MCP clients exhibit similar behavior with different parameters, the preprocessor can be easily extended to handle additional parameter types. The pattern is:

1. Add string alternative to type hint
2. Add conversion logic to `preprocess_parameters()`
3. Add tests for the new parameter

This approach provides a clean separation between protocol-level concerns (MCP serialization) and application logic (STAC operations).
