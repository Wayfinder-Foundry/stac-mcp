import time
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

import pytest
from fastmcp import Client

from stac_mcp.server import app
from stac_mcp.tools import execution


@pytest.mark.asyncio
async def test_search_cache_hit():
    # _get_cached_client keys on (catalog_url, headers); both are None/None
    # here (the defaults), so a stale client from a prior test would be
    # reused otherwise, along with its already-populated _search_cache.
    execution._CLIENT_CACHE.clear()  # noqa: SLF001

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
    # Same isolation reasoning as test_search_cache_hit above: without this,
    # a client (and its _search_cache) left over from a prior test can be
    # reused here, making the TTL-expiry assertion flaky depending on
    # CPython id() reuse for the mocked client object between tests.
    execution._CLIENT_CACHE.clear()  # noqa: SLF001

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
