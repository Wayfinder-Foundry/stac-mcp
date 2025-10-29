"""Tool to fetch STAC API root document (subset of fields)."""

from typing import Any

from mcp.types import TextContent
from pystac_client.exceptions import APIError

from stac_mcp.tools.client import STACClient


def handle_get_root(
    client: STACClient,
    arguments: dict[str, Any],
) -> list[TextContent] | dict[str, Any]:
    # Be robust: the execution layer might pass either our STACClient wrapper
    # or the underlying pystac_client.Client. Use isinstance to prefer our
    # wrapper's helper; otherwise attempt to use to_dict() on whatever was
    # provided. Never raise from this handler — return a helpful text
    # fallback on error so the tool returns a friendly message.
    try:
        # Prefer calling get_root_document() if the client provides it (covers
        # STACClient wrapper, FakeClientRoot, MagicMock, and similar objects).
        if hasattr(client, "get_root_document") and callable(client.get_root_document):
            try:
                doc = client.get_root_document()
            except (AttributeError, APIError):
                # If that fails with a known client error, fall through and
                # try to_dict() based fallbacks.
                doc = None
        else:
            doc = None

        if not doc:
            # Try a couple of to_dict() fallbacks.
            # Prefer client.to_dict(), then client.client.to_dict().
            raw = {}
            try:
                if hasattr(client, "to_dict") and callable(client.to_dict):
                    raw = client.to_dict() or {}
                elif hasattr(client, "client") and hasattr(client.client, "to_dict"):
                    raw = client.client.to_dict() or {}
            except (AttributeError, APIError, RuntimeError, TypeError, ValueError):
                # to_dict() may be missing or fail; treat as empty mapping.
                raw = {}
            doc = {
                "id": raw.get("id"),
                "title": raw.get("title"),
                "description": raw.get("description"),
                "links": raw.get("links", []),
                "conformsTo": raw.get("conformsTo", raw.get("conforms_to", [])),
            }
    except (AttributeError, APIError, RuntimeError, TypeError, ValueError) as exc:
        # Return a minimal root-like doc along with an explanatory message.
        doc = {
            "id": None,
            "title": None,
            "description": None,
            "links": [],
            "conformsTo": [],
            "_error": str(exc),
        }
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
