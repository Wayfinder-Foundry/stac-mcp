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
        """Simplified data size estimator.

        This version only considers GeoTIFF-like assets (media type
        containing 'image/tiff' or hrefs ending with .tif/.tiff). The
        resolution is determined from these sources in order of
        preference:
        1. explicit metadata (file:size, bytes, etc.)
        2. HTTP HEAD Content-Length
        3. rasterio inspection (if rasterio available and href is
           readable by rasterio)

        The function uses the SensorDtypeRegistry to apply a collection-
        specific native dtype hint when rasterio reports a float dtype
        but the sensor is known to use an integer native dtype.
        """

        # Lightweight search and normalization
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

        total_bytes = 0
        assets_info: list[dict[str, Any]] = []

        # If aoi_geojson is passed, we record that we intended to clip, but
        # simplified estimator does not perform geometry clipping.
        clipped_to_aoi = bool(aoi_geojson)

        # Lazy import of the sensor dtype registry (same package). Keep this
        # optional so the estimator can work without the helper module.
        try:
            from .sensor_dtypes import SensorDtypeRegistry  # noqa: PLC0415

            dtype_registry = SensorDtypeRegistry()
        except (ImportError, ModuleNotFoundError, AttributeError):
            dtype_registry = None  # optional helper

        for item in items:
            assets = getattr(item, "assets", {})
            for name, asset in assets.items() if assets else []:
                try:
                    asset_dict = self._asset_to_dict(asset)
                except (AttributeError, TypeError, ValueError) as exc:
                    logger.debug("Failed to normalize asset: %s", exc)
                    continue

                href = asset_dict.get("href")
                media = asset_dict.get("media_type") or asset_dict.get("type") or ""
                media = str(media).lower()
                # If registry suggests ignoring this asset (preview/thumbnail), skip it
                sensor_info = None
                try:
                    if dtype_registry is not None:
                        sensor_info = dtype_registry.get_info(
                            getattr(item, "collection_id", None)
                        )
                except (AttributeError, TypeError):
                    sensor_info = None

                if sensor_info is not None and sensor_info.should_ignore_asset(
                    name, media
                ):
                    # Skip preview/thumbnail/browse/RGB preview assets per registry
                    continue

                # Consider any asset whose media string mentions TIFF/GeoTIFF
                # or whose href ends with a TIFF extension as GeoTIFFs. Some
                # STAC providers use vendor media types like
                # 'image/vnd.stac.geotiff' so checking for 'tiff'/'geotiff'
                # substrings is more robust.
                is_geotiff = ("tiff" in media or "geotiff" in media) or (
                    isinstance(href, str)
                    and href.lower().endswith((".tif", ".tiff", ".tif.gz"))
                )
                if not is_geotiff:
                    # Skip non-GeoTIFF assets
                    continue

                # 1) Try metadata
                bytes_found = self._size_from_metadata(asset_dict)
                method_used = "metadata" if bytes_found is not None else ""

                # 2) HEAD (use signed href when available)
                if bytes_found is None and isinstance(href, str):
                    href_to_check = self._sign_href(href)
                    bytes_found = self._head_content_length(href_to_check)
                    if bytes_found is not None:
                        method_used = "head"

                # 3) rasterio inspection (optional)
                if bytes_found is None and isinstance(href, str):
                    try:
                        import rasterio  # noqa: PLC0415

                        # Use rasterio to compute bytes from shape/dtype. Combine
                        # the Env and open contexts in one statement. Use a
                        # signed href when available so remote blobs behind the
                        # Planetary Computer can be accessed.
                        href_to_open = self._sign_href(href)
                        with rasterio.Env(), rasterio.open(href_to_open) as src:
                            bands = src.count or 1
                            height = int(getattr(src, "height", 0))
                            width = int(getattr(src, "width", 0))
                            # src.dtypes is a list of dtype strings (per-band)
                            dtype_str = src.dtypes[0] if src.dtypes else src.dtypes

                            # Prefer registry-suggested native dtype when present.
                            if sensor_info is not None:
                                try:
                                    suggested = sensor_info.get_dtype_for_asset(name)
                                except (AttributeError, TypeError, ValueError):
                                    suggested = None
                                if suggested is not None:
                                    dtype = np.dtype(suggested)
                                else:
                                    dtype = np.dtype(dtype_str)
                            else:
                                dtype = np.dtype(dtype_str)

                            bytes_found = (
                                int(dtype.itemsize)
                                * int(bands)
                                * int(height)
                                * int(width)
                            )
                            method_used = "rasterio"
                    except (ImportError, ModuleNotFoundError):
                        # rasterio not installed; leave bytes_found as None
                        pass
                    except (AttributeError, OSError, ValueError, TypeError):
                        # Failed to open/inspect with rasterio; leave None
                        pass

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
                    total_bytes += int(bytes_found)
                    assets_info.append(
                        {
                            "asset": name,
                            "media_type": media,
                            "href": href,
                            "estimated_size_bytes": int(bytes_found),
                            "estimated_size_mb": round(bytes_found / (1024 * 1024), 2),
                            "method": method_used or "inferred",
                        }
                    )

        estimated_mb = total_bytes / (1024 * 1024)
        estimated_gb = total_bytes / (1024 * 1024 * 1024)

        # If we found nothing via GeoTIFF inspection, attempt fallback
        # heuristics (parquet metadata, zarr inspection, or HEAD). The
        # fallback logic is implemented in a private helper so the core
        # GeoTIFF-only path remains simple and testable.
        if total_bytes == 0:
            if force_metadata_only:
                # Caller explicitly requested fallback-only behavior
                return self._fallback_estimate(
                    items, bbox, datetime, collections, clipped_to_aoi
                )
            # Try fallback heuristics but prefer GeoTIFF results when
            # available. If fallback produces a non-zero estimate, return it.
            fb = self._fallback_estimate(
                items, bbox, datetime, collections, clipped_to_aoi
            )
            if fb.get("estimated_size_bytes", 0):
                return fb

        return {
            "item_count": len(items),
            "estimated_size_bytes": int(total_bytes),
            "estimated_size_mb": round(estimated_mb, 2),
            "estimated_size_gb": round(estimated_gb, 4),
            "bbox_used": bbox,
            "temporal_extent": datetime,
            "collections": collections
            or list({getattr(item, "collection_id", None) for item in items}),
            "clipped_to_aoi": clipped_to_aoi,
            "assets_analyzed": assets_info,
            "message": (
                "Successfully estimated data size for GeoTIFF assets"
                if total_bytes
                else "No GeoTIFF assets found or failed to estimate sizes"
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

    def _sign_href(self, href: str) -> str:
        """Return a signed href when possible (Planetary Computer assets).

        This is best-effort: if the optional `planetary_computer` package is
        available, use it to sign blob URLs so HEAD/rasterio can access them.
        If signing fails or the package is unavailable, return the original
        href unchanged.
        """
        if not isinstance(href, str) or not href:
            return href
        try:
            import planetary_computer as pc  # noqa: PLC0415

            signed = pc.sign(href)
            # pc.sign may return a string or a mapping with a 'url' field
            if isinstance(signed, str):
                return signed
            if isinstance(signed, dict):
                return signed.get("url", href)
        except (
            ImportError,
            ModuleNotFoundError,
            AttributeError,
            TypeError,
            ValueError,
        ):
            # Best-effort: leave href unchanged when signing is not possible
            return href
        return href

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
