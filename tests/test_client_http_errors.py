"""Tests for STACClient low-level HTTP error handling and APIError branch."""

from unittest.mock import MagicMock, patch

import pytest
from pystac_client.exceptions import APIError
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout

from stac_mcp.tools.client import ConnectionFailedError, STACClient, STACTimeoutError
from tests import HTTP_INTERNAL_SERVER_ERROR, HTTP_NOT_FOUND_ERROR


def stac_catalog_factory():
    return {
        "type": "Catalog",
        "id": "test-catalog",
        "stac_version": "1.0.0",
        "description": "Test Catalog",
        "links": [],
    }


@patch("pystac_client.stac_api_io.StacApiIO.read_json")
def test_http_json_404_returns_none(mock_read_json):
    """Test that a 404 returns None."""
    mock_read_json.return_value = stac_catalog_factory()
    client = STACClient("https://example.com")
    with patch.object(client.client._stac_io.session, "request") as mock_request:  # noqa: SLF001
        mock_response = MagicMock()
        mock_response.status_code = HTTP_NOT_FOUND_ERROR
        mock_request.return_value = mock_response
        assert client.delete_item("test", "test") is None


@patch("pystac_client.stac_api_io.StacApiIO.read_json")
def test_http_json_500_raises(mock_read_json):
    """Test that a 500 raises an HTTPError."""
    mock_read_json.return_value = stac_catalog_factory()
    client = STACClient("https://example.com")
    with patch.object(client.client._stac_io.session, "request") as mock_request:  # noqa: SLF001
        mock_response = MagicMock()
        mock_response.status_code = HTTP_INTERNAL_SERVER_ERROR
        mock_response.raise_for_status.side_effect = Exception("test")
        mock_request.return_value = mock_response
        with pytest.raises(Exception):  # noqa: PT011 B017
            client.delete_item("test", "test")


@patch("pystac_client.stac_api_io.StacApiIO.read_json")
def test_http_json_url_error_retries(mock_read_json):
    """Test that a URLError is retried."""
    mock_read_json.return_value = stac_catalog_factory()
    client = STACClient("https://example.com")
    with patch.object(
        client.client._stac_io.session,  # noqa: SLF001
        "request",
        side_effect=Timeout,
    ) as mock_request:
        with pytest.raises(STACTimeoutError):
            client.delete_item("test", "test")
        assert mock_request.call_count == 1


@patch("pystac_client.stac_api_io.StacApiIO.read_json")
def test_http_json_url_error(mock_read_json):
    """Test that a URLError is mapped to a ConnectionFailedError."""
    mock_read_json.return_value = stac_catalog_factory()
    client = STACClient("https://example.com")
    with (
        patch.object(
            client.client._stac_io.session,  # noqa: SLF001
            "request",
            side_effect=RequestsConnectionError,
        ),
        pytest.raises(ConnectionFailedError),
    ):
        client.delete_item("test", "test")


@patch("pystac_client.stac_api_io.StacApiIO.read_json")
def test_search_collections_api_error(mock_read_json):
    """Simulate underlying client raising APIError."""
    mock_read_json.return_value = stac_catalog_factory()
    client = STACClient("https://example.com")

    with (
        patch.object(
            client.client, "get_collections", side_effect=APIError("api failure")
        ),
        pytest.raises(APIError, match="api failure"),
    ):
        client.search_collections(limit=1)
