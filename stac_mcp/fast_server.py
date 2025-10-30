from __future__ import annotations

import json
import logging
from typing import Any

from fastmcp.prompts.prompt import PromptMessage, TextContent
from fastmcp.server.server import FastMCP

from stac_mcp.tools import execution

app = FastMCP()

_LOGGER = logging.getLogger(__name__)

# Prompts to guide agents how to call tools correctly.
#
# Notes on metadata locations (why both `meta` and `_meta` exist):
# - The `@app.prompt(..., meta=...)` decorator accepts a `meta` kwarg which
#   FastMCP stores on the prompt descriptor returned by `client.list_prompts()`
#   as `.meta`. This is the decorator-provided metadata (schema/example).
# - When the prompt function returns a `PromptMessage`, we attach the
#   machine-readable payload (the JSON schema + example used to generate the
#   human-facing prompt) under the MCP aliased metadata field `_meta` on the
#   PromptMessage instance. Clients retrieving a rendered prompt (`get_prompt`)
#   should therefore look for `message._meta["machine_payload"]` for the
#   machine payload, while discovery via `list_prompts()` will find decorator
#   metadata under `.meta`.
#
# This dual-mapping keeps decorator metadata discoverable via prompt listing
# while making the specific per-message machine payload available on the
# returned PromptMessage under `_meta` so agents can programmatically inspect
# the exact payload used to render the human text.


@app.prompt(
    name="tool_get_root_prompt",
    description="Usage for get_root tool",
    meta={
        "schema": {"type": "object", "properties": {}, "required": []},
        "example": {},
    },
)
def _prompt_get_root() -> PromptMessage:
    schema = {"type": "object", "properties": {}, "required": []}
    payload = {
        "name": "get_root",
        "description": "Return the STAC root document.",
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


@app.prompt(
    name="tool_get_conformance_prompt",
    description="Usage for get_conformance tool",
    meta={
        "schema": {"type": "object", "properties": {}, "required": []},
        "example": {},
    },
)
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


@app.prompt(
    name="tool_search_collections_prompt",
    description="Usage for search_collections tool",
    meta={
        "schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10},
                "catalog_url": {"type": "string"},
            },
            "required": [],
        },
        "example": {"limit": 5},
    },
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


@app.prompt(
    name="tool_get_collection_prompt",
    description="Usage for get_collection tool",
    meta={
        "schema": {
            "type": "object",
            "properties": {
                "collection_id": {"type": "string"},
                "catalog_url": {"type": "string"},
            },
            "required": ["collection_id"],
        },
        "example": {"collection_id": "my-collection"},
    },
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


@app.prompt(
    name="tool_get_item_prompt",
    description="Usage for get_item tool",
    meta={
        "schema": {
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
        },
        "example": {"collection_id": "c1", "item_id": "i1", "output_format": "json"},
    },
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


@app.prompt(
    name="tool_search_items_prompt",
    description="Usage for search_items tool",
    meta={
        "schema": {
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
        },
        "example": {"collections": ["c1"], "limit": 3},
    },
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
        f"{json.dumps(payload['example'], indent=2)}"
    )
    return PromptMessage(
        role="user",
        content=TextContent(type="text", text=human),
        _meta={"machine_payload": payload},
    )


@app.prompt(
    name="tool_estimate_data_size_prompt",
    description="Usage for estimate_data_size tool",
    meta={
        "schema": {
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
        },
        "example": {"collections": ["c1"], "limit": 10, "output_format": "json"},
    },
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


@app.prompt(
    name="tool_get_queryables_prompt",
    description="Usage for get_queryables tool",
    meta={
        "schema": {
            "type": "object",
            "properties": {
                "collection_id": {"type": "string"},
                "catalog_url": {"type": "string"},
            },
            "required": [],
        },
        "example": {"collection_id": "my-collection"},
    },
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

@app.prompt(
    name="tool_get_aggregations_prompt",
    description="Usage for get_aggregations tool",
    meta={
        "schema": {
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
        },
        "example": {"collections": ["c1"], "datetime": "2020-01-01/2020-12-31"},
    },
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
        "description": "Get STAC aggregations.",
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
    """Get the root STAC catalog document."""
    return await execution.execute_tool("get_root", {}, catalog_url=None, headers=None)


@app.tool
async def get_conformance() -> list[dict[str, Any]]:
    """Get the conformance classes for the STAC API."""
    return await execution.execute_tool(
        "get_conformance", {}, catalog_url=None, headers=None
    )


@app.tool
async def search_collections(
    limit: int | None = 10,
    catalog_url: str | None = None,
) -> list[dict[str, Any]]:
    """Search for STAC collections."""
    return await execution.execute_tool(
        "search_collections", {"limit": limit}, catalog_url=catalog_url, headers=None
    )


@app.tool
async def get_collection(
    collection_id: str,
    catalog_url: str | None = None,
) -> list[dict[str, Any]]:
    """Get a specific STAC collection by its ID."""
    return await execution.execute_tool(
        "get_collection",
        {"collection_id": collection_id},
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
    collections: list[str],
    bbox: list[float] | None = None,
    datetime: str | None = None,
    limit: int | None = 10,
    query: dict[str, Any] | None = None,
    output_format: str | None = "text",
    catalog_url: str | None = None,
) -> list[dict[str, Any]]:
    """Search for STAC items."""
    return await execution.execute_tool(
        "search_items",
        arguments={
            "collections": collections,
            "bbox": bbox,
            "datetime": datetime,
            "limit": limit,
            "query": query,
            "output_format": output_format,
        },
        catalog_url=catalog_url,
        headers=None,
    )


@app.tool
async def estimate_data_size(
    collections: list[str],
    bbox: list[float] | None = None,
    datetime: str | None = None,
    query: dict[str, Any] | None = None,
    aoi_geojson: dict[str, Any] | None = None,
    limit: int | None = 10,
    force_metadata_only: bool | None = False,
    output_format: str | None = "text",
    catalog_url: str | None = None,
) -> list[dict[str, Any]]:
    """Estimate the data size for a STAC query."""
    return await execution.execute_tool(
        "estimate_data_size",
        arguments={
            "collections": collections,
            "bbox": bbox,
            "datetime": datetime,
            "query": query,
            "aoi_geojson": aoi_geojson,
            "limit": limit,
            "force_metadata_only": force_metadata_only,
            "output_format": output_format,
        },
        catalog_url=catalog_url,
        headers=None,
    )

@app.tool
async def get_queryables(
    collection_id: str,
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