"""Timeout tests for estimate_data_size tool."""

import json
import sys
import types
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

import pytest
import requests
from fastmcp import Client

from stac_mcp.fast_server import app


def _make_fake_item_with_asset():
    class FakeAsset:
        def __init__(self):
            self.media_type = "image/tiff"
            self.extra_fields = {}

    class FakeItem:
        def __init__(self):
            self.id = "i1"
            self.collection_id = "c1"
            self.datetime = None
            self.assets = {"A": FakeAsset()}

    return [FakeItem()]


@pytest.mark.asyncio
async def test_estimate_data_size_head_timeout():
    """When HEAD requests time out during fallback, estimator should handle it."""
    # Force fallback path by making odc.stac.load raise an error
    fake_odc = types.ModuleType("odc")
    fake_stac = types.SimpleNamespace(
        load=lambda *_, **__: (_ for _ in ()).throw(RuntimeError("odc fail"))
    )
    fake_odc.stac = fake_stac
    sys.modules["odc"] = fake_odc
    sys.modules["odc.stac"] = fake_stac

    items = _make_fake_item_with_asset()
    search_mock = SimpleNamespace(items=lambda: items)
    internal = SimpleNamespace(search=lambda **_: search_mock)

    # Mock requests.Session.request to raise Timeout for HEAD requests
    def _request_raise_timeout(_session, method, _url, *_, **__):
        if method == "HEAD":
            msg = "timed out"
            raise requests.exceptions.Timeout(msg)
        return SimpleNamespace(headers={})

    with (
        patch(
            "stac_mcp.tools.client.STACClient.client",
            new_callable=PropertyMock,
            return_value=internal,
        ),
        patch("requests.Session.request", new=_request_raise_timeout),
    ):
        client = Client(app)
        async with client:
            # Use metadata-only to force HEAD-based fallback logic
            result = await client.call_tool(
                "estimate_data_size",
                {
                    "collections": ["c1"],
                    "limit": 1,
                    "force_metadata_only": True,
                    "output_format": "json",
                },
            )
            data = json.loads(result.content[0].text)
            assert "data" in data
            estimate = data["data"]["estimate"]
            # When HEADs time out we expect fallback assets but zero total
            # size and an explanatory message
            assert estimate["estimated_size_bytes"] == 0
            assert (
                "Error" in estimate["message"]
                or "Error estimating" in estimate["message"]
            )


@pytest.mark.asyncio
async def test_estimate_data_size_session_request_timeout():
    """If Session.request wrapper raises Timeout, estimator should handle it."""
    items = _make_fake_item_with_asset()
    search_mock = SimpleNamespace(items=lambda: items)
    internal = SimpleNamespace(search=lambda **_: search_mock)
    # Force fallback by making odc.stac.load fail, then have
    # session.request raise Timeout
    fake_odc = types.ModuleType("odc")
    fake_stac = types.SimpleNamespace(
        load=lambda *_, **__: (_ for _ in ()).throw(RuntimeError("odc fail"))
    )
    fake_odc.stac = fake_stac
    sys.modules["odc"] = fake_odc
    sys.modules["odc.stac"] = fake_stac

    timeout_exc = requests.exceptions.Timeout("session timed out")
    with (
        patch(
            "stac_mcp.tools.client.STACClient.client",
            new_callable=PropertyMock,
            return_value=internal,
        ),
        patch("requests.Session.request", side_effect=timeout_exc),
    ):
        client = Client(app)
        async with client:
            # Use metadata-only to force fallback and HEAD-based logic
            result = await client.call_tool(
                "estimate_data_size",
                {
                    "collections": ["c1"],
                    "limit": 1,
                    "force_metadata_only": True,
                    "output_format": "json",
                },
            )
            data = json.loads(result.content[0].text)
            assert "data" in data
            estimate = data["data"]["estimate"]
            # HEADs timed out so total estimated bytes should be zero and
            # message should indicate failure
            assert estimate["estimated_size_bytes"] == 0
            assert (
                "Error" in estimate["message"]
                or "Error estimating" in estimate["message"]
            )
