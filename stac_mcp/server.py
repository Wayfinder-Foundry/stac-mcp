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

try:
    import odc.stac

    ODC_STAC_AVAILABLE = True
except ImportError:
    ODC_STAC_AVAILABLE = False

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

    def estimate_data_size(
        self,
        collections: list[str] | None = None,
        bbox: list[float] | None = None,
        datetime: str | None = None,
        query: dict[str, Any] | None = None,
        aoi_geojson: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """Estimate data size for a STAC query using odc.stac lazy loading."""
        if not ODC_STAC_AVAILABLE:
            raise RuntimeError(
                "odc.stac is not available. Please install it to use data size estimation.",
            )

        try:
            # Search for items first to get the actual STAC items
            search = self.client.search(
                collections=collections,
                bbox=bbox,
                datetime=datetime,
                query=query,
                limit=limit,
            )

            items = list(search.items())

            if not items:
                return {
                    "item_count": 0,
                    "estimated_size_bytes": 0,
                    "estimated_size_mb": 0,
                    "estimated_size_gb": 0,
                    "bbox_used": bbox,
                    "temporal_extent": datetime,
                    "collections": collections or [],
                    "clipped_to_aoi": False,
                    "message": "No items found for the given query parameters",
                }

            # Determine the effective bounding box for clipping
            effective_bbox = bbox
            clipped_to_aoi = False

            if aoi_geojson:
                # Extract bbox from AOI geojson for clipping
                from shapely.geometry import shape

                geom = shape(aoi_geojson)
                aoi_bounds = geom.bounds  # (minx, miny, maxx, maxy)

                # If we have both bbox and AOI, use the intersection (smaller area)
                if bbox:
                    effective_bbox = [
                        max(bbox[0], aoi_bounds[0]),  # west
                        max(bbox[1], aoi_bounds[1]),  # south
                        min(bbox[2], aoi_bounds[2]),  # east
                        min(bbox[3], aoi_bounds[3]),  # north
                    ]
                else:
                    effective_bbox = list(aoi_bounds)
                clipped_to_aoi = True

            # Use odc.stac to load the data lazily and estimate size
            try:
                # Load with odc.stac - this creates a lazy xarray dataset
                ds = odc.stac.load(
                    items,
                    bbox=effective_bbox,
                    chunks={},  # Enable dask chunking for lazy evaluation
                )

                # Calculate estimated size from the lazy dataset
                estimated_bytes = 0
                data_vars_info = []

                for var_name, data_array in ds.data_vars.items():
                    # Get size in bytes for each data variable
                    var_nbytes = data_array.nbytes
                    estimated_bytes += var_nbytes

                    data_vars_info.append(
                        {
                            "variable": var_name,
                            "shape": list(data_array.shape),
                            "dtype": str(data_array.dtype),
                            "size_bytes": var_nbytes,
                            "size_mb": round(var_nbytes / (1024 * 1024), 2),
                        },
                    )

                # Calculate different size units
                estimated_mb = estimated_bytes / (1024 * 1024)
                estimated_gb = estimated_bytes / (1024 * 1024 * 1024)

                # Get temporal extent from the actual items
                temporal_extent = None
                if items:
                    dates = [item.datetime for item in items if item.datetime]
                    if dates:
                        temporal_extent = (
                            f"{min(dates).isoformat()} to {max(dates).isoformat()}"
                        )

                return {
                    "item_count": len(items),
                    "estimated_size_bytes": estimated_bytes,
                    "estimated_size_mb": round(estimated_mb, 2),
                    "estimated_size_gb": round(estimated_gb, 4),
                    "bbox_used": effective_bbox,
                    "temporal_extent": temporal_extent or datetime,
                    "collections": collections
                    or list(set(item.collection_id for item in items)),
                    "clipped_to_aoi": clipped_to_aoi,
                    "data_variables": data_vars_info,
                    "spatial_dims": (
                        {"x": ds.dims.get("x", 0), "y": ds.dims.get("y", 0)}
                        if "x" in ds.dims and "y" in ds.dims
                        else {}
                    ),
                    "message": f"Successfully estimated data size for {len(items)} items",
                }

            except Exception as e:
                # If odc.stac fails, fall back to a rough estimation based on item metadata
                logger.warning(
                    f"odc.stac loading failed, using fallback estimation: {e}",
                )
                return self._fallback_size_estimation(
                    items,
                    effective_bbox,
                    datetime,
                    collections,
                    clipped_to_aoi,
                )

        except APIError as e:
            logger.error(f"Error in data size estimation: {e}")
            raise

    def _fallback_size_estimation(
        self,
        items: list,
        effective_bbox: list[float] | None,
        datetime: str | None,
        collections: list[str] | None,
        clipped_to_aoi: bool,
    ) -> dict[str, Any]:
        """Fallback method to estimate data size when odc.stac fails."""

        # Rough estimation based on number of assets and typical file sizes
        total_estimated_bytes = 0
        assets_info = []

        for item in items:
            for asset_name, asset in item.assets.items():
                # Try to get file size from asset metadata if available
                asset_size = 0
                if hasattr(asset, "extra_fields"):
                    # Some STAC items include file size in extra fields
                    asset_size = asset.extra_fields.get("file:size", 0)

                if asset_size == 0:
                    # Fallback: estimate based on asset type and bbox
                    media_type = getattr(asset, "media_type", "") or ""
                    if "tiff" in media_type.lower() or "geotiff" in media_type.lower():
                        # Rough estimate for GeoTIFF based on bbox area
                        if effective_bbox:
                            bbox_area = (effective_bbox[2] - effective_bbox[0]) * (
                                effective_bbox[3] - effective_bbox[1]
                            )
                            # Very rough estimate: ~10MB per square degree for typical satellite data
                            asset_size = int(bbox_area * 10 * 1024 * 1024)
                        else:
                            asset_size = 50 * 1024 * 1024  # Default 50MB estimate
                    else:
                        asset_size = 5 * 1024 * 1024  # Default 5MB for other assets

                total_estimated_bytes += asset_size
                assets_info.append(
                    {
                        "asset": asset_name,
                        "media_type": getattr(asset, "media_type", "unknown"),
                        "estimated_size_bytes": asset_size,
                        "estimated_size_mb": round(asset_size / (1024 * 1024), 2),
                    },
                )

        # Get temporal extent
        temporal_extent = None
        if items:
            dates = [item.datetime for item in items if item.datetime]
            if dates:
                temporal_extent = (
                    f"{min(dates).isoformat()} to {max(dates).isoformat()}"
                )

        estimated_mb = total_estimated_bytes / (1024 * 1024)
        estimated_gb = total_estimated_bytes / (1024 * 1024 * 1024)

        return {
            "item_count": len(items),
            "estimated_size_bytes": total_estimated_bytes,
            "estimated_size_mb": round(estimated_mb, 2),
            "estimated_size_gb": round(estimated_gb, 4),
            "bbox_used": effective_bbox,
            "temporal_extent": temporal_extent or datetime,
            "collections": collections
            or list(set(item.collection_id for item in items)),
            "clipped_to_aoi": clipped_to_aoi,
            "assets_analyzed": assets_info,
            "estimation_method": "fallback",
            "message": f"Estimated data size for {len(items)} items using fallback method (odc.stac unavailable)",
        }


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
        Tool(
            name="estimate_data_size",
            description="Estimate data size for STAC items using lazy loading with odc.stac",
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

        if tool_name == "estimate_data_size":
            collections = arguments.get("collections")
            bbox = arguments.get("bbox")
            datetime = arguments.get("datetime")
            query = arguments.get("query")
            aoi_geojson = arguments.get("aoi_geojson")
            limit = arguments.get("limit", 100)

            # Perform data size estimation
            size_estimate = client.estimate_data_size(
                collections=collections,
                bbox=bbox,
                datetime=datetime,
                query=query,
                aoi_geojson=aoi_geojson,
                limit=limit,
            )

            result_text = "**Data Size Estimation**\n\n"
            result_text += f"Items analyzed: {size_estimate['item_count']}\n"
            result_text += f"Estimated size: {size_estimate['estimated_size_mb']:.2f} MB ({size_estimate['estimated_size_gb']:.4f} GB)\n"
            result_text += f"Raw bytes: {size_estimate['estimated_size_bytes']:,}\n\n"

            result_text += "**Query Parameters:**\n"
            result_text += f"Collections: {', '.join(size_estimate['collections']) if size_estimate['collections'] else 'All'}\n"
            if size_estimate["bbox_used"]:
                bbox = size_estimate["bbox_used"]
                result_text += f"Bounding box: [{bbox[0]:.4f}, {bbox[1]:.4f}, {bbox[2]:.4f}, {bbox[3]:.4f}]\n"
            if size_estimate["temporal_extent"]:
                result_text += f"Time range: {size_estimate['temporal_extent']}\n"
            if size_estimate["clipped_to_aoi"]:
                result_text += "Clipped to AOI: Yes (minimized to smallest area)\n"

            # Add data variable information if available
            if "data_variables" in size_estimate:
                result_text += "\n**Data Variables:**\n"
                for var_info in size_estimate["data_variables"]:
                    result_text += f"  - {var_info['variable']}: {var_info['size_mb']} MB, shape {var_info['shape']}, dtype {var_info['dtype']}\n"

            # Add spatial dimensions if available
            if size_estimate.get("spatial_dims"):
                spatial = size_estimate["spatial_dims"]
                result_text += "\n**Spatial Dimensions:**\n"
                result_text += f"  X (longitude): {spatial.get('x', 0)} pixels\n"
                result_text += f"  Y (latitude): {spatial.get('y', 0)} pixels\n"

            # Add assets info for fallback method
            if "assets_analyzed" in size_estimate:
                result_text += "\n**Assets Analyzed (fallback estimation):**\n"
                for asset_info in size_estimate["assets_analyzed"][
                    :5
                ]:  # Show first 5 assets
                    result_text += f"  - {asset_info['asset']}: {asset_info['estimated_size_mb']} MB ({asset_info['media_type']})\n"
                if len(size_estimate["assets_analyzed"]) > 5:
                    result_text += f"  ... and {len(size_estimate['assets_analyzed']) - 5} more assets\n"

            result_text += f"\n{size_estimate['message']}\n"

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
