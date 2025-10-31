"""Entry point for running the STAC MCP server as ``python -m stac_mcp``."""

from stac_mcp.server import app


def main() -> None:
    """Launch the STAC MCP server CLI."""
    app.run()


if __name__ == "__main__":
    main()
