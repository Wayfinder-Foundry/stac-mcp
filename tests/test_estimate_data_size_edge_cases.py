from unittest.mock import patch

from stac_mcp.tools.client import STACClient
from stac_mcp.tools.estimate_data_size import handle_estimate_data_size


@patch("stac_mcp.tools.client.STACClient.estimate_data_size")
def test_missing_sensor_native_keys(mock_estimate):
    """When sensor-native keys are absent, the handler should show 'n/a'."""
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
    client = STACClient()
    txt = handle_estimate_data_size(client, {"collections": ["c"]})
    assert isinstance(txt, list)
    assert "Sensor-native estimated size: n/a" in txt[0].text


@patch("stac_mcp.tools.client.STACClient.estimate_data_size")
def test_none_estimated_bytes_shows_na(mock_estimate):
    """If estimated bytes are None, the text should show
    Raw bytes: n/a and the JSON payload should contain None.
    """
    mock_estimate.return_value = {
        "item_count": 0,
        "estimated_size_bytes": None,
        "estimated_size_mb": None,
        "collections": ["c"],
        "bbox_used": None,
        "temporal_extent": None,
        "clipped_to_aoi": False,
        "message": "no items",
        "assets_analyzed": [],
    }
    client = STACClient()
    txt = handle_estimate_data_size(client, {"collections": ["c"]})
    assert "Raw bytes: n/a" in txt[0].text
    js = handle_estimate_data_size(
        client, {"collections": ["c"], "output_format": "json"}
    )
    assert js["queried_totals"]["bytes"] is None


@patch("stac_mcp.tools.client.STACClient.estimate_data_size")
def test_data_variables_fallback_to_estimated_bytes(mock_estimate):
    """data_variables with 'estimated_bytes' should be converted
    to MB in the text output.
    """
    mock_estimate.return_value = {
        "item_count": 1,
        "estimated_size_bytes": 1048576,
        "estimated_size_mb": 1.0,
        "collections": ["c"],
        "bbox_used": None,
        "temporal_extent": None,
        "clipped_to_aoi": False,
        "message": "ok",
        "assets_analyzed": [],
        "data_variables": [
            {
                "variable": "v1",
                "estimated_bytes": 1048576,
                "shape": [1, 1],
                "dtype": "float32",
            }
        ],
    }
    client = STACClient()
    txt = handle_estimate_data_size(client, {"collections": ["c"]})
    assert "v1: 1.00 MB" in txt[0].text
