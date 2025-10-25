from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pandas as pd
import xarray as xr

from stac_mcp.utils import tabular, today


def test_get_today_date_monkeypatched():
    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2025, 10, 22, 12, 0, 0, tzinfo=tz)

    with patch("stac_mcp.utils.today.datetime", FixedDatetime):
        assert today.get_today_date() == "2025-10-22"


def test_load_tabular_asset_zarr(monkeypatch):
    called = {}

    def fake_open_zarr(href, _storage_options=None, _consolidated=False):
        called["zarr"] = href
        return xr.Dataset()

    monkeypatch.setattr(xr, "open_zarr", fake_open_zarr)

    ds = tabular.load_tabular_asset_as_xarray("s3://bucket/data.zarr")
    assert isinstance(ds, xr.Dataset)
    assert called["zarr"] == "s3://bucket/data.zarr"


def test_load_tabular_asset_parquet_pandas(monkeypatch):
    class FakeDF:
        def to_xarray(self):
            return xr.Dataset()

    def fake_read_parquet(_href, _storage_options=None, _engine=None):
        return FakeDF()

    monkeypatch.setattr(pd, "read_parquet", fake_read_parquet)

    ds = tabular.load_tabular_asset_as_xarray(
        "s3://bucket/data.parquet", prefer_dask=False
    )
    assert isinstance(ds, xr.Dataset)


def test_load_tabular_asset_parquet_dask(monkeypatch):
    # Provide a fake dask dataframe with get_partition and compute
    class FakePDF:
        def to_xarray(self):
            return xr.Dataset()

    class FakeDDF:
        def get_partition(self, _idx):
            return self

        def compute(self):
            return FakePDF()

    def fake_dd_read_parquet(_href, _storage_options=None, _engine=None):
        return FakeDDF()

    monkeypatch.setattr(tabular.dd, "read_parquet", fake_dd_read_parquet)

    ds = tabular.load_tabular_asset_as_xarray(
        "s3://bucket/data.parquet", prefer_dask=True
    )
    assert isinstance(ds, xr.Dataset)


def test_load_tabular_asset_parquet_dask_partition_and_compute(monkeypatch):
    # Ensure both dask_partition and compute branches are exercised
    events = {"partition_called": None, "compute_called": False}

    class FakePDF:
        def to_xarray(self):
            return xr.Dataset()

    class FakeDDF:
        def __init__(self):
            self.partition_idx = None

        def get_partition(self, idx):
            events["partition_called"] = idx
            self.partition_idx = idx
            return self

        def compute(self):
            events["compute_called"] = True
            return FakePDF()

    def fake_dd_read_parquet(_href, _storage_options=None, _engine=None):
        return FakeDDF()

    monkeypatch.setattr(tabular.dd, "read_parquet", fake_dd_read_parquet)

    # explicit partition
    partition_idx = 2
    ds1 = tabular.load_tabular_asset_as_xarray(
        "s3://bucket/data.parquet", prefer_dask=True, dask_partition=partition_idx
    )
    assert isinstance(ds1, xr.Dataset)
    assert events["partition_called"] == partition_idx

    # compute all
    events["partition_called"] = None
    events["compute_called"] = False
    ds2 = tabular.load_tabular_asset_as_xarray(
        "s3://bucket/data.parquet", prefer_dask=True, compute=True
    )
    assert isinstance(ds2, xr.Dataset)
    assert events["compute_called"] is True
