"""Tests for STAC Transaction operations."""

import unittest
from unittest.mock import MagicMock, patch

from stac_mcp.tools.client import STACClient


class TestTransactions(unittest.TestCase):
    """Test cases for STAC transaction operations."""

    def setUp(self):
        """Set up test client and mock data."""
        self.client = STACClient(catalog_url="http://test-stac-api.com")
        self.client._conformance = [
            "https://api.stacspec.org/v1.0.0/collections#transaction"
        ]
        self.item = {"collection": "test-collection", "id": "test-item"}
        self.collection = {"id": "test-collection"}

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_create_item_success(self, mock_urlopen):
        """Test successful item creation."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "success"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        response = self.client.create_item("test-collection", self.item)
        self.assertEqual(response, {"status": "success"})
        mock_urlopen.assert_called_once()

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_update_item_success(self, mock_urlopen):
        """Test successful item update."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "success"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        response = self.client.update_item(self.item)
        self.assertEqual(response, {"status": "success"})
        mock_urlopen.assert_called_once()

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_delete_item_success(self, mock_urlopen):
        """Test successful item deletion."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "success"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        response = self.client.delete_item("test-collection", "test-item")
        self.assertEqual(response, {"status": "success"})
        mock_urlopen.assert_called_once()

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_create_collection_success(self, mock_urlopen):
        """Test successful collection creation."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "success"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        response = self.client.create_collection(self.collection)
        self.assertEqual(response, {"status": "success"})
        mock_urlopen.assert_called_once()

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_update_collection_success(self, mock_urlopen):
        """Test successful collection update."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "success"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        response = self.client.update_collection(self.collection)
        self.assertEqual(response, {"status": "success"})
        mock_urlopen.assert_called_once()

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_delete_collection_success(self, mock_urlopen):
        """Test successful collection deletion."""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "success"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        response = self.client.delete_collection("test-collection")
        self.assertEqual(response, {"status": "success"})
        mock_urlopen.assert_called_once()

    def test_update_item_missing_id_raises_error(self):
        """Test that updating an item with a missing ID raises a ValueError."""
        with self.assertRaises(ValueError):
            self.client.update_item({"collection": "test-collection"})

    def test_update_item_missing_collection_raises_error(self):
        """Test that updating an item with a missing collection raises a ValueError."""
        with self.assertRaises(ValueError):
            self.client.update_item({"id": "test-item"})

if __name__ == "__main__":
    unittest.main()