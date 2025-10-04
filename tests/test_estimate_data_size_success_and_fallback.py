"""Tests for estimate_data_size success and fallback paths in STACClient."""

from __future__ import annotations

import json
import sys
import types
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from stac_mcp.server import handle_call_tool
from stac_mcp.tools.client import STACClient


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
async def test_estimate_data_size_success(monkeypatch):
    with patch("stac_mcp.server.stac_client"):
        # Patch odc.stac availability and loader
        monkeypatch.setattr("stac_mcp.server.ODC_STAC_AVAILABLE", True)
        dts = [
            datetime(2024, 1, 1, tzinfo=UTC),
            datetime(2024, 1, 2, tzinfo=UTC),
        ]
        items = [FakeItem(dt) for dt in dts]

        search_mock = SimpleNamespace(items=lambda: items)
        mock_client_internal = SimpleNamespace(search=lambda **_: search_mock)

        # Patch STACClient.estimate_data_size to invoke real logic.
        real_client = STACClient("https://example.com/stac/v1")
        real_client._client = mock_client_internal  # noqa: SLF001

        # Provide a fake odc.stac module.
        fake_odc = types.ModuleType("odc")
        fake_stac = types.SimpleNamespace(load=lambda *_, **__: FakeDataset())
        fake_odc.stac = fake_stac  # type: ignore[attr-defined]
        sys.modules["odc"] = fake_odc
        sys.modules["odc.stac"] = fake_stac  # type: ignore[assignment]

        # Monkeypatch the global stac_client for the handler.
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
async def test_estimate_data_size_with_nodata_dtype_preservation(monkeypatch):
    """Test that original dtype is used when nodata causes upcast to float64."""
    with patch("stac_mcp.server.stac_client"):
        monkeypatch.setattr("stac_mcp.server.ODC_STAC_AVAILABLE", True)
        dts = [datetime(2024, 1, 1, tzinfo=UTC)]
        items = [FakeItem(dt) for dt in dts]

        search_mock = SimpleNamespace(items=lambda: items)
        mock_client_internal = SimpleNamespace(search=lambda **_: search_mock)

        real_client = STACClient("https://example.com/stac/v1")
        real_client._client = mock_client_internal  # noqa: SLF001

        # Create a fake dataset with float64 dtype but original int16 in encoding
        # Simulates the case where nodata conversion causes dtype upcast
        class FakeDatasetWithNodata:
            def __init__(self):
                # Original data is int16, but got upcast to float64 due to nodata=np.nan
                self.data_vars = {
                    "band1": FakeDataArray(
                        nbytes=8192,  # This would be the float64 size (2048 * 4 bytes)
                        shape=(32, 64),  # 2048 pixels
                        dtype="float64",  # Upcast dtype
                        encoding={
                            "dtype": "int16",
                            "_FillValue": -9999,
                        },  # Original dtype
                    ),
                }
                self.dims = {"x": 64, "y": 32}

        fake_odc = types.ModuleType("odc")
        fake_stac = types.SimpleNamespace(load=lambda *_, **__: FakeDatasetWithNodata())
        fake_odc.stac = fake_stac  # type: ignore[attr-defined]
        sys.modules["odc"] = fake_odc
        sys.modules["odc.stac"] = fake_stac  # type: ignore[assignment]

        monkeypatch.setattr("stac_mcp.server.stac_client", real_client)

        res = await handle_call_tool(
            "estimate_data_size",
            {"collections": ["c1"], "limit": 1, "output_format": "json"},
        )
        text = res[0].text
        result = json.loads(text)

        # Check that the dtype is reported as int16 (original), not float64 (upcast)
        assert result["data"]["estimate"]["data_variables"][0]["dtype"] == "int16"

        # Check that size calculation uses int16 (2 bytes) not float64 (8 bytes)
        # 2048 pixels * 2 bytes = 4096 bytes
        expected_bytes = 2048 * 2
        assert (
            result["data"]["estimate"]["data_variables"][0]["size_bytes"]
            == expected_bytes
        )


@pytest.mark.asyncio
async def test_estimate_data_size_fallback(monkeypatch):
    with patch("stac_mcp.server.stac_client"):
        monkeypatch.setattr("stac_mcp.server.ODC_STAC_AVAILABLE", True)
        items = [FakeItem(datetime(2024, 1, 1, tzinfo=UTC))]
        search_mock = SimpleNamespace(items=lambda: items)
        mock_client_internal = SimpleNamespace(search=lambda **_: search_mock)

        real_client = STACClient("https://example.com/stac/v1")
        real_client._client = mock_client_internal  # noqa: SLF001

        # Fake odc.stac raising to trigger fallback path
        def failing_load(*_, **__):
            msg = "fail"
            raise RuntimeError(msg)

        fake_odc = types.ModuleType("odc")
        fake_stac = types.SimpleNamespace(load=failing_load)
        fake_odc.stac = fake_stac  # type: ignore[attr-defined]
        sys.modules["odc"] = fake_odc
        sys.modules["odc.stac"] = fake_stac  # type: ignore[assignment]
        monkeypatch.setattr("stac_mcp.server.stac_client", real_client)

        res = await handle_call_tool(
            "estimate_data_size",
            {"collections": ["c1"], "limit": 1, "output_format": "json"},
        )
    text = res[0].text
    assert '"fallback"' in text or "fallback" in text
    assert '"estimation_method"' in text or "estimation_method" in text
