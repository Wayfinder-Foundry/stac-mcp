"""Tool to search for items in a STAC catalog."""

from typing import Any

from mcp.types import TextContent

from stac_mcp.tools.client import STACClient


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
        result_text += f"**{item['id']}** (Collection: `{item['collection']}`)\n"
        if item["datetime"]:
            result_text += f"  Date: {item['datetime']}\n"
        if item["bbox"]:
            b = item["bbox"]
            result_text += f"  BBox: [{b[0]:.2f}, {b[1]:.2f}, {b[2]:.2f}, {b[3]:.2f}]\n"
        result_text += f"  Assets: {len(item['assets'])}\n\n"
    return [TextContent(type="text", text=result_text)]
