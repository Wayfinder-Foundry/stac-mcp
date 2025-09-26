"""Tests for estimate_data_size success + fallback paths in STACClient via tool handler."""

from __future__ import annotations

import sys
import types
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from stac_mcp.server import handle_call_tool


class FakeDataArray:
    def __init__(self, nbytes, shape=(4, 4), dtype="uint16"):
        self.nbytes = nbytes
        self.shape = shape
        self.dtype = dtype


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
@patch("stac_mcp.server.stac_client")
async def test_estimate_data_size_success(mock_sc, monkeypatch):
    # Patch odc.stac availability and loader
    monkeypatch.setattr("stac_mcp.server.ODC_STAC_AVAILABLE", True)
    items = [FakeItem(datetime(2024, 1, 1)), FakeItem(datetime(2024, 1, 2))]

    search_mock = SimpleNamespace(items=lambda: items)
    mock_client_internal = SimpleNamespace(search=lambda **k: search_mock)
    mock_sc.estimate_data_size.side_effect = (
        None  # ensure using actual path requires patch inside client
    )

    # Patch STACClient.estimate_data_size to invoke real logic by constructing a fresh instance
    from stac_mcp.tools.client import STACClient

    real_client = STACClient("https://example.com/stac/v1")
    real_client._client = mock_client_internal  # inject mocked pystac client

    # Provide a fake odc.stac module (client imports from odc import stac as odc_stac)
    fake_odc = types.ModuleType("odc")
    fake_stac = types.SimpleNamespace(
        load=lambda items, bbox=None, chunks=None: FakeDataset(),
    )
    fake_odc.stac = fake_stac  # type: ignore[attr-defined]
    sys.modules["odc"] = fake_odc
    # Ensure odc.stac import path resolves
    sys.modules["odc.stac"] = fake_stac  # type: ignore

    # Monkeypatch the global stac_client used by server handlers to our prepared instance
    monkeypatch.setattr("stac_mcp.server.stac_client", real_client)

    res = await handle_call_tool(
        "estimate_data_size",
        {"collections": ["c1"], "limit": 2, "output_format": "json"},
    )
    text = res[0].text
    assert '"data_size_estimate"' in text or '"item_count"' in text
    assert '"item_count":2' in text.replace(" ", "")
    assert '"spatial_dims"' in text


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_estimate_data_size_fallback(mock_sc, monkeypatch):
    monkeypatch.setattr("stac_mcp.server.ODC_STAC_AVAILABLE", True)
    from stac_mcp.tools.client import STACClient

    items = [FakeItem(datetime(2024, 1, 1))]
    search_mock = SimpleNamespace(items=lambda: items)
    mock_client_internal = SimpleNamespace(search=lambda **k: search_mock)

    real_client = STACClient("https://example.com/stac/v1")
    real_client._client = mock_client_internal

    # Fake odc.stac raising to trigger fallback path
    fake_odc = types.ModuleType("odc")

    def failing_load(*a, **k):  # force fallback
        raise RuntimeError("fail")

    fake_stac = types.SimpleNamespace(load=failing_load)
    fake_odc.stac = fake_stac  # type: ignore[attr-defined]
    sys.modules["odc"] = fake_odc
    sys.modules["odc.stac"] = fake_stac  # type: ignore
    monkeypatch.setattr("stac_mcp.server.stac_client", real_client)

    res = await handle_call_tool(
        "estimate_data_size",
        {"collections": ["c1"], "limit": 1, "output_format": "json"},
    )
    text = res[0].text
    assert '"fallback"' in text or "fallback" in text
    assert '"estimation_method"' in text or "estimation_method" in text
