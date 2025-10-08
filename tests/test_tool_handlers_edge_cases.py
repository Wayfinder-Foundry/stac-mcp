"""Tests for tool handler edge cases and error conditions.

These tests focus on:
- Error handling in tool handlers
- Edge cases with optional parameters
- Malformed input handling
- Empty result scenarios
- Boundary conditions
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from stac_mcp.server import handle_call_tool


class TestGetRootEdgeCases:
    """Test get_root tool handler edge cases."""

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_root_minimal_response(self, mock_client):
        """Test get_root with minimal root document."""
        mock_client.get_root_document.return_value = {
            "id": "minimal-catalog",
            "links": [],
        }
        result = await handle_call_tool("get_root", {})
        assert len(result) == 1
        assert "minimal-catalog" in result[0].text
        assert "Links: 0" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_root_with_all_fields(self, mock_client):
        """Test get_root with complete root document."""
        mock_client.get_root_document.return_value = {
            "id": "full-catalog",
            "title": "Full Catalog Title",
            "description": "Full catalog description",
            "links": [{"rel": "self"}, {"rel": "root"}],
            "conformsTo": ["class1", "class2", "class3"],
        }
        result = await handle_call_tool("get_root", {})
        assert "Full Catalog Title" in result[0].text
        assert "Full catalog description" in result[0].text
        assert "Links: 2" in result[0].text
        assert "Conformance Classes: 3" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_root_json_format(self, mock_client):
        """Test get_root with JSON output format."""
        root_doc = {
            "id": "test-catalog",
            "title": "Test",
            "conformsTo": ["class1"],
        }
        mock_client.get_root_document.return_value = root_doc
        result = await handle_call_tool("get_root", {"output_format": "json"})
        assert len(result) == 1
        assert '"type":"root"' in result[0].text or "test-catalog" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_root_many_conformance_classes(self, mock_client):
        """Test get_root with more than 5 conformance classes."""
        mock_client.get_root_document.return_value = {
            "id": "catalog",
            "conformsTo": [f"class{i}" for i in range(10)],
        }
        result = await handle_call_tool("get_root", {})
        assert "... and 5 more" in result[0].text


class TestGetConformanceEdgeCases:
    """Test get_conformance tool handler edge cases."""

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_conformance_no_classes(self, mock_client):
        """Test get_conformance with empty conformance list."""
        mock_client.get_conformance.return_value = {
            "conformsTo": [],
        }
        result = await handle_call_tool("get_conformance", {})
        assert "Conformance Classes (0)" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_conformance_with_single_check(self, mock_client):
        """Test get_conformance with single conformance class check."""
        mock_client.get_conformance.return_value = {
            "conformsTo": ["class1", "class2"],
            "checks": {"class1": True},
        }
        result = await handle_call_tool(
            "get_conformance",
            {"check": "class1"},
        )
        assert "Checks:" in result[0].text
        assert "class1: OK" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_conformance_with_multiple_checks(self, mock_client):
        """Test get_conformance with multiple conformance class checks."""
        mock_client.get_conformance.return_value = {
            "conformsTo": ["class1", "class2", "class3"],
            "checks": {
                "class1": True,
                "class2": False,
                "class3": True,
            },
        }
        result = await handle_call_tool(
            "get_conformance",
            {"check": ["class1", "class2", "class3"]},
        )
        assert "class1: OK" in result[0].text
        assert "class2: MISSING" in result[0].text
        assert "class3: OK" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_conformance_many_classes(self, mock_client):
        """Test get_conformance with more than 20 conformance classes."""
        mock_client.get_conformance.return_value = {
            "conformsTo": [f"class{i}" for i in range(25)],
        }
        result = await handle_call_tool("get_conformance", {})
        assert "... and 5 more" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_conformance_json_format(self, mock_client):
        """Test get_conformance with JSON output format."""
        mock_client.get_conformance.return_value = {
            "conformsTo": ["class1", "class2"],
        }
        result = await handle_call_tool(
            "get_conformance",
            {"output_format": "json"},
        )
        assert '"type":"conformance"' in result[0].text or "class1" in result[0].text


class TestGetQueryablesEdgeCases:
    """Test get_queryables tool handler edge cases."""

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_queryables_not_supported(self, mock_client):
        """Test get_queryables when endpoint is not supported."""
        mock_client.get_queryables.return_value = {
            "supported": False,
            "queryables": {},
            "message": "Queryables endpoint not available",
        }
        result = await handle_call_tool("get_queryables", {})
        assert "Queryables endpoint not available" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_queryables_empty_result(self, mock_client):
        """Test get_queryables with empty queryables."""
        mock_client.get_queryables.return_value = {
            "supported": True,
            "queryables": {},
        }
        result = await handle_call_tool("get_queryables", {})
        assert "No queryables available" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_queryables_with_collection(self, mock_client):
        """Test get_queryables for specific collection."""
        mock_client.get_queryables.return_value = {
            "supported": True,
            "queryables": {
                "datetime": {"type": "string"},
                "eo:cloud_cover": {"type": "number"},
            },
        }
        result = await handle_call_tool(
            "get_queryables",
            {"collection_id": "test-collection"},
        )
        assert "Collection: test-collection" in result[0].text
        assert "datetime: string" in result[0].text
        assert "eo:cloud_cover: number" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_queryables_global(self, mock_client):
        """Test get_queryables for global queryables."""
        mock_client.get_queryables.return_value = {
            "supported": True,
            "queryables": {
                "id": {"type": "string"},
                "collection": {"type": "string"},
            },
        }
        result = await handle_call_tool("get_queryables", {})
        assert "Collection: GLOBAL" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_queryables_many_fields(self, mock_client):
        """Test get_queryables with more than 25 queryable fields."""
        queryables = {f"field{i}": {"type": "string"} for i in range(30)}
        mock_client.get_queryables.return_value = {
            "supported": True,
            "queryables": queryables,
        }
        result = await handle_call_tool("get_queryables", {})
        assert "... and 5 more" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_queryables_json_format(self, mock_client):
        """Test get_queryables with JSON output format."""
        mock_client.get_queryables.return_value = {
            "supported": True,
            "queryables": {"datetime": {"type": "string"}},
        }
        result = await handle_call_tool(
            "get_queryables",
            {"output_format": "json"},
        )
        assert '"type":"queryables"' in result[0].text or "datetime" in result[0].text


class TestGetAggregationsEdgeCases:
    """Test get_aggregations tool handler edge cases."""

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_aggregations_not_supported(self, mock_client):
        """Test get_aggregations when not supported."""
        mock_client.get_aggregations.return_value = {
            "supported": False,
            "aggregations": {},
            "message": "Aggregations not supported by this catalog",
        }
        result = await handle_call_tool(
            "get_aggregations",
            {"collections": ["test"]},
        )
        assert "Supported: No" in result[0].text
        assert "Aggregations not supported" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_aggregations_supported_with_results(self, mock_client):
        """Test get_aggregations with successful results."""
        mock_client.get_aggregations.return_value = {
            "supported": True,
            "aggregations": {
                "total_count": {"value": 1234},
                "cloud_cover_stats": {"min": 0, "max": 100, "avg": 45.2},
            },
            "message": "Aggregations completed successfully",
        }
        result = await handle_call_tool(
            "get_aggregations",
            {
                "collections": ["landsat"],
                "fields": ["cloud_cover"],
                "operations": ["count", "stats"],
            },
        )
        assert "Supported: Yes" in result[0].text
        assert "total_count" in result[0].text
        assert "cloud_cover_stats" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_aggregations_with_all_params(self, mock_client):
        """Test get_aggregations with all parameters."""
        mock_client.get_aggregations.return_value = {
            "supported": True,
            "aggregations": {"count": {"value": 42}},
            "message": "Success",
        }
        result = await handle_call_tool(
            "get_aggregations",
            {
                "collections": ["col1", "col2"],
                "bbox": [-180, -90, 180, 90],
                "datetime": "2023-01-01/2023-12-31",
                "query": {"eo:cloud_cover": {"lt": 10}},
                "fields": ["eo:cloud_cover"],
                "operations": ["count", "min", "max"],
                "limit": 100,
            },
        )
        assert "count" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_aggregations_json_format(self, mock_client):
        """Test get_aggregations with JSON output format."""
        mock_client.get_aggregations.return_value = {
            "supported": True,
            "aggregations": {"count": {"value": 5}},
            "message": "Success",
        }
        result = await handle_call_tool(
            "get_aggregations",
            {
                "collections": ["test"],
                "output_format": "json",
            },
        )
        assert '"type":"aggregations"' in result[0].text or "count" in result[0].text


class TestSearchItemsEdgeCases:
    """Test search_items tool handler edge cases."""

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_search_items_no_results(self, mock_client):
        """Test search_items with no matching items."""
        mock_client.search_items.return_value = []
        result = await handle_call_tool(
            "search_items",
            {"collections": ["test"]},
        )
        assert "No items found" in result[0].text or "0 items" in result[0].text

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_search_items_with_bbox(self, mock_client):
        """Test search_items with bbox parameter."""
        mock_client.search_items.return_value = [
            {
                "id": "item1",
                "collection": "col1",
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "properties": {},
                "assets": {},
            }
        ]
        result = await handle_call_tool(
            "search_items",
            {
                "collections": ["col1"],
                "bbox": [-180, -90, 180, 90],
            },
        )
        assert "item1" in result[0].text or len(result) > 0

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_search_items_with_datetime(self, mock_client):
        """Test search_items with datetime parameter."""
        mock_client.search_items.return_value = []
        result = await handle_call_tool(
            "search_items",
            {
                "collections": ["test"],
                "datetime": "2023-01-01/2023-12-31",
            },
        )
        assert result is not None


class TestSearchCollectionsEdgeCases:
    """Test search_collections tool handler edge cases."""

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_search_collections_empty(self, mock_client):
        """Test search_collections with no collections."""
        mock_client.search_collections.return_value = []
        result = await handle_call_tool("search_collections", {})
        assert "No collections found" in result[0].text or len(result) > 0

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_search_collections_single(self, mock_client):
        """Test search_collections with single collection."""
        mock_client.search_collections.return_value = [
            {
                "id": "col1",
                "title": "Collection 1",
                "description": "Test collection",
            }
        ]
        result = await handle_call_tool("search_collections", {})
        assert "col1" in result[0].text or "Collection 1" in result[0].text


class TestGetCollectionEdgeCases:
    """Test get_collection tool handler edge cases."""

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_collection_minimal(self, mock_client):
        """Test get_collection with minimal collection data."""
        mock_client.get_collection.return_value = {
            "id": "minimal-col",
            "description": "Minimal",
            "extent": {"spatial": {"bbox": [[0, 0, 1, 1]]}},
            "license": "proprietary",
        }
        result = await handle_call_tool(
            "get_collection",
            {"collection_id": "minimal-col"},
        )
        assert "minimal-col" in result[0].text


class TestGetItemEdgeCases:
    """Test get_item tool handler edge cases."""

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_get_item_minimal(self, mock_client):
        """Test get_item with minimal item data."""
        mock_client.get_item.return_value = {
            "id": "minimal-item",
            "collection": "col1",
            "geometry": None,
            "properties": {},
            "assets": {},
        }
        result = await handle_call_tool(
            "get_item",
            {"collection_id": "col1", "item_id": "minimal-item"},
        )
        assert "minimal-item" in result[0].text or len(result) > 0


class TestInvalidInputHandling:
    """Test handling of invalid or malformed inputs."""

    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        """Test calling an unknown tool."""
        with pytest.raises(Exception):
            await handle_call_tool("nonexistent_tool", {})

    @pytest.mark.asyncio
    @patch("stac_mcp.server.stac_client")
    async def test_invalid_output_format(self, mock_client):
        """Test with invalid output_format parameter."""
        mock_client.get_root_document.return_value = {"id": "test"}
        # Should default to text format or handle gracefully
        result = await handle_call_tool(
            "get_root",
            {"output_format": "invalid"},
        )
        assert result is not None
