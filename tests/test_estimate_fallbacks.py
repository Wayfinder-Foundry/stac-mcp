from types import SimpleNamespace
from unittest.mock import patch

import pytest

from stac_mcp.tools.client import STACClient

# Conditional import for odc-stac
try:
    from stac_mcp.utils import odc_stac
except ImportError:
    odc_stac = None

# Conditional import for xarray
try:
    import xarray as xr
except ImportError:
    xr = None


def _raise_no_raster(*_args, **_kwargs):
    msg = "don't have raster"
    raise TypeError(msg)


def _make_fake_search(items):
    return SimpleNamespace(items=lambda: items)


@pytest.mark.skipif(xr is None, reason="xarray not installed")
@patch("stac_mcp.tools.client.STACClient._cached_search")
def test_zarr_fallback_inspect(mock_cached_search, tmp_path):
    client = STACClient()
    zarr_asset_size = 24
    zdir = tmp_path / "test.zarr"
    href = f"file://{zdir}"
    asset = {"href": href, "media_type": "application/vnd+zarr"}
    item = SimpleNamespace(
        collection_id="era5-pds", assets={"arr": asset}, datetime=None
    )
    mock_cached_search.return_value = [item]

    with patch.object(
        client,
        "_parallel_head_content_lengths",
        return_value={href: zarr_asset_size},
    ):
        res = client.estimate_data_size(collections=["era5-pds"], limit=10)
        assert res["item_count"] == 1
        assert res["estimated_size_bytes"] >= zarr_asset_size
