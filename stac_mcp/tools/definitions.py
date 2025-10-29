"""Tool definitions and JSON Schemas.

Long descriptive strings are intentionally kept on single lines for stability of
user-facing help text. Line length lint (E501) is disabled for this file.

This module returns the list of MCP Tool objects supported by the current
server implementation. It mirrors the previous inline definitions from
``server.py`` (pre-refactor) to preserve backwards compatibility for clients
and tests.
"""

# ruff: noqa: E501

from mcp.types import Tool


def get_tool_definitions() -> list[Tool]:
    """Return tool definitions (schemas + descriptions)."""
    return [
        Tool(
            name="get_root",
            description="Get STAC API root document with basic metadata and conformance",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_format": {
                        "type": "string",
                        "description": "Result output format: 'text' (default) or 'json'",
                        "enum": ["text", "json"],
                        "default": "text",
                    },
                    "catalog_url": {
                        "type": "string",
                        "description": "STAC catalog URL (optional, defaults to Microsoft Planetary Computer)",
                    },
                },
            },
        ),
        Tool(
            name="get_conformance",
            description="List STAC API conformance classes; optionally check specific classes",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_format": {
                        "type": "string",
                        "description": "Result output format: 'text' (default) or 'json'",
                        "enum": ["text", "json"],
                        "default": "text",
                    },
                    "check": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "array", "items": {"type": "string"}},
                        ],
                        "description": "Conformance class URI or list of URIs to verify",
                    },
                    "catalog_url": {
                        "type": "string",
                        "description": "STAC catalog URL (optional, defaults to Microsoft Planetary Computer)",
                    },
                },
            },
        ),
        Tool(
            name="get_queryables",
            description="Get queryable fields (global or per collection) if supported",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_format": {
                        "type": "string",
                        "description": "Result output format: 'text' (default) or 'json'",
                        "enum": ["text", "json"],
                        "default": "text",
                    },
                    "collection_id": {
                        "type": "string",
                        "description": "Collection ID for collection-specific queryables (optional)",
                    },
                    "catalog_url": {
                        "type": "string",
                        "description": "STAC catalog URL (optional, defaults to Microsoft Planetary Computer)",
                    },
                },
            },
        ),
        Tool(
            name="get_aggregations",
            description="Run a STAC search requesting aggregations (count/stats) if supported",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_format": {
                        "type": "string",
                        "description": "Result output format: 'text' (default) or 'json'",
                        "enum": ["text", "json"],
                        "default": "text",
                    },
                    "collections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of collection IDs to search within",
                    },
                    "bbox": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                        "description": "Bounding box [west, south, east, north] in WGS84",
                    },
                    "datetime": {
                        "type": "string",
                        "description": "Date/time filter (ISO 8601 format, e.g., '2023-01-01/2023-12-31')",
                    },
                    "query": {
                        "type": "object",
                        "description": "Additional query parameters for filtering items",
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Fields to aggregate for field-based operations (e.g., stats, histogram)",
                    },
                    "operations": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Aggregation operation types (e.g., count, stats, histogram)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Optional item limit for the search (0 means rely on server defaults)",
                        "default": 0,
                        "minimum": 0,
                        "maximum": 1000,
                    },
                    "catalog_url": {
                        "type": "string",
                        "description": "STAC catalog URL (optional, defaults to Microsoft Planetary Computer)",
                    },
                },
            },
        ),
        Tool(
            name="search_collections",
            description="Search and list available STAC collections",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_format": {
                        "type": "string",
                        "description": "Result output format: 'text' (default) or 'json'",
                        "enum": ["text", "json"],
                        "default": "text",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of collections to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "catalog_url": {
                        "type": "string",
                        "description": "STAC catalog URL (optional, defaults to Microsoft Planetary Computer)",
                    },
                },
            },
        ),
        Tool(
            name="get_collection",
            description="Get detailed information about a specific STAC collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_format": {
                        "type": "string",
                        "description": "Result output format: 'text' (default) or 'json'",
                        "enum": ["text", "json"],
                        "default": "text",
                    },
                    "collection_id": {
                        "type": "string",
                        "description": "ID of the collection to retrieve",
                    },
                    "catalog_url": {
                        "type": "string",
                        "description": "STAC catalog URL (optional, defaults to Microsoft Planetary Computer)",
                    },
                },
                "required": ["collection_id"],
            },
        ),
        Tool(
            name="search_items",
            description="Search for STAC items across collections",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_format": {
                        "type": "string",
                        "description": "Result output format: 'text' (default) or 'json'",
                        "enum": ["text", "json"],
                        "default": "text",
                    },
                    "collections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of collection IDs to search within",
                    },
                    "bbox": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                        "description": "Bounding box [west, south, east, north] in WGS84",
                    },
                    "datetime": {
                        "type": "string",
                        "description": "Date/time filter (ISO 8601 format, e.g., '2023-01-01/2023-12-31')",
                    },
                    "query": {
                        "type": "object",
                        "description": "Additional query parameters for filtering items",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of items to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 100,
                    },
                    "catalog_url": {
                        "type": "string",
                        "description": "STAC catalog URL (optional, defaults to Microsoft Planetary Computer)",
                    },
                },
            },
        ),
        Tool(
            name="get_item",
            description="Get detailed information about a specific STAC item",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_format": {
                        "type": "string",
                        "description": "Result output format: 'text' (default) or 'json'",
                        "enum": ["text", "json"],
                        "default": "text",
                    },
                    "collection_id": {
                        "type": "string",
                        "description": "ID of the collection containing the item",
                    },
                    "item_id": {
                        "type": "string",
                        "description": "ID of the item to retrieve",
                    },
                    "catalog_url": {
                        "type": "string",
                        "description": "STAC catalog URL (optional, defaults to Microsoft Planetary Computer)",
                    },
                },
                "required": ["collection_id", "item_id"],
            },
        ),
        Tool(
            name="estimate_data_size",
            description="Estimate data size for STAC items using lazy loading with odc.stac",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_format": {
                        "type": "string",
                        "description": "Result output format: 'text' (default) or 'json'",
                        "enum": ["text", "json"],
                        "default": "text",
                    },
                    "collections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of collection IDs to search within",
                    },
                    "bbox": {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 4,
                        "maxItems": 4,
                        "description": "Bounding box [west, south, east, north] in WGS84",
                    },
                    "datetime": {
                        "type": "string",
                        "description": "Date/time filter (ISO 8601 format, e.g., '2023-01-01/2023-12-31')",
                    },
                    "query": {
                        "type": "object",
                        "description": "Additional query parameters for filtering items",
                    },
                    "aoi_geojson": {
                        "type": "object",
                        "description": "Area of Interest as GeoJSON geometry for clipping (will use smallest bbox between this and bbox parameter)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of items to analyze for size estimation",
                        "default": 100,
                        "minimum": 1,
                        "maximum": 500,
                    },
                    "catalog_url": {
                        "type": "string",
                        "description": "STAC catalog URL (optional, defaults to Microsoft Planetary Computer)",
                    },
                },
            },
        ),
        Tool(
            name="create_item",
            description="Create a new STAC item in a collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection_id": {
                        "type": "string",
                        "description": "ID of the collection",
                    },
                    "item": {"type": "object", "description": "STAC item JSON"},
                },
                "required": ["collection_id", "item"],
            },
        ),
        Tool(
            name="update_item",
            description="Update an existing STAC item",
            inputSchema={
                "type": "object",
                "properties": {
                    "item": {
                        "type": "object",
                        "description": "STAC item JSON to update",
                    },
                },
                "required": ["item"],
            },
        ),
        Tool(
            name="delete_item",
            description="Delete an existing STAC item from a collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection_id": {
                        "type": "string",
                        "description": "ID of the collection",
                    },
                    "item_id": {
                        "type": "string",
                        "description": "ID of the item to delete",
                    },
                },
                "required": ["collection_id", "item_id"],
            },
        ),
        Tool(
            name="create_collection",
            description="Create a new STAC collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "object",
                        "description": "STAC collection JSON",
                    },
                },
                "required": ["collection"],
            },
        ),
        Tool(
            name="update_collection",
            description="Update an existing STAC collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "object",
                        "description": "STAC collection JSON to update",
                    },
                },
                "required": ["collection"],
            },
        ),
        Tool(
            name="delete_collection",
            description="Delete a STAC collection",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection_id": {
                        "type": "string",
                        "description": "ID of the collection to delete",
                    },
                },
                "required": ["collection_id"],
            },
        ),
        # ==================== PySTAC-based CRUDL Tools ====================
        # Catalog CRUDL
        Tool(
            name="pystac_create_catalog",
            description="Create a new STAC Catalog using pystac (local file or remote endpoint with optional STAC_API_KEY authentication)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to save catalog (local file path or remote URL)",
                    },
                    "catalog_id": {
                        "type": "string",
                        "description": "Catalog identifier",
                    },
                    "description": {
                        "type": "string",
                        "description": "Catalog description",
                    },
                    "title": {
                        "type": "string",
                        "description": "Catalog title (optional, defaults to catalog_id)",
                    },
                },
                "required": ["path", "catalog_id", "description"],
            },
        ),
        Tool(
            name="pystac_read_catalog",
            description="Read a STAC Catalog using pystac (local file or remote URL)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to catalog (local file path or remote URL)",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="pystac_update_catalog",
            description="Update a STAC Catalog using pystac (local file or remote endpoint with optional STAC_API_KEY authentication)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to catalog (local file path or remote URL)",
                    },
                    "catalog": {
                        "type": "object",
                        "description": "Updated catalog dictionary following STAC Catalog specification",
                    },
                },
                "required": ["path", "catalog"],
            },
        ),
        Tool(
            name="pystac_delete_catalog",
            description="Delete a STAC Catalog using pystac (local file or remote endpoint with optional STAC_API_KEY authentication)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to catalog (local file path or remote URL)",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="pystac_list_catalogs",
            description="List STAC Catalogs using pystac (local directory or remote endpoint)",
            inputSchema={
                "type": "object",
                "properties": {
                    "base_path": {
                        "type": "string",
                        "description": "Base path to search (local directory or remote URL)",
                    },
                },
                "required": ["base_path"],
            },
        ),
        # Collection CRUDL
        Tool(
            name="pystac_create_collection",
            description="Create a new STAC Collection using pystac (local file or remote endpoint with optional STAC_API_KEY authentication)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to save collection (local file path or remote URL)",
                    },
                    "collection": {
                        "type": "object",
                        "description": "Collection dictionary following STAC Collection specification",
                    },
                },
                "required": ["path", "collection"],
            },
        ),
        Tool(
            name="pystac_read_collection",
            description="Read a STAC Collection using pystac (local file or remote URL)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to collection (local file path or remote URL)",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="pystac_update_collection",
            description="Update a STAC Collection using pystac (local file or remote endpoint with optional STAC_API_KEY authentication)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to collection (local file path or remote URL)",
                    },
                    "collection": {
                        "type": "object",
                        "description": "Updated collection dictionary following STAC Collection specification",
                    },
                },
                "required": ["path", "collection"],
            },
        ),
        Tool(
            name="pystac_delete_collection",
            description="Delete a STAC Collection using pystac (local file or remote endpoint with optional STAC_API_KEY authentication)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to collection (local file path or remote URL)",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="pystac_list_collections",
            description="List STAC Collections using pystac (local directory or remote endpoint)",
            inputSchema={
                "type": "object",
                "properties": {
                    "base_path": {
                        "type": "string",
                        "description": "Base path to search (local directory or remote URL)",
                    },
                },
                "required": ["base_path"],
            },
        ),
        # Item CRUDL
        Tool(
            name="pystac_create_item",
            description="Create a new STAC Item using pystac (local file or remote endpoint with optional STAC_API_KEY authentication)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to save item (local file path or remote URL)",
                    },
                    "item": {
                        "type": "object",
                        "description": "Item dictionary following STAC Item specification",
                    },
                },
                "required": ["path", "item"],
            },
        ),
        Tool(
            name="pystac_read_item",
            description="Read a STAC Item using pystac (local file or remote URL)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to item (local file path or remote URL)",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="pystac_update_item",
            description="Update a STAC Item using pystac (local file or remote endpoint with optional STAC_API_KEY authentication)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to item (local file path or remote URL)",
                    },
                    "item": {
                        "type": "object",
                        "description": "Updated item dictionary following STAC Item specification",
                    },
                },
                "required": ["path", "item"],
            },
        ),
        Tool(
            name="pystac_delete_item",
            description="Delete a STAC Item using pystac (local file or remote endpoint with optional STAC_API_KEY authentication)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to item (local file path or remote URL)",
                    },
                },
                "required": ["path"],
            },
        ),
        Tool(
            name="pystac_list_items",
            description="List STAC Items using pystac (local directory or remote endpoint)",
            inputSchema={
                "type": "object",
                "properties": {
                    "base_path": {
                        "type": "string",
                        "description": "Base path to search (local directory or remote URL)",
                    },
                },
                "required": ["base_path"],
            },
        ),
    ]
