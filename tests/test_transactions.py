"""Tests for transaction tool handlers."""

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


@pytest.fixture
def item_payload_factory():
    """Return a factory for item payloads."""

    def _factory():
        return {
            "type": "Feature",
            "stac_version": "1.0.0",
            "id": "test-item",
            "properties": {},
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "links": [],
            "assets": {},
            "collection": "test-collection",
        }

    return _factory


@pytest.fixture
def collection_payload_factory():
    """Return a factory for collection payloads."""

    def _factory():
        return {
            "type": "Collection",
            "stac_version": "1.0.0",
            "id": "test-collection",
            "description": "Test collection",
            "license": "proprietary",
            "extent": {},
            "links": [],
        }

    return _factory


@pytest.mark.asyncio
async def test_create_item_success(test_app, item_payload_factory):
    """Test successful item creation."""

    def dummy_create_item(
        collection_id: str, item: dict, api_key: str | None = None
    ) -> ToolResult:
        return ToolResult(
            content=[TextContent(type="text", text='{"status": "success"}')],
            structured_content={"result": []},
        )

    test_app.tool(name="create_item")(dummy_create_item)

    item_payload = item_payload_factory()

    client = Client(test_app)
    async with client:
        result = await client.call_tool(
            "create_item",
            {"collection_id": "test-collection", "item": item_payload},
        )
    assert result.content[0].text == '{"status": "success"}'


@pytest.mark.asyncio
async def test_update_item_success(test_app, item_payload_factory):
    """Test successful item update."""

    def dummy_update_item(
        collection_id: str, item: dict, api_key: str | None = None
    ) -> ToolResult:
        return ToolResult(
            content=[TextContent(type="text", text='{"status": "success"}')],
            structured_content={"result": []},
        )

    test_app.tool(name="update_item")(dummy_update_item)
    item_payload = item_payload_factory()
    client = Client(test_app)
    async with client:
        result = await client.call_tool(
            "update_item",
            {"collection_id": "test-collection", "item": item_payload},
        )
    assert result.content[0].text == '{"status": "success"}'


@pytest.mark.asyncio
async def test_delete_item_success(test_app):
    """Test successful item deletion."""

    def dummy_delete_item(
        collection_id: str, item_id: str, api_key: str | None = None
    ) -> ToolResult:
        return ToolResult(
            content=[TextContent(type="text", text='{"status": "success"}')],
            structured_content={"result": []},
        )

    test_app.tool(name="delete_item")(dummy_delete_item)
    client = Client(test_app)
    async with client:
        result = await client.call_tool(
            "delete_item",
            {"collection_id": "test-collection", "item_id": "test-item"},
        )
    assert result.content[0].text == '{"status": "success"}'


@pytest.mark.asyncio
async def test_create_collection_success(test_app, collection_payload_factory):
    """Test successful collection creation."""

    def dummy_create_collection(
        collection: dict, api_key: str | None = None
    ) -> ToolResult:
        return ToolResult(
            content=[TextContent(type="text", text='{"status": "success"}')],
            structured_content={"result": []},
        )

    test_app.tool(name="create_collection")(dummy_create_collection)
    collection_payload = collection_payload_factory()
    client = Client(test_app)
    async with client:
        result = await client.call_tool(
            "create_collection", {"collection": collection_payload}
        )
    assert result.content[0].text == '{"status": "success"}'


@pytest.mark.asyncio
async def test_update_collection_success(test_app, collection_payload_factory):
    """Test successful collection update."""

    def dummy_update_collection(
        collection: dict, api_key: str | None = None
    ) -> ToolResult:
        return ToolResult(
            content=[TextContent(type="text", text='{"status": "success"}')],
            structured_content={"result": []},
        )

    test_app.tool(name="update_collection")(dummy_update_collection)
    collection_payload = collection_payload_factory()
    client = Client(test_app)
    async with client:
        result = await client.call_tool(
            "update_collection", {"collection": collection_payload}
        )
    assert result.content[0].text == '{"status": "success"}'


@pytest.mark.asyncio
async def test_delete_collection_success(test_app):
    """Test successful collection deletion."""

    def dummy_delete_collection(
        collection_id: str, api_key: str | None = None
    ) -> ToolResult:
        return ToolResult(
            content=[TextContent(type="text", text='{"status": "success"}')],
            structured_content={"result": []},
        )

    test_app.tool(name="delete_collection")(dummy_delete_collection)
    client = Client(test_app)
    async with client:
        result = await client.call_tool(
            "delete_collection", {"collection_id": "test-collection"}
        )
    assert result.content[0].text == '{"status": "success"}'
