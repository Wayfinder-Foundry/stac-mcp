"""STAC client wrapper and size estimation logic (refactored from server)."""

from __future__ import annotations

import contextlib
import logging
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import numpy as np
import requests
from pystac_client.exceptions import APIError
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout
from shapely.geometry import shape

# Ensure Session.request enforces a default timeout when one is not provided.
# This is a conservative safeguard for environments where sessions may be
# constructed by third-party libraries (pystac_client) without an explicit
# timeout. We wrap at the class level so all Session instances pick this up.
try:
    _original_session_request = requests.Session.request

    def _session_request_with_default_timeout(
        self, method, url, *args, timeout=None, **kwargs
    ):
        default_timeout = int(os.getenv("STAC_MCP_REQUEST_TIMEOUT", "30"))
        if timeout is None:
            timeout = default_timeout
        return _original_session_request(
            self, method, url, *args, timeout=timeout, **kwargs
        )

    # Only set if not already wrapped (avoid double-wrapping in test environments)
    if requests.Session.request is not _session_request_with_default_timeout:
        requests.Session.request = _session_request_with_default_timeout
except (AttributeError, TypeError) as exc:  # pragma: no cover - defensive
    # logger may not be defined yet; use module-level logging as a fallback
    logging.getLogger(__name__).debug(
        "Could not install Session.request timeout wrapper: %s", exc
    )

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


# Initialized earlier for the timeout wrapper fallback
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
        head_timeout_seconds: int | None = None,
        head_max_workers: int | None = None,
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
        # HEAD request configuration: timeout and parallel workers. Values may be
        # provided programmatically or through environment variables for
        # runtime tuning.
        if head_timeout_seconds is None:
            try:
                head_timeout_seconds = int(
                    os.getenv("STAC_MCP_HEAD_TIMEOUT_SECONDS", "20")
                )
            except (TypeError, ValueError):
                head_timeout_seconds = 20
        self.head_timeout_seconds = head_timeout_seconds

        if head_max_workers is None:
            try:
                head_max_workers = int(os.getenv("STAC_MCP_HEAD_MAX_WORKERS", "4"))
            except (TypeError, ValueError):
                head_max_workers = 4
        self.head_max_workers = head_max_workers

        # Number of retries for HEAD probes on transient failures. A value of
        # 0 disables retries; default is read from STAC_MCP_HEAD_RETRIES.
        try:
            head_retries = int(os.getenv("STAC_MCP_HEAD_RETRIES", "1"))
        except (TypeError, ValueError):
            head_retries = 1
        self.head_retries = max(0, head_retries)

        # Backoff base (seconds) for exponential backoff calculation. Small
        # default keeps tests fast but is tunable in production.
        try:
            head_backoff_base = float(os.getenv("STAC_MCP_HEAD_BACKOFF_BASE", "0.05"))
        except (TypeError, ValueError):
            head_backoff_base = 0.05
        self.head_backoff_base = max(0.0, head_backoff_base)

        # Whether to apply jitter to backoff delays to reduce thundering herd
        # effects. Controlled via env var STAC_MCP_HEAD_JITTER ("1"/"0").
        self.head_backoff_jitter = os.getenv("STAC_MCP_HEAD_JITTER", "1") in (
            "1",
            "true",
            "True",
        )

        # Dedicated session for lightweight HEAD requests to avoid creating a
        # new Session per call and to allow the global Session.request wrapper
        # (installed above) to apply defaults consistently.
        self._head_session = requests.Session()

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
            # Ensure the underlying requests session used by pystac_client
            # enforces a sensible default timeout to avoid indefinite hangs.
            # Some HTTP libraries or network environments may drop or stall
            # connections; wrapping the session.request call provides a
            # portable safeguard without changing call sites.
            try:
                session = getattr(stac_io, "session", None)
                if session is not None and hasattr(session, "request"):
                    original_request = session.request

                    def _request_with_default_timeout(
                        method, url, *args, timeout=None, **kwargs
                    ):
                        # Default timeout (seconds) can be overridden via env var
                        default_timeout = int(
                            os.getenv("STAC_MCP_REQUEST_TIMEOUT", "30")
                        )
                        if timeout is None:
                            timeout = default_timeout
                        return original_request(
                            method, url, *args, timeout=timeout, **kwargs
                        )

                    # Monkey-patch the session.request to apply default timeout
                    session.request = _request_with_default_timeout
            except (AttributeError, TypeError, RuntimeError) as exc:
                # Be conservative: if wrapping fails, fall back to original behavior
                logger.debug(
                    "Could not wrap pystac_client session.request with timeout: %s",
                    exc,
                )
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
        force_metadata_only: bool = False,
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

        # Extracted helper methods moved to instance methods for testability
        # Use fallback via instance method when requested

        # If any item contains non-raster asset types (parquet/zarr), use fallback
        def _needs_fallback(items_list: list[Any]) -> bool:
            for it in items_list:
                assets = getattr(it, "assets", {})
                for _n, a in assets.items() if assets else []:
                    # Normalize asset entry to a minimal dict-like view
                    try:
                        if isinstance(a, dict):
                            a_dict = a
                        elif hasattr(a, "to_dict"):
                            a_dict = a.to_dict()  # type: ignore[attr-defined]
                        elif isinstance(a, str):
                            a_dict = {"href": a, "media_type": ""}
                        else:
                            a_dict = {
                                "href": getattr(a, "href", None),
                                "media_type": getattr(a, "media_type", None)
                                or getattr(a, "type", None)
                                or "",
                            }
                    except (AttributeError, TypeError) as exc:
                        # If normalization fails, log and skip this asset
                        logger.debug("Failed to normalize asset entry: %s", exc)
                        continue

                    media = a_dict.get("media_type")
                    href = a_dict.get("href")

                    # Include GeoTIFF/COG assets (image/tiff) as fallback candidates
                    # so that metadata/HEAD/zarr-inspect heuristics are applied.
                    if media and (
                        "parquet" in str(media).lower() or "zarr" in str(media).lower()
                    ):
                        return True
                    if href and (
                        str(href).endswith(".zarr") or str(href).endswith(".parquet")
                    ):
                        return True
            return False

        # If the caller requests metadata-only mode, run the fallback heuristics
        # directly (this avoids CRS/resolution auto-guess failures in some
        # remote catalogs). Otherwise use the normal detection logic.
        if force_metadata_only or _needs_fallback(items):
            return self._fallback_estimate(
                items, effective_bbox, datetime, collections, clipped_to_aoi
            )

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

                # Conservative downcast heuristic: when odc.stac doesn't provide
                # an original dtype and the loaded dtype is a float, attempt a
                # tiny-sample check to see if values are integer-valued and have
                # no NaNs. If so, estimate using a compact integer dtype (uint8,
                # uint16, int16, int32) based on the sampled range. This is a
                # best-effort optimization that may underestimate if the sample is
                # not representative; it's intentionally conservative (small
                # sample) to avoid heavy computation.
                try:
                    dtype_obj = np.dtype(effective_dtype)
                    # Only attempt sampling-based downcast for float dtypes when
                    # no explicit original dtype is provided by encoding.
                    # Additionally, avoid sampling/downcasting if the
                    # DataArray or encoding declares a nodata/_FillValue since
                    # that often forces dtype upcasts and sampling may be
                    # misleading (NaNs or fill values present).
                    has_nodata = False
                    try:
                        # xarray DataArray may expose .nodata (rasterio-like)
                        nod = getattr(data_array, "nodata", None)
                        if nod is not None:
                            has_nodata = True
                        # Check common attrs and encoding keys
                        if not has_nodata and isinstance(getattr(data_array, "attrs", None), dict):
                            if "_FillValue" in data_array.attrs:
                                has_nodata = True
                        if not has_nodata and hasattr(data_array, "encoding"):
                            enc = getattr(data_array, "encoding") or {}
                            if isinstance(enc, dict) and (
                                "nodata" in enc or "_FillValue" in enc
                            ):
                                has_nodata = True

                    except Exception:
                        # Be conservative on any attribute access error
                        has_nodata = True

                    if (
                        original_dtype is None
                        and not has_nodata
                        and np.issubdtype(dtype_obj, np.floating)
                        and hasattr(data_array, "sizes")
                    ):
                        # Build a tiny indexer selecting up to 2 elements along
                        # each dimension to form a very small sample block.
                        indexer: dict[str, slice] = {}
                        for d, s in data_array.sizes.items():
                            take = 1 if s == 0 else min(2, int(s))
                            indexer[d] = slice(0, take)

                        # Try to extract the tiny sample; fall back silently on
                        # any failure (e.g., remote IO or compute errors).
                        try:
                            sample = data_array.isel(indexer).values
                        except Exception:
                            sample = None

                        if sample is not None:
                            # Flatten and ensure it's a numpy array
                            arr = np.asarray(sample).ravel()
                            # If any NaNs present, don't downcast
                            if not np.isnan(arr).any() and arr.size > 0:
                                # Check integer-valuedness on the sample
                                if np.allclose(arr, np.round(arr)):
                                    vmin = int(arr.min())
                                    vmax = int(arr.max())
                                    # Choose smallest safe integer dtype
                                    chosen = None
                                    if vmin >= 0:
                                        if vmax <= 0xFF:
                                            chosen = np.dtype("uint8")
                                        elif vmax <= 0xFFFF:
                                            chosen = np.dtype("uint16")
                                        elif vmax <= 0xFFFFFFFF:
                                            chosen = np.dtype("uint32")
                                    else:
                                        if vmin >= -0x8000 and vmax <= 0x7FFF:
                                            chosen = np.dtype("int16")
                                        elif vmin >= -0x80000000 and vmax <= 0x7FFFFFFF:
                                            chosen = np.dtype("int32")

                                    if chosen is not None:
                                        dtype_obj = chosen
                    # Compute bytes using chosen dtype_obj
                    var_nbytes = dtype_obj.itemsize * data_array.size
                except Exception:
                    # If anything goes wrong, fall back to conservative
                    # estimation using data_array.dtype
                    dtype_obj = np.dtype(data_array.dtype)
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
            return self._fallback_estimate(
                items, effective_bbox, datetime, collections, clipped_to_aoi
            )

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

    # ---- Fallback helpers for estimate_data_size ----

    def _size_from_metadata(self, asset_obj: Any) -> int | None:
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

    def _head_content_length(self, href: str) -> int | None:
        # Simple retry with exponential backoff for transient failures.
        attempt = 0
        while attempt <= self.head_retries:
            try:
                resp = self._head_session.request(
                    "HEAD",
                    href,
                    headers=self.headers or {},
                    timeout=self.head_timeout_seconds,
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
                else:
                    return None
            except (requests.RequestException, ValueError, TypeError):
                # On transient error, backoff and retry up to head_retries
                if attempt >= self.head_retries:
                    return None
                backoff = self.head_backoff_base * (2**attempt)
                # Optionally add jitter in range [backoff, backoff * 1.5)
                if self.head_backoff_jitter:
                    # Use the stdlib random jitter (not for crypto - ignore lint)
                    jitter = random.uniform(0.0, backoff * 0.5)  # noqa: S311
                    backoff = backoff + jitter
                # sleep between retries; if sleep is interrupted raise the exception
                time.sleep(backoff)
                attempt += 1
        return None

    def _parallel_head_content_lengths(self, hrefs: list[str]) -> dict[str, int | None]:
        """Perform HEAD requests for multiple hrefs in parallel.

        Returns a map of href -> content-length (int) or None on failure.
        """
        results: dict[str, int | None] = {}
        if not hrefs:
            return results
        # Deduplicate hrefs to avoid redundant requests
        unique_hrefs = list(dict.fromkeys(hrefs))
        with ThreadPoolExecutor(max_workers=self.head_max_workers) as exc:
            future_to_href = {
                exc.submit(self._head_content_length, href): href
                for href in unique_hrefs
            }
            for fut in as_completed(future_to_href):
                href = future_to_href[fut]
                try:
                    results[href] = fut.result()
                except (requests.RequestException, ValueError, TypeError):
                    results[href] = None
        return results

    def _asset_to_dict(self, asset_obj: Any) -> dict[str, Any]:
        if isinstance(asset_obj, dict):
            return asset_obj
        try:
            if hasattr(asset_obj, "to_dict"):
                return asset_obj.to_dict()  # type: ignore[attr-defined]
        except (AttributeError, TypeError) as exc:
            logger.debug("asset_obj.to_dict() failed: %s", exc)
        return {
            "href": getattr(asset_obj, "href", None),
            "media_type": getattr(asset_obj, "media_type", None)
            or getattr(asset_obj, "type", None)
            or "",
            "extra_fields": getattr(asset_obj, "extra_fields", {}) or {},
        }

    def _fallback_estimate(
        self,
        items: list[Any],
        effective_bbox: list[float] | None,
        datetime: str | None,
        collections: list[str] | None,
        clipped_to_aoi: bool,
    ) -> dict[str, Any]:
        assets_info: list[dict[str, Any]] = []
        total_bytes = 0
        # First pass: normalize assets, collect hrefs that will need HEAD
        hrefs_to_check: list[str] = []
        normalized_assets: list[tuple[Any, str, dict[str, Any], str]] = []
        for item in items:
            assets = getattr(item, "assets", {})
            for name, asset in assets.items() if assets else []:
                try:
                    asset_dict = self._asset_to_dict(asset)
                    href = asset_dict.get("href")
                    media = asset_dict.get("media_type") or asset_dict.get("type") or ""
                    bytes_found: int | None = self._size_from_metadata(asset_dict)
                    normalized_assets.append((item, name, asset_dict, media))
                    # If metadata not available and asset looks like parquet/zarr or
                    # otherwise requires a HEAD check, queue the href.
                    if bytes_found is None and href:
                        if "parquet" in str(media).lower() or str(href).endswith(
                            ".parquet"
                        ):
                            hrefs_to_check.append(href)
                        elif "zarr" in str(media).lower() or str(href).endswith(
                            ".zarr"
                        ):
                            # zarr-inspect is attempted later; still add href so that
                            # if inspect fails, we can fall back to HEAD.
                            hrefs_to_check.append(href)
                except (AttributeError, TypeError, ValueError) as exc:
                    logger.debug(
                        "Error processing asset %s for item %s: %s",
                        name,
                        getattr(item, "id", "<unknown>"),
                        exc,
                    )
                    assets_info.append(
                        {
                            "asset": name,
                            "media_type": None,
                            "href": None,
                            "estimated_size_bytes": 0,
                            "estimated_size_mb": 0,
                            "method": "error",
                        }
                    )

        # Perform parallel HEAD requests for queued hrefs
        head_results: dict[str, int | None] = self._parallel_head_content_lengths(
            hrefs_to_check
        )

        # Second pass: decide method and assemble results using head_results
        for _item, name, asset_dict, media in normalized_assets:
            href = asset_dict.get("href")
            bytes_found: int | None = self._size_from_metadata(asset_dict)
            method_used = "metadata"

            if bytes_found is None and "parquet" in str(media).lower():
                bytes_found = head_results.get(href) if href else None
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
                    # If zarr inspection fails, fall back to HEAD if we have it
                    bytes_found = bytes_found or (
                        head_results.get(href) if href else None
                    )
                    if bytes_found:
                        method_used = "head"

            # If still unknown and we have a head result, use it
            if bytes_found is None and href:
                bytes_found = head_results.get(href)
                if bytes_found is not None:
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
                if os.getenv("STAC_MCP_DEBUG"):
                    extra = (
                        asset_dict.get("extra_fields")
                        if isinstance(asset_dict, dict)
                        else None
                    )
                    logger.debug(
                        "fallback asset=%s media=%s href=%s extra=%s",
                        name,
                        media,
                        href,
                        extra,
                    )
                    logger.debug(
                        "fallback bytes=%s method=%s", bytes_found, method_used
                    )
                if bytes_found is not None:
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
            "collections": collections or list({item.collection_id for item in items}),
            "clipped_to_aoi": clipped_to_aoi if "clipped_to_aoi" in locals() else False,
            "assets_analyzed": assets_info,
            "message": (
                "Successfully estimated data size using fallback heuristics"
                if total_bytes
                else "Error estimating data size"
            ),
        }


# Global instance preserved for backward compatibility (imported by server)
stac_client = STACClient()
