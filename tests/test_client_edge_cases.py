"""Additional client edge cases and error scenarios."""

from unittest.mock import MagicMock, patch

from stac_mcp.tools.client import STACClient


def stac_catalog_factory():
    return {
        "type": "Catalog",
        "id": "test-catalog",
        "stac_version": "1.0.0",
        "description": "Test Catalog",
        "links": [],
    }


class TestClientInitialization:
    """Test STACClient initialization edge cases."""

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_client_with_trailing_slash(self, mock_read_json):
        """Test client with catalog URL having trailing slash."""
        mock_read_json.return_value = stac_catalog_factory()
        client = STACClient("https://example.com/stac/")
        assert not client.catalog_url.endswith("/stac/")

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_client_without_trailing_slash(self, mock_read_json):
        """Test client with catalog URL without trailing slash."""
        mock_read_json.return_value = stac_catalog_factory()
        client = STACClient("https://example.com/stac")
        assert client.catalog_url == "https://example.com/stac"


class TestHeaderHandling:
    """Test HTTP header handling edge cases."""

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_default_headers_included(self, mock_read_json):
        """Test that default headers are included."""
        mock_read_json.return_value = stac_catalog_factory()
        client = STACClient("https://example.com")
        with patch.object(client.client._stac_io.session, "request") as mock_request:  # noqa: SLF001
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"ok": True}
            mock_request.return_value = mock_response
            client.delete_item("test", "test")
            mock_request.assert_called_once()


class TestSearchOperations:
    """Test search operation edge cases."""

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_search_collections_empty_result(self, mock_read_json):
        """Test search_collections with no results."""
        mock_read_json.return_value = stac_catalog_factory()
        client = STACClient("https://example.com")
        with patch.object(client.client, "get_collections") as mock_get_collections:
            mock_get_collections.return_value = []
            result = client.search_collections()
            assert result == []
            mock_get_collections.assert_called_once()
