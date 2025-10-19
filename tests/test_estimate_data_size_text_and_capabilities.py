"""Additional tests for estimate_data_size text branch and capability fallbacks."""

import sys
import types
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

import pytest
from fastmcp import Client

from stac_mcp.fast_server import app


class _FakeDataArray:
    def __init__(self, nbytes, shape=(2, 2), dtype="uint16"):
        self.nbytes = nbytes
        self.shape = shape
        self.dtype = dtype
        self.encoding = {}
        # Calculate size from shape
        self.size = 1
        for dim in shape:
            self.size *= dim


class _FakeDataset:
    def __init__(self):
        self.data_vars = {
            "red": _FakeDataArray(1024, (2, 2)),
            "green": _FakeDataArray(2048, (2, 2)),
        }
        self.dims = {"x": 2, "y": 2}


class _FakeAsset:
    def __init__(self, media_type="image/tiff", size=None):
        self.media_type = media_type
        self.extra_fields = {}
        if size is not None:
            self.extra_fields["file:size"] = size


class _FakeItem:
    def __init__(self, year=2024, collection="c1"):
        self.id = f"item-{year}"
        self.collection_id = collection
        self.datetime = datetime(year, 1, 1, tzinfo=UTC)
        self.assets = {"A": _FakeAsset(), "B": _FakeAsset("text/plain")}


def _install_fake_odc(load_callable):
    """Install a fake odc.stac module with a provided load callable."""
    fake_odc = types.ModuleType("odc")
    fake_stac = types.SimpleNamespace(load=load_callable)
    fake_odc.stac = fake_stac
    sys.modules["odc"] = fake_odc
    sys.modules["odc.stac"] = fake_stac


@pytest.mark.asyncio
async def test_estimate_data_size_text_success():
    """Success path for text format with data_variables + spatial dims."""
    items = [_FakeItem(2024), _FakeItem(2025)]
    search_mock = SimpleNamespace(items=lambda: items)
    internal = SimpleNamespace(search=lambda **_: search_mock)
    _install_fake_odc(lambda *_, **__: _FakeDataset())

    with patch(
        "stac_mcp.tools.client.STACClient.client",
        new_callable=PropertyMock,
        return_value=internal,
    ):
        client = Client(app)
        async with client:
            result = await client.call_tool(
                "estimate_data_size",
                {"collections": ["c1"], "limit": 2},
            )

            txt = result.content[0].text
            assert "Data Size Estimation" in txt
            assert "Items analyzed: 2" in txt
            assert "Spatial Dimensions" in txt


@pytest.mark.asyncio
async def test_estimate_data_size_text_aoi_clipping():
    """AOI clipping branch (no bbox provided, derive from AOI)."""
    items = [_FakeItem(2024), _FakeItem(2024)]
    search_mock = SimpleNamespace(items=lambda: items)
    internal = SimpleNamespace(search=lambda **_: search_mock)
    _install_fake_odc(lambda *_, **__: _FakeDataset())
    aoi = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
    }

    with patch(
        "stac_mcp.tools.client.STACClient.client",
        new_callable=PropertyMock,
        return_value=internal,
    ):
        client = Client(app)
        async with client:
            result = await client.call_tool(
                "estimate_data_size",
                {"collections": ["c1"], "limit": 2, "aoi_geojson": aoi},
            )
            txt = result.content[0].text
            assert "Clipped to AOI" in txt
            assert "Bounding box" in txt


@pytest.mark.asyncio
async def test_estimate_data_size_text_no_items():
    """Early return branch when no items found."""
    search_mock = SimpleNamespace(items=list)
    internal = SimpleNamespace(search=lambda **_: search_mock)
    _install_fake_odc(lambda *_, **__: _FakeDataset())

    with patch(
        "stac_mcp.tools.client.STACClient.client",
        new_callable=PropertyMock,
        return_value=internal,
    ):
        client = Client(app)
        async with client:
            result = await client.call_tool(
                "estimate_data_size",
                {"collections": ["c1"], "limit": 2},
            )
            txt = result.content[0].text
            assert "Items analyzed: 0" in txt
            assert "No items found" in txt
