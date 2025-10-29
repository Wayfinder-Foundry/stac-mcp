"""Performance tests for STAC MCP tools."""

import asyncio
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from stac_mcp.fast_server import (
    get_collection,
    get_conformance,
    get_item,
    get_root,
    search_collections,
    search_items,
)
from stac_mcp.tools import execution


@pytest.fixture(autouse=True)
def mock_pystac_client(monkeypatch):
    """Mock the pystac_client.Client to avoid network calls."""
    mock_client = MagicMock()
    mock_client.get_collections.return_value = []
    mock_client.get_collection.return_value = None
    search_mock = MagicMock()
    search_mock.items.return_value = []
    mock_client.search.return_value = search_mock

    # Since STACClient lazy-loads its client, we patch the property
    monkeypatch.setattr("stac_mcp.tools.client.STACClient.client", mock_client)


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
    return None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool,args",  # noqa: PT006
    [
        (get_root, {}),
        (get_conformance, {}),
        (search_collections, {"limit": 10}),
        (get_collection, {"collection_id": "test"}),
        (search_items, {"collections": ["test"]}),
        (get_item, {"collection_id": "test", "item_id": "test"}),
    ],
)
async def test_tool_performance(tool: Any, args: dict, monkeypatch):
    """Verify that tool operations execute within a baseline SLO/time."""
    # ASR 1008: max invocation 15s. We set a much lower threshold for mocked tests.
    slo_seconds = 1.0

    # Mock execute_tool to isolate the server logic from the tool implementation
    original_execute = execution.execute_tool

    async def mock_execute(*a, **kw):
        return await original_execute(*a, **kw)

    monkeypatch.setattr(execution, "execute_tool", mock_execute)

    start_time = time.monotonic()
    await call_tool(tool, **args)
    duration = time.monotonic() - start_time

    assert duration < slo_seconds, f"Tool {tool.name} took too long: {duration:.2f}s"


@pytest.mark.asyncio
async def test_get_root_performance(monkeypatch):
    """Test performance of get_root tool specifically."""
    slo_seconds = 0.5  # Stricter SLO for root endpoint

    original_execute = execution.execute_tool

    async def mock_execute(*a, **kw):
        return await original_execute(*a, **kw)

    monkeypatch.setattr(execution, "execute_tool", mock_execute)

    start_time = time.monotonic()
    await call_tool(get_root)
    duration = time.monotonic() - start_time

    assert duration < slo_seconds, f"get_root took too long: {duration:.2f}s"


@pytest.mark.asyncio
async def test_search_items_performance(monkeypatch):
    """Test performance of search_items tool with larger limits."""
    slo_seconds = 2.0  # Allow more time for larger searches

    original_execute = execution.execute_tool

    async def mock_execute(*a, **kw):
        return await original_execute(*a, **kw)

    monkeypatch.setattr(execution, "execute_tool", mock_execute)

    start_time = time.monotonic()
    await call_tool(search_items, collections=["test"], limit=100)
    duration = time.monotonic() - start_time

    assert duration < slo_seconds, f"search_items took too long: {duration:.2f}s"


@pytest.mark.asyncio
async def test_get_collection_performance(monkeypatch):
    """Test performance of get_collection tool with a valid collection ID."""
    slo_seconds = 1.0  # SLO for collection retrieval

    original_execute = execution.execute_tool

    async def mock_execute(*a, **kw):
        return await original_execute(*a, **kw)

    monkeypatch.setattr(execution, "execute_tool", mock_execute)

    start_time = time.monotonic()
    await call_tool(get_collection, collection_id="valid-collection-id")
    duration = time.monotonic() - start_time

    assert duration < slo_seconds, f"get_collection took too long: {duration:.2f}s"


@pytest.mark.asyncio
async def test_get_item_performance(monkeypatch):
    """Test performance of get_item tool with valid collection and item IDs."""
    slo_seconds = 1.0  # SLO for item retrieval

    original_execute = execution.execute_tool

    async def mock_execute(*a, **kw):
        return await original_execute(*a, **kw)

    monkeypatch.setattr(execution, "execute_tool", mock_execute)

    start_time = time.monotonic()
    await call_tool(
        get_item, collection_id="valid-collection-id", item_id="valid-item-id"
    )
    duration = time.monotonic() - start_time

    assert duration < slo_seconds, f"get_item took too long: {duration:.2f}s"


@pytest.mark.asyncio
async def test_get_conformance_performance(monkeypatch):
    """Test performance of get_conformance tool."""
    slo_seconds = 0.5  # SLO for conformance endpoint

    original_execute = execution.execute_tool

    async def mock_execute(*a, **kw):
        return await original_execute(*a, **kw)

    monkeypatch.setattr(execution, "execute_tool", mock_execute)

    start_time = time.monotonic()
    await call_tool(get_conformance)
    duration = time.monotonic() - start_time

    assert duration < slo_seconds, f"get_conformance took too long: {duration:.2f}s"


@pytest.mark.asyncio
async def test_search_collections_performance(monkeypatch):
    """Test performance of search_collections tool with larger limits."""
    slo_seconds = 1.0  # SLO for collection search

    original_execute = execution.execute_tool

    async def mock_execute(*a, **kw):
        return await original_execute(*a, **kw)

    monkeypatch.setattr(execution, "execute_tool", mock_execute)

    start_time = time.monotonic()
    await call_tool(search_collections, limit=50)
    duration = time.monotonic() - start_time

    assert duration < slo_seconds, f"search_collections took too long: {duration:.2f}s"
