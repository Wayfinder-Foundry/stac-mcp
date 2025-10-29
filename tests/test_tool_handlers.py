"""Tests for tool handlers."""

from unittest.mock import MagicMock

from stac_mcp.tools.get_aggregations import handle_get_aggregations
from stac_mcp.tools.get_collection import handle_get_collection
from stac_mcp.tools.get_conformance import handle_get_conformance
from stac_mcp.tools.get_item import handle_get_item
from stac_mcp.tools.get_queryables import handle_get_queryables
from stac_mcp.tools.get_root import handle_get_root
from stac_mcp.tools.search_collections import handle_search_collections
from stac_mcp.tools.search_items import handle_search_items


def test_handle_search_collections():
    """Test handle_search_collections."""
    mock_client = MagicMock()
    mock_client.search_collections.return_value = [
        {
            "id": "collection1",
            "title": "Test Collection",
            "description": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
            * 5,
            "license": "proprietary",
        }
    ]

    # Test text output
    result_text = handle_search_collections(mock_client, {})
    assert "Found 1 collections" in result_text[0].text
    assert "Test Collection" in result_text[0].text
    assert "collection1" in result_text[0].text
    assert "..." in result_text[0].text
    assert "License: proprietary" in result_text[0].text

    # Test JSON output
    result_json = handle_search_collections(mock_client, {"output_format": "json"})
    assert result_json["type"] == "collection_list"
    assert result_json["count"] == 1
    assert len(result_json["collections"]) == 1
    assert result_json["collections"][0]["id"] == "collection1"


def test_handle_search_items():
    """Test handle_search_items."""
    mock_client = MagicMock()
    mock_client.search_items.return_value = [
        {
            "id": "item1",
            "collection": "collection1",
            "datetime": "2025-01-01T00:00:00Z",
            "bbox": [1.0, 2.0, 3.0, 4.0],
            "assets": {"data": {}},
        }
    ]

    # Test text output
    result_text = handle_search_items(mock_client, {})
    assert "Found 1 items" in result_text[0].text
    assert "item1" in result_text[0].text
    assert "collection1" in result_text[0].text
    assert "Date: 2025-01-01T00:00:00Z" in result_text[0].text
    assert "BBox: [1.00, 2.00, 3.00, 4.00]" in result_text[0].text
    assert "Assets: 1" in result_text[0].text

    # Test JSON output
    result_json = handle_search_items(mock_client, {"output_format": "json"})
    assert result_json["type"] == "item_list"
    assert result_json["count"] == 1
    assert len(result_json["items"]) == 1
    assert result_json["items"][0]["id"] == "item1"


def test_handle_get_aggregations():
    """Test handle_get_aggregations."""
    mock_client = MagicMock()
    mock_client.get_aggregations.return_value = {
        "supported": True,
        "aggregations": {"total_count": 100},
        "message": "OK",
    }
    result = handle_get_aggregations(mock_client, {})
    assert "aggregations" in result[0].text


def test_handle_get_collection():
    """Test handle_get_collection."""
    mock_client = MagicMock()
    mock_client.get_collection.return_value = {
        "id": "test_collection",
        "title": "Test Collection",
        "description": "A comprehensive test collection.",
        "license": "CC-BY-4.0",
        "extent": {
            "spatial": {"bbox": [[-180.0, -90.0, 180.0, 90.0]]},
            "temporal": {"interval": [["2025-01-01T00:00:00Z", None]]},
        },
        "providers": [{"name": "Test Provider", "roles": ["producer"]}],
    }

    # Test text output
    result_text = handle_get_collection(
        mock_client, {"collection_id": "test_collection"}
    )
    output = result_text[0].text
    assert "Collection: Test Collection" in output
    assert "ID: `test_collection`" in output
    assert "Description: A comprehensive test collection." in output
    assert "License: CC-BY-4.0" in output
    assert "Spatial Extent: [-180.00, -90.00, 180.00, 90.00]" in output
    assert "Temporal Extent: 2025-01-01T00:00:00Z to present" in output
    assert "Providers: 1" in output
    assert "  - Test Provider (['producer'])" in output

    # Test JSON output
    result_json = handle_get_collection(
        mock_client, {"collection_id": "test_collection", "output_format": "json"}
    )
    assert result_json["type"] == "collection"
    assert result_json["collection"]["id"] == "test_collection"


def test_handle_get_conformance():
    """Test handle_get_conformance."""
    mock_client = MagicMock()
    mock_client.get_conformance.return_value = {"conformsTo": ["test"]}
    result = handle_get_conformance(mock_client, {})
    assert "conformsTo" in result[0].text


def test_handle_get_item():
    """Test handle_get_item."""
    mock_client = MagicMock()
    mock_client.get_item.return_value = {"id": "test"}
    result = handle_get_item(mock_client, {"collection_id": "test", "item_id": "test"})
    assert "test" in result[0].text


def test_handle_get_queryables():
    """Test handle_get_queryables."""
    mock_client = MagicMock()

    # Test with queryables and truncation
    mock_client.get_queryables.return_value = {
        "queryables": {f"prop{i}": {"type": "string"} for i in range(30)}
    }
    result_text = handle_get_queryables(mock_client, {"collection_id": "test"})
    output = result_text[0].text
    assert "Queryables" in output
    assert "Collection: test" in output
    assert "Count: 30" in output
    assert "prop24" in output
    assert "..." in output

    # Test with no queryables
    mock_client.get_queryables.return_value = {"queryables": {}}
    result_text = handle_get_queryables(mock_client, {})
    assert "No queryables available" in result_text[0].text

    # Test JSON output
    mock_client.get_queryables.return_value = {"queryables": {"prop1": {}}}
    result_json = handle_get_queryables(mock_client, {"output_format": "json"})
    assert result_json["type"] == "queryables"
    assert "prop1" in result_json["queryables"]


def test_handle_get_root():
    """Test handle_get_root."""
    mock_client = MagicMock()
    mock_client.get_root_document.return_value = {"id": "test"}
    result = handle_get_root(mock_client, {})
    assert "test" in result[0].text
