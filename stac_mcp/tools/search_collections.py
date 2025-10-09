"""Tool to search for STAC collections in a STAC catalog."""

from typing import Any

from mcp.types import TextContent

from stac_mcp.tools import MAX_DESC_PREVIEW
from stac_mcp.tools.client import STACClient


def handle_search_collections(
    client: STACClient,
    arguments: dict[str, Any],
) -> list[TextContent] | dict[str, Any]:
    limit = arguments.get("limit", 10)
    collections = client.search_collections(limit=limit)
    if arguments.get("output_format") == "json":
        return {
            "type": "collection_list",
            "count": len(collections),
            "collections": collections,
        }
    result_text = f"Found {len(collections)} collections:\n\n"
    for collection in collections:
        title = collection.get("title") or collection.get("id", "Untitled collection")
        identifier = collection.get("id", "unknown")
        result_text += f"**{title}** (`{identifier}`)\n"
        description = collection.get("description")
        if description:
            desc = str(description)
            truncated = desc[:MAX_DESC_PREVIEW]
            ellipsis = "..." if len(desc) > MAX_DESC_PREVIEW else ""
            result_text += f"  {truncated}{ellipsis}\n"
        license_value = collection.get("license", "unspecified")
        result_text += f"  License: {license_value}\n\n"
    return [TextContent(type="text", text=result_text)]
