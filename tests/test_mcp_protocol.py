"""Test MCP protocol compliance."""

from unittest.mock import patch

import pytest
from mcp.types import CallToolRequest, CallToolRequestParams

from stac_mcp.server import handle_call_tool, handle_list_tools


@pytest.mark.asyncio
async def test_list_tools():
    """Test that list_tools returns proper MCP tool definitions."""
    tools = await handle_list_tools()

    assert len(tools) == 4

    tool_names = [tool.name for tool in tools]
    expected_tools = [
        "search_collections",
        "get_collection",
        "search_items",
        "get_item",
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
    request = CallToolRequest(
        params=CallToolRequestParams(name="unknown_tool", arguments={}),
    )

    result = await handle_call_tool(request)

    assert result.isError is True
    assert "Unknown tool" in result.content[0].text


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_call_tool_search_collections(mock_stac_client):
    """Test calling search_collections tool."""
    # Mock the search_collections method
    mock_stac_client.search_collections.return_value = [
        {
            "id": "test-collection",
            "title": "Test Collection",
            "description": "A test collection",
            "license": "MIT",
        },
    ]

    request = CallToolRequest(
        params=CallToolRequestParams(name="search_collections", arguments={"limit": 1}),
    )

    result = await handle_call_tool(request)

    assert result.isError is False
    assert "Test Collection" in result.content[0].text
    assert "test-collection" in result.content[0].text


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_call_tool_with_error(mock_stac_client):
    """Test calling a tool that raises an exception."""
    mock_stac_client.search_collections.side_effect = Exception("Network error")

    request = CallToolRequest(
        params=CallToolRequestParams(name="search_collections", arguments={"limit": 1}),
    )

    result = await handle_call_tool(request)

    assert result.isError is True
    assert "Network error" in result.content[0].text


@pytest.mark.asyncio
async def test_tool_schemas_validation():
    """Test that all tool schemas are valid JSON Schema."""
    import jsonschema

    tools = await handle_list_tools()

    for tool in tools:
        # This should not raise an exception
        jsonschema.Draft7Validator.check_schema(tool.inputSchema)

        # Check required fields are properly defined
        if "required" in tool.inputSchema:
            required_fields = tool.inputSchema["required"]
            properties = tool.inputSchema["properties"]

            for field in required_fields:
                assert field in properties
