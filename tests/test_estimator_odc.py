import sys
import types
from types import SimpleNamespace

import numpy as np

from stac_mcp.tools.client import STACClient


def test_estimate_uses_odc_nbytes(monkeypatch):
    # Build a fake xarray DataArray-like object
    class FakeDataArray:
        def __init__(self, shape, dtype):
            self._arr = np.zeros(shape, dtype=dtype)

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

    # Create fake odc.stac module with load function
    def fake_load(*_args, **_kwargs):
        # Return a dataset with two variables with known sizes
        da1 = FakeDataArray((2, 10, 10), np.float32)  # nbytes = 2*10*10*4 = 800
        da2 = FakeDataArray((2, 5, 5), np.uint16)  # nbytes = 2*5*5*2 = 100
        return FakeDataset({"B02": da1, "SCL": da2})

    odc_mod = types.ModuleType("odc.stac")
    odc_mod.load = fake_load

    # Fake xarray module so isinstance check passes
    xr_mod = types.ModuleType("xarray")
    xr_mod.Dataset = FakeDataset

    monkeypatch.setitem(sys.modules, "odc.stac", odc_mod)
    monkeypatch.setitem(sys.modules, "xarray", xr_mod)

    # Monkeypatch the client's cached search to return a single fake item
    fake_item = SimpleNamespace(collection_id="sentinel-2-l2a")

    def _fake_cached_search(_self, **_kwargs):
        return [fake_item]

    monkeypatch.setattr(STACClient, "_cached_search", _fake_cached_search)

    client = STACClient()
    res = client.estimate_data_size(collections=["sentinel-2-l2a"], limit=1)

    # Expected bytes: da1 nbytes + da2 nbytes = 800 + 100 = 900
    assert isinstance(res, dict)
    assert res["item_count"] == 1
    expected_total = 900
    assert res["estimated_size_bytes"] == expected_total
    # verify data_variables reported
    expected_var_count = 2
    assert len(res.get("data_variables", [])) == expected_var_count
    names = {v["variable"] for v in res["data_variables"]}
    assert names == {"B02", "SCL"}
