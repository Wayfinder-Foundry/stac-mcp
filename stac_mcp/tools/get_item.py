"""Tool to get a STAC Item by collection ID and item ID."""

from typing import Any

from mcp.types import TextContent

from stac_mcp.tools.client import STACClient


def handle_get_item(
    client: STACClient,
    arguments: dict[str, Any],
) -> list[TextContent] | dict[str, Any]:
    collection_id = arguments["collection_id"]
    item_id = arguments["item_id"]
    item = client.get_item(collection_id, item_id)
    if arguments.get("output_format") == "json":
        return {"type": "item", "item": item}
    result_text = f"**Item: {item['id']}**\n\n"
    result_text += f"Collection: `{item['collection']}`\n"
    if item["datetime"]:
        result_text += f"Date: {item['datetime']}\n"
    if item["bbox"]:
        b = item["bbox"]
        result_text += f"BBox: [{b[0]:.2f}, {b[1]:.2f}, {b[2]:.2f}, {b[3]:.2f}]\n"
    result_text += "\n**Properties:**\n"
    for key, value in item["properties"].items():
        if isinstance(value, (str, int, float, bool)):
            result_text += f"  {key}: {value}\n"
    result_text += f"\n**Assets ({len(item['assets'])}):**\n"
    for asset_key, asset in item["assets"].items():
        result_text += f"  - **{asset_key}**: {asset.get('title', asset_key)}\n"
        result_text += f"    Type: {asset.get('type', 'unknown')}\n"
        if "href" in asset:
            result_text += f"    URL: {asset['href']}\n"
    return [TextContent(type="text", text=result_text)]
