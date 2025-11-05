"""Prompt registrations for the STAC MCP server.

This module exposes a single function `register_prompts(app)` which attaches
all prompt definitions to the provided FastMCP app. Keeping prompts in a
separate module avoids making the server module too large and prevents
import cycles.

Each prompt definition includes both the human-readable content and the
machine-readable payload schema and example. They aim to be epistemically
transparent about their purpose and usage - guiding users on geospatial data
tool interactions.
"""

from __future__ import annotations

import json
from typing import Any

from fastmcp.prompts.prompt import PromptMessage, TextContent


def register_prompts(app: Any) -> None:
    """Register all prompt definitions on the provided FastMCP `app`."""
    _common_required = ["collections", "datetime", "bbox", "limit"]

    @app.prompt(
        name="sensor_registry_info_prompt",
        description="Information about the STAC sensor registry",
        meta={},
    )
    def _prompt_sensor_registry_info() -> PromptMessage:
        human = (
            "The internal STAC sensor registry maps collection ids to native "
            "dtypes and provider-specific aliases. Use it as a fallback "
            "when a collection id cannot be found by searching the target "
            "catalog. It is not exhaustive; always confirm with "
            "search_collections or get_collection when available."
        )
        payload = {
            "name": "sensor_registry_info",
            "description": (
                "Return the internal sensor registry mapping of collection ids "
                "to dtype info."
            ),
            "parameters": {"type": "object", "properties": {}, "required": []},
            "example": {},
        }
        return PromptMessage(
            role="user",
            content=TextContent(type="text", text=human),
            _meta={"machine_payload": payload},
        )

    @app.prompt(
        name="stac_tool_overview_prompt",
        description="Overview of STAC tools available",
        meta={},
    )
    def _prompt_stac_tool_overview() -> PromptMessage:
        human = (
            "Available STAC tools: get_root, get_conformance, search_collections, "
            "get_collection, get_queryables, search_items, get_item, and "
            "estimate_data_size."
        )
        payload = {
            "name": "stac_tool_overview",
            "description": "Overview of STAC tools available",
            "parameters": {},
            "example": {},
        }
        return PromptMessage(
            role="user",
            content=TextContent(type="text", text=human),
            _meta={"machine_payload": payload},
        )

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
            "example": {
                "collection_id": "c1",
                "item_id": "i1",
                "output_format": "json",
            },
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
            "example": {
                "collection_id": "c1",
                "item_id": "i1",
                "output_format": "json",
            },
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
                "required": _common_required,
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
            "required": _common_required,
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
            "If get_collections has not been run yet for the target catalog, "
            "run it first to populate the collection list.\n"
            "On responses with zero items, validate that the collection IDs "
            "are correct.\n"
            "If using 'bbox', ensure coordinates are in [minLon, minLat, maxLon, "
            "maxLat] order.\n"
            "Datetime should be in ISO 8601 format, e.g., '2020-01-01/2020-12-31'.\n"
            "Limit should be a positive integer.\n"
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
                    "limit": {"type": "integer", "default": 10},
                    "force_metadata_only": {"type": "boolean", "default": False},
                    "output_format": {
                        "type": "string",
                        "enum": ["text", "json"],
                        "default": "text",
                    },
                },
                "required": _common_required,
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
            "required": _common_required,
        }
        payload = {
            "name": "estimate_data_size",
            "description": "Estimate data size for a STAC query.",
            "parameters": schema,
            "example": {"collections": ["c1"], "limit": 10, "output_format": "json"},
        }
        human = (
            f"Tool: estimate_data_size\nDescription: {payload['description']}\n\n"
            "Parameters:\n"
            f"{json.dumps(schema, indent=2)}\n\n"
            "Note: The response may include 'reported_bytes' and 'registry_bytes'\n"
            "for per-variable estimates. Prefer 'registry_bytes' when a sensor "
            "registry provides an instrument-native dtype.\n\n"
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
                "required": _common_required,
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
            "required": _common_required,
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

    @app.prompt(
        name="tool_ordering_info_prompt",
        description="Information on tool ordering and usage",
        meta={},
    )
    def _prompt_tool_ordering_info() -> PromptMessage:
        human = (
            "Preferred order: get_root -> get_conformance -> search_collections -> "
            "get_collection -> get_queryables -> search_items -> get_item -> "
            "estimate_data_size. Use caching and sampling (limit) when "
            "estimating."
        )
        payload = {
            "name": "tool_ordering_info",
            "description": "Preferred order and usage guidance for STAC tools",
            "parameters": {},
            "example": {},
        }
        return PromptMessage(
            role="user",
            content=TextContent(type="text", text=human),
            _meta={"machine_payload": payload},
        )

    @app.prompt(
        name="catalog_discovery_prompt",
        description="Steps to discover what a STAC catalog supports",
        meta={},
    )
    def _prompt_catalog_discovery() -> PromptMessage:
        human = (
            "Discovery steps:\n"
            "1) Call get_root to locate the catalog root and entrypoints.\n"
            "2) Call get_conformance to list supported STAC extensions.\n"
            "3) Run search_collections (limit=50) to inspect available "
            "collection IDs and titles.\n"
            "4) Sample get_collection for candidate collections to validate "
            "assets and links.\n\n"
            "Parameters:\n"
            "- None\n\n"
            "Example:\n"
            '{"catalog_url": "https://planetarycomputer.microsoft.com/api/stac/v1"}\n\n'
            "Notes:\n"
            "Use these steps before searching items to avoid mismatched "
            "collection IDs."
        )
        payload = {
            "name": "catalog_discovery",
            "description": "Checklist for discovering catalog capabilities",
            "parameters": {},
            "example": {},
        }
        return PromptMessage(
            role="user",
            content=TextContent(type="text", text=human),
            _meta={"machine_payload": payload},
        )

    @app.prompt(
        name="collection_alias_resolution_prompt",
        description="How to resolve collection id aliases across catalogs",
        meta={},
    )
    def _prompt_collection_alias_resolution() -> PromptMessage:
        human = (
            "Alias resolution strategy:\n"
            "1) When a collection ID lookup returns no result, normalize case "
            "and punctuation.\n"
            "2) Try provider-specific aliases (for example: 'sentinel-2-l2a' "
            "vs 'sentinel-2-c1-l2a').\n"
            "3) For each candidate alias call get_collection to verify presence "
            "and canonical metadata.\n"
            "4) If still unresolved, call the sensor_registry_info tool as a "
            "fallback to map known aliases.\n\n"
            "Parameters:\n"
            "- collection_id: string (optional)\n\n"
            "Example:\n"
            '{"collection_id": "sentinel-2-c1-l2a"}\n'
        )
        payload = {
            "name": "collection_alias_resolution",
            "description": "Steps to resolve collection id aliases across providers",
            "parameters": {},
            "example": {},
        }
        return PromptMessage(
            role="user",
            content=TextContent(type="text", text=human),
            _meta={"machine_payload": payload},
        )

    @app.prompt(
        name="estimate_size_strategy_prompt",
        description="Safe strategies for estimating data size at scale",
        meta={},
    )
    def _prompt_estimate_size_strategy() -> PromptMessage:
        human = (
            "Estimation strategy:\n"
            "1) Sample a modest number of items (N=10-100) across the "
            "requested timeframe.\n"
            "2) Prefer 'registry_bytes' when the sensor registry provides an "
            "instrument-native dtype.\n"
            "3) Aggregate per-band sizes and scale by item counts; persist "
            "detailed per-sample results as fixtures.\n"
            "4) Avoid downloading full assets; use metadata-only measurements "
            "whenever possible.\n\n"
            "Parameters:\n"
            "- collections: list[string]\n"
            "- limit: integer (samples per collection)\n\n"
            "Example:\n"
            '{"collections": ["sentinel-2-l2a"], "limit": 20}\n'
        )
        payload = {
            "name": "estimate_size_strategy",
            "description": "Guidance for safely estimating dataset sizes",
            "parameters": {},
            "example": {},
        }
        return PromptMessage(
            role="user",
            content=TextContent(type="text", text=human),
            _meta={"machine_payload": payload},
        )

    @app.prompt(
        name="explain_tool_output_prompt",
        description="Summarize and explain tool outputs for humans",
        meta={
            "schema": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string"},
                    "payload": {"type": "object"},
                },
                "required": ["tool", "payload"],
            },
            "example": {"tool": "get_collection", "payload": {}},
        },
    )
    def _prompt_explain_tool_output() -> PromptMessage:
        schema = {
            "type": "object",
            "properties": {"tool": {"type": "string"}, "payload": {"type": "object"}},
            "required": ["tool", "payload"],
        }
        payload = {
            "name": "explain_tool_output",
            "description": "Summarize and explain tool outputs",
            "parameters": schema,
            "example": {"tool": "get_collection", "payload": {}},
        }
        human = (
            "Explain tool output:\n"
            "- Give a 2-4 sentence human summary of the tool output.\n"
            "- Highlight 3 most important fields and why they matter.\n"
            "- Provide 1-2 concrete next steps (e.g., call ordering or "
            "validation checks).\n\n"
            "Parameters:\n"
            "- tool: string\n"
            "- payload: object (the tool response)\n\n"
            "Example:\n"
            '{"tool": "get_collection", "payload": {}}\n'
        )
        return PromptMessage(
            role="user",
            content=TextContent(type="text", text=human),
            _meta={"machine_payload": payload},
        )
