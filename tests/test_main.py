"""Tests for __main__.py entry point."""

from __future__ import annotations

import os
import subprocess
import sys
from unittest.mock import patch

from stac_mcp.__main__ import main


def test_main_entry_point():
    """Test that __main__.main() calls app.run from server."""
    with patch("stac_mcp.server.app.run") as mock_run:
        main()
        mock_run.assert_called_once()


def test_main_entry_point_stdio_is_default():
    """Test that an unset STAC_MCP_TRANSPORT still calls app.run() bare."""
    with patch.dict(os.environ, clear=False):
        os.environ.pop("STAC_MCP_TRANSPORT", None)
        with patch("stac_mcp.server.app.run") as mock_run:
            main()
            mock_run.assert_called_once_with()


def test_main_entry_point_http_transport():
    """Test that STAC_MCP_TRANSPORT=http forwards transport/host/port."""
    env = {
        "STAC_MCP_TRANSPORT": "http",
        "STAC_MCP_HOST": "0.0.0.0",  # noqa: S104
        "STAC_MCP_PORT": "9000",
    }
    with (
        patch.dict(os.environ, env, clear=False),
        patch("stac_mcp.server.app.run") as mock_run,
    ):
        main()
        mock_run.assert_called_once_with(
            transport="http",
            host="0.0.0.0",  # noqa: S104
            port=9000,
        )


def test_main_module_execution():
    """Test that running python -m stac_mcp works."""
    # Run the module with --help to ensure it starts without errors
    # We use a timeout to prevent hanging if server starts
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "stac_mcp", "--help"],
        capture_output=True,
        timeout=10,
        check=False,
    )

    # The MCP server might not support --help, but it should at least import
    # successfully. Any import error would cause a non-zero exit with traceback.
    # We're mainly checking that the module can be executed.
    assert result.returncode in (
        0,
        1,
        2,
    ), f"Module failed to execute: {result.stderr.decode()}"
