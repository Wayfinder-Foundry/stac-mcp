"""Tool to fetch STAC API root document (subset of fields)."""

from typing import Any

from mcp.types import TextContent

from stac_mcp.tools.client import STACClient


def handle_get_root(
    client: STACClient,
    arguments: dict[str, Any],
) -> list[TextContent] | dict[str, Any]:
    doc = client.get_root_document()
    if arguments.get("output_format") == "json":
        return {"type": "root", "root": doc}
    conforms = doc.get("conformsTo", []) or []
    result_text = "**STAC Root Document**\n\n"
    result_text += f"ID: {doc.get('id')}\n"
    if doc.get("title"):
        result_text += f"Title: {doc.get('title')}\n"
    if doc.get("description"):
        result_text += f"Description: {doc.get('description')}\n"
    result_text += f"Links: {len(doc.get('links', []))}\n"
    result_text += f"Conformance Classes: {len(conforms)}\n"
    preview = conforms[:5]
    for c in preview:
        result_text += f"  - {c}\n"
    if len(conforms) > len(preview):
        result_text += f"  ... and {len(conforms) - len(preview)} more\n"
    return [TextContent(type="text", text=result_text)]
