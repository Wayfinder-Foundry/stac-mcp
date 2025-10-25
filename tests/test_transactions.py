"""Tests for transaction tool handlers."""

from unittest.mock import MagicMock

import pytest
from fastmcp.client import Client
from fastmcp.tools.tool import ToolResult
from mcp.types import TextContent

from stac_mcp.fast_server import app
from stac_mcp.tools.transactions import (
    handle_create_collection,
    handle_create_item,
    handle_delete_collection,
    handle_delete_item,
    handle_update_collection,
    handle_update_item,
)


@pytest.fixture
def test_app():
    """Return a clean app for each test."""
    original_tools = app._tool_manager._tools.copy()  # noqa: SLF001
    yield app
    app._tool_manager._tools = original_tools  # noqa: SLF001


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
        collection_id: str,  # noqa: ARG001
        item: dict,  # noqa: ARG001
        api_key: str | None = None,  # noqa: ARG001
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
        collection_id: str,  # noqa: ARG001
        item: dict,  # noqa: ARG001
        api_key: str | None = None,  # noqa: ARG001
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
        collection_id: str,  # noqa: ARG001
        item_id: str,  # noqa: ARG001
        api_key: str | None = None,  # noqa: ARG001
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
        collection: dict,  # noqa: ARG001
        api_key: str | None = None,  # noqa: ARG001
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
        collection: dict,  # noqa: ARG001
        api_key: str | None = None,  # noqa: ARG001
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
        collection_id: str,  # noqa: ARG001
        api_key: str | None = None,  # noqa: ARG001
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


@pytest.fixture
def mock_stac_client():
    """Return a mock STACClient."""
    return MagicMock()


def test_handle_create_item_handler(mock_stac_client):
    """Tests the handle_create_item function."""
    collection_id = "test-collection"
    item = {"id": "test-item"}
    handle_create_item(mock_stac_client, {"collection_id": collection_id, "item": item})
    mock_stac_client.create_item.assert_called_once_with(collection_id, item)


def test_handle_update_item_handler(mock_stac_client):
    """Tests the handle_update_item function."""
    item = {"id": "test-item", "collection": "test-collection"}
    handle_update_item(mock_stac_client, {"item": item})
    mock_stac_client.update_item.assert_called_once_with(item)


def test_handle_delete_item_handler(mock_stac_client):
    """Tests the handle_delete_item function."""
    collection_id = "test-collection"
    item_id = "test-item"
    handle_delete_item(
        mock_stac_client, {"collection_id": collection_id, "item_id": item_id}
    )
    mock_stac_client.delete_item.assert_called_once_with(collection_id, item_id)


def test_handle_create_collection_handler(mock_stac_client):
    """Tests the handle_create_collection function."""
    collection = {"id": "test-collection"}
    handle_create_collection(mock_stac_client, {"collection": collection})
    mock_stac_client.create_collection.assert_called_once_with(collection)


def test_handle_update_collection_handler(mock_stac_client):
    """Tests the handle_update_collection function."""
    collection = {"id": "test-collection"}
    handle_update_collection(mock_stac_client, {"collection": collection})
    mock_stac_client.update_collection.assert_called_once_with(collection)


def test_handle_delete_collection_handler(mock_stac_client):
    """Tests the handle_delete_collection function."""
    collection_id = "test-collection"
    handle_delete_collection(mock_stac_client, {"collection_id": collection_id})
    mock_stac_client.delete_collection.assert_called_once_with(collection_id)
