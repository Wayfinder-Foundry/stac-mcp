"""Test MCP protocol compliance."""

from unittest.mock import patch

import jsonschema
import pytest

from stac_mcp.server import handle_call_tool, handle_list_tools

# Constants to satisfy lint (avoid magic numbers)
EXPECTED_TOOL_COUNT = 9


@pytest.mark.asyncio
async def test_list_tools():
    """Test that list_tools returns proper MCP tool definitions."""
    tools = await handle_list_tools()

    assert len(tools) == EXPECTED_TOOL_COUNT

    tool_names = [tool.name for tool in tools]
    expected_tools = [
        "get_root",
        "get_conformance",
        "get_queryables",
        "get_aggregations",
        "search_collections",
        "get_collection",
        "search_items",
        "get_item",
        "estimate_data_size",
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
    with pytest.raises(ValueError, match="Unknown tool:"):
        await handle_call_tool("unknown_tool", {})


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
async def test_call_tool_search_collections_json(mock_stac_client):
    """Test calling search_collections tool with JSON output."""
    mock_stac_client.search_collections.return_value = [
        {
            "id": "test-collection",
            "title": "Test Collection",
            "description": "A test collection",
            "license": "MIT",
        },
    ]
    result = await handle_call_tool(
        "search_collections",
        {"limit": 1, "output_format": "json"},
    )
    assert isinstance(result, list)
    assert result[0].type == "text"
    # Ensure JSON envelope present
    assert (
        '"mode":"json"' in result[0].text or '"mode":"text_fallback"' in result[0].text
    )
    assert "test-collection" in result[0].text


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_call_tool_get_item_json(mock_stac_client):
    """Test calling get_item tool with JSON output."""
    mock_stac_client.get_item.return_value = {
        "id": "item-1",
        "collection": "test-collection",
        "geometry": None,
        "bbox": None,
        "datetime": None,
        "properties": {"eo:cloud_cover": 10},
        "assets": {},
    }
    result = await handle_call_tool(
        "get_item",
        {
            "collection_id": "test-collection",
            "item_id": "item-1",
            "output_format": "json",
        },
    )
    assert isinstance(result, list)
    assert result[0].type == "text"
    assert "item-1" in result[0].text
    assert '"mode":"json"' in result[0].text


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_call_tool_with_error(mock_stac_client):
    """Test calling a tool that raises an exception."""
    mock_stac_client.search_collections.side_effect = Exception("Network error")
    with pytest.raises(Exception, match="Network error"):
        await handle_call_tool("search_collections", {"limit": 1})


@pytest.mark.asyncio
async def test_tool_schemas_validation():
    """Test that all tool schemas are valid JSON Schema."""

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
async def test_estimate_data_size_tool_call():
    """Test estimate_data_size tool call with mocked odc.stac unavailable."""
    # Patch both availability flag and the stac_client method to raise directly
    err_msg = (
        "odc.stac is not available. Please install it to use data size estimation."
    )
    with (
        patch("stac_mcp.server.ODC_STAC_AVAILABLE", False),
        patch(
            "stac_mcp.server.stac_client.estimate_data_size",
            side_effect=RuntimeError(err_msg),
        ),
    ):
        with pytest.raises(RuntimeError) as exc:
            await handle_call_tool(
                "estimate_data_size",
                {
                    "collections": ["test-collection"],
                    "bbox": [-122.5, 37.7, -122.3, 37.8],
                    "limit": 10,
                },
            )
        assert "odc.stac is not available" in str(exc.value)


# ---------------- New Capability Tool Tests ----------------- #


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_call_tool_get_root_json(mock_stac_client):
    mock_stac_client.get_root_document.return_value = {
        "id": "test-root",
        "title": "Test Root",
        "description": "Root doc",
        "links": [],
        "conformsTo": ["core"],
    }
    result = await handle_call_tool("get_root", {"output_format": "json"})
    assert result[0].type == "text"
    assert "test-root" in result[0].text
    assert '"mode":"json"' in result[0].text


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_call_tool_get_conformance_check(mock_stac_client):
    mock_stac_client.get_conformance.return_value = {
        "conformsTo": ["a", "b"],
        "checks": {"a": True, "c": False},
    }
    result = await handle_call_tool(
        "get_conformance",
        {"check": ["a", "c"], "output_format": "json"},
    )
    assert '"checks"' in result[0].text
    assert '"c":false' in result[0].text or '"c": false' in result[0].text


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_call_tool_get_queryables_text(mock_stac_client):
    mock_stac_client.get_queryables.return_value = {
        "queryables": {"eo:cloud_cover": {"type": "number"}},
        "collection_id": None,
    }
    result = await handle_call_tool("get_queryables", {})
    assert result[0].type == "text"
    assert "Queryables" in result[0].text
    assert "eo:cloud_cover" in result[0].text


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_call_tool_get_aggregations_unsupported(mock_stac_client):
    mock_stac_client.get_aggregations.return_value = {
        "supported": False,
        "aggregations": {},
        "message": "Aggregations unsupported (404)",
        "parameters": {"collections": ["c"]},
    }
    result = await handle_call_tool(
        "get_aggregations",
        {"collections": ["c"], "output_format": "json"},
    )
    assert (
        '"supported":false' in result[0].text or '"supported": false' in result[0].text
    )
    assert "Aggregations unsupported" in result[0].text
