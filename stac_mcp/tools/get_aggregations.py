"""Tool to get STAC aggregations."""

from typing import Any

from mcp.types import TextContent

from stac_mcp.tools.client import STACClient


def handle_get_aggregations(
    client: STACClient,
    arguments: dict[str, Any],
) -> list[TextContent] | dict[str, Any]:
    data = client.get_aggregations(
        collections=arguments.get("collections"),
        ids=arguments.get("ids"),
        bbox=arguments.get("bbox"),
        intersects=arguments.get("intersects"),
        datetime=arguments.get("datetime"),
        query=arguments.get("query"),
        filter_lang=arguments.get("filter_lang"),
        filter_expr=arguments.get("filter"),
        fields=arguments.get("fields"),
        sortby=arguments.get("sortby"),
        limit=arguments.get("limit", 0),
    )
    if arguments.get("output_format") == "json":
        return {"type": "aggregations", **data}

    result_text = "**Aggregations**\n\n"
    result_text += f"Supported: {'Yes' if data.get('supported') else 'No'}\n"
    if data.get("aggregations"):
        result_text += "Aggregations:\n"
        for agg in data["aggregations"]:
            name = agg.get("name", "unnamed")
            value = agg.get("value", {})
            result_text += f"  - {name}:\n"
            if isinstance(value, dict):
                for k, v in value.items():
                    result_text += f"    - {k}: {v}\n"
            else:
                result_text += f"    - value: {value}\n"
    if data.get("meta"):
        result_text += f"\nMeta:\n  - Matched: {data['meta'].get('matched')}\n"
    result_text += f"\n{data.get('message', '')}\n"
    return [TextContent(type="text", text=result_text)]
