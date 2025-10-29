from unittest.mock import MagicMock, patch

from stac_mcp.tools.client import STACClient

ASSET_1_SIZE = 1024
ASSET_2_SIZE = 2048


@patch("stac_mcp.tools.client.STACClient._cached_search")
def test_fallback_estimate_aggregates_metadata(mock_cached_search):
    """Ensure the fallback estimator correctly aggregates file:size metadata."""
    client = STACClient()
    mock_item = MagicMock()
    mock_item.assets = {
        "asset1": {"extra_fields": {"file:size": ASSET_1_SIZE}},
        "asset2": {"extra_fields": {"file:size": ASSET_2_SIZE}},
    }
    mock_cached_search.return_value = [mock_item]

    result = client.estimate_data_size(collections=["test"])
    assert result["estimated_size_bytes"] == ASSET_1_SIZE + ASSET_2_SIZE


@patch("stac_mcp.tools.client.STACClient._cached_search")
def test_fallback_estimate_uses_head_when_needed(mock_cached_search):
    """Verify fallback estimator uses HEAD requests when metadata is missing."""
    client = STACClient()
    mock_item = MagicMock()
    mock_item.assets = {
        "asset1": {"href": "http://test.com/asset1.tif", "media_type": "image/tiff"}
    }
    mock_cached_search.return_value = [mock_item]

    with patch.object(
        client._head_session,  # noqa: SLF001
        "request",
        return_value=MagicMock(headers={"Content-Length": str(ASSET_1_SIZE)}),
    ):
        result = client.estimate_data_size(collections=["test"])
        assert result["estimated_size_bytes"] == ASSET_1_SIZE
