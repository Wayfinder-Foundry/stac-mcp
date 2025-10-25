from __future__ import annotations

import logging
from typing import Any

from fastmcp.server.server import FastMCP

from stac_mcp.tools import execution

app = FastMCP()

_LOGGER = logging.getLogger(__name__)

# Keep imports local to avoid hard dependency at module-import time.
_ESTIMATE_HANDLER = None
try:
    # import lazily to avoid import-time side-effects when package not fully
    # installed (tests may run without fastmcp present)
    from stac_mcp.tools.estimate_data_size import handle_estimate_data_size

    _ESTIMATE_HANDLER = handle_estimate_data_size
except (ImportError, ModuleNotFoundError):  # pragma: no cover - defensive import
    _ESTIMATE_HANDLER = None


@app.tool
async def get_root() -> list[dict[str, Any]]:
    """Get the root STAC catalog document."""
    return await execution.execute_tool("get_root", {})


@app.tool
async def get_conformance() -> list[dict[str, Any]]:
    """Get the conformance classes for the STAC API."""
    return await execution.execute_tool("get_conformance", {})


@app.tool
async def search_collections(
    limit: int | None = 10,
    catalog_url: str | None = None,
) -> list[dict[str, Any]]:
    """Search for STAC collections."""
    return await execution.execute_tool(
        "search_collections", {"limit": limit}, catalog_url=catalog_url
    )


@app.tool
async def get_collection(
    collection_id: str,
    catalog_url: str | None = None,
) -> list[dict[str, Any]]:
    """Get a specific STAC collection by its ID."""
    return await execution.execute_tool(
        "get_collection", {"collection_id": collection_id}, catalog_url=catalog_url
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
    )


@app.tool
async def search_items(
    collections: list[str],
    bbox: list[float] | None = None,
    datetime: str | None = None,
    limit: int | None = 10,
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
        },
        catalog_url=catalog_url,
    )

@app.tool
async def estimate_data_size(
    collections: list[str],
    bbox: list[float] | None = None,
    datetime: str | None = None,
    query: dict[str, Any] | None = None,
    aoi_geojson: dict[str, Any] | None = None,
    limit: int | None = 100,
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
    )


@app.tool
async def create_item(
    collection_id: str,
    item: dict[str, Any],
    api_key: str | None = None,
    catalog_url: str | None = None,
) -> list[dict[str, Any]]:
    """Create a new STAC Item in a collection."""
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    return await execution.execute_tool(
        "create_item",
        arguments={"collection_id": collection_id, "item": item, "api_key": api_key},
        catalog_url=catalog_url,
        headers=headers,
    )


@app.tool
async def update_item(
    collection_id: str,
    item: dict[str, Any],
    api_key: str | None = None,
    catalog_url: str | None = None,
) -> list[dict[str, Any]]:
    """Update an existing STAC Item in a collection."""
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    return await execution.execute_tool(
        "update_item",
        arguments={"collection_id": collection_id, "item": item, "api_key": api_key},
        catalog_url=catalog_url,
        headers=headers,
    )


@app.tool
async def delete_item(
    collection_id: str,
    item_id: str,
    api_key: str | None = None,
    catalog_url: str | None = None,
) -> list[dict[str, Any]]:
    """Delete a STAC Item from a collection."""
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key
    return await execution.execute_tool(
        "delete_item",
        arguments={
            "collection_id": collection_id,
            "item_id": item_id,
            "api_key": api_key,
        },
        catalog_url=catalog_url,
        headers=headers,
    )
