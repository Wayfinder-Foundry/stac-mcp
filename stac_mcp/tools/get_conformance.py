"""Tool to get STAC conformance classes."""

from typing import Any

from mcp.types import TextContent

from stac_mcp.tools.client import STACClient


def handle_get_conformance(
    client: STACClient,
    arguments: dict[str, Any],
) -> list[TextContent] | dict[str, Any]:
    check = arguments.get("check")
    data = client.get_conformance(check)
    if arguments.get("output_format") == "json":
        return {"type": "conformance", **data}
    conforms_to = data.get("conformsTo", [])
    num_classes = len(conforms_to)
    result_text = f"**Conformance Classes ({num_classes})**\n\n"
    if conforms_to:
        result_text += "conformsTo:\n"
        for class_uri in conforms_to:
            result_text += f"- `{class_uri}`\n"
    checks = data.get("checks")
    if checks:
        result_text += "\n**Checks**\n"
        for class_uri, satisfied in checks.items():
            result_text += (
                f"- `{class_uri}`: {'Satisfied' if satisfied else 'Not Satisfied'}\n"
            )
    return [TextContent(type="text", text=result_text)]
