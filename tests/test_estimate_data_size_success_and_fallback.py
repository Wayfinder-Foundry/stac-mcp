from unittest.mock import MagicMock, patch

from stac_mcp.tools.client import STACClient

ASSET_1_SIZE = 1024
ASSET_2_SIZE = 2048
EXPECTED_ASSETS = 2


@patch("stac_mcp.tools.client.STACClient._cached_search")
@patch("stac_mcp.tools.client.STACClient._head_content_length")
def test_estimate_data_size_success(mock_head, mock_search):
    """Verify data size estimation success with a mix of metadata and HEAD."""
    client = STACClient()
    mock_search.return_value = [
        MagicMock(
            assets={
                "asset1": {"extra_fields": {"file:size": ASSET_1_SIZE}},
                "asset2": {"href": "http://test.com/asset2.tif"},
            }
        )
    ]
    mock_head.return_value = ASSET_2_SIZE

    result = client.estimate_data_size(collections=["test"])
    assert result["estimated_size_bytes"] == ASSET_1_SIZE + ASSET_2_SIZE
    assert result["item_count"] == 1
    assert len(result["assets_analyzed"]) == EXPECTED_ASSETS
    assert result["assets_analyzed"][0]["method"] == "metadata"
    assert result["assets_analyzed"][1]["method"] == "head"
