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
    "tool, args",
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
