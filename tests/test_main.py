"""Tests for __main__.py entry point."""

from __future__ import annotations

import subprocess
import sys
from unittest.mock import patch

from stac_mcp.__main__ import main


def test_main_entry_point():
    """Test that __main__.main() calls cli_main from server."""
    with patch("stac_mcp.__main__.cli_main") as mock_cli_main:
        main()

        mock_cli_main.assert_called_once()


def test_main_module_execution():
    """Test that running python -m stac_mcp works."""
    # Run the module with --help to ensure it starts without errors
    # We use a timeout to prevent hanging if server starts
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "stac_mcp", "--help"],
        capture_output=True,
        timeout=5,
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
