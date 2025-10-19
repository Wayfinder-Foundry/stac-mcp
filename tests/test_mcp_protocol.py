"""Test MCP protocol compliance."""

import json
from typing import Any, Literal

import pytest
from fastmcp import Client

from stac_mcp.fast_server import app


@pytest.fixture
def test_app():
    """Return a clean app for each test."""
    original_tools = app._tool_manager._tools.copy()
    yield app
    app._tool_manager._tools = original_tools


@pytest.mark.asyncio
async def test_list_tools():
    """Test that list_tools returns proper MCP tool definitions."""
    client = Client(app)
    async with client:
        tools = await client.list_tools()

        # The number of tools is now dynamic, so we just check that it's positive
        assert len(tools) > 0

        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "get_root",
            "get_conformance",
            "search_collections",
            "get_collection",
            "search_items",
        ]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

        # Check that each tool has proper schema
        for tool in tools:
            assert tool.name
            assert tool.description
            assert tool.inputSchema
            assert "type" in tool.inputSchema
            assert tool.inputSchema["type"] == "object"
            assert "properties" in tool.inputSchema


@pytest.mark.asyncio
async def test_call_tool_unknown():
    """Test calling an unknown tool returns an error."""
    client = Client(app)
    async with client:
        with pytest.raises(Exception, match="Unknown tool:"):
            await client.call_tool("unknown_tool", {})


@pytest.mark.asyncio
async def test_call_tool_search_collections(test_app):
    """Test calling search_collections tool."""

    def dummy_search_collections(
        output_format: Literal["text", "json"] = "text",
        limit: int = 10,
        catalog_url: str | None = None,
    ) -> list[dict[str, Any]]:
        return [
            {
                "id": "test-collection",
                "title": "Test Collection",
                "description": "A test collection",
                "license": "MIT",
            }
        ]

    test_app.tool(name="search_collections")(dummy_search_collections)

    client = Client(test_app)
    async with client:
        result = await client.call_tool("search_collections", {"limit": 1})
        assert isinstance(result.content, list)
        assert len(result.content) > 0
        response_data = json.loads(result.content[0].text)
        assert "Test Collection" in response_data[0]["title"]
        assert "test-collection" in response_data[0]["id"]
