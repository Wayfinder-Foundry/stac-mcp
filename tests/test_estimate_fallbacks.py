from types import SimpleNamespace

import numpy as np
import odc.stac as odc_stac
import xarray as xr

from stac_mcp.tools.client import STACClient


def _make_fake_search(items):
    class FakeSearch:
        def __init__(self, items_):
            self._items = items_

        def items(self):
            yield from self._items

    return FakeSearch(items)


RUNTIME_MSG = "no raster"


def _raise_no_raster(*_args, **_kwargs):
    msg = RUNTIME_MSG
    raise RuntimeError(msg)


def test_parquet_fallback_metadata(monkeypatch):
    # Force odc.stac.load to raise so estimator uses fallback
    monkeypatch.setattr(odc_stac, "load", _raise_no_raster)

    client = STACClient()

    # Create a fake item with a parquet asset providing file:bytes metadata
    size_bytes = 4096
    asset = {
        "href": "https://example.com/data.parquet",
        "media_type": "application/x-parquet",
        "extra_fields": {"file:bytes": str(size_bytes)},
    }
    item = SimpleNamespace(collection_id="fia", assets={"data": asset}, datetime=None)

    # Patch client's internal _client to return our fake search
    fake_search = _make_fake_search([item])
    fake_client = SimpleNamespace(search=lambda **_kw: fake_search)
    monkeypatch.setattr(client, "_client", fake_client, raising=False)

    res = client.estimate_data_size(collections=["fia"], limit=10)
    assert res["item_count"] == 1
    assert res["estimated_size_bytes"] == size_bytes
    assert any(a["asset"] == "data" for a in res.get("assets_analyzed", []))


def test_zarr_fallback_inspect(tmp_path, monkeypatch):
    # Force odc.stac.load to raise
    monkeypatch.setattr(odc_stac, "load", _raise_no_raster)

    client = STACClient()

    # Create small xarray dataset and write to zarr
    ds = xr.Dataset({"var": (("x", "y"), np.ones((2, 3), dtype=np.float32))})
    zdir = tmp_path / "test.zarr"
    ds.to_zarr(str(zdir), mode="w")

    href = f"{zdir}"
    asset = {"href": href, "media_type": "application/vnd+zarr"}
    item = SimpleNamespace(
        collection_id="era5-pds", assets={"arr": asset}, datetime=None
    )
    fake_search = _make_fake_search([item])
    fake_client = SimpleNamespace(search=lambda **_kw: fake_search)
    monkeypatch.setattr(client, "_client", fake_client, raising=False)

    res = client.estimate_data_size(collections=["era5-pds"], limit=10)
    assert res["item_count"] == 1
    # dataset has 2*3 elements of float32 => 24 bytes
    min_bytes = 24
    assert res["estimated_size_bytes"] >= min_bytes
    assets = res.get("assets_analyzed", [])
    assert any(a.get("method") == "zarr-inspect" for a in assets)
