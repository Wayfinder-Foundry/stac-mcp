"""Integration tests for ADR 0007 implementation.

These tests verify the complete ADR 0007 requirements:
1. Per-call configuration (headers, timeout) works end-to-end
2. Error mapping provides actionable guidance
3. Backward compatibility is maintained
4. Error logging follows ADR guidance
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch
from urllib.error import URLError

import pytest

from stac_mcp.tools.client import (
    ConnectionFailedError,
    STACClient,
    STACTimeoutError,
)


class TestADR0007Integration:
    """Integration tests for complete ADR 0007 compliance."""

    def test_adr_requirement_per_call_timeout(self):
        """ADR 0007: Add optional client configuration at call level (timeout)."""
        client = STACClient("https://example.com")

        # Test that timeout parameter is accepted and used
        with patch("stac_mcp.tools.client.urllib.request.urlopen") as mock_urlopen:

            def capture_timeout(req, timeout=None, context=None):
                # Verify timeout was passed through
                assert timeout == 120, "Custom timeout should be used"
                mock_response = MagicMock()
                mock_response.read.return_value = b'{"conformsTo": []}'
                mock_response.__enter__ = lambda self: self
                mock_response.__exit__ = lambda self, *args: None
                return mock_response

            mock_urlopen.side_effect = capture_timeout
            client._http_json("/test", timeout=120)  # noqa: SLF001

    def test_adr_requirement_per_call_headers(self):
        """ADR 0007: Add optional client configuration at call level (headers)."""
        client = STACClient(
            "https://example.com",
            headers={"X-Instance": "value1"},
        )

        with patch("stac_mcp.tools.client.urllib.request.urlopen") as mock_urlopen:

            def capture_headers(req, timeout=None, context=None):
                # Verify headers were merged correctly
                assert req.headers.get("X-instance") == "value1"
                assert req.headers.get("X-override") == "value2"
                mock_response = MagicMock()
                mock_response.read.return_value = b'{"conformsTo": []}'
                mock_response.__enter__ = lambda self: self
                mock_response.__exit__ = lambda self, *args: None
                return mock_response

            mock_urlopen.side_effect = capture_headers
            client._http_json("/test", headers={"X-Override": "value2"})  # noqa: SLF001

    def test_adr_requirement_timeout_error_mapping(self):
        """ADR 0007: Map timeouts to concise messages."""
        client = STACClient("https://example.com")

        with patch("stac_mcp.tools.client.urllib.request.urlopen") as mock_urlopen:
            import socket

            mock_urlopen.side_effect = socket.timeout("read timeout")

            with pytest.raises(STACTimeoutError) as exc_info:
                client._http_json("/test", timeout=15)  # noqa: SLF001

            error_msg = str(exc_info.value)
            # Verify message is concise and actionable
            assert "timed out after 15s" in error_msg
            assert "attempted 3 times" in error_msg
            assert "increasing timeout" in error_msg.lower()

    def test_adr_requirement_connection_error_mapping(self):
        """ADR 0007: Map connection errors to concise messages."""
        client = STACClient("https://example.com")

        with patch("stac_mcp.tools.client.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = URLError("Connection refused")

            with pytest.raises(ConnectionFailedError) as exc_info:
                client._http_json("/test")  # noqa: SLF001

            error_msg = str(exc_info.value)
            # Verify message provides actionable guidance
            assert "Connection refused" in error_msg
            assert "server may be down" in error_msg.lower()

    def test_adr_requirement_preserve_error_details(self):
        """ADR 0007: Preserve error details; avoid swallowing context."""
        client = STACClient("https://example.com")

        with patch("stac_mcp.tools.client.urllib.request.urlopen") as mock_urlopen:
            original_error = URLError("Network is unreachable")
            mock_urlopen.side_effect = original_error

            with pytest.raises(ConnectionFailedError) as exc_info:
                client._http_json("/test")  # noqa: SLF001

            # Verify original error is preserved via exception chaining
            assert exc_info.value.__cause__ is original_error
            # Verify details are in message
            assert "unreachable" in str(exc_info.value).lower()

    def test_adr_requirement_error_logging(self, caplog):
        """ADR 0007: Log at error level; no prints."""
        client = STACClient("https://example.com")

        with patch("stac_mcp.tools.client.urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = URLError("test error")

            try:
                client._http_json("/test")  # noqa: SLF001
            except ConnectionFailedError:
                pass

            # Verify error was logged at ERROR level (not EXCEPTION)
            error_logs = [r for r in caplog.records if r.levelname == "ERROR"]
            assert len(error_logs) > 0
            assert "Connection failed" in error_logs[0].message

    def test_backward_compatibility_no_timeout_param(self):
        """Verify existing code without timeout parameter still works."""
        client = STACClient("https://example.com")

        with patch("stac_mcp.tools.client.urllib.request.urlopen") as mock_urlopen:

            def check_default(req, timeout=None, context=None):
                assert timeout == 30, "Should use default timeout"
                mock_response = MagicMock()
                mock_response.read.return_value = b'{"test": "data"}'
                mock_response.__enter__ = lambda self: self
                mock_response.__exit__ = lambda self, *args: None
                return mock_response

            mock_urlopen.side_effect = check_default
            # Call without timeout parameter (as existing code does)
            result = client._http_json("/test")  # noqa: SLF001
            assert result == {"test": "data"}

    def test_backward_compatibility_no_headers_param(self):
        """Verify existing code without headers parameter still works."""
        client = STACClient("https://example.com")

        with patch("stac_mcp.tools.client.urllib.request.urlopen") as mock_urlopen:

            def check_no_extra_headers(req, timeout=None, context=None):
                # Should only have Accept header (set by default)
                assert "Accept" in req.headers
                mock_response = MagicMock()
                mock_response.read.return_value = b'{"test": "data"}'
                mock_response.__enter__ = lambda self: self
                mock_response.__exit__ = lambda self, *args: None
                return mock_response

            mock_urlopen.side_effect = check_no_extra_headers
            # Call without headers parameter (as existing code does)
            result = client._http_json("/test")  # noqa: SLF001
            assert result == {"test": "data"}

    def test_retry_behavior_with_custom_timeout(self):
        """Verify retry logic works correctly with custom timeout."""
        client = STACClient("https://example.com")
        call_count = 0

        with patch("stac_mcp.tools.client.urllib.request.urlopen") as mock_urlopen:

            def side_effect(req, timeout=None, context=None):
                nonlocal call_count
                call_count += 1
                assert timeout == 45, "Custom timeout should be used in all retries"
                if call_count < 3:
                    raise URLError("temporary error")
                # Success on 3rd attempt
                mock_response = MagicMock()
                mock_response.read.return_value = b'{"success": true}'
                mock_response.__enter__ = lambda self: self
                mock_response.__exit__ = lambda self, *args: None
                return mock_response

            mock_urlopen.side_effect = side_effect
            result = client._http_json("/test", timeout=45)  # noqa: SLF001
            assert result == {"success": True}  # JSON boolean becomes Python bool
            assert call_count == 3

    def test_headers_merge_behavior(self):
        """Verify headers are merged correctly with precedence rules."""
        client = STACClient(
            "https://example.com",
            headers={"X-Instance": "instance", "X-Both": "instance"},
        )

        with patch("stac_mcp.tools.client.urllib.request.urlopen") as mock_urlopen:

            def check_merge(req, timeout=None, context=None):
                # Instance header kept
                assert req.headers.get("X-instance") == "instance"
                # Per-call override
                assert req.headers.get("X-both") == "override"
                # Per-call only
                assert req.headers.get("X-call") == "call"
                mock_response = MagicMock()
                mock_response.read.return_value = b"{}"
                mock_response.__enter__ = lambda self: self
                mock_response.__exit__ = lambda self, *args: None
                return mock_response

            mock_urlopen.side_effect = check_merge
            client._http_json(  # noqa: SLF001
                "/test",
                headers={"X-Both": "override", "X-Call": "call"},
            )

    def test_error_message_includes_url_and_timeout(self):
        """Verify error messages include sufficient context for debugging."""
        client = STACClient("https://test-catalog.example.com/stac/v1")

        with patch("stac_mcp.tools.client.urllib.request.urlopen") as mock_urlopen:
            import socket

            mock_urlopen.side_effect = socket.timeout()

            with pytest.raises(STACTimeoutError) as exc_info:
                client._http_json("/search", timeout=25)  # noqa: SLF001

            error_msg = str(exc_info.value)
            # Verify URL is in message with precise hostname match
            import re
            from urllib.parse import urlparse

            urls = re.findall(r'https?://[^\s"]+', error_msg)
            assert any(
                urlparse(u).hostname == "test-catalog.example.com" for u in urls
            ), (
                f"Expected hostname 'test-catalog.example.com' "
                f"in error message, got: {error_msg}"
            )
            assert "/stac/v1/search" in error_msg
            # Verify timeout value is in message
            assert "25s" in error_msg


class TestADR0007EdgeCases:
    """Edge case tests for ADR 0007 implementation."""

    def test_timeout_zero_handled_correctly(self):
        """Test that timeout=0 (no timeout) is handled correctly."""
        client = STACClient("https://example.com")

        with patch("stac_mcp.tools.client.urllib.request.urlopen") as mock_urlopen:

            def check_zero_timeout(req, timeout=None, context=None):
                assert timeout == 0, "Timeout 0 should be passed through"
                mock_response = MagicMock()
                mock_response.read.return_value = b"{}"
                mock_response.__enter__ = lambda self: self
                mock_response.__exit__ = lambda self, *args: None
                return mock_response

            mock_urlopen.side_effect = check_zero_timeout
            client._http_json("/test", timeout=0)  # noqa: SLF001

    def test_empty_headers_dict_handled(self):
        """Test that empty headers dict is handled correctly."""
        client = STACClient("https://example.com")

        with patch("stac_mcp.tools.client.urllib.request.urlopen") as mock_urlopen:

            def check_headers(req, timeout=None, context=None):
                # Should still have Accept header
                assert "Accept" in req.headers
                mock_response = MagicMock()
                mock_response.read.return_value = b"{}"
                mock_response.__enter__ = lambda self: self
                mock_response.__exit__ = lambda self, *args: None
                return mock_response

            mock_urlopen.side_effect = check_headers
            client._http_json("/test", headers={})  # noqa: SLF001

    def test_none_timeout_uses_default(self):
        """Test that timeout=None explicitly uses default."""
        client = STACClient("https://example.com")

        with patch("stac_mcp.tools.client.urllib.request.urlopen") as mock_urlopen:

            def check_default(req, timeout=None, context=None):
                assert timeout == 30, "None should use default 30s"
                mock_response = MagicMock()
                mock_response.read.return_value = b"{}"
                mock_response.__enter__ = lambda self: self
                mock_response.__exit__ = lambda self, *args: None
                return mock_response

            mock_urlopen.side_effect = check_default
            client._http_json("/test", timeout=None)  # noqa: SLF001
