"""Tool to fetch STAC API (or collection) queryables."""

from typing import Any

from mcp.types import TextContent

from stac_mcp.tools.client import STACClient

PREVIEW_LIMIT = 25


def handle_get_queryables(
    client: STACClient,
    arguments: dict[str, Any],
) -> list[TextContent] | dict[str, Any]:
    collection_id = arguments.get("collection_id")
    data = client.get_queryables(collection_id=collection_id)
    if arguments.get("output_format") == "json":
        return {"type": "queryables", **data}
    props = data.get("queryables", {})
    result_text = "**Queryables**\n\n"
    if not props:
        result_text += data.get("message", "No queryables available") + "\n"
        return [TextContent(type="text", text=result_text)]
    result_text += f"Collection: {collection_id or 'GLOBAL'}\n"
    result_text += f"Count: {len(props)}\n\n"
    for name, spec in list(props.items())[:PREVIEW_LIMIT]:
        typ = spec.get("type", "unknown") if isinstance(spec, dict) else "unknown"
        result_text += f"  - {name}: {typ}\n"
    if len(props) > PREVIEW_LIMIT:
        result_text += f"  ... and {len(props) - PREVIEW_LIMIT} more\n"
    return [TextContent(type="text", text=result_text)]
