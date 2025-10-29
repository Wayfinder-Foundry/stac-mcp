from unittest.mock import patch

from stac_mcp.tools.client import STACClient
from stac_mcp.tools.estimate_data_size import handle_estimate_data_size


@patch("stac_mcp.tools.client.STACClient.estimate_data_size")
def test_estimate_data_size_text_success(mock_estimate):
    """Verify the text output of the data size estimation tool on success."""
    mock_estimate.return_value = {
        "item_count": 1,
        "estimated_size_bytes": 1024,
        "estimated_size_mb": 0.001,
        "estimated_size_gb": 0.0,
        "collections": ["test"],
        "bbox_used": [0, 0, 1, 1],
        "temporal_extent": "2021-01-01/2021-01-02",
        "clipped_to_aoi": False,
        "message": "Success",
        "assets_analyzed": [],
    }
    client = STACClient()
    result = handle_estimate_data_size(
        client, {"collections": ["test"], "bbox": [0, 0, 1, 1]}
    )
    assert "Data Size Estimation" in result[0].text
    assert "Items analyzed: 1" in result[0].text


@patch("stac_mcp.tools.client.STACClient.estimate_data_size")
def test_estimate_data_size_text_aoi_clipping(mock_estimate):
    """Ensure AOI clipping is reflected in the text output."""
    mock_estimate.return_value = {
        "item_count": 1,
        "estimated_size_bytes": 1024,
        "estimated_size_mb": 0.001,
        "estimated_size_gb": 0.0,
        "collections": ["test"],
        "bbox_used": None,
        "temporal_extent": None,
        "clipped_to_aoi": True,
        "message": "Success",
        "assets_analyzed": [],
    }
    client = STACClient()
    result = handle_estimate_data_size(client, {"collections": ["test"]})
    assert "Clipped to AOI: Yes" in result[0].text


@patch("stac_mcp.tools.client.STACClient.estimate_data_size")
def test_estimate_data_size_text_no_items(mock_estimate):
    """Verify text output when no items are found."""
    mock_estimate.return_value = {
        "item_count": 0,
        "estimated_size_bytes": 0,
        "estimated_size_mb": 0.0,
        "estimated_size_gb": 0.0,
        "collections": ["test"],
        "bbox_used": None,
        "temporal_extent": None,
        "clipped_to_aoi": False,
        "message": "No items found",
    }
    client = STACClient()
    result = handle_estimate_data_size(client, {"collections": ["test"]})
    assert "No items found" in result[0].text
