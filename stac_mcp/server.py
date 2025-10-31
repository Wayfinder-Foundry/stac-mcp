from __future__ import annotations

import json
import logging
from typing import Any

from fastmcp.prompts.prompt import PromptMessage, TextContent
from fastmcp.server.server import FastMCP

from stac_mcp.prompts import register_prompts
from stac_mcp.tools import execution
from stac_mcp.tools.params import preprocess_parameters

app = FastMCP()

_LOGGER = logging.getLogger(__name__)

# Prompts are registered separately to keep the server module small and
# avoid import cycles. See `stac_mcp.prompts.register_prompts` for details.
register_prompts(app)


def _prompt_get_conformance() -> PromptMessage:
    schema = {"type": "object", "properties": {}, "required": []}
    payload = {
        "name": "get_conformance",
        "description": "Return server conformance classes.",
        "parameters": schema,
        "example": {},
    }
    human = (
        f"Tool: get_conformance\nDescription: {payload['description']}\n\n"
        "Parameters:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Example:\n"
        f"{json.dumps(payload['example'], indent=2)}"
    )
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=human),
        _meta={"machine_payload": payload},
    )


def _prompt_get_root() -> PromptMessage:
    """Module-level prompt helper for get_root (kept for tests).

    The authoritative prompt is registered dynamically by
    `stac_mcp.prompts.register_prompts`, but tests expect a callable with
    this name to exist on the module. Provide a minimal in-module copy so
    test introspection succeeds.
    """
    schema = {"type": "object", "properties": {}, "required": []}
    payload = {
        "name": "get_root",
        "description": "Return the STAC root document for a catalog.",
        "parameters": schema,
        "example": {},
    }
    human = (
        f"Tool: get_root\nDescription: {payload['description']}\n\n"
        "Parameters:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Example:\n"
        f"{json.dumps(payload['example'], indent=2)}"
    )
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=human),
        _meta={"machine_payload": payload},
    )


def _prompt_search_collections() -> PromptMessage:
    schema = {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "default": 10},
            "catalog_url": {"type": "string"},
        },
        "required": [],
    }
    payload = {
        "name": "search_collections",
        "description": "Return a page of STAC collections.",
        "parameters": schema,
        "example": {"limit": 5},
    }
    human = (
        f"Tool: search_collections\nDescription: {payload['description']}\n\n"
        "Parameters:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Example:\n"
        f"{json.dumps(payload['example'], indent=2)}"
    )
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=human),
        _meta={"machine_payload": payload},
    )


def _prompt_get_collection() -> PromptMessage:
    schema = {
        "type": "object",
        "properties": {
            "collection_id": {"type": "string"},
            "catalog_url": {"type": "string"},
        },
        "required": ["collection_id"],
    }
    payload = {
        "name": "get_collection",
        "description": "Fetch a single STAC Collection by id.",
        "parameters": schema,
        "example": {"collection_id": "my-collection"},
    }
    human = (
        f"Tool: get_collection\nDescription: {payload['description']}\n\n"
        "Parameters:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Example:\n"
        f"{json.dumps(payload['example'], indent=2)}"
    )
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=human),
        _meta={"machine_payload": payload},
    )


def _prompt_get_item() -> PromptMessage:
    schema = {
        "type": "object",
        "properties": {
            "collection_id": {"type": "string"},
            "item_id": {"type": "string"},
            "output_format": {
                "type": "string",
                "enum": ["text", "json"],
                "default": "text",
            },
            "catalog_url": {"type": "string"},
        },
        "required": ["collection_id", "item_id"],
    }
    payload = {
        "name": "get_item",
        "description": "Retrieve a single STAC Item.",
        "parameters": schema,
        "example": {"collection_id": "c1", "item_id": "i1", "output_format": "json"},
    }
    human = (
        f"Tool: get_item\nDescription: {payload['description']}\n\n"
        "Parameters:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Example:\n"
        f"{json.dumps(payload['example'], indent=2)}"
    )
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=human),
        _meta={"machine_payload": payload},
    )


def _prompt_search_items() -> PromptMessage:
    schema = {
        "type": "object",
        "properties": {
            "collections": {"type": "array", "items": {"type": "string"}},
            "bbox": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 4,
                "maxItems": 4,
            },
            "datetime": {"type": "string"},
            "limit": {"type": "integer", "default": 10},
        },
        "required": ["collections"],
    }
    payload = {
        "name": "search_items",
        "description": "Search for STAC Items.",
        "parameters": schema,
        "example": {"collections": ["c1"], "limit": 3},
    }
    human = (
        f"Tool: search_items\nDescription: {payload['description']}\n\n"
        "Parameters:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Example:\n"
        f"{json.dumps(payload['example'], indent=2)}\n\n"
        "Notes:\n"
        "If get_collections has not been run yet for the target catalog, run it "
        "first to populate the collection list.\n"
        "On responses with zero items, validate that the colliection IDs are "
        "correct.\n"
        "If using 'bbox', ensure coordinates are in [minLon, minLat, maxLon, maxLat] "
        "order.\n"
        "Datetime should be in ISO 8601 format, e.g., '2020-01-01/2020-12-31'.\n"
        "Limit should be a positive integer.\n"
    )
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=human),
        _meta={"machine_payload": payload},
    )


def _prompt_estimate_data_size() -> PromptMessage:
    schema = {
        "type": "object",
        "properties": {
            "collections": {"type": "array", "items": {"type": "string"}},
            "bbox": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 4,
                "maxItems": 4,
            },
            "datetime": {"type": "string"},
            "query": {"type": "object"},
            "aoi_geojson": {"type": "object"},
            "limit": {"type": "integer", "default": 100},
            "force_metadata_only": {"type": "boolean", "default": False},
            "output_format": {
                "type": "string",
                "enum": ["text", "json"],
                "default": "text",
            },
        },
        "required": ["collections"],
    }
    payload = {
        "name": "estimate_data_size",
        "description": "Estimate data size for a STAC query.",
        "parameters": schema,
        "example": {"collections": ["c1"], "limit": 10, "output_format": "json"},
    }
    # Note for users: this tool returns both the DataArray-reported size
    # (reported_bytes from .data.nbytes) and a registry-corrected size
    # (registry_bytes) when the sensor registry suggests a different
    # instrument-native dtype. The numeric totals are computed from the
    # reported values by default; check 'registry_bytes' for storage-native
    # estimates.
    human = (
        f"Tool: estimate_data_size\nDescription: {payload['description']}\n\n"
        "Parameters:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Note: The response includes per-variable fields 'reported_bytes' and\n"
        "'registry_bytes' when applicable. Use 'registry_bytes' to estimate\n"
        "instrument-native storage sizes.\n\n"
        "Example:\n"
        f"{json.dumps(payload['example'], indent=2)}"
    )
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=human),
        _meta={"machine_payload": payload},
    )


def _prompt_get_queryables() -> PromptMessage:
    schema = {
        "type": "object",
        "properties": {
            "collection_id": {"type": "string"},
            "catalog_url": {"type": "string"},
        },
        "required": [],
    }
    payload = {
        "name": "get_queryables",
        "description": "Fetch STAC API (or collection) queryables.",
        "parameters": schema,
        "example": {"collection_id": "my-collection"},
    }
    human = (
        f"Tool: get_queryables\nDescription: {payload['description']}\n\n"
        "Parameters:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Example:\n"
        f"{json.dumps(payload['example'], indent=2)}"
    )
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=human),
        _meta={"machine_payload": payload},
    )


def _prompt_get_aggregations() -> PromptMessage:
    schema = {
        "type": "object",
        "properties": {
            "collections": {"type": "array", "items": {"type": "string"}},
            "bbox": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 4,
                "maxItems": 4,
            },
            "datetime": {"type": "string"},
            "query": {"type": "object"},
            "catalog_url": {"type": "string"},
        },
        "required": ["collections"],
    }
    payload = {
        "name": "get_aggregations",
        "description": "Return aggregations for STAC Items in a collection.",
        "parameters": schema,
        "example": {"collections": ["c1"], "datetime": "2020-01-01/2020-12-31"},
    }
    human = (
        f"Tool: get_aggregations\nDescription: {payload['description']}\n\n"
        "Parameters:\n"
        f"{json.dumps(schema, indent=2)}\n\n"
        "Example:\n"
        f"{json.dumps(payload['example'], indent=2)}"
    )
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=human),
        _meta={"machine_payload": payload},
    )


@app.tool
async def get_root() -> list[dict[str, Any]]:
    """Return the STAC root document for a catalog."""
    return await execution.execute_tool(
        "get_root", arguments={}, catalog_url=None, headers=None
    )


@app.tool
async def get_conformance() -> list[dict[str, Any]]:
    """Return server conformance classes."""
    return await execution.execute_tool(
        "get_conformance", arguments={}, catalog_url=None, headers=None
    )


@app.tool
async def search_collections(
    limit: int | None = 10, catalog_url: str | None = None
) -> list[dict[str, Any]]:
    """Return a page of STAC collections."""
    return await execution.execute_tool(
        "search_collections",
        arguments={"limit": limit},
        catalog_url=catalog_url,
        headers=None,
    )


@app.tool
async def get_collection(
    collection_id: str, catalog_url: str | None = None
) -> list[dict[str, Any]]:
    """Fetch a single STAC Collection by id."""
    return await execution.execute_tool(
        "get_collection",
        arguments={"collection_id": collection_id},
        catalog_url=catalog_url,
        headers=None,
    )


@app.tool
async def get_item(
    collection_id: str,
    item_id: str,
    output_format: str | None = "text",
    catalog_url: str | None = None,
) -> list[dict[str, Any]]:
    """Get a specific STAC Item by collection and item ID."""
    return await execution.execute_tool(
        "get_item",
        arguments={
            "collection_id": collection_id,
            "item_id": item_id,
            "output_format": output_format,
        },
        catalog_url=catalog_url,
        headers=None,
    )


@app.tool
async def search_items(
    collections: list[str] | str,
    bbox: list[float] | str | None = None,
    datetime: str | None = None,
    limit: int | None = 10,
    query: dict[str, Any] | str | None = None,
    output_format: str | None = "text",
    catalog_url: str | None = None,
) -> list[dict[str, Any]]:
    """Search for STAC items."""
    arguments = preprocess_parameters(
        {
            "collections": collections,
            "bbox": bbox,
            "datetime": datetime,
            "limit": limit,
            "query": query,
            "output_format": output_format,
        }
    )
    return await execution.execute_tool(
        "search_items",
        arguments=arguments,
        catalog_url=catalog_url,
        headers=None,
    )


@app.tool
async def estimate_data_size(
    collections: list[str] | str,
    bbox: list[float] | str | None = None,
    datetime: str | None = None,
    query: dict[str, Any] | str | None = None,
    aoi_geojson: dict[str, Any] | str | None = None,
    limit: int | None = 10,
    force_metadata_only: bool | None = False,
    output_format: str | None = "text",
    catalog_url: str | None = None,
) -> list[dict[str, Any]]:
    """Estimate the data size for a STAC query."""
    arguments = preprocess_parameters(
        {
            "collections": collections,
            "bbox": bbox,
            "datetime": datetime,
            "query": query,
            "aoi_geojson": aoi_geojson,
            "limit": limit,
            "force_metadata_only": force_metadata_only,
            "output_format": output_format,
        }
    )
    return await execution.execute_tool(
        "estimate_data_size",
        arguments=arguments,
        catalog_url=catalog_url,
        headers=None,
    )


@app.tool
async def get_queryables(
    collection_id: list[str],
    catalog_url: str | None = None,
) -> list[dict[str, Any]]:
    """Get the queryable properties for a specific STAC collection by its ID."""
    return await execution.execute_tool(
        "get_queryables",
        {"collection_id": collection_id},
        catalog_url=catalog_url,
        headers=None,
    )


@app.tool
async def get_aggregations(
    collections: list[str],
    bbox: list[float] | None = None,
    datetime: str | None = None,
    query: dict[str, Any] | None = None,
    catalog_url: str | None = None,
) -> list[dict[str, Any]]:
    """Get aggregations for STAC items."""
    return await execution.execute_tool(
        "get_aggregations",
        arguments={
            "collections": collections,
            "bbox": bbox,
            "datetime": datetime,
            "query": query,
        },
        catalog_url=catalog_url,
        headers=None,
    )


@app.tool
async def get_sensor_registry_info() -> list[dict[str, Any]]:
    """Get information about the STAC sensor registry."""
    return await execution.execute_tool(
        "sensor_registry_info",
        arguments={},
        catalog_url=None,
        headers=None,
    )
