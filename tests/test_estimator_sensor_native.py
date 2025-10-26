import sys
import types
from types import SimpleNamespace

import numpy as np

from stac_mcp.tools.client import STACClient


class FakeDataArray:
    def __init__(self, arr: np.ndarray):
        self._arr = arr

    @property
    def data(self):
        return self._arr

    @property
    def shape(self):
        return self._arr.shape

    @property
    def dtype(self):
        return self._arr.dtype


class FakeDataset:
    def __init__(self, data_vars):
        self.data_vars = data_vars


def make_fake_load(data_vars):
    def _load(*_args, **_kwargs):
        return FakeDataset(data_vars)

    return _load


def test_sensor_native_dual_report(monkeypatch):
    # single variable float32; registry for sentinel-2-l2a -> uint16
    da = FakeDataArray(np.zeros((1, 2, 2), dtype=np.float32))
    odc_mod = types.ModuleType("odc.stac")
    odc_mod.load = make_fake_load({"B02": da})

    xr_mod = types.ModuleType("xarray")
    xr_mod.Dataset = FakeDataset

    monkeypatch.setitem(sys.modules, "odc.stac", odc_mod)
    monkeypatch.setitem(sys.modules, "xarray", xr_mod)

    fake_item = SimpleNamespace(collection_id="sentinel-2-l2a")

    def _fake_cached_search(_self, **_kwargs):
        return [fake_item]

    monkeypatch.setattr(STACClient, "_cached_search", _fake_cached_search)

    client = STACClient()
    res = client.estimate_data_size(collections=["sentinel-2-l2a"], limit=1)

    assert isinstance(res, dict)
    dvs = res.get("data_variables", [])
    assert len(dvs) == 1
    v = dvs[0]
    assert "reported_bytes" in v
    assert "sensor_native_bytes" in v
    assert "sensor_native_dtype" in v
    assert v.get("sensor_native_recommended") is True
    # sensor native should be <= reported when dtype is narrower
    assert v["sensor_native_bytes"] <= v["reported_bytes"]
    assert "sensor_native_estimated_size_bytes" in res


def test_message_summarization(monkeypatch):
    # Use two variables to validate message counts
    da1 = FakeDataArray(np.zeros((1, 2, 2), dtype=np.float32))
    da2 = FakeDataArray(np.zeros((1, 1, 1), dtype=np.float32))
    odc_mod = types.ModuleType("odc.stac")
    odc_mod.load = make_fake_load({"B02": da1, "SCL": da2})

    xr_mod = types.ModuleType("xarray")
    xr_mod.Dataset = FakeDataset

    monkeypatch.setitem(sys.modules, "odc.stac", odc_mod)
    monkeypatch.setitem(sys.modules, "xarray", xr_mod)

    fake_item = SimpleNamespace(collection_id="sentinel-2-l2a")

    def _fake_cached_search(_self, **_kwargs):
        return [fake_item]

    monkeypatch.setattr(STACClient, "_cached_search", _fake_cached_search)

    client = STACClient()
    res = client.estimate_data_size(collections=["sentinel-2-l2a"], limit=1)

    msg = res.get("message", "")
    assert "sensor-native total" in msg or "sensor-native" in msg
    # counts: reported_nbytes_count should equal number of data variables (2)
    assert (
        "2 variable(s) contributed reported .data.nbytes" in msg
        or "2 variable(s)" in msg
        or "Reported .data.nbytes count: 2" in msg
    )


def test_numeric_total_preservation(monkeypatch):
    # Build two vars with known sizes and validate numeric totals
    # var1: shape (1,2,2) float32 -> 1*2*2*4 = 16 bytes
    # var2: shape (1,1,1) float32 -> 4 bytes
    da1 = FakeDataArray(np.zeros((1, 2, 2), dtype=np.float32))
    da2 = FakeDataArray(np.zeros((1, 1, 1), dtype=np.float32))
    odc_mod = types.ModuleType("odc.stac")
    odc_mod.load = make_fake_load({"B02": da1, "B03": da2})

    xr_mod = types.ModuleType("xarray")
    xr_mod.Dataset = FakeDataset

    monkeypatch.setitem(sys.modules, "odc.stac", odc_mod)
    monkeypatch.setitem(sys.modules, "xarray", xr_mod)

    fake_item = SimpleNamespace(collection_id="sentinel-2-l2a")

    def _fake_cached_search(_self, **_kwargs):
        return [fake_item]

    monkeypatch.setattr(STACClient, "_cached_search", _fake_cached_search)

    client = STACClient()
    res = client.estimate_data_size(collections=["sentinel-2-l2a"], limit=1)

    # reported total should be sum of .nbytes: 16 + 4 = 20
    expected_reported_total = 20
    assert res.get("estimated_size_bytes") == expected_reported_total
    # sensor-native total should be <= reported total (as uint16 halves bytes)
    assert res.get("sensor_native_estimated_size_bytes") <= res.get(
        "estimated_size_bytes"
    )
