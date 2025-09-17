"""Test MCP protocol compliance."""

from unittest.mock import patch

import pytest

from stac_mcp.server import handle_call_tool, handle_list_tools


@pytest.mark.asyncio
async def test_list_tools():
    """Test that list_tools returns proper MCP tool definitions."""
    tools = await handle_list_tools()

    assert len(tools) == 6

    tool_names = [tool.name for tool in tools]
    expected_tools = [
        "search_collections",
        "get_collection",
        "search_items",
        "get_item",
        "code-catalog-connect",
        "code-catalog-search",
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
    try:
        await handle_call_tool("unknown_tool", {})
        assert False, "Expected ValueError for unknown tool"
    except ValueError as e:
        assert "Unknown tool: unknown_tool" in str(e)


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

    result = await handle_call_tool("search_collections", {"limit": 1})

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"
    assert "Test Collection" in result[0].text
    assert "test-collection" in result[0].text


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_call_tool_with_error(mock_stac_client):
    """Test calling a tool that raises an exception."""
    mock_stac_client.search_collections.side_effect = Exception("Network error")

    try:
        await handle_call_tool("search_collections", {"limit": 1})
        assert False, "Expected exception to be raised"
    except Exception as e:
        assert "Network error" in str(e)


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


@pytest.mark.asyncio
async def test_call_tool_code_catalog_connect():
    """Test calling code-catalog-connect tool."""
    result = await handle_call_tool("code-catalog-connect", {})

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"
    assert "Python Code Snippet - STAC Catalog Connection" in result[0].text
    assert "import pystac_client" in result[0].text
    assert "catalog = pystac_client.Client.open" in result[0].text
    assert "planetarycomputer.microsoft.com" in result[0].text


@pytest.mark.asyncio
async def test_call_tool_code_catalog_connect_custom():
    """Test calling code-catalog-connect tool with custom parameters."""
    result = await handle_call_tool(
        "code-catalog-connect",
        {
            "catalog_url": "https://example.com/stac",
            "variable_name": "my_catalog",
        },
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"
    assert "my_catalog = pystac_client.Client.open" in result[0].text
    assert "https://example.com/stac" in result[0].text


@pytest.mark.asyncio
async def test_call_tool_code_catalog_search():
    """Test calling code-catalog-search tool."""
    result = await handle_call_tool(
        "code-catalog-search",
        {
            "collections": ["landsat-c2l2-sr"],
            "bbox": [-122.5, 37.7, -122.3, 37.8],
            "datetime": "2023-01-01/2023-12-31",
        },
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"
    assert "Python Code Snippet - StackSTAC Query Operation" in result[0].text
    assert "import stackstac" in result[0].text
    assert "import pystac_client" in result[0].text
    assert 'collections=["landsat-c2l2-sr"]' in result[0].text
    assert "bbox=[-122.5, 37.7, -122.3, 37.8]" in result[0].text
    assert 'datetime="2023-01-01/2023-12-31"' in result[0].text
    assert "stackstac.stack" in result[0].text


@pytest.mark.asyncio
async def test_call_tool_code_catalog_search_minimal():
    """Test calling code-catalog-search tool with minimal parameters."""
    result = await handle_call_tool(
        "code-catalog-search",
        {
            "collections": ["sentinel-2-l2a"],
        },
    )

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].type == "text"
    assert 'collections=["sentinel-2-l2a"]' in result[0].text
    assert "limit=10" in result[0].text
