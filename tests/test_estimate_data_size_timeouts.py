from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import Timeout

from stac_mcp.tools.client import STACClient, STACTimeoutError


@patch("stac_mcp.tools.client.STACClient._cached_search")
def test_estimate_data_size_head_timeout(mock_cached_search):
    """Verify that a HEAD request timeout is handled gracefully."""
    client = STACClient()
    mock_item = MagicMock()
    mock_item.assets = {
        "asset1": {"href": "http://test.com/asset1.tif", "media_type": "image/tiff"}
    }
    mock_cached_search.return_value = [mock_item]

    with patch.object(
        client._head_session,  # noqa: SLF001
        "request",
        side_effect=Timeout("HEAD request timed out"),
    ):
        result = client.estimate_data_size(collections=["test"])
        assert result["estimated_size_bytes"] == 0
        assert result["assets_analyzed"][0]["method"] == "failed"


@patch("stac_mcp.tools.client.STACClient._cached_search")
def test_estimate_data_size_session_request_timeout(mock_cached_search):
    """Verify that a session request timeout is handled."""
    client = STACClient()
    mock_cached_search.side_effect = STACTimeoutError("Session request timed out")

    with pytest.raises(STACTimeoutError):
        client.estimate_data_size(collections=["test"])
