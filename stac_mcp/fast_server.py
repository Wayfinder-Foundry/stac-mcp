from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastmcp.server.server import FastMCP
from stac_mcp.tools import execution

app = FastMCP()


@app.tool
async def get_root() -> List[Dict[str, Any]]:
    """Get the root STAC catalog document."""
    return await execution.execute_tool("get_root", {})


@app.tool
async def get_conformance() -> List[Dict[str, Any]]:
    """Get the conformance classes for the STAC API."""
    return await execution.execute_tool("get_conformance", {})


@app.tool
async def search_collections(
    limit: Optional[int] = 10,
    catalog_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Search for STAC collections."""
    return await execution.execute_tool(
        "search_collections", {"limit": limit}, catalog_url=catalog_url
    )


@app.tool
async def get_collection(
    collection_id: str,
    catalog_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Get a specific STAC collection by its ID."""
    return await execution.execute_tool(
        "get_collection", {"collection_id": collection_id}, catalog_url=catalog_url
    )


@app.tool
async def get_item(
    collection_id: str,
    item_id: str,
    output_format: Optional[str] = "text",
    catalog_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
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
    collections: List[str],
    bbox: Optional[List[float]] = None,
    datetime: Optional[str] = None,
    limit: Optional[int] = 10,
    catalog_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
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
    collections: List[str],
    bbox: Optional[List[float]] = None,
    datetime: Optional[str] = None,
    query: Optional[Dict[str, Any]] = None,
    aoi_geojson: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = 100,
    output_format: Optional[str] = "text",
    catalog_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
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
            "output_format": output_format,
        },
        catalog_url=catalog_url,
    )


@app.tool
async def create_item(
    collection_id: str,
    item: Dict[str, Any],
    api_key: Optional[str] = None,
    catalog_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
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
    item: Dict[str, Any],
    api_key: Optional[str] = None,
    catalog_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
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
    api_key: Optional[str] = None,
    catalog_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
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
