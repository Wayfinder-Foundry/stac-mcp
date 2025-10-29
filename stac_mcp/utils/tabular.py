"""Tabular helpers (parquet/zarr) — removed.

This module formerly provided helpers to load Parquet and Zarr assets into
an xarray.Dataset for the estimation fallback path. The parquet/zarr-based
fallback was intentionally removed in this change. To avoid import-time
errors in remaining code or tests, we keep a minimal stub that raises a
clear error if used.
"""

from __future__ import annotations

from typing import Any


def load_tabular_asset_as_xarray(*args: Any, **kwargs: Any):
    """Removed helper.

    Calling this will raise NotImplementedError to make the removal explicit.
    """
    msg = (
        "Parquet/Zarr tabular helpers have been removed — this functionality"
        " is deprecated and will be reintroduced in a dedicated PR if needed."
    )
    raise NotImplementedError(msg)
