import re
from unittest.mock import patch

import pytest

from stac_mcp.tools import estimate_data_size as eds
from stac_mcp.tools.client import STACClient
from stac_mcp.tools.estimate_data_size import handle_estimate_data_size
from stac_mcp.utils.tabular import load_tabular_asset_as_xarray
from stac_mcp.utils.today import get_today_date


def test_tabular_stub_raises():
    """Ensure the removed tabular helper raises a clear NotImplementedError."""
    with pytest.raises(NotImplementedError) as excinfo:
        load_tabular_asset_as_xarray()
    assert "Parquet/Zarr tabular helpers have been removed" in str(excinfo.value)


def test_get_today_date_format():
    """get_today_date should return ISO YYYY-MM-DD string."""
    s = get_today_date()
    assert isinstance(s, str)
    assert re.match(r"^\d{4}-\d{2}-\d{2}$", s)


@patch("stac_mcp.tools.client.STACClient.estimate_data_size")
def test_estimator_advisory_included(mock_estimate):
    """When dtype_size_preferences is available, its advisory should be appended."""
    mock_estimate.return_value = {
        "item_count": 1,
        "estimated_size_bytes": 1024,
        "estimated_size_mb": 0.0009765625,
        "collections": ["c"],
        "bbox_used": None,
        "temporal_extent": None,
        "clipped_to_aoi": False,
        "message": "ok",
        "assets_analyzed": [],
    }

    # Monkeypatch the advisory provider to return a known string
    original = getattr(eds, "dtype_size_preferences", None)
    eds.dtype_size_preferences = lambda: "Prefer uint16 where possible"
    try:
        client = STACClient()
        txt = handle_estimate_data_size(client, {"collections": ["c"]})
        assert "Estimator Advisory" in txt[0].text
        assert "Prefer uint16 where possible" in txt[0].text
    finally:
        # restore original to avoid test cross-talk
        eds.dtype_size_preferences = original
