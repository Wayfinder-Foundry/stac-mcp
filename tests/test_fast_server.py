import asyncio
import json
from typing import Any, Literal

import pytest
from fastmcp import Client

from stac_mcp import fast_server
from stac_mcp.fast_server import app
from tests import ARG_LIMIT_FIVE, ARG_LIMIT_TWO


async def call_tool(tool, *a, **kw):
    # fastmcp's @app.tool wraps the function in a tool object. The original
    # coroutine is often available on an attribute; try common names first.
    candidates = [
        getattr(tool, "func", None),
        getattr(tool, "__wrapped__", None),
        getattr(tool, "fn", None),
        getattr(tool, "function", None),
    ]
    for fn in candidates:
        if fn and callable(fn):
            coro = fn(*a, **kw)
            if asyncio.iscoroutine(coro):
                return await coro
            return coro

    # As a fallback, scan attributes for a callable defined in this module
    for name in dir(tool):
        try:
            attr = getattr(tool, name)
        except AttributeError:
            continue
        if (
            callable(attr)
            and getattr(attr, "__module__", None) == "stac_mcp.fast_server"
        ):
            coro = attr(*a, **kw)
            if asyncio.iscoroutine(coro):
                return await coro
            return coro
    err_msg = "Could not find wrapped function on tool object"
    raise TypeError(err_msg)


def test_tool_introspection():
    # Ensure the tool object exposes something we can use in tests;
    # print dir for debugging
    t = fast_server.get_root
    attrs = set(dir(t))
    # assert some likely properties exist so we fail clearly if not
    assert "name" in attrs or "__class__" in attrs


class DummyCall:
    def __init__(self):
        self.calls = []

    async def __call__(self, name, arguments=None, catalog_url=None, headers=None):
        self.calls.append(
            {
                "name": name,
                "arguments": arguments,
                "catalog_url": catalog_url,
                "headers": headers,
            }
        )
        # return a simple predictable payload
        return [
            {
                "tool": name,
                "args": arguments or {},
                "catalog_url": catalog_url,
                "headers": headers,
            }
        ]


@pytest.mark.asyncio
async def test_basic_tools_call_execute_tool(monkeypatch):
    dummy = DummyCall()
    monkeypatch.setattr(fast_server.execution, "execute_tool", dummy)

    res = await call_tool(fast_server.get_root)
    assert res == [
        {"tool": "get_root", "args": {}, "catalog_url": None, "headers": None}
    ]
    assert dummy.calls[-1]["name"] == "get_root"

    res = await call_tool(fast_server.get_conformance)
    assert dummy.calls[-1]["name"] == "get_conformance"

    # search_collections with explicit limit and catalog_url
    res = await call_tool(
        fast_server.search_collections, limit=5, catalog_url="https://example.com"
    )
    assert dummy.calls[-1]["name"] == "search_collections"
    assert dummy.calls[-1]["arguments"]["limit"] == ARG_LIMIT_FIVE
    assert dummy.calls[-1]["catalog_url"] == "https://example.com"


@pytest.mark.asyncio
async def test_get_and_search_items_variants(monkeypatch):
    dummy = DummyCall()
    monkeypatch.setattr(fast_server.execution, "execute_tool", dummy)

    # get_item default output_format
    res = await call_tool(fast_server.get_item, "col-1", "item-1")
    assert dummy.calls[-1]["name"] == "get_item"
    assert dummy.calls[-1]["arguments"]["collection_id"] == "col-1"
    assert dummy.calls[-1]["arguments"]["item_id"] == "item-1"
    assert dummy.calls[-1]["arguments"]["output_format"] == "text"

    # search_items with multiple params
    res = await call_tool(  # noqa: F841
        fast_server.search_items,
        collections=["c1", "c2"],
        bbox=[0.0, 0.0, 1.0, 1.0],
        datetime=None,
        limit=2,
    )
    assert dummy.calls[-1]["name"] == "search_items"
    assert dummy.calls[-1]["arguments"]["collections"] == ["c1", "c2"]
    assert dummy.calls[-1]["arguments"]["limit"] == ARG_LIMIT_TWO


@pytest.fixture
def test_app():
    """Return a clean app for each test."""
    original_tools = app._tool_manager._tools.copy()  # noqa: SLF001
    yield app
    app._tool_manager._tools = original_tools  # noqa: SLF001


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
        output_format: Literal["text", "json"] = "text",  # noqa: ARG001
        catalog_url: str | None = None,  # noqa: ARG001
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


@pytest.mark.asyncio
async def test_call_search_items_tool(test_app):
    """Test calling the search_items tool with arguments."""

    def dummy_search_items(
        collections: list[str],
        bbox: list[float] | None = None,  # noqa: ARG001
        datetime: str | None = None,  # noqa: ARG001
        limit: int | None = 10,  # noqa: ARG001
        query: dict[str, Any] | None = None,  # noqa: ARG001
        output_format: str | None = "text",  # noqa: ARG001
        catalog_url: str | None = None,  # noqa: ARG001
    ) -> list[dict[str, Any]]:
        assert collections == ["test-collection"]
        return [{"type": "text", "text": "mocked search response"}]

    test_app.tool(name="search_items")(dummy_search_items)

    client = Client(test_app)
    async with client:
        result = await client.call_tool(
            "search_items", {"collections": ["test-collection"]}
        )
        response_data = json.loads(result.content[0].text)
        assert response_data == [{"type": "text", "text": "mocked search response"}]


@pytest.mark.asyncio
async def test_call_estimate_data_size_tool(test_app):
    """Test calling the estimate_data_size tool with arguments."""

    def dummy_estimate_data_size(
        collections: list[str],
        bbox: list[float] | None = None,  # noqa: ARG001
        datetime: str | None = None,  # noqa: ARG001
        query: dict[str, Any] | None = None,  # noqa: ARG001
        aoi_geojson: dict[str, Any] | None = None,  # noqa: ARG001
        limit: int | None = 10,  # noqa: ARG001
        force_metadata_only: bool | None = False,  # noqa: ARG001
        output_format: str | None = "text",  # noqa: ARG001
        catalog_url: str | None = None,  # noqa: ARG001
    ) -> list[dict[str, Any]]:
        assert collections == ["test-collection"]
        return [{"type": "text", "text": "mocked estimate response"}]

    test_app.tool(name="estimate_data_size")(dummy_estimate_data_size)

    client = Client(test_app)
    async with client:
        result = await client.call_tool(
            "estimate_data_size", {"collections": ["test-collection"]}
        )
        response_data = json.loads(result.content[0].text)
        assert response_data == [{"type": "text", "text": "mocked estimate response"}]


@pytest.mark.asyncio
async def test_call_get_item_tool(test_app):
    """Test calling the get_item tool with arguments."""

    def dummy_get_item(
        collection_id: str,
        item_id: str,
        output_format: str | None = "text",  # noqa: ARG001
        catalog_url: str | None = None,  # noqa: ARG001
    ) -> list[dict[str, Any]]:
        assert collection_id == "test-collection"
        assert item_id == "test-item"
        return [{"type": "text", "text": "mocked get_item response"}]

    test_app.tool(name="get_item")(dummy_get_item)

    client = Client(test_app)
    async with client:
        result = await client.call_tool(
            "get_item", {"collection_id": "test-collection", "item_id": "test-item"}
        )
        response_data = json.loads(result.content[0].text)
        assert response_data == [{"type": "text", "text": "mocked get_item response"}]


@pytest.mark.asyncio
async def test_call_get_root_tool(test_app):
    """Test calling the get_root tool."""

    def dummy_get_root() -> list[dict[str, Any]]:
        return [{"type": "text", "text": "mocked get_root response"}]

    test_app.tool(name="get_root")(dummy_get_root)

    client = Client(test_app)
    async with client:
        result = await client.call_tool("get_root")
        response_data = json.loads(result.content[0].text)
        assert response_data == [{"type": "text", "text": "mocked get_root response"}]


@pytest.mark.asyncio
async def test_call_get_conformance_tool(test_app):
    """Test calling the get_conformance tool."""

    def dummy_get_conformance() -> list[dict[str, Any]]:
        return [{"type": "text", "text": "mocked get_conformance response"}]

    test_app.tool(name="get_conformance")(dummy_get_conformance)

    client = Client(test_app)
    async with client:
        result = await client.call_tool("get_conformance")
        response_data = json.loads(result.content[0].text)
        assert response_data == [
            {"type": "text", "text": "mocked get_conformance response"}
        ]


@pytest.mark.asyncio
async def test_call_search_collections_tool(test_app):
    """Test calling the search_collections tool."""

    def dummy_search_collections(
        limit: int | None = 10,  # noqa: ARG001
        catalog_url: str | None = None,  # noqa: ARG001
    ) -> list[dict[str, Any]]:
        return [{"type": "text", "text": "mocked search_collections response"}]

    test_app.tool(name="search_collections")(dummy_search_collections)

    client = Client(test_app)
    async with client:
        result = await client.call_tool("search_collections")
        response_data = json.loads(result.content[0].text)
        assert response_data == [
            {"type": "text", "text": "mocked search_collections response"}
        ]

        result = await client.call_tool(
            "search_collections", {"catalog_url": "https://example.com"}
        )
        response_data = json.loads(result.content[0].text)
        assert response_data == [
            {"type": "text", "text": "mocked search_collections response"}
        ]

        result = await client.call_tool("search_collections", {"limit": 5})
        response_data = json.loads(result.content[0].text)
        assert response_data == [
            {"type": "text", "text": "mocked search_collections response"}
        ]
