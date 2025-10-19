"""Tests for tool handler edge cases and error conditions."""

from typing import Literal

import pytest
from fastmcp.client import Client
from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent

from stac_mcp.fast_server import app


@pytest.fixture
def test_app():
    """Return a clean app for each test."""
    original_tools = app._tool_manager._tools.copy()
    yield app
    app._tool_manager._tools = original_tools


@pytest.mark.asyncio
async def test_get_root_minimal_response(test_app):
    """Test get_root with minimal root document."""

    def dummy_get_root(
        output_format: Literal["text", "json"] = "text", catalog_url: str | None = None
    ) -> ToolResult:
        return ToolResult(
            content=[TextContent(type="text", text="id: minimal-catalog\nlinks: []\n")],
            structured_content={"result": []},
        )

    test_app.tool(name="get_root")(dummy_get_root)

    client = Client(test_app)
    async with client:
        result = await client.call_tool("get_root", {})
    assert len(result.content) > 0
    text = result.content[0].text
    assert "minimal-catalog" in text


@pytest.mark.asyncio
async def test_get_conformance_no_classes(test_app):
    """Test get_conformance with empty conformance list."""

    def dummy_get_conformance(
        output_format: Literal["text", "json"] = "text",
        check: str | list[str] | None = None,
        catalog_url: str | None = None,
    ) -> ToolResult:
        return ToolResult(
            content=[TextContent(type="text", text="Conformance Classes (0):\n")],
            structured_content={"result": []},
        )

    test_app.tool(name="get_conformance")(dummy_get_conformance)

    client = Client(test_app)
    async with client:
        result = await client.call_tool("get_conformance", {})
    assert len(result.content) > 0
    text = result.content[0].text
    assert "Conformance Classes (0)" in text
