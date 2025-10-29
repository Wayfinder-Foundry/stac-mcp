from unittest.mock import MagicMock, patch

from stac_mcp.tools.client import STACClient
from stac_mcp.tools.execution import Session

ASSET_1_SIZE = 1024


def test_stac_client_init():
    """Verify STACClient initialization."""
    client = STACClient()
    assert client.catalog_url is not None


def test_stac_client_session_dependency():
    """Verify that the STAC client is correctly injected into the session."""
    session = Session(client=MagicMock())
    stac_client = session.stac_client
    assert isinstance(stac_client, STACClient)


@patch("stac_mcp.tools.client.STACClient._cached_search")
def test_estimate_data_size_no_items(mock_cached_search):
    """Test data size estimation when no items are returned."""
    mock_cached_search.return_value = []
    client = STACClient()
    result = client.estimate_data_size(collections=["test"])
    assert result["item_count"] == 0
    assert result["estimated_size_bytes"] == 0


@patch("stac_mcp.tools.client.STACClient._cached_search")
def test_estimate_data_size_with_metadata(mock_cached_search):
    """Test data size estimation using metadata."""
    client = STACClient()
    mock_item = MagicMock()
    mock_item.assets = {"asset1": {"extra_fields": {"file:size": ASSET_1_SIZE}}}
    mock_cached_search.return_value = [mock_item]

    result = client.estimate_data_size(collections=["test"])
    assert result["estimated_size_bytes"] == ASSET_1_SIZE


@patch("stac_mcp.tools.client.STACClient._cached_search")
def test_estimate_data_size_with_head_request(mock_cached_search):
    """Test data size estimation using HEAD requests."""
    client = STACClient()
    mock_item = MagicMock()
    asset_size = 2048
    mock_item.assets = {
        "asset1": {"href": "http://test.com/asset1.tif", "media_type": "image/tiff"}
    }
    mock_cached_search.return_value = [mock_item]

    with patch.object(
        client._head_session,  # noqa: SLF001
        "request",
        return_value=MagicMock(headers={"Content-Length": str(asset_size)}),
    ):
        result = client.estimate_data_size(collections=["test"])
        assert result["estimated_size_bytes"] == asset_size
