import pandas as pd
import xarray as xr

from stac_mcp.utils.tabular import load_tabular_asset_as_xarray


def test_load_parquet_to_xarray(tmp_path):
    df = pd.DataFrame({"a": [1, 2, 3], "b": [0.1, 0.2, 0.3]})
    p = tmp_path / "test.parquet"
    df.to_parquet(p)

    ds = load_tabular_asset_as_xarray(str(p), prefer_dask=False)
    assert isinstance(ds, xr.Dataset)
    assert "a" in ds
    assert "b" in ds


def test_load_zarr_to_xarray(tmp_path):
    ds = xr.Dataset({"x": ("i", [1, 2, 3])})
    z = tmp_path / "test.zarr"
    ds.to_zarr(str(z))

    loaded = load_tabular_asset_as_xarray(str(z))
    assert isinstance(loaded, xr.Dataset)
    assert "x" in loaded
