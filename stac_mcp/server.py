"""Main MCP Server implementation for STAC requests."""

import asyncio
import logging
from typing import Any

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)
from pystac_client import Client
from pystac_client.exceptions import APIError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the MCP server
server = Server("stac-mcp")


class STACClient:
    """STAC Client wrapper for common operations."""

    def __init__(
        self,
        catalog_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1",
    ):
        """Initialize STAC client with default to Microsoft Planetary Computer."""
        self.catalog_url = catalog_url
        self._client: Client | None = None

    @property
    def client(self) -> Client:
        """Get or create STAC client."""
        if self._client is None:
            self._client = Client.open(self.catalog_url)
        return self._client

    def search_collections(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get list of available collections."""
        try:
            collections = []
            for collection in self.client.get_collections():
                collections.append(
                    {
                        "id": collection.id,
                        "title": collection.title or collection.id,
                        "description": collection.description,
                        "extent": (
                            collection.extent.to_dict() if collection.extent else None
                        ),
                        "license": collection.license,
                        "providers": (
                            [p.to_dict() for p in collection.providers]
                            if collection.providers
                            else []
                        ),
                    },
                )
                if len(collections) >= limit:
                    break
            return collections
        except APIError as e:
            logger.error(f"Error fetching collections: {e}")
            raise

    def get_collection(self, collection_id: str) -> dict[str, Any]:
        """Get details for a specific collection."""
        try:
            collection = self.client.get_collection(collection_id)
            return {
                "id": collection.id,
                "title": collection.title or collection.id,
                "description": collection.description,
                "extent": collection.extent.to_dict() if collection.extent else None,
                "license": collection.license,
                "providers": (
                    [p.to_dict() for p in collection.providers]
                    if collection.providers
                    else []
                ),
                "summaries": (
                    collection.summaries.to_dict() if collection.summaries else {}
                ),
                "assets": (
                    {k: v.to_dict() for k, v in collection.assets.items()}
                    if collection.assets
                    else {}
                ),
            }
        except APIError as e:
            logger.error(f"Error fetching collection {collection_id}: {e}")
            raise

    def search_items(
        self,
        collections: list[str] | None = None,
        bbox: list[float] | None = None,
        datetime: str | None = None,
        query: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search for STAC items."""
        try:
            search = self.client.search(
                collections=collections,
                bbox=bbox,
                datetime=datetime,
                query=query,
                limit=limit,
            )

            items = []
            for item in search.items():
                items.append(
                    {
                        "id": item.id,
                        "collection": item.collection_id,
                        "geometry": item.geometry,
                        "bbox": item.bbox,
                        "datetime": (
                            item.datetime.isoformat() if item.datetime else None
                        ),
                        "properties": item.properties,
                        "assets": {k: v.to_dict() for k, v in item.assets.items()},
                    },
                )
                if len(items) >= limit:
                    break

            return items
        except APIError as e:
            logger.error(f"Error searching items: {e}")
            raise

    def get_item(self, collection_id: str, item_id: str) -> dict[str, Any]:
        """Get a specific STAC item."""
        try:
            item = self.client.get_collection(collection_id).get_item(item_id)
            return {
                "id": item.id,
                "collection": item.collection_id,
                "geometry": item.geometry,
                "bbox": item.bbox,
                "datetime": item.datetime.isoformat() if item.datetime else None,
                "properties": item.properties,
                "assets": {k: v.to_dict() for k, v in item.assets.items()},
            }
        except APIError as e:
            logger.error(
                f"Error fetching item {item_id} from collection {collection_id}: {e}",
            )
            raise


# Global STAC client instance
stac_client = STACClient()


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available STAC tools."""
    return [
        Tool(
            name="search_collections",
            description="Search and list available STAC collections",
            inputSchema={
                "type": "object",
                "properties": {
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
    ]


@server.call_tool()
async def handle_call_tool(tool_name: str, arguments: dict):
    """Handle tool calls for STAC operations."""
    try:
        # Check if custom catalog URL is provided
        catalog_url = arguments.get("catalog_url")
        if catalog_url:
            client = STACClient(catalog_url)
        else:
            client = stac_client

        if tool_name == "search_collections":
            limit = arguments.get("limit", 10)
            collections = client.search_collections(limit=limit)

            result_text = f"Found {len(collections)} collections:\n\n"
            for collection in collections:
                result_text += f"**{collection['title']}** (`{collection['id']}`)\n"
                if collection["description"]:
                    result_text += f"  {collection['description'][:200]}{'...' if len(collection['description']) > 200 else ''}\n"
                result_text += f"  License: {collection['license']}\n\n"

            return [TextContent(type="text", text=result_text)]

        if tool_name == "get_collection":
            collection_id = arguments["collection_id"]
            collection = client.get_collection(collection_id)

            result_text = f"**Collection: {collection['title']}**\n\n"
            result_text += f"ID: `{collection['id']}`\n"
            result_text += f"Description: {collection['description']}\n"
            result_text += f"License: {collection['license']}\n\n"

            if collection["extent"]:
                extent = collection["extent"]
                if "spatial" in extent and extent["spatial"]["bbox"]:
                    bbox = extent["spatial"]["bbox"][0]
                    result_text += f"Spatial Extent: [{bbox[0]:.2f}, {bbox[1]:.2f}, {bbox[2]:.2f}, {bbox[3]:.2f}]\n"
                if "temporal" in extent and extent["temporal"]["interval"]:
                    interval = extent["temporal"]["interval"][0]
                    result_text += f"Temporal Extent: {interval[0]} to {interval[1] or 'present'}\n"

            if collection["providers"]:
                result_text += f"\nProviders: {len(collection['providers'])}\n"
                for provider in collection["providers"]:
                    result_text += f"  - {provider.get('name', 'Unknown')} ({provider.get('roles', [])})\n"

            return [TextContent(type="text", text=result_text)]

        if tool_name == "search_items":
            collections = arguments.get("collections")
            bbox = arguments.get("bbox")
            datetime = arguments.get("datetime")
            query = arguments.get("query")
            limit = arguments.get("limit", 10)

            items = client.search_items(
                collections=collections,
                bbox=bbox,
                datetime=datetime,
                query=query,
                limit=limit,
            )

            result_text = f"Found {len(items)} items:\n\n"
            for item in items:
                result_text += (
                    f"**{item['id']}** (Collection: `{item['collection']}`)\n"
                )
                if item["datetime"]:
                    result_text += f"  Date: {item['datetime']}\n"
                if item["bbox"]:
                    bbox = item["bbox"]
                    result_text += f"  BBox: [{bbox[0]:.2f}, {bbox[1]:.2f}, {bbox[2]:.2f}, {bbox[3]:.2f}]\n"
                result_text += f"  Assets: {len(item['assets'])}\n\n"

            return [TextContent(type="text", text=result_text)]

        if tool_name == "get_item":
            collection_id = arguments["collection_id"]
            item_id = arguments["item_id"]

            item = client.get_item(collection_id, item_id)

            result_text = f"**Item: {item['id']}**\n\n"
            result_text += f"Collection: `{item['collection']}`\n"
            if item["datetime"]:
                result_text += f"Date: {item['datetime']}\n"
            if item["bbox"]:
                bbox = item["bbox"]
                result_text += f"BBox: [{bbox[0]:.2f}, {bbox[1]:.2f}, {bbox[2]:.2f}, {bbox[3]:.2f}]\n"

            result_text += "\n**Properties:**\n"
            for key, value in item["properties"].items():
                if isinstance(value, (str, int, float, bool)):
                    result_text += f"  {key}: {value}\n"

            result_text += f"\n**Assets ({len(item['assets'])}):**\n"
            for asset_key, asset in item["assets"].items():
                result_text += f"  - **{asset_key}**: {asset.get('title', asset_key)}\n"
                result_text += f"    Type: {asset.get('type', 'unknown')}\n"
                if "href" in asset:
                    result_text += f"    URL: {asset['href']}\n"

            return [TextContent(type="text", text=result_text)]

        raise ValueError(f"Unknown tool: {tool_name}")

    except Exception as e:
        logger.error(f"Error in tool call {tool_name}: {e}")
        raise


async def main():
    """Main entry point for the STAC MCP server."""
    # Run the server using stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="stac-mcp",
                server_version="0.1.1",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def cli_main():
    """CLI entry point for the STAC MCP server."""
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
