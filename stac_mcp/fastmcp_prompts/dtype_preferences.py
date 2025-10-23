"""Prompt guidance for agents about choosing compact data types when estimating sizes.

This module defines a prompt that can be registered with the FastMCP server
to provide guidance on selecting appropriate data types (dtypes) for estimating
data sizes in STAC assets. The prompt advises on preferring smaller integer
dtypes when applicable, rather than defaulting to float32/float64, to yield
more accurate storage estimates. The module is import-safe in environments
without `fastmcp` installed. If `fastmcp.mcp.prompt` is available at import time,
the function will be registered as a prompt; otherwise it remains a plain callable
returning a helpful guidance string (which is sufficient for including in tool outputs).
"""

def dtype_size_preferences() -> str:
    """Return guidance string about dtype selection for data-size estimation."""
    return (
        "When estimating storage for raster arrays, prefer the smallest practical "
        "integer dtype rather than defaulting to float32/float64 if data semantics "
        "allow it. Common heuristics:\n"
        "  - If pixel values are counts, categories, or indices (no fractional "
        "values), use unsigned integers (uint8, uint16) sized to range.\n"
        "  - If values are continuous but stored as scaled integers (e.g., reflectance "
        "scaled by 10000), prefer the integer backing dtype and include the scale factor.\n"
        "  - If nodata is represented by a sentinel (e.g., 0 or -9999), use integer dtype; "
        "only use NaN-based nodata when missingness is inherent and fractional values exist.\n"
        "  - If odc.stac encodes an original dtype in asset encoding, prefer that dtype; "
        "otherwise, consider downcasting floats to float32 or to an integer with a scale when safe.\n"
        "These rules reduce estimated bytes and better reflect storage when data are "
        "stored as integers or compressed chunked formats (zarr). Always validate by "
        "inspecting asset metadata when available."
    )
