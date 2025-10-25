"""Tests for estimate_data_size success and fallback paths."""

import json
import sys
import types
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import PropertyMock, patch

import pytest
from fastmcp import Client

from stac_mcp.fast_server import app

from . import ITEM_COUNT_TWO


class FakeDataArray:
    def __init__(self, nbytes, shape=(4, 4), dtype="uint16", encoding=None):
        self.nbytes = nbytes
        self.shape = shape
        self.dtype = dtype
        self.encoding = encoding or {}
        # Calculate size from shape
        self.size = 1
        for dim in shape:
            self.size *= dim


class FakeDataset:
    def __init__(self):
        self.data_vars = {
            "red": FakeDataArray(1024, (2, 2), "uint16"),
            "green": FakeDataArray(2048, (2, 2), "uint16"),
        }
        self.dims = {"x": 2, "y": 2}


class FakeAsset:
    def __init__(self, media_type="image/tiff", size=None):
        self.media_type = media_type
        self.extra_fields = {}
        if size is not None:
            self.extra_fields["file:size"] = size


class FakeItem:
    def __init__(self, dt, collection="c1"):
        self.id = f"item-{dt.year}"
        self.collection_id = collection
        self.datetime = dt
        self.assets = {"A": FakeAsset(), "B": FakeAsset("text/plain")}


@pytest.mark.asyncio
async def test_estimate_data_size_success(monkeypatch):  # noqa: ARG001
    """Test the data size estimation tool succeeds."""
    # Fake odc.stac module
    fake_odc = types.ModuleType("odc")
    fake_stac = types.SimpleNamespace(load=lambda *_, **__: FakeDataset())
    fake_odc.stac = fake_stac
    sys.modules["odc"] = fake_odc
    sys.modules["odc.stac"] = fake_stac

    dts = [
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 1, 2, tzinfo=UTC),
    ]
    items = [FakeItem(dt) for dt in dts]

    search_mock = SimpleNamespace(items=lambda: items)
    mock_client_internal = SimpleNamespace(search=lambda **_: search_mock)

    with patch(
        "stac_mcp.tools.client.STACClient.client",
        new_callable=PropertyMock,
        return_value=mock_client_internal,
    ):
        client = Client(app)
        async with client:
            result = await client.call_tool(
                "estimate_data_size",
                {"collections": ["c1"], "limit": 2, "output_format": "json"},
            )
            response_data = json.loads(result.content[0].text)
            assert "data" in response_data
            assert "estimate" in response_data["data"]
            assert "item_count" in response_data["data"]["estimate"]
            assert response_data["data"]["estimate"]["item_count"] == ITEM_COUNT_TWO
            # GeoTIFF-only estimator does not compute spatial_dims here;
            # ensure we returned asset analysis instead.
            assert "assets_analyzed" in response_data["data"]["estimate"]
