"""Tests for execution fallback branches in tools.execution."""

import json
from typing import Any, Dict, List

import pytest
from fastmcp.client import Client

from stac_mcp.fast_server import app


@pytest.fixture
def test_app():
    """Return a clean app for each test."""
    original_tools = app._tool_manager._tools.copy()
    yield app
    app._tool_manager._tools = original_tools


@pytest.mark.asyncio
async def test_json_fallback_mode(test_app):
    """Test that text content is correctly wrapped in a JSON fallback response."""

    def dummy_tool_func(output_format: str = "text") -> List[Dict[str, Any]]:
        return [
            {"type": "text", "text": "Line1"},
            {"type": "text", "text": "Line2"},
        ]

    test_app.tool(name="dummy_tool")(dummy_tool_func)

    client = Client(test_app)
    async with client:
        result = await client.call_tool("dummy_tool", {"output_format": "json"})
    response_data = json.loads(result.content[0].text)
    assert response_data[0]["text"] == "Line1"
    assert response_data[1]["text"] == "Line2"


@pytest.mark.asyncio
async def test_dict_to_text_conversion(test_app):
    """Test that dictionary results are correctly serialized to text."""

    def dummy_dict_tool(output_format: str = "text") -> List[Dict[str, Any]]:
        return [{"a": 1, "b": 2}]

    test_app.tool(name="dict_tool")(dummy_dict_tool)

    client = Client(test_app)
    async with client:
        result = await client.call_tool("dict_tool", {"output_format": "text"})
    # The result from fastmcp for a list of dicts will be a single TextContent
    # block containing the JSON representation of the list.
    response_data = json.loads(result.content[0].text)
    assert response_data == [{"a": 1, "b": 2}]
