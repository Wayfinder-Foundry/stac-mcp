"""Tool execution logic separated from server module.

Each handler returns a list of TextContent objects to remain compatible
with existing tests. Later enhancements (JSON mode, error abstraction)
can hook here centrally.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any, NoReturn

from mcp.types import TextContent

from stac_mcp.tools.client import STACClient
from stac_mcp.tools.estimate_data_size import handle_estimate_data_size
from stac_mcp.tools.get_aggregations import handle_get_aggregations
from stac_mcp.tools.get_collection import handle_get_collection
from stac_mcp.tools.get_conformance import handle_get_conformance
from stac_mcp.tools.get_item import handle_get_item
from stac_mcp.tools.get_queryables import handle_get_queryables
from stac_mcp.tools.get_root import handle_get_root
from stac_mcp.tools.search_collections import handle_search_collections
from stac_mcp.tools.search_items import handle_search_items

logger = logging.getLogger(__name__)


Handler = Callable[
    [STACClient, dict[str, Any]],
    list[TextContent] | dict[str, Any],
]


_TOOL_HANDLERS: dict[str, Handler] = {
    "search_collections": handle_search_collections,
    "get_collection": handle_get_collection,
    "search_items": handle_search_items,
    "get_item": handle_get_item,
    "estimate_data_size": handle_estimate_data_size,
    "get_root": handle_get_root,
    "get_conformance": handle_get_conformance,
    "get_queryables": handle_get_queryables,
    "get_aggregations": handle_get_aggregations,
}


async def execute_tool(tool_name: str, arguments: dict[str, Any]):
    """Dispatch tool execution based on name using registered handlers.

    Maintains backward-compatible output format (list[TextContent]).
    """

    def _raise_unknown_tool(name: str) -> NoReturn:
        """Raise a standardized error for unknown tool names."""
        _tools = list(_TOOL_HANDLERS.keys())
        msg = f"Unknown tool: {name}. Available tools: {_tools}"
        raise ValueError(msg)

    from stac_mcp import server as _server  # local import so test patching works

    catalog_url = arguments.get("catalog_url")
    client = STACClient(catalog_url) if catalog_url else _server.stac_client
    handler = _TOOL_HANDLERS.get(tool_name)
    if handler is None:
        _raise_unknown_tool(tool_name)
    # Let handler exceptions propagate so tests can assert on them
    output_format = arguments.get("output_format", "text")
    raw_result = handler(client, arguments)
    # Backward compatibility: existing handlers return list[TextContent].
    # New JSON mode: handlers may return dict when output_format == 'json'.
    if output_format == "json":
        if isinstance(raw_result, list):  # handler didn't implement JSON branch
            # Wrap textual output in a JSON envelope for consistency
            payload = {"mode": "text_fallback", "content": [c.text for c in raw_result]}
        else:
            payload = {"mode": "json", "data": raw_result}
        return [
            TextContent(type="text", text=json.dumps(payload, separators=(",", ":"))),
        ]
    # Default text path: ensure list[TextContent]
    if isinstance(raw_result, list):
        return raw_result
    # If a dict was returned but text requested, convert to pretty text summary
    try:
        summary = json.dumps(raw_result, indent=2)
    except Exception:  # pragma: no cover - edge serialization
        summary = str(raw_result)
    return [TextContent(type="text", text=summary)]
