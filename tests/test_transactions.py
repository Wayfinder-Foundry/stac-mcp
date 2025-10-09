"""Tests for STAC Transaction operations."""

from unittest.mock import patch

import pytest


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_create_item_success(
    mock_urlopen,
    stac_transactions_client,
    item_payload_factory,
    http_response_factory,
):
    """Test successful item creation."""
    mock_urlopen.return_value = http_response_factory({"status": "success"})

    item_payload = item_payload_factory()
    response = stac_transactions_client.create_item("test-collection", item_payload)
    assert response == {"status": "success"}
    mock_urlopen.assert_called_once()


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_update_item_success(
    mock_urlopen,
    stac_transactions_client,
    item_payload_factory,
    http_response_factory,
):
    """Test successful item update."""
    mock_urlopen.return_value = http_response_factory({"status": "success"})

    item_payload = item_payload_factory()
    response = stac_transactions_client.update_item(item_payload)
    assert response == {"status": "success"}
    mock_urlopen.assert_called_once()


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_delete_item_success(
    mock_urlopen,
    stac_transactions_client,
    http_response_factory,
):
    """Test successful item deletion."""
    mock_urlopen.return_value = http_response_factory({"status": "success"})

    response = stac_transactions_client.delete_item("test-collection", "test-item")
    assert response == {"status": "success"}
    mock_urlopen.assert_called_once()


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_create_collection_success(
    mock_urlopen,
    stac_transactions_client,
    collection_payload_factory,
    http_response_factory,
):
    """Test successful collection creation."""
    mock_urlopen.return_value = http_response_factory({"status": "success"})

    collection_payload = collection_payload_factory()
    response = stac_transactions_client.create_collection(collection_payload)
    assert response == {"status": "success"}
    mock_urlopen.assert_called_once()


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_update_collection_success(
    mock_urlopen,
    stac_transactions_client,
    collection_payload_factory,
    http_response_factory,
):
    """Test successful collection update."""
    mock_urlopen.return_value = http_response_factory({"status": "success"})

    collection_payload = collection_payload_factory()
    response = stac_transactions_client.update_collection(collection_payload)
    assert response == {"status": "success"}
    mock_urlopen.assert_called_once()


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_delete_collection_success(
    mock_urlopen,
    stac_transactions_client,
    http_response_factory,
):
    """Test successful collection deletion."""
    mock_urlopen.return_value = http_response_factory({"status": "success"})

    response = stac_transactions_client.delete_collection("test-collection")
    assert response == {"status": "success"}
    mock_urlopen.assert_called_once()


def test_update_item_missing_id_raises_error(stac_transactions_client):
    """Test that updating an item with a missing ID raises a ValueError."""
    with pytest.raises(
        ValueError,
        match=r"Item must have 'collection' and 'id' fields for update.",
    ):
        stac_transactions_client.update_item({"collection": "test-collection"})


def test_update_item_missing_collection_raises_error(stac_transactions_client):
    """Test that updating an item with a missing collection raises a ValueError."""
    with pytest.raises(
        ValueError,
        match=r"Item must have 'collection' and 'id' fields for update.",
    ):
        stac_transactions_client.update_item({"id": "test-item"})
