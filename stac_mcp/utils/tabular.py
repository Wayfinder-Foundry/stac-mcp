from __future__ import annotations

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
        return xr.open_zarr(href, storage_options=storage_options, consolidated=True)

    # Parquet path
    if prefer_dask:
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

    pdf = pd.read_parquet(href, storage_options=storage_options, engine=engine)
    return pdf.to_xarray()
