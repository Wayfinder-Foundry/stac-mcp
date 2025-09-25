"""Tool to request aggregations for a STAC item search (Aggregations Extension)."""

from typing import Any

from mcp.types import TextContent

from stac_mcp.tools.client import STACClient


def handle_get_aggregations(
    client: STACClient,
    arguments: dict[str, Any],
) -> list[TextContent] | dict[str, Any]:
    collections = arguments.get("collections")
    bbox = arguments.get("bbox")
    dt = arguments.get("datetime")
    query = arguments.get("query")
    fields = arguments.get("fields")
    operations = arguments.get("operations")
    limit = arguments.get("limit", 0)
    data = client.get_aggregations(
        collections=collections,
        bbox=bbox,
        datetime=dt,
        query=query,
        fields=fields,
        operations=operations,
        limit=limit,
    )
    if arguments.get("output_format") == "json":
        return {"type": "aggregations", **data}
    result_text = "**Aggregations**\n\n"
    result_text += f"Supported: {'Yes' if data['supported'] else 'No'}\n"
    if data["aggregations"]:
        for name, agg in data["aggregations"].items():
            result_text += f"  - {name}: {agg}\n"
    result_text += f"\n{data['message']}\n"
    return [TextContent(type="text", text=result_text)]
