"""Estimate data size for a STAC query."""

from typing import Any

from mcp.types import TextContent

from stac_mcp.tools import MAX_ASSET_LIST
from stac_mcp.tools.client import STACClient

try:  # pragma: no cover - import guard
    import odc.stac  # type: ignore

    ODC_STAC_AVAILABLE = True
except ImportError:  # pragma: no cover - conditional path
    ODC_STAC_AVAILABLE = False


def handle_estimate_data_size(
    client: STACClient,
    arguments: dict[str, Any],
) -> list[TextContent] | dict[str, Any]:
    collections = arguments.get("collections")
    bbox = arguments.get("bbox")
    dt = arguments.get("datetime")
    query = arguments.get("query")
    aoi_geojson = arguments.get("aoi_geojson")
    limit = arguments.get("limit", 100)
    size_estimate = client.estimate_data_size(
        collections=collections,
        bbox=bbox,
        datetime=dt,
        query=query,
        aoi_geojson=aoi_geojson,
        limit=limit,
    )
    if arguments.get("output_format") == "json":
        return {"type": "data_size_estimate", "estimate": size_estimate}
    result_text = "**Data Size Estimation**\n\n"
    result_text += f"Items analyzed: {size_estimate['item_count']}\n"
    result_text += (
        f"Estimated size: {size_estimate['estimated_size_mb']:.2f} MB "
        f"({size_estimate['estimated_size_gb']:.4f} GB)\n"
    )
    result_text += f"Raw bytes: {size_estimate['estimated_size_bytes']:,}\n\n"
    result_text += "**Query Parameters:**\n"
    result_text += "Collections: "
    collections_list = (
        ", ".join(size_estimate["collections"])
        if size_estimate["collections"]
        else "All"
    )
    result_text += f"{collections_list}\n"
    if size_estimate["bbox_used"]:
        b = size_estimate["bbox_used"]
        result_text += (
            "Bounding box: " f"[{b[0]:.4f}, {b[1]:.4f}, {b[2]:.4f}, {b[3]:.4f}]\n"
        )
    if size_estimate["temporal_extent"]:
        result_text += f"Time range: {size_estimate['temporal_extent']}\n"
    if size_estimate["clipped_to_aoi"]:
        result_text += "Clipped to AOI: Yes (minimized to smallest area)\n"
    if "data_variables" in size_estimate:
        result_text += "\n**Data Variables:**\n"
        for var_info in size_estimate["data_variables"]:
            result_text += (
                f"  - {var_info['variable']}: {var_info['size_mb']} MB, "
                f"shape {var_info['shape']}, dtype {var_info['dtype']}\n"
            )
    if size_estimate.get("spatial_dims"):
        spatial = size_estimate["spatial_dims"]
        result_text += "\n**Spatial Dimensions:**\n"
        result_text += f"  X (longitude): {spatial.get('x', 0)} pixels\n"
        result_text += f"  Y (latitude): {spatial.get('y', 0)} pixels\n"
    if "assets_analyzed" in size_estimate:
        result_text += "\n**Assets Analyzed (fallback estimation):**\n"
        for asset_info in size_estimate["assets_analyzed"][:MAX_ASSET_LIST]:
            result_text += (
                f"  - {asset_info['asset']}: {asset_info['estimated_size_mb']} MB "
                f"({asset_info['media_type']})\n"
            )
        remaining = len(size_estimate["assets_analyzed"]) - MAX_ASSET_LIST
        if remaining > 0:
            result_text += f"  ... and {remaining} more assets\n"
    result_text += f"\n{size_estimate['message']}\n"
    return [TextContent(type="text", text=result_text)]
