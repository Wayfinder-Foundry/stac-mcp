"""Tool to fetch STAC API conformance classes and optionally check specific ones."""

from typing import Any

from mcp.types import TextContent

from stac_mcp.tools.client import STACClient


def handle_get_conformance(
    client: STACClient,
    arguments: dict[str, Any],
) -> list[TextContent] | dict[str, Any]:
    check = arguments.get("check")
    data = client.get_conformance(check=check)
    if arguments.get("output_format") == "json":
        return {"type": "conformance", **data}
    conforms = data["conformsTo"]
    result_text = f"**Conformance Classes ({len(conforms)})**\n\n"
    for c in conforms[:20]:  # limit static preview
        result_text += f"  - {c}\n"
    if len(conforms) > 20:
        result_text += f"  ... and {len(conforms) - 20} more\n"
    if data.get("checks"):
        result_text += "\n**Checks:**\n"
        for uri, ok in data["checks"].items():
            status = "OK" if ok else "MISSING"
            result_text += f"  - {uri}: {status}\n"
    return [TextContent(type="text", text=result_text)]
