from unittest.mock import patch

from stac_mcp.tools.client import STACClient
from stac_mcp.tools.estimate_data_size import handle_estimate_data_size

# Named constants to avoid magic-number lint warnings
EXPECTED_QUERIED_BYTES = 4096
EXPECTED_SENSOR_BYTES = 2048


@patch("stac_mcp.tools.client.STACClient.estimate_data_size")
def test_text_includes_sensor_native(mock_estimate):
    mock_estimate.return_value = {
        "item_count": 2,
        "estimated_size_bytes": 2048,
        "estimated_size_mb": 0.001953125,
        "estimated_size_gb": 0.0,
        "sensor_native_estimated_size_bytes": 1024,
        "sensor_native_estimated_size_mb": 0.0009765625,
        "collections": ["c"],
        "bbox_used": None,
        "temporal_extent": None,
        "clipped_to_aoi": False,
        "message": "ok",
        "assets_analyzed": [],
    }
    client = STACClient()
    res = handle_estimate_data_size(client, {"collections": ["c"]})
    assert isinstance(res, list)
    text = res[0].text
    assert "Sensor-native estimated size" in text
    assert "Estimated size" in text


@patch("stac_mcp.tools.client.STACClient.estimate_data_size")
def test_json_includes_sensor_native_totals(mock_estimate):
    mock_estimate.return_value = {
        "item_count": 1,
        "estimated_size_bytes": EXPECTED_QUERIED_BYTES,
        "estimated_size_mb": 0.00390625,
        "sensor_native_estimated_size_bytes": EXPECTED_SENSOR_BYTES,
        "sensor_native_estimated_size_mb": 0.001953125,
        "collections": ["c"],
        "bbox_used": None,
        "temporal_extent": None,
        "clipped_to_aoi": False,
        "message": "ok",
        "assets_analyzed": [],
    }
    client = STACClient()
    res = handle_estimate_data_size(
        client, {"collections": ["c"], "output_format": "json"}
    )
    assert isinstance(res, dict)
    assert res.get("type") == "data_size_estimate"
    assert "estimate" in res
    assert "queried_totals" in res
    assert "sensor_native_totals" in res
    assert res["queried_totals"]["bytes"] == EXPECTED_QUERIED_BYTES
    assert res["sensor_native_totals"]["bytes"] == EXPECTED_SENSOR_BYTES
