"""Extra tests for stac_mcp/tools/client.py."""

from unittest.mock import MagicMock, patch

import pytest

from stac_mcp.tools.client import STACClient


@pytest.fixture
def client():
    """Fixture for STACClient."""
    with patch("pystac_client.Client.open", return_value=MagicMock()):
        c = STACClient(catalog_url="https://example.com")
        c._search_cache = {}  # noqa: SLF001
        c.headers = {}
        yield c


def test_client_init_with_defaults():
    """Test STACClient.__init__ with default values."""
    with patch("pystac_client.Client.open", return_value=MagicMock()):
        client = STACClient()
        assert (
            client.catalog_url == "https://planetarycomputer.microsoft.com/api/stac/v1"
        )
        assert client.headers == {}

        default_timeout = 20
        default_max_workers = 4
        default_retries = 1
        default_backoff_base = 0.05

        assert client.head_timeout_seconds == default_timeout
        assert client.head_max_workers == default_max_workers
        assert client.head_retries == default_retries
        assert client.head_backoff_base == default_backoff_base
        assert client.head_backoff_jitter is True


def test_search_cache_key(client: STACClient):
    """Test _search_cache_key."""
    key = client._search_cache_key(  # noqa: SLF001
        collections=["test"],
        bbox=[0, 0, 1, 1],
        datetime="2022-01-01T00:00:00Z",
        query={"key": "value"},
        limit=10,
    )
    assert isinstance(key, str)


def test_invalidate_cache(client: STACClient):
    """Test _invalidate_cache."""
    client._search_cache = {"test": (0, [])}  # noqa: SLF001
    client._invalidate_cache()  # noqa: SLF001
    assert not client._search_cache  # noqa: SLF001


def test_invalidate_cache_with_collections(client: STACClient):
    """Test _invalidate_cache with collections."""
    client._search_cache = {"collection1": (0, []), "collection2": (0, [])}  # noqa: SLF001
    client._invalidate_cache(affected_collections=["collection1"])  # noqa: SLF001
    assert "collection2" in client._search_cache  # noqa: SLF001
    assert "collection1" not in client._search_cache  # noqa: SLF001


def test_asset_to_dict(client: STACClient):
    """Test _asset_to_dict."""
    asset = MagicMock()
    asset.to_dict.return_value = {"key": "value"}
    result = client._asset_to_dict(asset)  # noqa: SLF001
    assert result == {"key": "value"}


def test_size_from_metadata(client: STACClient):
    """Test _size_from_metadata."""
    file_size = 123
    asset_obj = {"file:size": file_size}
    result = client._size_from_metadata(asset_obj)  # noqa: SLF001
    assert result == file_size


@patch("stac_mcp.tools.client.STACClient._head_content_length")
def test_parallel_head_content_lengths(
    mock_head_content_length: MagicMock, client: STACClient
):
    """Test _parallel_head_content_lengths."""
    mock_head_content_length.return_value = 123
    hrefs = ["https://example.com"]
    result = client._parallel_head_content_lengths(hrefs)  # noqa: SLF001
    assert result == {"https://example.com": 123}


def test_sign_href(client: STACClient):
    """Test _sign_href."""
    href = "https://example.com"
    result = client._sign_href(href)  # noqa: SLF001
    assert result == href


@patch("requests.Session.request")
def test_head_content_length(mock_request: MagicMock, client: STACClient):
    """Test _head_content_length."""
    mock_response = MagicMock()
    content_length = "123"
    mock_response.headers = {"Content-Length": content_length}
    mock_request.return_value = mock_response

    result = client._head_content_length("https://example.com")  # noqa: SLF001
    assert result == int(content_length)
