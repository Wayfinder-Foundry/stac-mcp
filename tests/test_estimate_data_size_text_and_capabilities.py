"""Additional tests for estimate_data_size text branch and capability fallbacks.

These target uncovered branches in:
 - stac_mcp/tools/estimate_data_size.py (text formatting path)
 - stac_mcp/tools/client.py capability helpers (_http_json fallbacks)
 - STACClient.estimate_data_size: AOI clipping + empty items early return
"""

from __future__ import annotations

import sys
import types
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from stac_mcp.server import handle_call_tool
from stac_mcp.tools.client import STACClient


class _FakeDataArray:
    def __init__(self, nbytes, shape=(2, 2), dtype="uint16"):
        self.nbytes = nbytes
        self.shape = shape
        self.dtype = dtype


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
        self.datetime = datetime(year, 1, 1)
        self.assets = {"A": _FakeAsset(), "B": _FakeAsset("text/plain")}


def _install_fake_odc(load_callable):
    """Install a fake odc.stac module with a provided load callable."""
    fake_odc = types.ModuleType("odc")
    fake_stac = types.SimpleNamespace(load=load_callable)
    fake_odc.stac = fake_stac  # type: ignore[attr-defined]
    sys.modules["odc"] = fake_odc
    sys.modules["odc.stac"] = fake_stac  # type: ignore


# ---------------- estimate_data_size text path tests -----------------


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_estimate_data_size_text_success(mock_sc, monkeypatch):
    """Success path exercising text formatting with data_variables + spatial dims."""
    monkeypatch.setattr("stac_mcp.server.ODC_STAC_AVAILABLE", True)
    items = [_FakeItem(2024), _FakeItem(2025)]
    search_mock = SimpleNamespace(items=lambda: items)
    internal = SimpleNamespace(search=lambda **k: search_mock)
    real_client = STACClient("https://example.com/stac/v1")
    real_client._client = internal
    _install_fake_odc(lambda *a, **k: _FakeDataset())
    monkeypatch.setattr("stac_mcp.server.stac_client", real_client)
    out = await handle_call_tool(
        "estimate_data_size",
        {"collections": ["c1"], "limit": 2},  # text mode
    )
    txt = out[0].text
    assert "Data Size Estimation" in txt
    assert "Items analyzed: 2" in txt
    assert "Spatial Dimensions" in txt


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_estimate_data_size_text_fallback(mock_sc, monkeypatch):
    """Fallback path (odc load failure) exercising assets_analyzed section."""
    monkeypatch.setattr("stac_mcp.server.ODC_STAC_AVAILABLE", True)
    items = [_FakeItem(2024)]
    search_mock = SimpleNamespace(items=lambda: items)
    internal = SimpleNamespace(search=lambda **k: search_mock)
    real_client = STACClient("https://example.com/stac/v1")
    real_client._client = internal

    def failing_load(*a, **k):  # force fallback
        raise RuntimeError("boom")

    _install_fake_odc(failing_load)
    monkeypatch.setattr("stac_mcp.server.stac_client", real_client)
    out = await handle_call_tool(
        "estimate_data_size",
        {"collections": ["c1"], "limit": 1},  # text mode
    )
    txt = out[0].text
    assert "fallback" in txt.lower()
    assert "Assets Analyzed" in txt


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_estimate_data_size_text_aoi_clipping(mock_sc, monkeypatch):
    """AOI clipping branch (no bbox provided, derive from AOI)."""
    monkeypatch.setattr("stac_mcp.server.ODC_STAC_AVAILABLE", True)
    items = [_FakeItem(2024), _FakeItem(2024)]
    search_mock = SimpleNamespace(items=lambda: items)
    internal = SimpleNamespace(search=lambda **k: search_mock)
    real_client = STACClient("https://example.com/stac/v1")
    real_client._client = internal
    _install_fake_odc(lambda *a, **k: _FakeDataset())
    monkeypatch.setattr("stac_mcp.server.stac_client", real_client)
    aoi = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
    }  # 1x1 box
    out = await handle_call_tool(
        "estimate_data_size",
        {"collections": ["c1"], "limit": 2, "aoi_geojson": aoi},
    )
    txt = out[0].text
    assert "Clipped to AOI" in txt
    assert "Bounding box" in txt


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_estimate_data_size_text_no_items(mock_sc, monkeypatch):
    """Early return branch when no items found."""
    monkeypatch.setattr("stac_mcp.server.ODC_STAC_AVAILABLE", True)
    search_mock = SimpleNamespace(items=list)
    internal = SimpleNamespace(search=lambda **k: search_mock)
    real_client = STACClient("https://example.com/stac/v1")
    real_client._client = internal
    _install_fake_odc(lambda *a, **k: _FakeDataset())  # won't be used
    monkeypatch.setattr("stac_mcp.server.stac_client", real_client)
    out = await handle_call_tool(
        "estimate_data_size",
        {"collections": ["c1"], "limit": 2},
    )
    txt = out[0].text
    assert "Items analyzed: 0" in txt
    assert "No items found" in txt


# ---------------- STACClient capability fallback tests -----------------


def test_client_get_root_document_empty():
    client = STACClient("https://example.com/stac/v1")
    # monkeypatch _http_json to return None
    client._http_json = lambda path, method="GET", payload=None: None  # type: ignore
    root = client.get_root_document()
    assert root["id"] is None and root["conformsTo"] == []


def test_client_get_root_document_alt_key():
    client = STACClient("https://example.com/stac/v1")
    # Return alt key 'conforms_to'
    client._http_json = lambda path, method="GET", payload=None: {  # type: ignore
        "id": "root",
        "title": "t",
        "description": "d",
        "links": [],
        "conforms_to": ["core"],
    }
    root = client.get_root_document()
    assert root["conformsTo"] == ["core"]


def test_client_get_conformance_fallback_to_root():
    client = STACClient("https://example.com/stac/v1")

    def fake_http_json(path, method="GET", payload=None):
        if path == "/conformance":
            return None  # trigger fallback
        return {"conformsTo": ["a", "b"]}

    client._http_json = fake_http_json  # type: ignore
    conf = client.get_conformance(check=["a", "x"])
    assert conf["checks"] == {"a": True, "x": False}


def test_client_get_queryables_not_available():
    client = STACClient("https://example.com/stac/v1")
    client._http_json = lambda path, method="GET", payload=None: None  # type: ignore
    q = client.get_queryables()
    assert q["queryables"] == {}
    assert "message" in q
