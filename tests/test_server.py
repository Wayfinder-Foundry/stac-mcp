"""Test STAC MCP Server functionality."""

from unittest.mock import ANY, Mock, patch

import pytest

from stac_mcp.server import STACClient


class TestSTACClient:
    """Test STACClient functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = STACClient()

    def test_init(self):
        """Test STACClient initialization."""
        assert (
            self.client.catalog_url
            == "https://planetarycomputer.microsoft.com/api/stac/v1"
        )
        assert self.client._client is None  # noqa: SLF001

    @patch("stac_mcp.server.Client")
    def test_client_property(self, mock_client_cls):
        """Test client property creates and caches client."""
        mock_client = Mock()
        mock_client_cls.open.return_value = mock_client

        # First access should create client
        client = self.client.client
        assert client == mock_client
        mock_client_cls.open.assert_called_once_with(self.client.catalog_url, stac_io=ANY)

        # Second access should return cached client
        client2 = self.client.client
        assert client2 == mock_client
        assert mock_client_cls.open.call_count == 1

    @patch("stac_mcp.server.Client")
    def test_search_collections(self, mock_client_cls):
        """Test search_collections method."""
        # Mock collection
        mock_collection = Mock()
        mock_collection.id = "test-collection"
        mock_collection.title = "Test Collection"
        mock_collection.description = "A test collection"
        mock_collection.extent = None
        mock_collection.license = "MIT"
        mock_collection.providers = []

        # Mock client
        mock_client = Mock()
        mock_client.get_collections.return_value = [mock_collection]
        mock_client_cls.open.return_value = mock_client

        # Test the method
        collections = self.client.search_collections(limit=1)

        assert len(collections) == 1
        assert collections[0]["id"] == "test-collection"
        assert collections[0]["title"] == "Test Collection"
        assert collections[0]["description"] == "A test collection"
        assert collections[0]["license"] == "MIT"

    @patch("stac_mcp.server.Client")
    def test_custom_catalog_url(self, mock_client_cls):
        """Test STACClient with custom catalog URL."""
        custom_url = "https://example.com/stac/v1"
        client = STACClient(custom_url)

        assert client.catalog_url == custom_url

        mock_client = Mock()
        mock_client_cls.open.return_value = mock_client

        # Access client property to trigger creation
        _ = client.client
        mock_client_cls.open.assert_called_once_with(custom_url, stac_io=ANY)

    def test_estimate_data_size_no_odc_stac(self):
        """Test estimate_data_size when odc.stac is not available."""
        with patch("stac_mcp.server.ODC_STAC_AVAILABLE", False):
            client = STACClient()
            with pytest.raises(
                RuntimeError,
                match=r"odc\.stac is not available",
            ):
                client.estimate_data_size(collections=["test"])