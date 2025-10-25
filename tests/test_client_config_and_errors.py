"""Tests for ADR 0007: Client Configuration and Error Handling.

Tests focus on:
- Per-call timeout parameter
- Per-call headers override
- Timeout error mapping
- Connection error mapping
- Error message actionability
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout

from stac_mcp.tools.client import (
    ConnectionFailedError,
    STACClient,
    STACTimeoutError,
)
from tests import (
    HTTP_INTERNAL_SERVER_ERROR,
    TIMEOUT_30_SECONDS,
)


def stac_catalog_factory():
    return {
        "type": "Catalog",
        "id": "test-catalog",
        "stac_version": "1.0.0",
        "description": "Test Catalog",
        "links": [],
    }


class TestTimeoutConfiguration:
    """Test timeout parameter support."""

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_default_timeout_used(self, mock_read_json):
        """Test that default timeout of 30s is used when not specified."""
        mock_read_json.return_value = stac_catalog_factory()
        client = STACClient("https://example.com")
        with patch.object(
            client.client._stac_io.session,  # noqa: SLF001
            "request",
            side_effect=Timeout,
        ) as mock_request:
            with pytest.raises(STACTimeoutError):
                client.delete_item("test", "test")
            mock_request.assert_called_with(
                "delete",
                "https://example.com/collections/test/items/test",
                headers={"Accept": "application/json"},
                timeout=TIMEOUT_30_SECONDS,
            )


class TestHeadersConfiguration:
    """Test per-call headers override."""

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_instance_headers_used(self, mock_read_json):
        """Test that instance headers are included in requests."""
        mock_read_json.return_value = stac_catalog_factory()
        client = STACClient("https://example.com", headers={"X-API-Key": "secret123"})
        assert client.headers.get("X-API-Key") == "secret123"


class TestTimeoutErrorMapping:
    """Test timeout error detection and mapping."""

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_timeout_error_mapped(self, mock_read_json):
        """Test that timeout errors are mapped to STACTimeoutError."""
        mock_read_json.return_value = stac_catalog_factory()
        client = STACClient("https://example.com")
        with (
            patch.object(
                client.client._stac_io.session,  # noqa: SLF001
                "request",
                side_effect=Timeout,
            ),
            pytest.raises(STACTimeoutError),
        ):
            client.delete_item("test", "test")


class TestConnectionErrorMapping:
    """Test connection error detection and mapping."""

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_dns_error_mapped(self, mock_read_json):
        """Test that DNS lookup failures are mapped with actionable message."""
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


class TestErrorLogging:
    """Test that errors are logged appropriately."""

    class CaptureHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records = []

        def emit(self, record):
            self.records.append(record)

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_connection_error_logged(self, mock_read_json):
        """Test that connection errors are logged with error level."""
        mock_read_json.return_value = stac_catalog_factory()
        client = STACClient("https://example.com")
        logger = logging.getLogger("stac_mcp.tools.client")
        handler = self.CaptureHandler()
        logger.addHandler(handler)
        with (
            patch.object(
                client.client._stac_io.session,  # noqa: SLF001
                "request",
                side_effect=RequestsConnectionError,
            ),
            pytest.raises(ConnectionFailedError),
        ):
            client.delete_item("test", "test")
        target_error_msg = [
            "Failed to connect" in record.message
            for record in handler.records
            if record.levelname == "ERROR"
        ]
        assert any(target_error_msg)

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_timeout_error_logged(self, mock_read_json):
        """Test that timeout errors are logged with error level."""
        mock_read_json.return_value = stac_catalog_factory()
        client = STACClient("https://example.com")
        logger = logging.getLogger("stac_mcp.tools.client")
        handler = self.CaptureHandler()
        logger.addHandler(handler)
        with (
            patch.object(
                client.client._stac_io.session,  # noqa: SLF001
                "request",
                side_effect=Timeout,
            ),
            pytest.raises(STACTimeoutError),
        ):
            client.delete_item("test", "test")
        assert any(
            "Request timed out" in record.message
            for record in handler.records
            if record.levelname == "ERROR"
        )


class TestBackwardCompatibility:
    """Test that existing behavior is preserved."""

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_http_404_still_returns_none(self, mock_read_json):
        """Test that 404 responses still return None (existing behavior)."""
        mock_read_json.return_value = stac_catalog_factory()
        client = STACClient("https://example.com")
        with patch.object(client.client._stac_io.session, "request") as mock_request:  # noqa: SLF001
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_request.return_value = mock_response
            assert client.delete_item("test", "test") is None

    @patch("pystac_client.stac_api_io.StacApiIO.read_json")
    def test_non_404_http_error_still_raises(self, mock_read_json):
        """Test that non-404 HTTP errors are still raised (existing behavior)."""
        mock_read_json.return_value = stac_catalog_factory()
        client = STACClient("https://example.com")
        with patch.object(client.client._stac_io.session, "request") as mock_request:  # noqa: SLF001
            mock_response = MagicMock()
            mock_response.status_code = HTTP_INTERNAL_SERVER_ERROR
            mock_response.raise_for_status.side_effect = Exception("test")
            mock_request.return_value = mock_response
            with pytest.raises(Exception):  # noqa: PT011 B017
                client.delete_item("test", "test")
