"""Tool to get and describe a STAC collection by its ID."""

from typing import Any

from mcp.types import TextContent

from stac_mcp.tools.client import STACClient

BBOX_MIN_COORDS = 4


def handle_get_collection(
    client: STACClient,
    arguments: dict[str, Any],
) -> list[TextContent] | dict[str, Any]:
    collection_id = arguments["collection_id"]
    collection = client.get_collection(collection_id)
    if collection is None:
        return {"type": "collection", "collection": None}
    if arguments.get("output_format") == "json":
        return {"type": "collection", "collection": collection}
    title = collection.get("title", collection.get("id", collection_id))
    result_text = f"**Collection: {title}**\n\n"
    identifier = collection.get("id", collection_id)
    result_text += f"ID: `{identifier}`\n"
    description = collection.get("description", "No description available")
    result_text += f"Description: {description}\n"
    license_value = collection.get("license", "unspecified")
    result_text += f"License: {license_value}\n\n"
    extent = collection.get("extent") or {}
    if extent:
        spatial = extent.get("spatial") or {}
        bbox_list = spatial.get("bbox") or []
        if bbox_list:
            bbox = bbox_list[0]
            if isinstance(bbox, list | tuple) and len(bbox) >= BBOX_MIN_COORDS:
                result_text += (
                    "Spatial Extent: "
                    f"[{bbox[0]:.2f}, {bbox[1]:.2f}, {bbox[2]:.2f}, {bbox[3]:.2f}]\n"
                )
        temporal = extent.get("temporal") or {}
        interval_list = temporal.get("interval") or []
        if interval_list:
            interval = interval_list[0]
            start = interval[0] if len(interval) > 0 else "unknown"
            end = interval[1] if len(interval) > 1 else "present"
            result_text += f"Temporal Extent: {start} to {end or 'present'}\n"
    providers = collection.get("providers") or []
    if providers:
        result_text += f"\nProviders: {len(providers)}\n"
        for provider in providers:
            name = provider.get("name", "Unknown")
            roles = provider.get("roles", [])
            result_text += f"  - {name} ({roles})\n"
    return [TextContent(type="text", text=result_text)]
