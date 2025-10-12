"""Tests for STAC Transaction operations."""

from unittest.mock import patch

import pytest

from stac_mcp.tools.transactions import (
    handle_create_collection,
    handle_create_item,
    handle_delete_collection,
    handle_delete_item,
    handle_update_collection,
    handle_update_item,
)


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


# ======================== Transaction Handler Tests ========================


def test_handle_create_item(stac_transactions_client, item_payload_factory):
    """Test handle_create_item handler."""
    item_payload = item_payload_factory()
    arguments = {
        "collection_id": "test-collection",
        "item": item_payload,
    }

    with patch.object(stac_transactions_client, "create_item") as mock_create:
        mock_create.return_value = {"status": "success"}
        result = handle_create_item(stac_transactions_client, arguments)

        assert result == {"status": "success"}
        mock_create.assert_called_once_with("test-collection", item_payload)


def test_handle_update_item(stac_transactions_client, item_payload_factory):
    """Test handle_update_item handler."""
    item_payload = item_payload_factory()
    arguments = {"item": item_payload}

    with patch.object(stac_transactions_client, "update_item") as mock_update:
        mock_update.return_value = {"status": "success"}
        result = handle_update_item(stac_transactions_client, arguments)

        assert result == {"status": "success"}
        mock_update.assert_called_once_with(item_payload)


def test_handle_delete_item(stac_transactions_client):
    """Test handle_delete_item handler."""
    arguments = {
        "collection_id": "test-collection",
        "item_id": "test-item",
    }

    with patch.object(stac_transactions_client, "delete_item") as mock_delete:
        mock_delete.return_value = {"status": "success"}
        result = handle_delete_item(stac_transactions_client, arguments)

        assert result == {"status": "success"}
        mock_delete.assert_called_once_with("test-collection", "test-item")


def test_handle_create_collection(stac_transactions_client, collection_payload_factory):
    """Test handle_create_collection handler."""
    collection_payload = collection_payload_factory()
    arguments = {"collection": collection_payload}

    with patch.object(stac_transactions_client, "create_collection") as mock_create:
        mock_create.return_value = {"status": "success"}
        result = handle_create_collection(stac_transactions_client, arguments)

        assert result == {"status": "success"}
        mock_create.assert_called_once_with(collection_payload)


def test_handle_update_collection(stac_transactions_client, collection_payload_factory):
    """Test handle_update_collection handler."""
    collection_payload = collection_payload_factory()
    arguments = {"collection": collection_payload}

    with patch.object(stac_transactions_client, "update_collection") as mock_update:
        mock_update.return_value = {"status": "success"}
        result = handle_update_collection(stac_transactions_client, arguments)

        assert result == {"status": "success"}
        mock_update.assert_called_once_with(collection_payload)


def test_handle_delete_collection(stac_transactions_client):
    """Test handle_delete_collection handler."""
    arguments = {"collection_id": "test-collection"}

    with patch.object(stac_transactions_client, "delete_collection") as mock_delete:
        mock_delete.return_value = {"status": "success"}
        result = handle_delete_collection(stac_transactions_client, arguments)

        assert result == {"status": "success"}
        mock_delete.assert_called_once_with("test-collection")



