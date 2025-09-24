"""Tool execution logic separated from server module.

Each handler returns a list of TextContent objects to remain compatible
with existing tests. Later enhancements (JSON mode, error abstraction)
can hook here centrally.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any, NoReturn

from mcp.types import TextContent

from stac_mcp.tools.client import STACClient, stac_client
from stac_mcp.tools.estimate_data_size import handle_estimate_data_size
from stac_mcp.tools.get_collection import handle_get_collection
from stac_mcp.tools.get_item import handle_get_item
from stac_mcp.tools.search_collections import handle_search_collections
from stac_mcp.tools.search_items import handle_search_items

logger = logging.getLogger(__name__)


Handler = Callable[[STACClient, dict[str, Any]], list[TextContent]]


_TOOL_HANDLERS: dict[str, Handler] = {
    "search_collections": handle_search_collections,
    "get_collection": handle_get_collection,
    "search_items": handle_search_items,
    "get_item": handle_get_item,
    "estimate_data_size": handle_estimate_data_size,
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

    try:
        catalog_url = arguments.get("catalog_url")
        client = STACClient(catalog_url) if catalog_url else stac_client
        handler = _TOOL_HANDLERS.get(tool_name)
        if handler is None:
            _raise_unknown_tool(tool_name)
        return handler(client, arguments)
    except Exception:  # pragma: no cover - error path
        logger.exception("Error in tool call %s", tool_name)
        return [
            TextContent(
                f"An error occurred while executing tool '{tool_name}'. Please check the logs for details."
            )
        ]
