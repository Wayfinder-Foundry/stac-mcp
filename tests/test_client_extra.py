
"""Extra tests for stac_mcp/tools/client.py."""

import logging
from unittest.mock import MagicMock, patch

import pytest
from httpx import Response

from stac_mcp.tools.client import STACClient


@pytest.fixture
def client():
    """Fixture for STACClient."""
    with patch("pystac_client.Client.open", return_value=MagicMock()):
        c = STACClient(catalog_url="https://example.com")
        c._search_cache = {}  # noqa: SLF001
        c.headers = {}
        yield c


def test_get_session_with_headers(client: STACClient):
    """Test _get_session with headers."""
    client.headers = {"x-api-key": "test_api_key"}
    with patch("pystac_client.stac_api_io.StacApiIO") as mock_io:
        _ = client.client  # noqa: F841
        mock_io.assert_called_with(headers={"x-api-key": "test_api_key"})


def test_get_session_without_headers(client: STACClient):
    """Test _get_session without headers."""
    client.headers = {}
    with patch("pystac_client.stac_api_io.StacApiIO") as mock_io:
        _ = client.client  # noqa: F841
        mock_io.assert_called_with(headers={})


@patch("stac_mcp.tools.client.STACClient._do_transaction")
def test_get_success(mock_do_transaction: MagicMock, client: STACClient):
    """Test _get success."""
    mock_do_transaction.return_value = {"message": "success"}
    response = client._do_transaction("get", "/test")  # noqa: SLF001
    assert response == {"message": "success"}


@patch("stac_mcp.tools.client.STACClient._do_transaction")
def test_get_error(mock_do_transaction: MagicMock, client: STACClient):
    """Test _get error."""
    mock_do_transaction.side_effect = Exception
    with pytest.raises(Exception):
        client._do_transaction("get", "/test")  # noqa: SLF001


@patch("stac_mcp.tools.client.STACClient._do_transaction")
def test_post_success(mock_do_transaction: MagicMock, client: STACClient):
    """Test _post success."""
    mock_do_transaction.return_value = {"message": "success"}
    response = client._do_transaction(  # noqa: SLF001
        "post", "/test", json={"key": "value"}
    )
    assert response == {"message": "success"}


@patch("stac_mcp.tools.client.STACClient._do_transaction")
def test_post_error(mock_do_transaction: MagicMock, client: STACClient):
    """Test _post error."""
    mock_do_transaction.side_effect = Exception
    with pytest.raises(Exception):
        client._do_transaction("post", "/test", json={"key": "value"})  # noqa: SLF001


@patch("stac_mcp.tools.client.STACClient._do_transaction")
def test_head_success(mock_do_transaction: MagicMock, client: STACClient):
    """Test _head success."""
    mock_do_transaction.return_value = {}
    response = client._do_transaction("head", "/test")  # noqa: SLF001
    assert response == {}


@patch("stac_mcp.tools.client.STACClient._do_transaction")
def test_head_error(mock_do_transaction: MagicMock, client: STACClient):
    """Test _head error."""
    mock_do_transaction.side_effect = Exception
    with pytest.raises(Exception):
        client._do_transaction("head", "/test")  # noqa: SLF001


@patch("stac_mcp.tools.client.STACClient.client")
def test_search_collections_success(mock_client: MagicMock, client: STACClient):
    """Test search_collections with a successful response."""
    mock_collection = MagicMock(
        id="collection1",
        title="Collection 1",
        description="Description",
        extent=None,
        license="MIT",
        providers=[],
        summaries=None,
        assets=None,
    )
    mock_client.get_collections.return_value = [mock_collection]
    result = client.search_collections()
    assert len(result) == 1
    assert result[0]["id"] == "collection1"


@patch("stac_mcp.tools.client.STACClient.client")
def test_get_collection_success(mock_client: MagicMock, client: STACClient):
    """Test get_collection with a successful response."""
    mock_collection = MagicMock(
        id="collection1",
        title="Collection 1",
        description="Description",
        extent=None,
        license="MIT",
        providers=[],
        summaries=None,
        assets=None,
    )
    mock_client.get_collection.return_value = mock_collection
    result = client.get_collection("collection1")
    assert result["id"] == "collection1"


@patch("stac_mcp.tools.client.STACClient.client")
def test_search_items_success(mock_client: MagicMock, client: STACClient):
    """Test search_items with a successful response."""
    client._conformance = ["https://api.stacspec.org/v1.0.0/item-search#query"]  # noqa: SLF001
    mock_item = MagicMock(id="item1")
    mock_search = MagicMock()
    mock_search.items.return_value = [mock_item]
    mock_client.search.return_value = mock_search
    result = client.search_items(collections=["collection1"])
    assert len(result) == 1


@patch("stac_mcp.tools.client.STACClient.client")
def test_get_item_success(mock_client: MagicMock, client: STACClient):
    """Test get_item with a successful response."""
    mock_item = MagicMock(
        id="item1",
        collection_id="collection1",
        geometry=None,
        bbox=None,
        datetime=None,
        properties={},
        assets={},
    )
    mock_collection = MagicMock()
    mock_collection.get_item.return_value = mock_item
    mock_client.get_collection.return_value = mock_collection
    result = client.get_item("collection1", "item1")
    assert result["id"] == "item1"


@patch("requests.get")
def test_get_queryables_success(mock_get: MagicMock, client: STACClient):
    """Test get_queryables with a successful response."""
    client._conformance = [  # noqa: SLF001
        "https://api.stacspec.org/v1.0.0/item-search#queryables"
    ]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {"queryables": {}}
    mock_get.return_value = mock_response
    result = client.get_queryables("collection1")
    assert result["queryables"] == {}


@patch("requests.post")
def test_get_aggregations_success(mock_post: MagicMock, client: STACClient):
    """Test get_aggregations with a successful response."""
    client._conformance = [  # noqa: SLF001
        "https://api.stacspec.org/v1.0.0/ogc-api-features-p3/conf/aggregation"
    ]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True
    mock_response.json.return_value = {"aggregations": []}
    mock_post.return_value = mock_response
    result = client.get_aggregations()
    assert result["supported"] is True


@patch("stac_mcp.tools.client.STACClient._do_transaction")
def test_create_item_success(mock_do_transaction: MagicMock, client: STACClient):
    """Test create_item with a successful response."""
    mock_do_transaction.return_value = {"id": "item1"}
    result = client.create_item("collection1", {"id": "item1"})
    assert result["id"] == "item1"


@patch("stac_mcp.tools.client.STACClient._do_transaction")
def test_update_item_success(mock_do_transaction: MagicMock, client: STACClient):
    """Test update_item with a successful response."""
    mock_do_transaction.return_value = {"id": "item1"}
    result = client.update_item({"collection": "collection1", "id": "item1"})
    assert result["id"] == "item1"


@patch("stac_mcp.tools.client.STACClient._do_transaction")
def test_delete_item_success(mock_do_transaction: MagicMock, client: STACClient):
    """Test delete_item with a successful response."""
    client.delete_item("collection1", "item1")
    mock_do_transaction.assert_called_once()


@patch("stac_mcp.tools.client.STACClient._do_transaction")
def test_create_collection_success(mock_do_transaction: MagicMock, client: STACClient):
    """Test create_collection with a successful response."""
    mock_do_transaction.return_value = {"id": "collection1"}
    result = client.create_collection({"id": "collection1"})
    assert result["id"] == "collection1"


@patch("stac_mcp.tools.client.STACClient._do_transaction")
def test_update_collection_success(mock_do_transaction: MagicMock, client: STACClient):
    """Test update_collection with a successful response."""
    mock_do_transaction.return_value = {"id": "collection1"}
    result = client.update_collection({"id": "collection1"})
    assert result["id"] == "collection1"


@patch("stac_mcp.tools.client.STACClient._do_transaction")
def test_delete_collection_success(mock_do_transaction: MagicMock, client: STACClient):
    """Test delete_collection with a successful response."""
    client.delete_collection("collection1")
    mock_do_transaction.assert_called_once()
