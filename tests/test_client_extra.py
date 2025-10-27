"""Extra tests for stac_mcp/tools/client.py."""

from unittest.mock import MagicMock, patch

import pytest

from stac_mcp.tools.client import STACClient


@pytest.fixture
def client():
    """Fixture for STACClient."""
    with patch("pystac_client.Client.open", return_value=MagicMock()):
        c = STACClient(catalog_url="https://example.com")
        c._search_cache = {}  # noqa: SLF001
        c.headers = {}
        yield c


def test_client_init_with_defaults():
    """Test STACClient.__init__ with default values."""
    with patch("pystac_client.Client.open", return_value=MagicMock()):
        client = STACClient()
        assert (
            client.catalog_url == "https://planetarycomputer.microsoft.com/api/stac/v1"
        )
        assert client.headers == {}
        assert client.head_timeout_seconds == 20
        assert client.head_max_workers == 4
        assert client.head_retries == 1
        assert client.head_backoff_base == 0.05
        assert client.head_backoff_jitter is True


def test_search_cache_key(client: STACClient):
    """Test _search_cache_key."""
    key = client._search_cache_key(  # noqa: SLF001
        collections=["test"],
        bbox=[0, 0, 1, 1],
        datetime="2022-01-01T00:00:00Z",
        query={"key": "value"},
        limit=10,
    )
    assert isinstance(key, str)


def test_invalidate_cache(client: STACClient):
    """Test _invalidate_cache."""
    client._search_cache = {"test": (0, [])}  # noqa: SLF001
    client._invalidate_cache()  # noqa: SLF001
    assert not client._search_cache  # noqa: SLF001


def test_invalidate_cache_with_collections(client: STACClient):
    """Test _invalidate_cache with collections."""
    client._search_cache = {"collection1": (0, []), "collection2": (0, [])}  # noqa: SLF001
    client._invalidate_cache(affected_collections=["collection1"])  # noqa: SLF001
    assert "collection2" in client._search_cache  # noqa: SLF001
    assert "collection1" not in client._search_cache  # noqa: SLF001
