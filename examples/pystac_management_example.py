#!/usr/bin/env python3
"""Example usage of PySTAC-based CRUDL tools.

This script demonstrates how to use the new pystac-based tools for managing
STAC catalogs, collections, and items on both local filesystems and remote
endpoints.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any

from mcp.types import CallToolRequest, CallToolRequestParams, CallToolResult

from stac_mcp.server import handle_list_tools, server


async def call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
    """Helper function to call a tool through MCP server."""
    request = CallToolRequest(
        params=CallToolRequestParams(name=name, arguments=arguments),
    )
    handler = server.request_handlers[CallToolRequest]
    result = await handler(request)
    return result.root if hasattr(result, "root") else result


async def demonstrate_pystac_usage():
    """Demonstrate PySTAC-based CRUDL tools."""
    print("🚀 PySTAC-based CRUDL Tools Demonstration")
    print("=" * 60)

    # Create a temporary directory for local operations
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)

        print("\n📋 1. Listing available PySTAC tools:")
        tools = await handle_list_tools()
        pystac_tools = [t for t in tools if t.name.startswith("pystac_")]
        print(f"   Found {len(pystac_tools)} PySTAC tools:")
        for tool in pystac_tools:
            print(f"   - {tool.name}")

        # ==================== Catalog Examples ====================
        print("\n📦 2. Catalog Management Examples:")

        print("\n   2a. Creating a local catalog:")
        catalog_path = str(tmp_path / "test-catalog" / "catalog.json")
        try:
            result = await call_tool(
                "pystac_create_catalog",
                {
                    "path": catalog_path,
                    "catalog_id": "example-catalog",
                    "description": "Example STAC catalog for demonstration",
                    "title": "Example Catalog",
                },
            )
            if result.isError:
                print(f"   ❌ Error: {result.content[0].text[:200]}")
            else:
                print(f"   ✅ Catalog created at: {catalog_path}")
                data = json.loads(result.content[0].text)
                print(f"   Catalog ID: {data.get('id', 'N/A')}")
        except Exception as e:  # noqa: BLE001
            print(f"   ⚠️ Note: {str(e)[:100]}")

        print("\n   2b. Reading the catalog:")
        try:
            result = await call_tool(
                "pystac_read_catalog",
                {"path": catalog_path},
            )
            if result.isError:
                print(f"   ❌ Error: {result.content[0].text[:200]}")
            else:
                print("   ✅ Catalog read successfully")
        except Exception as e:  # noqa: BLE001
            print(f"   ⚠️ Note: {str(e)[:100]}")

        print("\n   2c. Listing catalogs in directory:")
        try:
            result = await call_tool(
                "pystac_list_catalogs",
                {"base_path": str(tmp_path)},
            )
            if result.isError:
                print(f"   ❌ Error: {result.content[0].text[:200]}")
            else:
                print("   ✅ Catalogs listed successfully")
        except Exception as e:  # noqa: BLE001
            print(f"   ⚠️ Note: {str(e)[:100]}")

        # ==================== Collection Examples ====================
        print("\n📚 3. Collection Management Examples:")

        print("\n   3a. Creating a local collection:")
        collection_path = str(tmp_path / "test-collection" / "collection.json")
        collection_data = {
            "type": "Collection",
            "id": "example-collection",
            "stac_version": "1.0.0",
            "description": "Example STAC collection",
            "license": "MIT",
            "extent": {
                "spatial": {"bbox": [[-180, -90, 180, 90]]},
                "temporal": {"interval": [[None, None]]},
            },
            "links": [],
        }
        try:
            result = await call_tool(
                "pystac_create_collection",
                {
                    "path": collection_path,
                    "collection": collection_data,
                },
            )
            if result.isError:
                print(f"   ❌ Error: {result.content[0].text[:200]}")
            else:
                print(f"   ✅ Collection created at: {collection_path}")
        except Exception as e:  # noqa: BLE001
            print(f"   ⚠️ Note: {str(e)[:100]}")

        print("\n   3b. Reading the collection:")
        try:
            result = await call_tool(
                "pystac_read_collection",
                {"path": collection_path},
            )
            if result.isError:
                print(f"   ❌ Error: {result.content[0].text[:200]}")
            else:
                print("   ✅ Collection read successfully")
        except Exception as e:  # noqa: BLE001
            print(f"   ⚠️ Note: {str(e)[:100]}")

        # ==================== Item Examples ====================
        print("\n📄 4. Item Management Examples:")

        print("\n   4a. Creating a local item:")
        item_path = str(tmp_path / "test-item" / "item.json")
        item_data = {
            "type": "Feature",
            "stac_version": "1.0.0",
            "id": "example-item",
            "properties": {"datetime": "2023-01-01T00:00:00Z"},
            "geometry": {
                "type": "Point",
                "coordinates": [0.0, 0.0],
            },
            "links": [],
            "assets": {},
        }
        try:
            result = await call_tool(
                "pystac_create_item",
                {
                    "path": item_path,
                    "item": item_data,
                },
            )
            if result.isError:
                print(f"   ❌ Error: {result.content[0].text[:200]}")
            else:
                print(f"   ✅ Item created at: {item_path}")
        except Exception as e:  # noqa: BLE001
            print(f"   ⚠️ Note: {str(e)[:100]}")

        print("\n   4b. Reading the item:")
        try:
            result = await call_tool(
                "pystac_read_item",
                {"path": item_path},
            )
            if result.isError:
                print(f"   ❌ Error: {result.content[0].text[:200]}")
            else:
                print("   ✅ Item read successfully")
        except Exception as e:  # noqa: BLE001
            print(f"   ⚠️ Note: {str(e)[:100]}")

        # ==================== Remote Examples ====================
        print("\n🌐 5. Remote Operations (with API key):")
        print("   Note: Remote operations require a running STAC server")
        print("   and should set STAC_API_KEY environment variable if needed.")
        print()
        print("   Example remote catalog URL:")
        print("   https://example.com/stac/catalogs/my-catalog")
        print()
        print("   Example usage with API key:")
        print("   export STAC_API_KEY=your-api-key")
        print("   Then use tools with remote URLs like:")
        print('   {"path": "https://example.com/stac/catalogs", ...}')

    print("\n" + "=" * 60)
    print("🎯 Summary:")
    print("   ✅ PySTAC-based CRUDL tools demonstrated")
    print("   ✅ Local filesystem operations shown")
    print("   ✅ Remote operations explained (require running server)")
    print("   ✅ API key authentication supported via STAC_API_KEY")
    print()
    print("   These tools complement the existing transaction tools:")
    print("   - Transaction tools: Remote API operations via pystac-client")
    print("   - PySTAC tools: Local/remote operations via pystac library")


if __name__ == "__main__":
    asyncio.run(demonstrate_pystac_usage())
