"""Tool to get a STAC Item by collection ID and item ID."""

from typing import Any

from mcp.types import TextContent

from stac_mcp.tools.client import STACClient

BBOX_MIN_COORDS = 4


def handle_get_item(
    client: STACClient,
    arguments: dict[str, Any],
) -> list[TextContent] | dict[str, Any]:
    collection_id = arguments["collection_id"]
    item_id = arguments["item_id"]
    item = client.get_item(collection_id, item_id)
    if item is None:
        return {"type": "item", "item": None}
    if arguments.get("output_format") == "json":
        return {"type": "item", "item": item}
    item_id_value = item.get("id", item_id)
    result_text = f"**Item: {item_id_value}**\n\n"
    collection_value = item.get("collection", collection_id)
    result_text += f"Collection: `{collection_value}`\n"
    dt_value = item.get("datetime")
    if dt_value:
        result_text += f"Date: {dt_value}\n"
    bbox = item.get("bbox")
    if isinstance(bbox, list | tuple) and len(bbox) >= BBOX_MIN_COORDS:
        result_text += (
            f"BBox: [{bbox[0]:.2f}, {bbox[1]:.2f}, {bbox[2]:.2f}, {bbox[3]:.2f}]\n"
        )
    result_text += "\n**Properties:**\n"
    properties = item.get("properties") or {}
    for key, value in properties.items():
        if isinstance(value, str | int | float | bool):
            result_text += f"  {key}: {value}\n"
    assets = item.get("assets") or {}
    asset_count = len(assets) if hasattr(assets, "__len__") else 0
    result_text += f"\n**Assets ({asset_count}):**\n"
    asset_entries = assets.items() if isinstance(assets, dict) else []
    for asset_key, asset in asset_entries:
        title = asset.get("title", asset_key) if isinstance(asset, dict) else asset_key
        result_text += f"  - **{asset_key}**: {title}\n"
        asset_type = (
            asset.get("type", "unknown") if isinstance(asset, dict) else "unknown"
        )
        result_text += f"    Type: {asset_type}\n"
        if isinstance(asset, dict) and "href" in asset:
            result_text += f"    URL: {asset['href']}\n"
    return [TextContent(type="text", text=result_text)]
