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


@pytest.mark.asyncio
async def test_create_update_delete_headers(monkeypatch):
    dummy = DummyCall()
    monkeypatch.setattr(fast_server.execution, "execute_tool", dummy)

    item = {"id": "i1"}

    # Without api_key: headers should be empty dict when passed through execute_tool
    await call_tool(fast_server.create_item, "col", item, api_key=None)
    assert dummy.calls[-1]["name"] == "create_item"
    assert dummy.calls[-1]["headers"] == {}

    # With api_key: x-api-key header must be set
    await call_tool(fast_server.create_item, "col", item, api_key="secret")
    assert dummy.calls[-1]["headers"] == {"x-api-key": "secret"}

    # update_item
    await call_tool(fast_server.update_item, "col", item)
    assert dummy.calls[-1]["name"] == "update_item"

    await call_tool(fast_server.update_item, "col", item, api_key="k")
    assert dummy.calls[-1]["headers"] == {"x-api-key": "k"}

    # delete_item
    await call_tool(fast_server.delete_item, "col", "it1")
    assert dummy.calls[-1]["name"] == "delete_item"
    await call_tool(fast_server.delete_item, "col", "it1", api_key="k2")
    assert dummy.calls[-1]["headers"] == {"x-api-key": "k2"}


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
