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
    """Test that the server lists its registered tools."""
    client = Client(app)
    async with client:
        tools = await client.list_tools()
        assert isinstance(tools, list)
        assert len(tools) > 0
        tool_names = [t.name for t in tools]
        assert "get_root" in tool_names
        assert "search_items" in tool_names


@pytest.mark.asyncio
async def test_call_tool(test_app):
    """Test calling a tool with arguments."""

    # Define a dummy function with the correct signature to replace the real tool
    def dummy_get_collection(
        collection_id: str,
        output_format: Literal["text", "json"] = "text",
        catalog_url: str | None = None,
    ) -> list[dict[str, Any]]:
        # We can add assertions here to check the arguments
        assert collection_id == "test-collection"
        return [{"type": "text", "text": "mocked response"}]

    # Register the dummy function as the 'get_collection' tool
    test_app.tool(name="get_collection")(dummy_get_collection)

    client = Client(test_app)
    async with client:
        result = await client.call_tool(
            "get_collection", {"collection_id": "test-collection"}
        )
        # The result from the tool function is JSON serialized into the content block
        response_data = json.loads(result.content[0].text)
        assert response_data == [{"type": "text", "text": "mocked response"}]
