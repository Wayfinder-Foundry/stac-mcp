"""Entry point for running the STAC MCP server as ``python -m stac_mcp``."""

from __future__ import annotations

from .server import cli_main


def main() -> None:
    """Launch the STAC MCP server CLI."""

    cli_main()


if __name__ == "__main__":  # pragma: no cover - exercised via python -m
    main()
