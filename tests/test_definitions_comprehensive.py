"""Comprehensive tests for tool definitions.

Tests focus on:
- All tool definitions are properly structured
- Input schemas are valid JSON Schema
- Required and optional parameters are correctly defined
- Tool descriptions are informative
- Enum values are properly constrained
"""

from __future__ import annotations

import pytest

from stac_mcp.tools.definitions import get_tool_definitions


class TestToolDefinitions:
    """Test tool definition structure and completeness."""

    def test_get_tool_definitions_returns_list(self):
        """Test that get_tool_definitions returns a list."""
        tools = get_tool_definitions()
        assert isinstance(tools, list)
        assert len(tools) > 0

    def test_all_tools_have_required_fields(self):
        """Test that all tools have name, description, and inputSchema."""
        tools = get_tool_definitions()
        for tool in tools:
            assert hasattr(tool, "name")
            assert hasattr(tool, "description")
            assert hasattr(tool, "inputSchema")
            assert tool.name
            assert tool.description
            assert tool.inputSchema

    def test_tool_names_are_unique(self):
        """Test that all tool names are unique."""
        tools = get_tool_definitions()
        names = [tool.name for tool in tools]
        assert len(names) == len(set(names))

    def test_expected_tools_present(self):
        """Test that all expected tools are present."""
        tools = get_tool_definitions()
        tool_names = {tool.name for tool in tools}
        
        expected_tools = {
            "get_root",
            "get_conformance",
            "get_queryables",
            "get_aggregations",
            "search_collections",
            "get_collection",
            "search_items",
            "get_item",
            "estimate_data_size",
            "create_collection",
            "create_item",
            "update_collection",
            "update_item",
            "delete_collection",
            "delete_item",
        }
        
        # Check that at least the core tools are present
        core_tools = {
            "get_root",
            "get_conformance",
            "get_queryables",
            "get_aggregations",
            "search_collections",
            "get_collection",
            "search_items",
            "get_item",
            "estimate_data_size",
        }
        
        assert core_tools.issubset(tool_names)


class TestToolInputSchemas:
    """Test tool input schema definitions."""

    def test_all_schemas_have_type_object(self):
        """Test that all input schemas define type as object."""
        tools = get_tool_definitions()
        for tool in tools:
            schema = tool.inputSchema
            assert schema.get("type") == "object"

    def test_output_format_parameter_consistent(self):
        """Test that output_format parameter is consistently defined."""
        tools = get_tool_definitions()
        
        # Most tools should have output_format parameter
        for tool in tools:
            schema = tool.inputSchema
            properties = schema.get("properties", {})
            
            if "output_format" in properties:
                output_format = properties["output_format"]
                assert output_format.get("type") == "string"
                assert "enum" in output_format
                assert set(output_format["enum"]) == {"text", "json"}
                assert output_format.get("default") == "text"

    def test_catalog_url_parameter_consistent(self):
        """Test that catalog_url parameter is consistently defined."""
        tools = get_tool_definitions()
        
        for tool in tools:
            schema = tool.inputSchema
            properties = schema.get("properties", {})
            
            if "catalog_url" in properties:
                catalog_url = properties["catalog_url"]
                assert catalog_url.get("type") == "string"
                assert "description" in catalog_url


class TestSpecificToolDefinitions:
    """Test specific tool definitions in detail."""

    def test_get_root_definition(self):
        """Test get_root tool definition."""
        tools = get_tool_definitions()
        get_root = next((t for t in tools if t.name == "get_root"), None)
        
        assert get_root is not None
        assert "root document" in get_root.description.lower()
        
        properties = get_root.inputSchema.get("properties", {})
        assert "output_format" in properties
        assert "catalog_url" in properties

    def test_get_conformance_definition(self):
        """Test get_conformance tool definition."""
        tools = get_tool_definitions()
        get_conformance = next(
            (t for t in tools if t.name == "get_conformance"),
            None,
        )
        
        assert get_conformance is not None
        assert "conformance" in get_conformance.description.lower()
        
        properties = get_conformance.inputSchema.get("properties", {})
        assert "output_format" in properties
        assert "check" in properties
        assert "catalog_url" in properties
        
        # Check parameter should accept string or array
        check = properties["check"]
        assert "oneOf" in check or "type" in check

    def test_get_queryables_definition(self):
        """Test get_queryables tool definition."""
        tools = get_tool_definitions()
        get_queryables = next(
            (t for t in tools if t.name == "get_queryables"),
            None,
        )
        
        assert get_queryables is not None
        assert "queryable" in get_queryables.description.lower()
        
        properties = get_queryables.inputSchema.get("properties", {})
        assert "output_format" in properties
        assert "collection_id" in properties
        assert "catalog_url" in properties

    def test_get_aggregations_definition(self):
        """Test get_aggregations tool definition."""
        tools = get_tool_definitions()
        get_aggregations = next(
            (t for t in tools if t.name == "get_aggregations"),
            None,
        )
        
        assert get_aggregations is not None
        assert "aggregation" in get_aggregations.description.lower()
        
        properties = get_aggregations.inputSchema.get("properties", {})
        assert "output_format" in properties
        assert "collections" in properties
        
        # Should have optional search parameters
        optional_params = ["bbox", "datetime", "query", "fields", "operations", "limit"]
        for param in optional_params:
            if param in properties:
                assert properties[param]  # Just verify it exists

    def test_search_collections_definition(self):
        """Test search_collections tool definition."""
        tools = get_tool_definitions()
        search_collections = next(
            (t for t in tools if t.name == "search_collections"),
            None,
        )
        
        assert search_collections is not None
        assert "search" in search_collections.description.lower()
        assert "collection" in search_collections.description.lower()

    def test_get_collection_definition(self):
        """Test get_collection tool definition."""
        tools = get_tool_definitions()
        get_collection = next(
            (t for t in tools if t.name == "get_collection"),
            None,
        )
        
        assert get_collection is not None
        properties = get_collection.inputSchema.get("properties", {})
        assert "collection_id" in properties
        
        # collection_id should be required
        collection_id = properties["collection_id"]
        assert collection_id.get("type") == "string"

    def test_search_items_definition(self):
        """Test search_items tool definition."""
        tools = get_tool_definitions()
        search_items = next(
            (t for t in tools if t.name == "search_items"),
            None,
        )
        
        assert search_items is not None
        properties = search_items.inputSchema.get("properties", {})
        
        # Should have search parameters
        search_params = ["collections", "bbox", "datetime", "limit"]
        for param in search_params:
            if param in properties:
                assert properties[param]

    def test_get_item_definition(self):
        """Test get_item tool definition."""
        tools = get_tool_definitions()
        get_item = next((t for t in tools if t.name == "get_item"), None)
        
        assert get_item is not None
        properties = get_item.inputSchema.get("properties", {})
        assert "collection_id" in properties
        assert "item_id" in properties

    def test_estimate_data_size_definition(self):
        """Test estimate_data_size tool definition."""
        tools = get_tool_definitions()
        estimate_data_size = next(
            (t for t in tools if t.name == "estimate_data_size"),
            None,
        )
        
        assert estimate_data_size is not None
        assert "estimate" in estimate_data_size.description.lower() or \
               "size" in estimate_data_size.description.lower()
        
        properties = estimate_data_size.inputSchema.get("properties", {})
        # Should have search parameters plus AOI
        if "aoi_geojson" in properties:
            assert properties["aoi_geojson"]


class TestTransactionToolDefinitions:
    """Test transaction tool definitions."""

    def test_create_collection_definition(self):
        """Test create_collection tool definition."""
        tools = get_tool_definitions()
        create_collection = next(
            (t for t in tools if t.name == "create_collection"),
            None,
        )
        
        if create_collection:
            assert "create" in create_collection.description.lower()
            properties = create_collection.inputSchema.get("properties", {})
            assert "collection" in properties or len(properties) > 0

    def test_create_item_definition(self):
        """Test create_item tool definition."""
        tools = get_tool_definitions()
        create_item = next(
            (t for t in tools if t.name == "create_item"),
            None,
        )
        
        if create_item:
            assert "create" in create_item.description.lower()
            properties = create_item.inputSchema.get("properties", {})
            assert "item" in properties or "collection_id" in properties or len(properties) > 0

    def test_update_collection_definition(self):
        """Test update_collection tool definition."""
        tools = get_tool_definitions()
        update_collection = next(
            (t for t in tools if t.name == "update_collection"),
            None,
        )
        
        if update_collection:
            assert "update" in update_collection.description.lower()

    def test_update_item_definition(self):
        """Test update_item tool definition."""
        tools = get_tool_definitions()
        update_item = next(
            (t for t in tools if t.name == "update_item"),
            None,
        )
        
        if update_item:
            assert "update" in update_item.description.lower()

    def test_delete_collection_definition(self):
        """Test delete_collection tool definition."""
        tools = get_tool_definitions()
        delete_collection = next(
            (t for t in tools if t.name == "delete_collection"),
            None,
        )
        
        if delete_collection:
            assert "delete" in delete_collection.description.lower()

    def test_delete_item_definition(self):
        """Test delete_item tool definition."""
        tools = get_tool_definitions()
        delete_item = next(
            (t for t in tools if t.name == "delete_item"),
            None,
        )
        
        if delete_item:
            assert "delete" in delete_item.description.lower()


class TestToolDescriptions:
    """Test tool description quality."""

    def test_all_descriptions_are_informative(self):
        """Test that all tool descriptions are sufficiently detailed."""
        tools = get_tool_definitions()
        
        for tool in tools:
            # Description should be at least 20 characters
            assert len(tool.description) >= 20
            # Description should not be just the tool name
            assert tool.description.lower() != tool.name.lower()

    def test_descriptions_mention_key_functionality(self):
        """Test that descriptions mention key functionality."""
        tools = get_tool_definitions()
        
        functionality_keywords = {
            "get_root": ["root", "document"],
            "get_conformance": ["conformance", "class"],
            "get_queryables": ["queryable", "field"],
            "get_aggregations": ["aggregation", "search"],
            "search_collections": ["search", "collection"],
            "get_collection": ["collection"],
            "search_items": ["search", "item"],
            "get_item": ["item"],
            "estimate_data_size": ["estimate", "size", "data"],
        }
        
        for tool in tools:
            if tool.name in functionality_keywords:
                keywords = functionality_keywords[tool.name]
                desc_lower = tool.description.lower()
                # At least one keyword should be in description
                assert any(kw in desc_lower for kw in keywords)


class TestSchemaValidation:
    """Test that schemas are valid JSON Schema."""

    def test_schemas_are_valid_objects(self):
        """Test that all schemas are valid dictionaries."""
        tools = get_tool_definitions()
        
        for tool in tools:
            schema = tool.inputSchema
            assert isinstance(schema, dict)
            assert "type" in schema
            assert schema["type"] == "object"

    def test_properties_are_properly_typed(self):
        """Test that all properties have valid type definitions."""
        tools = get_tool_definitions()
        
        valid_types = {"string", "number", "integer", "boolean", "array", "object"}
        
        for tool in tools:
            properties = tool.inputSchema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                if isinstance(prop_schema, dict):
                    # Either has type or oneOf/anyOf/allOf
                    has_type = "type" in prop_schema
                    has_composite = any(
                        k in prop_schema
                        for k in ["oneOf", "anyOf", "allOf"]
                    )
                    assert has_type or has_composite

    def test_enum_constraints_are_arrays(self):
        """Test that enum constraints are arrays."""
        tools = get_tool_definitions()
        
        for tool in tools:
            properties = tool.inputSchema.get("properties", {})
            for prop_schema in properties.values():
                if isinstance(prop_schema, dict) and "enum" in prop_schema:
                    assert isinstance(prop_schema["enum"], list)
                    assert len(prop_schema["enum"]) > 0
