"""Tool to get and describe a STAC collection by its ID."""

from typing import Any

from mcp.types import TextContent

from stac_mcp.tools.client import STACClient


def handle_get_collection(
    client: STACClient,
    arguments: dict[str, Any],
) -> list[TextContent] | dict[str, Any]:
    collection_id = arguments["collection_id"]
    collection = client.get_collection(collection_id)
    if arguments.get("output_format") == "json":
        return {"type": "collection", "collection": collection}
    result_text = f"**Collection: {collection['title']}**\n\n"
    result_text += f"ID: `{collection['id']}`\n"
    result_text += f"Description: {collection['description']}\n"
    result_text += f"License: {collection['license']}\n\n"
    if collection["extent"]:
        extent = collection["extent"]
        if "spatial" in extent and extent["spatial"].get("bbox"):
            bbox = extent["spatial"]["bbox"][0]
            result_text += (
                "Spatial Extent: "
                f"[{bbox[0]:.2f}, {bbox[1]:.2f}, {bbox[2]:.2f}, {bbox[3]:.2f}]\n"
            )
        if "temporal" in extent and extent["temporal"].get("interval"):
            interval = extent["temporal"]["interval"][0]
            result_text += (
                f"Temporal Extent: {interval[0]} to {interval[1] or 'present'}\n"
            )
    if collection["providers"]:
        result_text += f"\nProviders: {len(collection['providers'])}\n"
        for provider in collection["providers"]:
            result_text += (
                f"  - {provider.get('name', 'Unknown')} ({provider.get('roles', [])})\n"
            )
    return [TextContent(type="text", text=result_text)]
