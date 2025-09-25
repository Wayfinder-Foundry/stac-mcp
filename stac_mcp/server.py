"""Main MCP Server implementation for STAC requests.

This module now delegates tool definitions and execution to the
``stac_mcp.tools`` package (see ADR 0009+). The previous monolithic
implementation has been split for clarity and maintainability.
Tests maintain backward compatibility by re-exporting the original
symbols (``STACClient`` and ``stac_client``) and keeping handler
function names stable.
"""

import asyncio
import logging

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool

from stac_mcp.tools import definitions, execution
from stac_mcp.tools.client import STACClient, stac_client

# Backwards compatibility exports expected by tests (monolithic server refactor)
try:  # pragma: no cover - optional dependency
    from pystac_client import Client  # type: ignore
except Exception:  # pragma: no cover - fallback for environments without dependency
    Client = None  # type: ignore

# The odc.stac availability flag used by tests that patch server.ODC_STAC_AVAILABLE
try:  # pragma: no cover - import guard
    import odc.stac  # type: ignore  # noqa: F401

    ODC_STAC_AVAILABLE = True
except Exception:  # pragma: no cover - absence is acceptable
    ODC_STAC_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("stac-mcp")

# Re-export legacy attribute names so patch("stac_mcp.server.stac_client") works
__all__ = [
    "ODC_STAC_AVAILABLE",
    "Client",
    "STACClient",
    "handle_call_tool",
    "handle_list_tools",
    "stac_client",
]


@server.list_tools()
async def handle_list_tools() -> list[Tool]:  # pragma: no cover - thin wrapper
    """List available STAC tools (delegated)."""
    return definitions.get_tool_definitions()


@server.call_tool()
async def handle_call_tool(tool_name: str, arguments: dict):  # pragma: no cover
    """Delegate tool execution to the tools.execution module."""
    return await execution.execute_tool(tool_name, arguments)


async def main():
    """Main entry point for the STAC MCP server."""
    # Run the server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="stac-mcp",
                server_version="0.4.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def cli_main():
    """CLI entry point for the STAC MCP server."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
