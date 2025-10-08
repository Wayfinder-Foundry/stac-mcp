"""Tests for ADR 0007: Client Configuration and Error Handling.

Tests focus on:
- Per-call timeout parameter
- Per-call headers override
- Timeout error mapping
- Connection error mapping
- Error message actionability
"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest

from stac_mcp.tools.client import (
    ConnectionFailedError,
    STACClient,
    STACTimeoutError,
)
from tests import (
    CALL_COUNT,
    HTTP_INTERNAL_SERVER_ERROR,
    RETRY_ATTEMPTS,
    TIMEOUT_30_SECONDS,
    TIMEOUT_60_SECONDS,
    TIMEOUT_NONE,
)


class TestTimeoutConfiguration:
    """Test timeout parameter support."""

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_default_timeout_used(self, mock_urlopen):
        """Test that default timeout of 30s is used when not specified."""
        client = STACClient("https://example.com")

        def check_timeout(req, timeout=None, context=None):  # noqa: ARG001
            assert timeout == TIMEOUT_30_SECONDS, "Default timeout should be 30 seconds"
            test_error = "test"
            raise URLError(test_error)

        mock_urlopen.side_effect = check_timeout

        with pytest.raises(ConnectionFailedError):
            client._http_json("/test")  # noqa: SLF001

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_custom_timeout_used(self, mock_urlopen):
        """Test that custom timeout is passed to urlopen."""
        client = STACClient("https://example.com")

        def check_timeout(req, timeout=None, context=None):  # noqa: ARG001
            assert timeout == TIMEOUT_60_SECONDS, "Custom timeout should be 60 seconds"
            test_error = "test"
            raise URLError(test_error)

        mock_urlopen.side_effect = check_timeout

        with pytest.raises(ConnectionFailedError):
            client._http_json("/test", timeout=60)  # noqa: SLF001

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_timeout_zero_allowed(self, mock_urlopen):
        """Test that timeout=0 (no timeout) is allowed."""
        client = STACClient("https://example.com")

        def check_timeout(req, timeout=None, context=None):  # noqa: ARG001
            assert timeout == TIMEOUT_NONE, "Timeout 0 should be passed through"
            test_error = "test"
            raise URLError(test_error)

        mock_urlopen.side_effect = check_timeout

        with pytest.raises(ConnectionFailedError):
            client._http_json("/test", timeout=0)  # noqa: SLF001


class TestHeadersConfiguration:
    """Test per-call headers override."""

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_instance_headers_used(self, mock_urlopen):
        """Test that instance headers are included in requests."""
        client = STACClient("https://example.com", headers={"X-API-Key": "secret123"})

        def check_headers(req, timeout=None, context=None):  # noqa: ARG001
            assert req.headers.get("X-api-key") == "secret123"
            test_error = "test"
            raise URLError(test_error)

        mock_urlopen.side_effect = check_headers

        with pytest.raises(ConnectionFailedError):
            client._http_json("/test")  # noqa: SLF001

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_call_headers_override(self, mock_urlopen):
        """Test that per-call headers override instance headers."""
        client = STACClient(
            "https://example.com",
            headers={"X-API-Key": "default", "X-Other": "value"},
        )

        def check_headers(req, timeout=None, context=None):  # noqa: ARG001
            # Override should replace X-API-Key but keep X-Other
            assert req.headers.get("X-api-key") == "override"
            assert req.headers.get("X-other") == "value"
            test_error = "test"
            raise URLError(test_error)

        mock_urlopen.side_effect = check_headers

        with pytest.raises(ConnectionFailedError):
            client._http_json(  # noqa: SLF001
                "/test",
                headers={"X-API-Key": "override"},
            )

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_accept_header_always_set(self, mock_urlopen):
        """Test that Accept header is always set to application/json."""
        client = STACClient("https://example.com")

        def check_headers(req, timeout=None, context=None):  # noqa: ARG001
            assert req.headers.get("Accept") == "application/json"
            test_error = "test"
            raise URLError(test_error)

        mock_urlopen.side_effect = check_headers

        with pytest.raises(ConnectionFailedError):
            client._http_json("/test")  # noqa: SLF001


class TestTimeoutErrorMapping:
    """Test timeout error detection and mapping."""

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_timeout_error_mapped(self, mock_urlopen):
        """Test that timeout errors are mapped to STACTimeoutError."""
        client = STACClient("https://example.com")

        # Simulate timeout by raising OSError with timeout message
        mock_urlopen.side_effect = OSError("timed out")

        with pytest.raises(STACTimeoutError) as exc_info:
            client._http_json("/test", timeout=15)  # noqa: SLF001

        assert "timed out after 15s" in str(exc_info.value)
        assert "attempted 3 times" in str(exc_info.value)
        assert "increasing timeout" in str(exc_info.value).lower()

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_socket_timeout_error_mapped(self, mock_urlopen):
        """Test that socket.timeout errors are mapped to STACTimeoutError."""
        client = STACClient("https://example.com")

        # socket.timeout is a subclass of OSError
        mock_urlopen.side_effect = TimeoutError("The read operation timed out")

        with pytest.raises(STACTimeoutError) as exc_info:
            client._http_json("/test")  # noqa: SLF001

        assert "timed out after 30s" in str(exc_info.value)

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_timeout_retry_behavior(self, mock_urlopen):
        """Test that timeout errors are retried before failing."""
        client = STACClient("https://example.com")
        call_count = 0

        def side_effect(*args, **kwargs):  # noqa: ARG001
            nonlocal call_count
            call_count += 1
            timed_out_error = "timed out"
            raise TimeoutError(timed_out_error)

        mock_urlopen.side_effect = side_effect

        with pytest.raises(STACTimeoutError):
            client._http_json("/test")  # noqa: SLF001

        # Should retry 3 times (initial + 2 retries)
        assert call_count == CALL_COUNT
        assert client._last_retry_attempts == RETRY_ATTEMPTS  # noqa: SLF001


class TestConnectionErrorMapping:
    """Test connection error detection and mapping."""

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_dns_error_mapped(self, mock_urlopen):
        """Test that DNS lookup failures are mapped with actionable message."""
        client = STACClient("https://example.com")

        mock_urlopen.side_effect = URLError("Name or service not known")

        with pytest.raises(ConnectionFailedError) as exc_info:
            client._http_json("/test")  # noqa: SLF001

        assert "DNS lookup failed" in str(exc_info.value)
        assert "Check the catalog URL" in str(exc_info.value)

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_connection_refused_mapped(self, mock_urlopen):
        """Test that connection refused errors are mapped with actionable message."""
        client = STACClient("https://example.com")

        mock_urlopen.side_effect = URLError("Connection refused")

        with pytest.raises(ConnectionFailedError) as exc_info:
            client._http_json("/test")  # noqa: SLF001

        assert "Connection refused" in str(exc_info.value)
        assert "server may be down" in str(exc_info.value)

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_network_unreachable_mapped(self, mock_urlopen):
        """Test that network unreachable errors are mapped with actionable message."""
        client = STACClient("https://example.com")

        mock_urlopen.side_effect = URLError("Network is unreachable")

        with pytest.raises(ConnectionFailedError) as exc_info:
            client._http_json("/test")  # noqa: SLF001

        assert "Network unreachable" in str(exc_info.value)
        assert "firewall settings" in str(exc_info.value)

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_generic_connection_error_mapped(self, mock_urlopen):
        """Test that generic connection errors have a fallback message."""
        client = STACClient("https://example.com")

        mock_urlopen.side_effect = URLError("Some unknown error")

        with pytest.raises(ConnectionFailedError) as exc_info:
            client._http_json("/test")  # noqa: SLF001

        assert "Failed to connect" in str(exc_info.value)
        assert "Some unknown error" in str(exc_info.value)

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_connection_error_retry_behavior(self, mock_urlopen):
        """Test that connection errors are retried before failing."""
        client = STACClient("https://example.com")
        call_count = 0

        def side_effect(*args, **kwargs):  # noqa: ARG001
            nonlocal call_count
            call_count += 1
            conn_refused = "Connection refused"
            raise URLError(conn_refused)

        mock_urlopen.side_effect = side_effect

        with pytest.raises(ConnectionFailedError):
            client._http_json("/test")  # noqa: SLF001

        # Should retry 3 times (initial + 2 retries)
        assert call_count == CALL_COUNT
        assert client._last_retry_attempts == RETRY_ATTEMPTS  # noqa: SLF001


class TestErrorLogging:
    """Test that errors are logged appropriately."""

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_connection_error_logged(self, mock_urlopen, caplog):
        """Test that connection errors are logged with error level."""
        client = STACClient("https://example.com")
        mock_urlopen.side_effect = URLError("Connection refused")

        with pytest.raises(ConnectionFailedError):
            client._http_json("/test")  # noqa: SLF001

        # Check that error was logged
        assert any(
            "Connection failed after 3 attempts" in record.message
            for record in caplog.records
            if record.levelname == "ERROR"
        )

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_timeout_error_logged(self, mock_urlopen, caplog):
        """Test that timeout errors are logged with error level."""
        client = STACClient("https://example.com")
        mock_urlopen.side_effect = TimeoutError("timed out")

        with pytest.raises(STACTimeoutError):
            client._http_json("/test")  # noqa: SLF001

        # Check that error was logged
        assert any(
            "Request timeout" in record.message
            for record in caplog.records
            if record.levelname == "ERROR"
        )


class TestBackwardCompatibility:
    """Test that existing behavior is preserved."""

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_http_404_still_returns_none(self, mock_urlopen):
        """Test that 404 responses still return None (existing behavior)."""

        client = STACClient("https://example.com")

        def raise_404(*_, **__):
            raise HTTPError(
                url="https://example.com/missing",
                code=404,
                msg="Not Found",
                hdrs=None,
                fp=BytesIO(),
            )

        mock_urlopen.side_effect = raise_404

        result = client._http_json("/missing")  # noqa: SLF001
        assert result is None

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_non_404_http_error_still_raises(self, mock_urlopen):
        """Test that non-404 HTTP errors are still raised (existing behavior)."""

        client = STACClient("https://example.com")

        def raise_500(*_, **__):
            raise HTTPError(
                url="https://example.com/error",
                code=500,
                msg="Server Error",
                hdrs=None,
                fp=BytesIO(),
            )

        mock_urlopen.side_effect = raise_500

        with pytest.raises(HTTPError) as exc_info:
            client._http_json("/error")  # noqa: SLF001

        assert exc_info.value.code == HTTP_INTERNAL_SERVER_ERROR
