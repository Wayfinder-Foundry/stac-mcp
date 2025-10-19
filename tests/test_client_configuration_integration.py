"""Integration tests for ADR 0007 implementation."""

from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError as RequestsConnectionError, Timeout

from stac_mcp.tools.client import (
    ConnectionFailedError,
    STACClient,
    STACTimeoutError,
)


def stac_catalog_factory():
    return {
        "type": "Catalog",
        "id": "test-catalog",
        "stac_version": "1.0.0",
        "description": "Test Catalog",
        "links": [],
    }


class TestADR0007Integration:
    """Integration tests for complete ADR 0007 compliance."""

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_adr_requirement_per_call_timeout(self, mock_read_json):
        """ADR 0007: Add optional client configuration at call level (timeout)."""
        mock_read_json.return_value = stac_catalog_factory()
        client = STACClient("https://example.com")
        with patch.object(client.client._stac_io.session, "request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"ok": True}
            mock_request.return_value = mock_response
            client.delete_item("test", "test", timeout=120)
            mock_request.assert_called_with(
                "delete",
                "https://example.com/collections/test/items/test",
                headers={"Accept": "application/json"},
                timeout=120,
            )

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_adr_requirement_per_call_headers(self, mock_read_json):
        """ADR 0007: Add optional client configuration at call level (headers)."""
        mock_read_json.return_value = stac_catalog_factory()
        client = STACClient(
            "https://example.com",
            headers={"X-Instance": "value1"},
        )
        with patch.object(client.client._stac_io.session, "request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"ok": True}
            mock_request.return_value = mock_response
            client.delete_item("test", "test", headers={"X-Override": "value2"})
            mock_request.assert_called_with(
                "delete",
                "https://example.com/collections/test/items/test",
                headers={
                    "Accept": "application/json",
                    "X-Instance": "value1",
                    "X-Override": "value2",
                },
                timeout=30,
            )

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_adr_requirement_timeout_error_mapping(self, mock_read_json):
        """ADR 0007: Map timeouts to concise messages."""
        mock_read_json.return_value = stac_catalog_factory()
        client = STACClient("https://example.com")
        with patch.object(
            client.client._stac_io.session, "request", side_effect=Timeout
        ):
            with pytest.raises(STACTimeoutError):
                client.delete_item("test", "test", timeout=15)

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_adr_requirement_connection_error_mapping(self, mock_read_json):
        """ADR 0007: Map connection errors to concise messages."""
        mock_read_json.return_value = stac_catalog_factory()
        client = STACClient("https://example.com")
        with patch.object(
            client.client._stac_io.session,
            "request",
            side_effect=RequestsConnectionError,
        ):
            with pytest.raises(ConnectionFailedError):
                client.delete_item("test", "test")
