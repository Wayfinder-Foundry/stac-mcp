import time
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

import pytest
from fastmcp import Client

from stac_mcp.server import app


@pytest.mark.asyncio
async def test_search_cache_hit():
    calls = {"n": 0}

    items = [
        SimpleNamespace(
            id="i1",
            collection_id="c1",
            datetime=None,
            assets={},
            to_dict=lambda: {
                "id": "i1",
                "collection": "c1",
                "datetime": None,
                "assets": {},
            },
        )
    ]

    def search_fn(**_):
        calls["n"] += 1
        return SimpleNamespace(
            items_as_dicts=lambda: [
                {
                    "id": item.id,
                    "collection": item.collection_id,
                    "datetime": None,
                    "assets": {},
                }
                for item in items
            ]
        )

    with patch(
        "stac_mcp.tools.client.STACClient.client",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(search=search_fn),
    ):
        search_items_tool = app._tool_manager._tools["search_items"].fn  # noqa: SLF001
        # first call - should invoke underlying search
        res1 = search_items_tool(collections=["c1"], limit=5)
        _ = [r async for r in res1]
        # second call same params - should be served from cache (no new search)
        res2 = search_items_tool(collections=["c1"], limit=5)
        _ = [r async for r in res2]

    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_search_cache_ttl_expiry(monkeypatch):
    calls = {"n": 0}

    items = [
        SimpleNamespace(
            id="i1",
            collection_id="c1",
            datetime=None,
            assets={},
            to_dict=lambda: {
                "id": "i1",
                "collection": "c1",
                "datetime": None,
                "assets": {},
            },
        )
    ]

    def search_fn(**_):
        calls["n"] += 1
        return SimpleNamespace(
            items_as_dicts=lambda: [
                {
                    "id": item.id,
                    "collection": item.collection_id,
                    "datetime": None,
                    "assets": {},
                }
                for item in items
            ]
        )

    # set TTL to 1 second
    monkeypatch.setenv("STAC_MCP_SEARCH_CACHE_TTL_SECONDS", "1")

    with patch(
        "stac_mcp.tools.client.STACClient.client",
        new_callable=PropertyMock,
        return_value=SimpleNamespace(search=search_fn),
    ):
        search_items_tool = app._tool_manager._tools["search_items"].fn  # noqa: SLF001
        res1 = search_items_tool(collections=["c1"], limit=5)
        _ = [r async for r in res1]
        # wait for TTL to expire
        time.sleep(1.1)
        res2 = search_items_tool(collections=["c1"], limit=5)
        _ = [r async for r in res2]

    min_num_calls = 2
    assert calls["n"] >= min_num_calls
