import time
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

import pytest
from fastmcp import Client

from stac_mcp.server import app


@pytest.mark.asyncio
async def test_search_cache_hit():
    calls = {"n": 0}

    def search_fn(**_):
        calls["n"] += 1
        return SimpleNamespace(
            items=lambda: iter([]),
        )

    with patch(
        "stac_mcp.tools.client.STACClient.client",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(search=search_fn),
    ):
        client = Client(app)
        async with client:
            # first call - should invoke underlying search
            await client.call_tool("search_items", {"collections": ["c1"], "limit": 5})
            # second call same params - should be served from cache (no new search)
            await client.call_tool("search_items", {"collections": ["c1"], "limit": 5})

    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_search_cache_ttl_expiry(monkeypatch):
    calls = {"n": 0}

    def search_fn(**_):
        calls["n"] += 1
        return SimpleNamespace(
            items=lambda: iter([]),
        )

    # set TTL to 1 second
    monkeypatch.setenv("STAC_MCP_SEARCH_CACHE_TTL_SECONDS", "1")

    with patch(
        "stac_mcp.tools.client.STACClient.client",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(search=search_fn),
    ):
        client = Client(app)
        async with client:
            await client.call_tool("search_items", {"collections": ["c1"], "limit": 5})
            # wait for TTL to expire
            time.sleep(1.1)
            await client.call_tool("search_items", {"collections": ["c1"], "limit": 5})

    min_num_calls = 2
    assert calls["n"] >= min_num_calls
