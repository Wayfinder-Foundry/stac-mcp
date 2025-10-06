"""STAC client wrapper and size estimation logic (refactored from server)."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from pystac_client.exceptions import APIError
from shapely.geometry import shape

# HTTP status code constants (avoid magic numbers - PLR2004)
HTTP_400 = 400
HTTP_404 = 404

# Conformance URIs from STAC API specifications. Lists include multiple versions
# to support older APIs.
CONFORMANCE_AGGREGATION = [
    "https://api.stacspec.org/v1.0.0/ogc-api-features-p3/conf/aggregation",
]
CONFORMANCE_QUERY = [
    "https://api.stacspec.org/v1.0.0/item-search#query",
    "https://api.stacspec.org/v1.0.0-beta.2/item-search#query",
]
CONFORMANCE_QUERYABLES = [
    "https://api.stacspec.org/v1.0.0/item-search#queryables",
    "https://api.stacspec.org/v1.0.0-rc.1/item-search#queryables",
]
CONFORMANCE_SORT = [
    "https://api.stacspec.org/v1.0.0/item-search#sort",
]
CONFORMANCE_TRANSACTION = [
    "https://api.stacspec.org/v1.0.0/collections#transaction",
    "http://stacspec.org/spec/v1.0.0/collections#transaction",
]


logger = logging.getLogger(__name__)


class ConformanceError(NotImplementedError):
    """Raised when a STAC API does not support a required capability."""


class STACClient:
    """STAC Client wrapper for common operations."""

    def __init__(
        self,
        catalog_url: str = "https://planetarycomputer.microsoft.com/api/stac/v1",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.catalog_url = catalog_url.rstrip("/")
        self.headers = headers or {}
        self._client: Any | None = None
        self._conformance: list[str] | None = None

    @property
    def client(self) -> Any:
        if self._client is None:
            # Dynamic import avoids circular import; server may set Client.
            from stac_mcp import server as _server  # noqa: PLC0415

            client_ref = getattr(_server, "Client", None)
            if client_ref is None:  # Fallback if dependency missing
                # Import inside branch so tests can simulate missing dependency.
                from pystac_client import Client as client_ref  # type: ignore[attr-defined]  # noqa: PLC0415,N813,I001

            self._client = client_ref.open(self.catalog_url)  # type: ignore[attr-defined]
        return self._client

    @property
    def conformance(self) -> list[str]:
        """Lazy-loads and caches STAC API conformance classes."""
        if self._conformance is None:
            conf = self._http_json("/conformance")
            if conf and "conformsTo" in conf:
                self._conformance = conf["conformsTo"]
            else:  # Fallback to root document
                root = self.get_root_document()
                self._conformance = root.get("conformsTo", []) or []
        return self._conformance

    def _check_conformance(self, capability_uris: list[str]) -> None:
        """Raises ConformanceError if API lacks a given capability.

        Checks if any of the provided URIs are in the server's conformance list.
        """
        if not any(uri in self.conformance for uri in capability_uris):
            # For a cleaner error message, report the first (preferred) URI.
            capability_name = capability_uris[0]
            msg = (
                f"API at {self.catalog_url} does not support '{capability_name}' "
                "(or a compatible version)"
            )
            raise ConformanceError(msg)

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
                if limit > 0 and len(collections) >= limit:
                    break
        except APIError:  # pragma: no cover - network dependent
            logger.exception("Error fetching collections")
            raise
        return collections

    def get_collection(self, collection_id: str) -> dict[str, Any]:
        try:
            collection = self.client.get_collection(collection_id)
        except APIError:  # pragma: no cover - network dependent
            logger.exception("Error fetching collection %s", collection_id)
            raise
        else:
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

    # ------------------------------- Items -------------------------------- #
    def search_items(
        self,
        collections: list[str] | None = None,
        bbox: list[float] | None = None,
        datetime: str | None = None,
        query: dict[str, Any] | None = None,
        sortby: list[tuple[str, str]] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if query:
            self._check_conformance(CONFORMANCE_QUERY)
        if sortby:
            self._check_conformance(CONFORMANCE_SORT)
        try:
            search = self.client.search(
                collections=collections,
                bbox=bbox,
                datetime=datetime,
                query=query,
                sortby=sortby,
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
                if limit and limit > 0 and len(items) >= limit:
                    break
        except APIError:  # pragma: no cover - network dependent
            logger.exception("Error searching items")
            raise
        else:
            return items

    def get_item(self, collection_id: str, item_id: str) -> dict[str, Any]:
        try:
            item = self.client.get_collection(collection_id).get_item(item_id)
        except APIError:  # pragma: no cover - network dependent
            logger.exception(
                "Error fetching item %s from collection %s",
                item_id,
                collection_id,
            )
            raise
        else:
            return {
                "id": item.id,
                "collection": item.collection_id,
                "geometry": item.geometry,
                "bbox": item.bbox,
                "datetime": item.datetime.isoformat() if item.datetime else None,
                "properties": item.properties,
                "assets": {k: v.to_dict() for k, v in item.assets.items()},
            }

    # --------------------------- Transactions --------------------------- #
    def create_item(
        self, collection_id: str, item: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Creates a new STAC Item in a collection."""
        self._check_conformance(CONFORMANCE_TRANSACTION)
        path = f"/collections/{collection_id}/items"
        return self._http_json(path, method="POST", payload=item)

    def update_item(self, item: dict[str, Any]) -> dict[str, Any] | None:
        """Updates an existing STAC Item."""
        self._check_conformance(CONFORMANCE_TRANSACTION)
        collection_id = item.get("collection")
        item_id = item.get("id")
        if not collection_id or not item_id:
            msg = "Item must have 'collection' and 'id' fields for update."
            raise ValueError(msg)
        path = f"/collections/{collection_id}/items/{item_id}"
        return self._http_json(path, method="PUT", payload=item)

    def delete_item(self, collection_id: str, item_id: str) -> dict[str, Any] | None:
        """Deletes a STAC Item."""
        self._check_conformance(CONFORMANCE_TRANSACTION)
        path = f"/collections/{collection_id}/items/{item_id}"
        return self._http_json(path, method="DELETE")

    def create_collection(self, collection: dict[str, Any]) -> dict[str, Any] | None:
        """Creates a new STAC Collection."""
        self._check_conformance(CONFORMANCE_TRANSACTION)
        return self._http_json("/collections", method="POST", payload=collection)

    def update_collection(self, collection: dict[str, Any]) -> dict[str, Any] | None:
        """Updates an existing STAC Collection."""
        self._check_conformance(CONFORMANCE_TRANSACTION)
        # Per spec, PUT is to /collections, not /collections/{id}
        return self._http_json("/collections", method="PUT", payload=collection)

    def delete_collection(self, collection_id: str) -> dict[str, Any] | None:
        """Deletes a STAC Collection."""
        self._check_conformance(CONFORMANCE_TRANSACTION)
        path = f"/collections/{collection_id}"
        return self._http_json(path, method="DELETE")

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
        # Local import (intentional) lets tests patch server.ODC_STAC_AVAILABLE.
        from stac_mcp import server as _server  # noqa: PLC0415

        if not getattr(_server, "ODC_STAC_AVAILABLE", False):
            msg = (
                "odc.stac is not available. Please install it to use data size "
                "estimation."
            )
            raise RuntimeError(msg)
        from odc import stac as odc_stac  # noqa: PLC0415 local import (guarded)

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
                # Use original dtype from encoding if available (before nodata
                # conversion). This prevents overestimation when nodata values
                # cause dtype upcast to float64
                original_dtype = (
                    data_array.encoding.get("dtype")
                    if hasattr(data_array, "encoding")
                    else None
                )
                effective_dtype = (
                    original_dtype if original_dtype is not None else data_array.dtype
                )

                # Calculate bytes using original dtype to avoid overestimation
                import numpy as np  # noqa: PLC0415

                dtype_obj = np.dtype(effective_dtype)
                var_nbytes = dtype_obj.itemsize * data_array.size

                estimated_bytes += var_nbytes
                data_vars_info.append(
                    {
                        "variable": var_name,
                        "shape": list(data_array.shape),
                        "dtype": str(effective_dtype),
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
                or list({item.collection_id for item in items}),
                "clipped_to_aoi": clipped_to_aoi,
                "data_variables": data_vars_info,
                "spatial_dims": (
                    {"x": ds.dims.get("x", 0), "y": ds.dims.get("y", 0)}
                    if "x" in ds.dims and "y" in ds.dims
                    else {}
                ),
                "message": f"Successfully estimated data size for {len(items)} items",
            }
        except (
            RuntimeError,
            ValueError,
            AttributeError,
            KeyError,
            TypeError,
        ) as exc:  # pragma: no cover - fallback path
            logger.warning(
                "odc.stac loading failed, using fallback estimation: %s",
                exc,
            )
            return self._fallback_size_estimation(
                items,
                effective_bbox,
                datetime,
                collections,
                clipped_to_aoi,
            )

    def _fallback_size_estimation(
        self,
        items: list[Any],
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
            "collections": collections or list({item.collection_id for item in items}),
            "clipped_to_aoi": clipped_to_aoi,
            "assets_analyzed": assets_info,
            "estimation_method": "fallback",
            "message": (
                "Estimated data size for "
                f"{len(items)} items using fallback method (odc.stac unavailable)"
            ),
        }

    # ----------------------- Capabilities & Discovery -------------------- #
    def _http_json(
        self,
        path: str,
        method: str = "GET",
        payload: dict | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict | None:
        """Lightweight HTTP helper using stdlib (avoids extra deps).

        Returns parsed JSON dict or None on 404 for capability endpoints where
        absence is acceptable.
        """
        url = self.catalog_url.rstrip("/") + path
        data = None
        request_headers = self.headers.copy()
        request_headers.update(headers or {})
        request_headers["Accept"] = "application/json"

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        if not url.startswith(("http://", "https://")):
            msg = f"Unsupported URL scheme in {url}"
            raise ValueError(msg)
        # Request object creation is safe: url already validated to http/https only.
        req = urllib.request.Request(  # noqa: S310 safe: url already validated to http/https
            url,
            data=data,
            headers=request_headers,
            method=method,
        )
        try:
            # S310: urlopen restricted to http/https (validated) and only performs
            # metadata retrieval (no dynamic user-controlled scheme or path parts).
            with urllib.request.urlopen(  # type: ignore[urllib-direct-use]  # noqa: S310
                req,
                timeout=30,
            ) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:  # pragma: no cover - network specific
            if exc.code == HTTP_404:
                return None
            raise
        except urllib.error.URLError:  # pragma: no cover - network
            # Preserve original URLError behavior so callers/tests can handle explicitly
            raise

    def get_root_document(self) -> dict[str, Any]:
        root = self._http_json("")  # base endpoint already ends with /stac/v1
        if not root:  # Unexpected but keep consistent shape
            return {
                "id": None,
                "title": None,
                "description": None,
                "links": [],
                "conformsTo": [],
            }
        # Normalize subset we care about
        return {
            "id": root.get("id"),
            "title": root.get("title"),
            "description": root.get("description"),
            "links": root.get("links", []),
            "conformsTo": root.get("conformsTo", root.get("conforms_to", [])),
        }

    def get_conformance(
        self,
        check: str | list[str] | None = None,
    ) -> dict[str, Any]:
        conforms = self.conformance
        checks: dict[str, bool] | None = None
        if check:
            targets = [check] if isinstance(check, str) else list(check)
            checks = {c: c in conforms for c in targets}
        return {"conformsTo": conforms, "checks": checks}

    def get_queryables(self, collection_id: str | None = None) -> dict[str, Any]:
        self._check_conformance(CONFORMANCE_QUERYABLES)
        path = (
            f"/collections/{collection_id}/queryables"
            if collection_id
            else "/queryables"
        )
        q = self._http_json(path)
        if not q:
            return {
                "queryables": {},
                "collection_id": collection_id,
                "message": "Queryables not available",
            }
        # STAC Queryables spec nests properties under 'properties' in newer versions
        props = q.get("properties") or q.get("queryables") or {}
        return {"queryables": props, "collection_id": collection_id}

    def get_aggregations(
        self,
        collections: list[str] | None = None,
        bbox: list[float] | None = None,
        datetime: str | None = None,
        query: dict[str, Any] | None = None,
        fields: list[str] | None = None,
        operations: list[str] | None = None,
        limit: int = 0,
    ) -> dict[str, Any]:
        self._check_conformance(CONFORMANCE_AGGREGATION)
        # Build STAC search body with aggregations extension
        body: dict[str, Any] = {}
        if collections:
            body["collections"] = collections
        if bbox:
            body["bbox"] = bbox
        if datetime:
            body["datetime"] = datetime
        if query:
            body["query"] = query
        if limit:
            body["limit"] = limit
        aggs: dict[str, Any] = {}
        # Simple default: count of items
        requested_ops = operations or ["count"]
        target_fields = fields or []
        for op in requested_ops:
            if op == "count":
                aggs["count"] = {"type": "count"}
            else:
                # Field operations require fields (e.g., stats/histogram)
                for f in target_fields:
                    aggs[f"{f}_{op}"] = {"type": op, "field": f}
        if aggs:
            body["aggregations"] = aggs
        try:
            res = self._http_json("/search", method="POST", payload=body)
            if not res:
                return {
                    "supported": False,
                    "aggregations": {},
                    "message": "Search endpoint unavailable",
                    "parameters": body,
                }
            aggs_result = res.get("aggregations") or {}
            return {
                "supported": bool(aggs_result),
                "aggregations": aggs_result,
                "message": "OK" if aggs_result else "No aggregations returned",
                "parameters": body,
            }
        except urllib.error.HTTPError as exc:  # pragma: no cover - network
            if exc.code in (HTTP_400, HTTP_404):
                return {
                    "supported": False,
                    "aggregations": {},
                    "message": f"Aggregations unsupported ({exc.code})",
                    "parameters": body,
                }
            raise
        except (
            RuntimeError,
            ValueError,
            KeyError,
            TypeError,
        ) as exc:  # pragma: no cover - network
            return {
                "supported": False,
                "aggregations": {},
                "message": f"Aggregation request failed: {exc}",
                "parameters": body,
            }


# Global instance preserved for backward compatibility (imported by server)
stac_client = STACClient()
