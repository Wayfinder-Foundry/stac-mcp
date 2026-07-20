"""Entry point for running the STAC MCP server as ``python -m stac_mcp``."""

import os

from stac_mcp.server import app


def main() -> None:
    """Launch the STAC MCP server CLI.

    Defaults to stdio, matching every previously documented invocation.
    Set STAC_MCP_TRANSPORT=http (or streamable-http/sse) to serve over HTTP
    instead, configurable via STAC_MCP_HOST/STAC_MCP_PORT.
    """
    transport = os.environ.get("STAC_MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        app.run()
    else:
        app.run(
            transport=transport,
            host=os.environ.get("STAC_MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("STAC_MCP_PORT", "8000")),
        )


if __name__ == "__main__":
    main()
