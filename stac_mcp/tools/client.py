"""STAC client wrapper and size estimation logic (refactored from server)."""

from __future__ import annotations

import logging
from typing import Any

from pystac_client.exceptions import APIError
from shapely.geometry import shape

logger = logging.getLogger(__name__)


class STACClient:
    """STAC Client wrapper for common operations."""

    def __init__(
        self,
        catalog_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1",
    ) -> None:
        self.catalog_url = catalog_url
        self._client: Any | None = None

    @property
    def client(self) -> Any:
        if self._client is None:
            # Import Client through server module so tests patching stac_mcp.server.Client work
            from stac_mcp import server as _server  # local import for patching

            ClientRef = getattr(_server, "Client", None)
            if ClientRef is None:  # Fallback if dependency missing at runtime
                from pystac_client import Client as ClientRef  # type: ignore

            self._client = ClientRef.open(self.catalog_url)  # type: ignore[attr-defined]
        return self._client

    # ----------------------------- Collections ----------------------------- #
    def search_collections(self, limit: int = 10) -> list[dict[str, Any]]:
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
        except APIError as e:  # pragma: no cover - network dependent
            logger.error(f"Error fetching collections: {e}")
            raise

    def get_collection(self, collection_id: str) -> dict[str, Any]:
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
        except APIError as e:  # pragma: no cover - network dependent
            logger.error(f"Error fetching collection {collection_id}: {e}")
            raise

    # ------------------------------- Items -------------------------------- #
    def search_items(
        self,
        collections: list[str] | None = None,
        bbox: list[float] | None = None,
        datetime: str | None = None,
        query: dict[str, Any] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
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
        except APIError as e:  # pragma: no cover - network dependent
            logger.error(f"Error searching items: {e}")
            raise

    def get_item(self, collection_id: str, item_id: str) -> dict[str, Any]:
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
        except APIError as e:  # pragma: no cover - network dependent
            logger.error(
                f"Error fetching item {item_id} from collection {collection_id}: {e}",
            )
            raise

    # ------------------------- Data Size Estimation ----------------------- #
    def estimate_data_size(
        self,
        collections: list[str] | None = None,
        bbox: list[float] | None = None,
        datetime: str | None = None,
        query: dict[str, Any] | None = None,
        aoi_geojson: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        # Import inside method to honor patched value in tests (server.ODC_STAC_AVAILABLE)
        from stac_mcp import (
            server as _server,
        )  # local import to avoid circular at module load

        if not getattr(_server, "ODC_STAC_AVAILABLE", False):
            raise RuntimeError(
                "odc.stac is not available. Please install it to use data size estimation.",
            )
        from odc import stac as odc_stac  # local import for clarity (already guarded)

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

        effective_bbox = bbox
        clipped_to_aoi = False
        if aoi_geojson:
            geom = shape(aoi_geojson)
            aoi_bounds = geom.bounds
            if bbox:
                effective_bbox = [
                    max(bbox[0], aoi_bounds[0]),
                    max(bbox[1], aoi_bounds[1]),
                    min(bbox[2], aoi_bounds[2]),
                    min(bbox[3], aoi_bounds[3]),
                ]
            else:
                effective_bbox = list(aoi_bounds)
            clipped_to_aoi = True

        try:
            ds = odc_stac.load(items, bbox=effective_bbox, chunks={})
            estimated_bytes = 0
            data_vars_info: list[dict[str, Any]] = []
            for var_name, data_array in ds.data_vars.items():
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
            estimated_mb = estimated_bytes / (1024 * 1024)
            estimated_gb = estimated_bytes / (1024 * 1024 * 1024)
            dates = [item.datetime for item in items if item.datetime]
            temporal_extent = None
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
        except Exception as e:  # pragma: no cover - fallback path
            logger.warning(f"odc.stac loading failed, using fallback estimation: {e}")
            return self._fallback_size_estimation(
                items,
                effective_bbox,
                datetime,
                collections,
                clipped_to_aoi,
            )

    def _fallback_size_estimation(
        self,
        items: list,
        effective_bbox: list[float] | None,
        datetime: str | None,
        collections: list[str] | None,
        clipped_to_aoi: bool,
    ) -> dict[str, Any]:
        total_estimated_bytes = 0
        assets_info = []
        for item in items:
            for asset_name, asset in item.assets.items():
                asset_size = 0
                if hasattr(asset, "extra_fields"):
                    asset_size = asset.extra_fields.get("file:size", 0)
                if asset_size == 0:
                    media_type = getattr(asset, "media_type", "") or ""
                    if "tiff" in media_type.lower() or "geotiff" in media_type.lower():
                        if effective_bbox:
                            bbox_area = (effective_bbox[2] - effective_bbox[0]) * (
                                effective_bbox[3] - effective_bbox[1]
                            )
                            asset_size = int(bbox_area * 10 * 1024 * 1024)
                        else:
                            asset_size = 50 * 1024 * 1024
                    else:
                        asset_size = 5 * 1024 * 1024
                total_estimated_bytes += asset_size
                assets_info.append(
                    {
                        "asset": asset_name,
                        "media_type": getattr(asset, "media_type", "unknown"),
                        "estimated_size_bytes": asset_size,
                        "estimated_size_mb": round(asset_size / (1024 * 1024), 2),
                    },
                )
        dates = [item.datetime for item in items if item.datetime]
        temporal_extent = None
        if dates:
            temporal_extent = f"{min(dates).isoformat()} to {max(dates).isoformat()}"
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


# Global instance preserved for backward compatibility (imported by server)
stac_client = STACClient()
