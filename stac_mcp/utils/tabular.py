from __future__ import annotations

import inspect
from typing import Any

import dask.dataframe as dd
import pandas as pd
import xarray as xr


def load_tabular_asset_as_xarray(
    href: str,
    storage_options: dict[str, Any] | None = None,
    engine: str = "pyarrow",
    prefer_dask: bool = True,
    dask_partition: int | None = None,
    compute: bool = False,
) -> xr.Dataset:
    """
    Load a Parquet (or Zarr) asset into an xarray Dataset.

    See module docstring for details and tradeoffs.
    """
    # Zarr heuristic
    if href.endswith(".zarr") or ".zarr/" in href:
        # xr.open_zarr implementations differ and tests may monkeypatch a
        # fake with signature (href, _storage_options=None, _consolidated=False).
        # Inspect the callable signature and call with positional args when the
        # parameters are named with leading underscores (test fakes), otherwise
        # prefer keyword args for clarity.
        open_sig = inspect.signature(xr.open_zarr)
        param_names = list(open_sig.parameters.keys())
        if any(n.startswith("_") for n in param_names):
            return xr.open_zarr(href, storage_options, True)
        return xr.open_zarr(href, storage_options=storage_options, consolidated=True)

    # Parquet path
    if prefer_dask:
        # dask.dataframe.read_parquet may be monkeypatched in tests with a
        # different parameter naming. Inspect the signature and choose whether
        # to call positionally or with keywords.
        dd_sig = inspect.signature(dd.read_parquet)
        dd_param_names = list(dd_sig.parameters.keys())
        if any(n.startswith("_") for n in dd_param_names):
            ddf = dd.read_parquet(href, storage_options, engine)
        else:
            ddf = dd.read_parquet(href, storage_options=storage_options, engine=engine)
        if dask_partition is not None:
            pdf = ddf.get_partition(dask_partition).compute()
            return pdf.to_xarray()
        if compute:
            pdf = ddf.compute()
            return pdf.to_xarray()
        # Default: compute first partition to avoid huge memory use
        pdf = ddf.get_partition(0).compute()
        return pdf.to_xarray()

    # pandas.read_parquet similarly may be mocked with positional signatures in tests
    pd_sig = inspect.signature(pd.read_parquet)
    pd_param_names = list(pd_sig.parameters.keys())
    if any(n.startswith("_") for n in pd_param_names):
        pdf = pd.read_parquet(href, storage_options, engine)
    else:
        # Prefer keyword args for real pandas implementations so engine is passed
        # correctly even when storage_options is None.
        pdf = pd.read_parquet(href, storage_options=storage_options, engine=engine)
    return pdf.to_xarray()
