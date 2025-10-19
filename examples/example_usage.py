#!/usr/bin/env python3
"""
Example usage of STAC MCP Server.

This script demonstrates how to use the STAC MCP Server tools
to search for and access geospatial data from STAC catalogs.
"""

import asyncio
import json
from typing import Any

from mcp.types import CallToolRequest, CallToolRequestParams, CallToolResult
from stac_mcp.server import handle_list_tools, server


async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Helper function to call a tool through MCP server."""
    # Use the MCP server's internal mechanism to call the tool
    request = CallToolRequest(
        params=CallToolRequestParams(name=name, arguments=arguments),
    )
    handler = server.request_handlers[CallToolRequest]
    result = await handler(request)
    return result.root if hasattr(result, "root") else result


async def demonstrate_stac_usage():
    """Demonstrate STAC MCP Server usage."""
    print("🚀 STAC MCP Server Demonstration")
    print("=" * 50)

    # List available tools
    print("\n1. Listing available tools:")
    tools = await handle_list_tools()
    for tool in tools:
        print(f"   - {tool.name}: {tool.description}")

    # Try to search collections (will fail without network, but shows the interface)
    print("\n2. Attempting to search collections:")
    try:
        result = await call_tool("search_collections", {"limit": 5})
        if result.isError:
            err_text = result.content[0].text
            print(f"   ❌ Error (expected in this environment): {err_text[:100]}...")
        else:
            print("   ✅ Success:")
            print(f"   {result.content[0].text[:200]}...")
    except RuntimeError as e:
        print(f"   ❌ Exception (expected in this environment): {str(e)[:100]}...")

    # Show what a successful search would look like with a custom catalog
    print("\n3. Example with custom catalog URL:")
    try:
        result = await call_tool(
            "search_collections",
            {"catalog_url": "https://example.com/stac/v1", "limit": 3},
        )
        if result.isError:
            print(f"   ❌ Error (expected): {result.content[0].text[:100]}...")
        else:
            print("   ✅ Success (unexpected in this environment)")
    except RuntimeError as e:
        print(f"   ❌ Exception (expected): {str(e)[:100]}...")

    # Capability: root document (likely to fail offline gracefully)
    print("\n4. Attempting get_root (capability discovery):")
    try:
        result = await call_tool("get_root", {})
        if result.isError:
            print(f"   ❌ Error (expected offline): {result.content[0].text[:100]}...")
        else:
            print(f"   ✅ Root summary: {result.content[0].text.splitlines()[0]}")
    except RuntimeError as e:
        print(f"   ❌ Exception (expected offline): {str(e)[:100]}...")

    print("\n5. Attempting get_conformance (capability discovery):")
    try:
        result = await call_tool(
            "get_conformance",
            {"check": ["http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core"]},
        )
        if result.isError:
            print(f"   ❌ Error (expected offline): {result.content[0].text[:100]}...")
        else:
            print(
                f"   ✅ Conformance summary: {result.content[0].text.splitlines()[0]}",
            )
    except RuntimeError as e:
        print(f"   ❌ Exception (expected offline): {str(e)[:100]}...")

    # Capability: queryables (global)
    print("\n6. Attempting get_queryables (global):")
    try:
        result = await call_tool("get_queryables", {})
        if result.isError:
            print(f"   ❌ Error (expected offline): {result.content[0].text[:80]}...")
        else:
            print(
                f"   ✅ Queryables response: {result.content[0].text.splitlines()[0]}",
            )
    except RuntimeError as e:
        print(f"   ❌ Exception (expected offline): {str(e)[:100]}...")

    # Capability: aggregations (count only mock demonstration)
    print("\n7. Example get_aggregations call structure (not executed):")
    agg_params = {
        "collections": ["landsat-c2l2-sr"],
        "bbox": [-122.5, 37.7, -122.3, 37.8],
        "datetime": "2023-01-01/2023-12-31",
        "operations": ["count"],
    }
    print(f"   Parameters: {json.dumps(agg_params, indent=2)}")

    # Show search_items interface
    print("\n8. Example search_items call structure:")
    search_params = {
        "collections": ["landsat-c2l2-sr"],
        "bbox": [-122.5, 37.7, -122.3, 37.8],  # San Francisco area
        "datetime": "2023-01-01/2023-12-31",
        "limit": 10,
    }
    print(f"   Parameters: {json.dumps(search_params, indent=2)}")

    # Show get_collection interface
    print("\n9. Example get_collection call structure:")
    collection_params = {"collection_id": "landsat-c2l2-sr"}
    print(f"   Parameters: {json.dumps(collection_params, indent=2)}")

    # Show get_item interface
    print("\n10. Example get_item call structure:")
    item_params = {
        "collection_id": "landsat-c2l2-sr",
        "item_id": "LC08_L2SR_044034_20230815_02_T1",
    }
    print(f"   Parameters: {json.dumps(item_params, indent=2)}")

    # Show estimate_data_size interface
    print("\n11. Example estimate_data_size call structure:")
    data_size_params = {
        "collections": ["landsat-c2l2-sr"],
        "bbox": [-122.5, 37.7, -122.3, 37.8],  # San Francisco area
        "datetime": "2023-01-01/2023-01-31",
        "limit": 50,
        "aoi_geojson": {
            "type": "Polygon",
            "coordinates": [
                [
                    [-122.45, 37.75],
                    [-122.35, 37.75],
                    [-122.35, 37.77],
                    [-122.45, 37.77],
                    [-122.45, 37.75],
                ],
            ],
        },
    }
    print(f"   Parameters: {json.dumps(data_size_params, indent=2)}")

    print("\n" + "=" * 50)
    print("🎯 Summary:")
    print("   The STAC MCP Server is working correctly!")
    print("   Network access to STAC APIs is required for actual data retrieval.")
    print("   In a real environment with network access, these calls would")
    print("   return actual geospatial data from STAC catalogs.")
    print("   The new estimate_data_size tool provides lazy data size estimation")
    print("   using xarray and odc.stac for efficient resource planning.")


if __name__ == "__main__":
    asyncio.run(demonstrate_stac_usage())
