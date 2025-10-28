from unittest.mock import MagicMock, patch

import pytest
import requests

from stac_mcp.tools.client import (
    ConnectionFailedError,
    STACClient,
    STACTimeoutError,
)


@patch("pystac_client.Client")
def test_create_item_success(mock_pystac_client):  # noqa: ARG001
    client = STACClient(catalog_url="https://stac.example.com")
    with patch.object(client, "_do_transaction") as mock_do_transaction:
        mock_do_transaction.return_value = {"type": "Feature", "id": "test-item"}
        item_data = {
            "id": "test-item",
            "type": "Feature",
            "collection": "test-collection",
        }
        response = client.create_item("test-collection", item_data)
        assert response["id"] == "test-item"
        mock_do_transaction.assert_called_once()


@patch("pystac_client.Client")
def test_update_item_success(mock_pystac_client):  # noqa: ARG001
    client = STACClient(catalog_url="https://stac.example.com")
    with patch.object(client, "_do_transaction") as mock_do_transaction:
        mock_do_transaction.return_value = {
            "type": "Feature",
            "id": "test-item",
            "properties": {"updated": True},
        }
        item_data = {
            "id": "test-item",
            "type": "Feature",
            "collection": "test-collection",
        }
        response = client.update_item(item_data)
        assert response["properties"]["updated"] is True
        mock_do_transaction.assert_called_once()


@patch("pystac_client.Client")
def test_delete_item_success(mock_pystac_client):  # noqa: ARG001
    client = STACClient(catalog_url="https://stac.example.com")
    with patch.object(client, "_do_transaction") as mock_do_transaction:
        mock_do_transaction.return_value = {"message": "item deleted"}
        response = client.delete_item("test-collection", "test-item")
        assert response["message"] == "item deleted"
        mock_do_transaction.assert_called_once()


@patch("pystac_client.Client")
def test_create_collection_success(mock_pystac_client):  # noqa: ARG001
    client = STACClient(catalog_url="https://stac.example.com")
    with patch.object(client, "_do_transaction") as mock_do_transaction:
        mock_do_transaction.return_value = {
            "id": "test-collection",
            "description": "A test collection",
        }
        collection_data = {"id": "test-collection", "description": "A test collection"}
        response = client.create_collection(collection_data)
        assert response["id"] == "test-collection"
        mock_do_transaction.assert_called_once()


@patch("pystac_client.Client")
def test_update_collection_success(mock_pystac_client):  # noqa: ARG001
    client = STACClient(catalog_url="https://stac.example.com")
    with patch.object(client, "_do_transaction") as mock_do_transaction:
        mock_do_transaction.return_value = {
            "id": "test-collection",
            "description": "An updated collection",
        }
        collection_data = {
            "id": "test-collection",
            "description": "An updated collection",
        }
        response = client.update_collection(collection_data)
        assert response["description"] == "An updated collection"
        mock_do_transaction.assert_called_once()


@patch("pystac_client.Client")
def test_delete_collection_success(mock_pystac_client):  # noqa: ARG001
    client = STACClient(catalog_url="https://stac.example.com")
    with patch.object(client, "_do_transaction") as mock_do_transaction:
        mock_do_transaction.return_value = {"message": "collection deleted"}
        response = client.delete_collection("test-collection")
        assert response["message"] == "collection deleted"
        mock_do_transaction.assert_called_once()


@patch("pystac_client.Client")
def test_update_item_value_error(mock_pystac_client):  # noqa: ARG001
    client = STACClient(catalog_url="https://stac.example.com")
    with pytest.raises(ValueError, match="collection"):
        client.update_item({"id": "foo"})
    with pytest.raises(ValueError, match="id"):
        client.update_item({"collection": "bar"})


@patch("pystac_client.Client")
def test_do_transaction_timeout(mock_pystac_client):  # noqa: ARG001
    client = STACClient(catalog_url="https://stac.example.com")
    _ = client.client
    with patch.object(
        client.client._stac_io.session,  # noqa: SLF001
        "request",
        side_effect=requests.exceptions.Timeout,
    ), pytest.raises(STACTimeoutError):
        client._do_transaction("post", "https://stac.example.com/items")  # noqa: SLF001


@patch("pystac_client.Client")
def test_do_transaction_connection_error(mock_pystac_client):  # noqa: ARG001
    client = STACClient(catalog_url="https://stac.example.com")
    _ = client.client
    with patch.object(
        client.client._stac_io.session,  # noqa: SLF001
        "request",
        side_effect=requests.exceptions.ConnectionError,
    ), pytest.raises(ConnectionFailedError):
        client._do_transaction("post", "https://stac.example.com/items")  # noqa: SLF001


@patch("pystac_client.Client")
def test_do_transaction_404(mock_pystac_client):  # noqa: ARG001
    client = STACClient(catalog_url="https://stac.example.com")
    _ = client.client
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 404
    with patch.object(
        client.client._stac_io.session, "request", return_value=mock_response  # noqa: SLF001
    ):
        result = client._do_transaction(  # noqa: SLF001
            "get", "https://stac.example.com/items/1"
        )
        assert result is None


@patch("pystac_client.Client")
def test_do_transaction_request_exception(mock_pystac_client):  # noqa: ARG001
    client = STACClient(catalog_url="https://stac.example.com")
    _ = client.client
    with patch.object(
        client.client._stac_io.session,  # noqa: SLF001
        "request",
        side_effect=requests.exceptions.RequestException,
    ), pytest.raises(requests.exceptions.RequestException):
        client._do_transaction("post", "https://stac.example.com/items")  # noqa: SLF001


@patch("pystac_client.Client")
def test_do_transaction_invalidation(mock_pystac_client):  # noqa: ARG001
    client = STACClient(catalog_url="https://stac.example.com/")
    _ = client.client
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 200
    mock_response.content = b'{"id": "test"}'
    mock_response.json.return_value = {"id": "test"}

    with patch.object(client, "_invalidate_cache") as mock_invalidate, patch.object(
        client.client._stac_io.session, "request", return_value=mock_response  # noqa: SLF001
    ):
        client._do_transaction(  # noqa: SLF001
            "post", "https://stac.example.com/collections/c1/items"
        )
        mock_invalidate.assert_called_once_with(["c1"])


@patch("pystac_client.Client")
def test_do_transaction_no_content(mock_pystac_client):  # noqa: ARG001
    client = STACClient(catalog_url="https://stac.example.com/")
    _ = client.client
    mock_response = MagicMock(spec=requests.Response)
    mock_response.status_code = 204
    mock_response.content = None

    with patch.object(
        client.client._stac_io.session, "request", return_value=mock_response  # noqa: SLF001
    ):
        result = client._do_transaction(  # noqa: SLF001
            "delete", "https://stac.example.com/collections/c1/items/i1"
        )
        assert result is None
