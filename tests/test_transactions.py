"""Tests for STAC Transaction operations."""

from unittest.mock import MagicMock, patch

import pytest

from stac_mcp.tools.client import STACClient


@pytest.fixture
def client():
    """Set up test client and mock data."""
    client = STACClient(catalog_url="http://test-stac-api.com")
    client._conformance = [  # noqa: SLF001
        "https://api.stacspec.org/v1.0.0/collections#transaction",
    ]
    return client


@pytest.fixture
def item():
    """Mock item data."""
    return {"collection": "test-collection", "id": "test-item"}


@pytest.fixture
def collection():
    """Mock collection data."""
    return {"id": "test-collection"}


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_create_item_success(mock_urlopen, client, item):
    """Test successful item creation."""
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"status": "success"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    response = client.create_item("test-collection", item)
    assert response == {"status": "success"}
    mock_urlopen.assert_called_once()


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_update_item_success(mock_urlopen, client, item):
    """Test successful item update."""
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"status": "success"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    response = client.update_item(item)
    assert response == {"status": "success"}
    mock_urlopen.assert_called_once()


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_delete_item_success(mock_urlopen, client):
    """Test successful item deletion."""
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"status": "success"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    response = client.delete_item("test-collection", "test-item")
    assert response == {"status": "success"}
    mock_urlopen.assert_called_once()


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_create_collection_success(mock_urlopen, client, collection):
    """Test successful collection creation."""
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"status": "success"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    response = client.create_collection(collection)
    assert response == {"status": "success"}
    mock_urlopen.assert_called_once()


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_update_collection_success(mock_urlopen, client, collection):
    """Test successful collection update."""
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"status": "success"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    response = client.update_collection(collection)
    assert response == {"status": "success"}
    mock_urlopen.assert_called_once()


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_delete_collection_success(mock_urlopen, client):
    """Test successful collection deletion."""
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"status": "success"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    response = client.delete_collection("test-collection")
    assert response == {"status": "success"}
    mock_urlopen.assert_called_once()


def test_update_item_missing_id_raises_error(client):
    """Test that updating an item with a missing ID raises a ValueError."""
    with pytest.raises(
        ValueError, match=r"Item must have 'collection' and 'id' fields for update.",
    ):
        client.update_item({"collection": "test-collection"})


def test_update_item_missing_collection_raises_error(client):
    """Test that updating an item with a missing collection raises a ValueError."""
    with pytest.raises(
        ValueError, match=r"Item must have 'collection' and 'id' fields for update.",
    ):
        client.update_item({"id": "test-item"})
