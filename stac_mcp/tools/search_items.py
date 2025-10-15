"""Tool to search for items in a STAC catalog."""

from typing import Any

from mcp.types import TextContent

from stac_mcp.tools.client import STACClient

BBOX_MIN_COORDS = 4


def handle_search_items(
    client: STACClient,
    arguments: dict[str, Any],
) -> list[TextContent] | dict[str, Any]:
    collections = arguments.get("collections")
    bbox = arguments.get("bbox")
    dt = arguments.get("datetime")
    query = arguments.get("query")
    limit = arguments.get("limit", 10)
    items = client.search_items(
        collections=collections,
        bbox=bbox,
        datetime=dt,
        query=query,
        limit=limit,
    )
    if arguments.get("output_format") == "json":
        return {"type": "item_list", "count": len(items), "items": items}
    result_text = f"Found {len(items)} items:\n\n"
    for item in items:
        item_id = item.get("id", "unknown")
        collection_id = item.get("collection", "unknown")
        result_text += f"**{item_id}** (Collection: `{collection_id}`)\n"
        dt_value = item.get("datetime")
        if dt_value:
            result_text += f"  Date: {dt_value}\n"
        bbox = item.get("bbox")
        if isinstance(bbox, list | tuple) and len(bbox) >= BBOX_MIN_COORDS:
            result_text += (
                "  BBox: "
                f"[{bbox[0]:.2f}, {bbox[1]:.2f}, {bbox[2]:.2f}, {bbox[3]:.2f}]\n"
            )
        assets = item.get("assets") or {}
        asset_count = len(assets) if hasattr(assets, "__len__") else 0
        result_text += f"  Assets: {asset_count}\n\n"
    return [TextContent(type="text", text=result_text)]
