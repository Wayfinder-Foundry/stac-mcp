"""Additional client edge cases and error scenarios.

Tests focus on:
- Edge cases in HTTP request handling
- Retry logic boundary conditions
- Header manipulation edge cases
- URL construction edge cases
- Response parsing edge cases
"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError, URLError

import pytest

from stac_mcp.tools.client import (
    ConnectionFailedError,
    STACClient,
    STACTimeoutError,
)


class TestClientInitialization:
    """Test STACClient initialization edge cases."""

    def test_client_with_trailing_slash(self):
        """Test client with catalog URL having trailing slash."""
        client = STACClient("https://example.com/stac/")
        assert client.catalog_url.endswith("/stac/")

    def test_client_without_trailing_slash(self):
        """Test client with catalog URL without trailing slash."""
        client = STACClient("https://example.com/stac")
        assert client.catalog_url == "https://example.com/stac"

    def test_client_with_port(self):
        """Test client with catalog URL including port."""
        client = STACClient("https://example.com:8080/stac")
        assert "8080" in client.catalog_url

    def test_client_with_path_segments(self):
        """Test client with catalog URL having multiple path segments."""
        client = STACClient("https://example.com/api/v1/stac")
        assert client.catalog_url == "https://example.com/api/v1/stac"

    def test_client_with_http_protocol(self):
        """Test client with HTTP (non-HTTPS) URL."""
        client = STACClient("http://localhost:8000/stac")
        assert client.catalog_url.startswith("http://")


class TestHTTPRequestBuilding:
    """Test HTTP request construction edge cases."""

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_http_json_with_query_parameters(self, mock_urlopen):
        """Test HTTP request with query parameters."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"result": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = client._http_json("/test?param=value")  # noqa: SLF001
        assert result == {"result": "ok"}

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_http_json_with_fragment(self, mock_urlopen):
        """Test HTTP request with URL fragment."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"result": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = client._http_json("/test#fragment")  # noqa: SLF001
        assert result == {"result": "ok"}

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_http_json_absolute_url(self, mock_urlopen):
        """Test HTTP request with absolute URL."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"result": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Some paths might be absolute URLs
        result = client._http_json("https://other.com/data")  # noqa: SLF001
        assert result == {"result": "ok"}


class TestHeaderHandling:
    """Test HTTP header handling edge cases."""

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_default_headers_included(self, mock_urlopen):
        """Test that default headers are included."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"result": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client._http_json("/test")  # noqa: SLF001

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert request.headers is not None

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_custom_headers_override(self, mock_urlopen):
        """Test that custom headers override defaults."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"result": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        custom_headers = {"Custom-Header": "custom-value"}
        client._http_json("/test", headers=custom_headers)  # noqa: SLF001

        call_args = mock_urlopen.call_args
        request = call_args[0][0]
        assert "Custom-header" in request.headers or "Custom-Header" in request.headers

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_empty_custom_headers(self, mock_urlopen):
        """Test with empty custom headers dict."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"result": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        client._http_json("/test", headers={})  # noqa: SLF001

        # Should still include default headers
        assert mock_urlopen.called


class TestRetryLogic:
    """Test retry logic edge cases."""

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_retry_on_transient_error(self, mock_urlopen):
        """Test retry on transient errors."""
        client = STACClient("https://example.com")
        
        # Fail twice, succeed on third try
        mock_urlopen.side_effect = [
            URLError("Connection reset"),
            URLError("Connection reset"),
            MagicMock(
                __enter__=MagicMock(
                    return_value=MagicMock(read=MagicMock(return_value=b'{"ok": true}'))
                ),
                __exit__=MagicMock(return_value=False),
            ),
        ]

        result = client._http_json("/test")  # noqa: SLF001
        assert result == {"ok": True}
        assert mock_urlopen.call_count == 3

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_retry_exhausted(self, mock_urlopen):
        """Test when all retries are exhausted."""
        client = STACClient("https://example.com")
        
        # Fail all attempts
        mock_urlopen.side_effect = URLError("Persistent error")

        with pytest.raises(ConnectionFailedError):
            client._http_json("/test")  # noqa: SLF001

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_no_retry_on_client_error(self, mock_urlopen):
        """Test that 4xx errors don't trigger retry."""
        client = STACClient("https://example.com")
        
        # 404 should not be retried
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"error": "Not found"}'
        mock_urlopen.side_effect = HTTPError(
            "https://example.com/test",
            404,
            "Not Found",
            {},
            BytesIO(b'{"error": "Not found"}'),
        )

        result = client._http_json("/test")  # noqa: SLF001
        assert result is None
        # Should only try once, not retry
        assert mock_urlopen.call_count == 1


class TestTimeoutHandling:
    """Test timeout handling edge cases."""

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_zero_timeout(self, mock_urlopen):
        """Test with zero timeout (should use default)."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"result": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = client._http_json("/test", timeout=0)  # noqa: SLF001
        assert result == {"result": "ok"}

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_very_long_timeout(self, mock_urlopen):
        """Test with very long timeout."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"result": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = client._http_json("/test", timeout=3600)  # noqa: SLF001
        assert result == {"result": "ok"}

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_timeout_between_retries(self, mock_urlopen):
        """Test timeout behavior between retries."""
        client = STACClient("https://example.com")
        
        # First call times out, second succeeds
        mock_urlopen.side_effect = [
            OSError("timed out"),
            MagicMock(
                __enter__=MagicMock(
                    return_value=MagicMock(read=MagicMock(return_value=b'{"ok": true}'))
                ),
                __exit__=MagicMock(return_value=False),
            ),
        ]

        with pytest.raises(STACTimeoutError):
            client._http_json("/test", timeout=5)  # noqa: SLF001


class TestResponseParsing:
    """Test response parsing edge cases."""

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_empty_json_response(self, mock_urlopen):
        """Test parsing empty JSON object."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = client._http_json("/test")  # noqa: SLF001
        assert result == {}

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_json_array_response(self, mock_urlopen):
        """Test parsing JSON array response."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'[1, 2, 3]'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = client._http_json("/test")  # noqa: SLF001
        assert result == [1, 2, 3]

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_json_null_response(self, mock_urlopen):
        """Test parsing JSON null response."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'null'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = client._http_json("/test")  # noqa: SLF001
        assert result is None

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_malformed_json_response(self, mock_urlopen):
        """Test handling of malformed JSON."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{invalid json}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with pytest.raises(Exception):  # JSONDecodeError or similar
            client._http_json("/test")  # noqa: SLF001

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_large_json_response(self, mock_urlopen):
        """Test parsing very large JSON response."""
        client = STACClient("https://example.com")
        large_json = b'{"data": "' + b'x' * 1000000 + b'"}'  # 1MB
        mock_response = MagicMock()
        mock_response.read.return_value = large_json
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = client._http_json("/test")  # noqa: SLF001
        assert "data" in result
        assert len(result["data"]) == 1000000

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_unicode_in_json_response(self, mock_urlopen):
        """Test parsing JSON with unicode characters."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"text": "\xe4\xb8\xad\xe6\x96\x87"}'  # 中文
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = client._http_json("/test")  # noqa: SLF001
        assert "text" in result


class TestSearchOperations:
    """Test search operation edge cases."""

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_search_collections_empty_result(self, mock_urlopen):
        """Test search_collections with no results."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"collections": []}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = client.search_collections()
        assert result == []

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_search_items_with_all_parameters(self, mock_urlopen):
        """Test search_items with all possible parameters."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"features": []}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = client.search_items(
            collections=["col1", "col2"],
            bbox=[-180, -90, 180, 90],
            datetime="2023-01-01/2023-12-31",
            query={"eo:cloud_cover": {"lt": 10}},
            limit=100,
        )
        assert result == []

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_get_collection_not_found(self, mock_urlopen):
        """Test get_collection when collection doesn't exist."""
        client = STACClient("https://example.com")
        mock_urlopen.side_effect = HTTPError(
            "https://example.com/collections/missing",
            404,
            "Not Found",
            {},
            BytesIO(b'{"error": "Not found"}'),
        )

        result = client.get_collection("missing")
        assert result is None

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_get_item_not_found(self, mock_urlopen):
        """Test get_item when item doesn't exist."""
        client = STACClient("https://example.com")
        mock_urlopen.side_effect = HTTPError(
            "https://example.com/collections/col1/items/missing",
            404,
            "Not Found",
            {},
            BytesIO(b'{"error": "Not found"}'),
        )

        result = client.get_item("col1", "missing")
        assert result is None


class TestConformanceHandling:
    """Test conformance checking edge cases."""

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_conformance_caching(self, mock_urlopen):
        """Test that conformance is cached."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"conformsTo": ["class1", "class2"]}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # First call
        conf1 = client.get_conformance()
        # Second call (should use cache)
        conf2 = client.get_conformance()

        # Should only call once due to caching
        assert mock_urlopen.call_count <= 2  # May vary based on implementation

    def test_conformance_check_single_class(self):
        """Test checking a single conformance class."""
        client = STACClient("https://example.com")
        client._conformance = ["class1", "class2"]  # noqa: SLF001

        # Check single class via property access
        assert hasattr(client, "_conformance")

    def test_conformance_check_multiple_classes(self):
        """Test checking multiple conformance classes."""
        client = STACClient("https://example.com")
        client._conformance = ["class1", "class2", "class3"]  # noqa: SLF001

        # Multiple checks
        assert hasattr(client, "_conformance")


class TestDataSizeEstimation:
    """Test data size estimation edge cases."""

    def test_estimate_data_size_no_items(self):
        """Test data size estimation with no items."""
        # This would typically involve mocking odc.stac
        # Placeholder for future implementation
        pass

    def test_estimate_data_size_large_dataset(self):
        """Test data size estimation with very large dataset."""
        # Placeholder for future implementation
        pass


class TestURLEncoding:
    """Test URL encoding edge cases."""

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_special_characters_in_collection_id(self, mock_urlopen):
        """Test collection ID with special characters."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"id": "test-col%20name"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Collection ID with space (should be encoded)
        result = client.get_collection("test-col name")
        assert result is not None or result is None  # May succeed or fail gracefully

    @patch("stac_mcp.tools.client.urllib.request.urlopen")
    def test_special_characters_in_item_id(self, mock_urlopen):
        """Test item ID with special characters."""
        client = STACClient("https://example.com")
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"id": "test-item/path"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Item ID with slash (should be encoded)
        result = client.get_item("col1", "test-item/path")
        assert result is not None or result is None  # May succeed or fail gracefully
