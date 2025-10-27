"""Performance tests for the STAC tools."""

import time
from unittest.mock import MagicMock

import pytest

from stac_mcp.tools import execution
from stac_mcp.tools.execution import execute_tool


@pytest.fixture
def mock_tool(monkeypatch):
    """Fixture to temporarily register a mock tool handler."""

    def _register(name, handler):
        monkeypatch.setitem(execution._TOOL_HANDLERS, name, handler)  # noqa: SLF001

    return _register


@pytest.mark.asyncio
async def test_search_collections_performance(mock_tool):
    """Test performance of search_collections."""
    mock_handler = MagicMock(
        return_value=[{"id": f"collection_{i}"} for i in range(100)]
    )
    mock_tool("search_collections", mock_handler)

    start_time = time.time()
    await execute_tool("search_collections", {})
    end_time = time.time()

    assert end_time - start_time < 0.1  # 100ms


@pytest.mark.asyncio
async def test_search_items_performance(mock_tool):
    """Test performance of search_items."""
    mock_handler = MagicMock(return_value=[{"id": f"item_{i}"} for i in range(1000)])
    mock_tool("search_items", mock_handler)

    start_time = time.time()
    await execute_tool("search_items", {"collections": ["test"]})
    end_time = time.time()

    assert end_time - start_time < 0.2  # 200ms


@pytest.mark.asyncio
async def test_estimate_data_size_performance(mock_tool):
    """Test performance of estimate_data_size."""
    mock_handler = MagicMock(
        return_value={
            "item_count": 100,
            "estimated_size_bytes": 1024 * 1024 * 100,
            "message": "Success",
        }
    )
    mock_tool("estimate_data_size", mock_handler)

    start_time = time.time()
    await execute_tool("estimate_data_size", {"collections": ["test"]})
    end_time = time.time()

    assert end_time - start_time < 0.1  # 100ms
