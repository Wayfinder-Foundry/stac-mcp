"""STAC client wrapper and size estimation logic (refactored from server)."""

from __future__ import annotations

import contextlib
import logging
import os
from typing import Any

import requests
from pystac_client.exceptions import APIError
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout
from shapely.geometry import shape

from tests import HTTP_NOT_FOUND_ERROR

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


class SSLVerificationError(ConnectionError):
    """Raised when SSL certificate verification fails for a STAC request.

    This wraps an underlying ``ssl.SSLCertVerificationError`` (if available)
    to provide a clearer, library-specific failure mode and actionable
    guidance for callers. Handlers may choose to surface remediation steps
    (e.g., setting a custom CA bundle) without needing to parse low-level
    urllib exceptions.
    """


class STACTimeoutError(OSError):
    """Raised when a STAC API request times out.

    Provides actionable guidance for timeout scenarios, including suggestions
    to increase timeout or check network connectivity.
    """


class ConnectionFailedError(ConnectionError):
    """Raised when connection to STAC API fails.

    Wraps underlying connection errors (DNS, refused connection, etc.) with
    clearer context and remediation guidance.
    """


class STACClient:
    """STAC Client wrapper for common operations."""

    def __init__(
        self,
        catalog_url: str | None = "https://planetarycomputer.microsoft.com/api/stac/v1",
        headers: dict[str, str] | None = None,
    ) -> None:
        self.catalog_url = (
            catalog_url.rstrip("/")
            if catalog_url
            else "https://planetarycomputer.microsoft.com/api/stac/v1"
        )
        self.headers = headers or {}
        self._client: Any | None = None
        self._conformance: list[str] | None = None
        # Internal meta flags (used by execution layer for experimental meta)
        self._last_retry_attempts = 0  # number of retry attempts performed (int)
        self._last_insecure_ssl = False  # whether unsafe SSL was used (bool)

    @property
    def client(self) -> Any:
        if self._client is None:
            from pystac_client import (  # noqa: PLC0415 local import (guarded)
                Client as _client,  # noqa: N813
            )
            from pystac_client.stac_api_io import (  # noqa: PLC0415 local import (guarded)
                StacApiIO,
            )

            stac_io = StacApiIO(headers=self.headers)
            self._client = _client.open(self.catalog_url, stac_io=stac_io)
        return self._client

    @property
    def conformance(self) -> list[str]:
        """Lazy-loads and caches STAC API conformance classes."""
        if self._conformance is None:
            self._conformance = self.client.to_dict().get("conformsTo", [])
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
            if item is None:
                return None
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
    def _do_transaction(
        self,
        method: str,
        url: str,
        timeout: int = 30,
        headers: dict[str, str] | None = None,
        **kwargs,
    ) -> dict[str, Any] | None:
        """Centralized transaction request handling with error mapping."""
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
        request_headers["Accept"] = "application/json"
        if not self.client:
            client_not_initialized = (
                "STACClient 'client' property not initialized before transaction."
            )
            raise RuntimeError(client_not_initialized)
        try:
            # TODO: Replace internal pystac_client call with public API when available
            response = self.client._stac_io.session.request(  # noqa: SLF001
                method, url, headers=request_headers, timeout=timeout, **kwargs
            )
            if response.status_code == HTTP_NOT_FOUND_ERROR:
                return None
            response.raise_for_status()
            if not response.content:
                return None
            return response.json()
        except Timeout as e:
            err_msg = f"Request timed out to {url} after {timeout} seconds"
            logger.exception(err_msg)
            raise STACTimeoutError(err_msg) from e
        except RequestsConnectionError as e:
            err_msg = f"Failed to connect to {self.catalog_url}"
            logger.exception(err_msg)
            raise ConnectionFailedError(err_msg) from e

    def create_item(
        self,
        collection_id: str,
        item: dict[str, Any],
        timeout: int = 30,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Creates a new STAC Item in a collection."""
        # Remove any double slashes from URL after http:// or https://
        path = f"collections/{collection_id}/items"
        url = f"{self.catalog_url.replace('catalog.json', '')}{path}"
        return self._do_transaction(
            "post", url, json=item, timeout=timeout, headers=headers
        )

    def update_item(
        self,
        item: dict[str, Any],
        timeout: int = 30,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Updates an existing STAC Item."""
        collection_id = item.get("collection")
        item_id = item.get("id")
        if not collection_id or not item_id:
            msg = "Item must have 'collection' and 'id' fields for update."
            raise ValueError(msg)
        path = f"/collections/{collection_id}/items/{item_id}"
        url = f"{self.catalog_url.replace('catalog.json', '')}{path}"
        return self._do_transaction(
            "put", url, json=item, timeout=timeout, headers=headers
        )

    def delete_item(
        self,
        collection_id: str,
        item_id: str,
        timeout: int = 30,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Deletes a STAC Item."""
        path = f"/collections/{collection_id}/items/{item_id}"
        url = f"{self.catalog_url.replace('catalog.json', '')}{path}"
        return self._do_transaction("delete", url, timeout=timeout, headers=headers)

    def create_collection(
        self,
        collection: dict[str, Any],
        timeout: int = 30,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Creates a new STAC Collection."""
        url = f"{self.catalog_url.replace('catalog.json', '')}/collections"
        return self._do_transaction(
            "post", url, json=collection, timeout=timeout, headers=headers
        )

    def update_collection(
        self,
        collection: dict[str, Any],
        timeout: int = 30,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Updates an existing STAC Collection."""
        # Per spec, PUT is to /collections, not /collections/{id}
        url = f"{self.catalog_url.replace('catalog.json', '')}/collections"
        return self._do_transaction(
            "put", url, json=collection, timeout=timeout, headers=headers
        )

    def delete_collection(
        self,
        collection_id: str,
        timeout: int = 30,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        """Deletes a STAC Collection."""
        path = f"/collections/{collection_id}"
        url = f"{self.catalog_url.replace('catalog.json', '')}{path}"
        return self._do_transaction("delete", url, timeout=timeout, headers=headers)

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
        from odc import stac as odc_stac  # noqa: PLC0415 local import (guarded)

        logger.debug("odc_stac.load before call: %r", getattr(odc_stac, "load", None))

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

        def _fallback_estimate() -> dict[str, Any]:
            # Reuse the fallback logic implemented in the except block.
            assets_info: list[dict[str, Any]] = []
            total_bytes = 0

            def _size_from_metadata(asset_obj: Any) -> int | None:
                keys = [
                    "file:size",
                    "file:bytes",
                    "bytes",
                    "size",
                    "byte_size",
                    "content_length",
                ]
                if isinstance(asset_obj, dict):
                    extra = asset_obj.get("extra_fields") or {}
                else:
                    extra = getattr(asset_obj, "extra_fields", None) or {}
                for k in keys:
                    v = extra.get(k)
                    if v is not None:
                        try:
                            return int(v)
                        except (TypeError, ValueError):
                            continue
                try:
                    for k in keys:
                        v = asset_obj.get(k)  # type: ignore[attr-defined]
                        if v is not None:
                            try:
                                return int(v)
                            except (TypeError, ValueError):
                                continue
                except AttributeError:
                    pass
                return None

            def _head_content_length(href: str) -> int | None:
                try:
                    session = requests.Session()
                    resp = session.request(
                        "HEAD", href, headers=self.headers or {}, timeout=20
                    )
                    if resp is None or not resp.headers:
                        return None
                    cl = resp.headers.get("Content-Length") or resp.headers.get(
                        "content-length"
                    )
                    if cl:
                        try:
                            return int(cl)
                        except (TypeError, ValueError):
                            return None
                except (requests.RequestException, ValueError, TypeError):
                    return None
                return None

            for item in items:
                assets = getattr(item, "assets", {})
                for name, asset in assets.items() if assets else []:
                    if isinstance(asset, dict):
                        href = asset.get("href")
                        media = asset.get("media_type") or asset.get("type") or ""
                    else:
                        href = getattr(asset, "href", None)
                        media = (
                            getattr(asset, "media_type", None)
                            or getattr(asset, "type", "")
                            or ""
                        )

                    bytes_found: int | None = _size_from_metadata(asset)
                    method_used = "metadata"
                    if bytes_found is None and "parquet" in str(media).lower():
                        bytes_found = _head_content_length(href) if href else None
                        method_used = "head"
                    elif "zarr" in str(media).lower() or (
                        isinstance(href, str) and str(href).endswith(".zarr")
                    ):
                        try:
                            import fsspec as _fsspec  # noqa: PLC0415
                            import numpy as np  # noqa: PLC0415
                            import xarray as _xr  # noqa: PLC0415

                            mapper = _fsspec.get_mapper(href) if href else None
                            if mapper is not None:
                                ds = _xr.open_zarr(mapper, consolidated=False)
                                z_bytes = 0
                                for v in ds.data_vars:
                                    var = ds[v]
                                    try:
                                        dtype = np.dtype(var.dtype)
                                        count = 1
                                        for d in var.shape:
                                            count *= int(d)
                                        z_bytes += int(dtype.itemsize) * int(count)
                                    except (TypeError, ValueError):
                                        continue
                                if z_bytes:
                                    bytes_found = z_bytes
                                    method_used = "zarr-inspect"
                                with contextlib.suppress(Exception):
                                    ds.close()
                        except (ImportError, RuntimeError, OSError):
                            bytes_found = None

                    if bytes_found is None and href:
                        bytes_found = _head_content_length(href)
                        method_used = "head"

                    if bytes_found is None:
                        assets_info.append(
                            {
                                "asset": name,
                                "media_type": media,
                                "href": href,
                                "estimated_size_bytes": 0,
                                "estimated_size_mb": 0,
                                "method": "unknown",
                            }
                        )
                    else:
                        total_bytes += bytes_found
                        # Debug logging to help diagnose test-order dependent failures
                        if os.getenv("STAC_MCP_DEBUG"):
                            try:
                                extra = (
                                    asset.get("extra_fields")
                                    if isinstance(asset, dict)
                                    else getattr(asset, "extra_fields", None)
                                )
                            except (AttributeError, TypeError):
                                extra = None
                            logger.debug(
                                "fallback asset=%s media=%s href=%s extra=%s",
                                name,
                                media,
                                href,
                                extra,
                            )
                            logger.debug(
                                "fallback bytes=%s method=%s",
                                bytes_found,
                                method_used,
                            )
                        assets_info.append(
                            {
                                "asset": name,
                                "media_type": media,
                                "href": href,
                                "estimated_size_bytes": int(bytes_found),
                                "estimated_size_mb": round(
                                    bytes_found / (1024 * 1024), 2
                                ),
                                "method": method_used,
                            }
                        )

            estimated_mb = total_bytes / (1024 * 1024)
            estimated_gb = total_bytes / (1024 * 1024 * 1024)
            return {
                "item_count": len(items),
                "estimated_size_bytes": int(total_bytes),
                "estimated_size_mb": round(estimated_mb, 2),
                "estimated_size_gb": round(estimated_gb, 4),
                "bbox_used": effective_bbox,
                "temporal_extent": datetime,
                "collections": collections
                or list({item.collection_id for item in items}),
                "clipped_to_aoi": clipped_to_aoi
                if "clipped_to_aoi" in locals()
                else False,
                "assets_analyzed": assets_info,
                "message": (
                    "Successfully estimated data size using fallback heuristics"
                    if total_bytes
                    else "Error estimating data size"
                ),
            }

        # If any item contains non-raster asset types (parquet/zarr), use fallback
        def _needs_fallback(items_list: list[Any]) -> bool:
            for it in items_list:
                assets = getattr(it, "assets", {})
                for _n, a in assets.items() if assets else []:
                    media = (
                        a.get("media_type")
                        if isinstance(a, dict)
                        else getattr(a, "media_type", None)
                    )
                    href = (
                        a.get("href")
                        if isinstance(a, dict)
                        else getattr(a, "href", None)
                    )
                    if media and (
                        "parquet" in str(media).lower() or "zarr" in str(media).lower()
                    ):
                        return True
                    if href and (
                        str(href).endswith(".zarr") or str(href).endswith(".parquet")
                    ):
                        return True
            return False

        if _needs_fallback(items):
            return _fallback_estimate()

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
            # Implement fallback estimation for non-raster assets and zarr.
            assets_info: list[dict[str, Any]] = []
            total_bytes = 0

            def _size_from_metadata(asset_obj: Any) -> int | None:
                keys = [
                    "file:size",
                    "file:bytes",
                    "bytes",
                    "size",
                    "byte_size",
                    "content_length",
                ]
                if isinstance(asset_obj, dict):
                    extra = asset_obj.get("extra_fields") or {}
                else:
                    extra = getattr(asset_obj, "extra_fields", None) or {}
                for k in keys:
                    v = extra.get(k)
                    if v is not None:
                        try:
                            return int(v)
                        except (TypeError, ValueError):
                            continue
                try:
                    for k in keys:
                        v = asset_obj.get(k)  # type: ignore[attr-defined]
                        if v is not None:
                            try:
                                return int(v)
                            except (TypeError, ValueError):
                                continue
                except AttributeError:
                    pass
                return None

            def _head_content_length(href: str) -> int | None:
                try:
                    session = requests.Session()
                    resp = session.request(
                        "HEAD", href, headers=self.headers or {}, timeout=20
                    )
                    if resp is None or not resp.headers:
                        return None
                    cl = resp.headers.get("Content-Length") or resp.headers.get(
                        "content-length"
                    )
                    if cl:
                        try:
                            return int(cl)
                        except (TypeError, ValueError):
                            return None
                except (requests.RequestException, ValueError, TypeError):
                    return None
                return None

            for item in items:
                assets = getattr(item, "assets", {})
                for name, asset in assets.items() if assets else []:
                    if isinstance(asset, dict):
                        href = asset.get("href")
                        media = asset.get("media_type") or asset.get("type") or ""
                    else:
                        href = getattr(asset, "href", None)
                        media = (
                            getattr(asset, "media_type", None)
                            or getattr(asset, "type", "")
                            or ""
                        )

                    bytes_found: int | None = _size_from_metadata(asset)
                    method_used = "metadata"
                    if bytes_found is None and "parquet" in str(media).lower():
                        bytes_found = _head_content_length(href) if href else None
                        method_used = "head"
                    elif "zarr" in str(media).lower() or (
                        isinstance(href, str) and str(href).endswith(".zarr")
                    ):
                        # attempt a simple zarr inspect using xarray if available
                        try:
                            import fsspec as _fsspec  # noqa: PLC0415
                            import numpy as np  # noqa: PLC0415
                            import xarray as _xr  # noqa: PLC0415

                            mapper = _fsspec.get_mapper(href) if href else None
                            if mapper is not None:
                                ds = _xr.open_zarr(mapper, consolidated=False)
                                z_bytes = 0
                                for v in ds.data_vars:
                                    var = ds[v]
                                    try:
                                        dtype = np.dtype(var.dtype)
                                        count = 1
                                        for d in var.shape:
                                            count *= int(d)
                                        z_bytes += int(dtype.itemsize) * int(count)
                                    except (TypeError, ValueError):
                                        continue
                                if z_bytes:
                                    bytes_found = z_bytes
                                    method_used = "zarr-inspect"
                                with contextlib.suppress(Exception):
                                    ds.close()
                        except (ImportError, RuntimeError, OSError):
                            bytes_found = None

                    if bytes_found is None and href:
                        bytes_found = _head_content_length(href)
                        method_used = "head"

                    if bytes_found is None:
                        assets_info.append(
                            {
                                "asset": name,
                                "media_type": media,
                                "href": href,
                                "estimated_size_bytes": 0,
                                "estimated_size_mb": 0,
                                "method": "unknown",
                            }
                        )
                    else:
                        total_bytes += bytes_found
                    # Debug logging to help diagnose test-order dependent failures
                    if os.getenv("STAC_MCP_DEBUG"):
                        try:
                            extra = (
                                asset.get("extra_fields")
                                if isinstance(asset, dict)
                                else getattr(asset, "extra_fields", None)
                            )
                        except (AttributeError, TypeError):
                            extra = None
                        logger.debug(
                            "fallback asset=%s media=%s href=%s extra=%s",
                            name,
                            media,
                            href,
                            extra,
                        )
                        logger.debug(
                            "fallback bytes=%s method=%s",
                            bytes_found,
                            method_used,
                        )
                    assets_info.append(
                        {
                            "asset": name,
                            "media_type": media,
                            "href": href,
                            "estimated_size_bytes": int(bytes_found),
                            "estimated_size_mb": round(bytes_found / (1024 * 1024), 2),
                            "method": method_used,
                        }
                    )

            estimated_mb = total_bytes / (1024 * 1024)
            estimated_gb = total_bytes / (1024 * 1024 * 1024)
            return {
                "item_count": len(items),
                "estimated_size_bytes": int(total_bytes),
                "estimated_size_mb": round(estimated_mb, 2),
                "estimated_size_gb": round(estimated_gb, 4),
                "bbox_used": effective_bbox,
                "temporal_extent": datetime,
                "collections": collections
                or list({item.collection_id for item in items}),
                "clipped_to_aoi": clipped_to_aoi
                if "clipped_to_aoi" in locals()
                else False,
                "assets_analyzed": assets_info,
                "message": (
                    "Successfully estimated data size using fallback heuristics"
                    if total_bytes
                    else f"Error estimating data size: {exc}"
                ),
            }

    def get_root_document(self) -> dict[str, Any]:
        # Some underlying client implementations do not provide a
        # get_root_document() convenience. Use to_dict() as a stable
        # fallback and normalize the keys we care about.
        try:
            raw = self.client.to_dict() if hasattr(self.client, "to_dict") else {}
        except (AttributeError, APIError):
            # to_dict() may not be available or the underlying client raised an
            # APIError; swallow those specific errors and return an empty dict.
            raw = {}
        if not raw:  # Unexpected but keep consistent shape
            return {
                "id": None,
                "title": None,
                "description": None,
                "links": [],
                "conformsTo": [],
            }
        # Normalize subset we care about
        return {
            "id": raw.get("id"),
            "title": raw.get("title"),
            "description": raw.get("description"),
            "links": raw.get("links", []),
            "conformsTo": raw.get("conformsTo", raw.get("conforms_to", [])),
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
        # TODO: Replace internal pystac_client call with public API when available
        q = self.client._stac_io.read_json(path)  # noqa: SLF001
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
            # TODO: Replace internal pystac_client call with public API when available
            res = self.client._stac_io.post("/search", json=body)  # noqa: SLF001
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
        except APIError as exc:  # pragma: no cover - network
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
