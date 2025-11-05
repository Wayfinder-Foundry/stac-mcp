"""STAC client wrapper and size estimation logic (refactored from server)."""

from __future__ import annotations

import json
import logging
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests
from pystac_client.exceptions import APIError

from .sensor_dtypes import SensorDtypeRegistry

# Optional odc.stac/xarray path for more accurate, dtype-aware size estimates.
try:
    # Detect optional runtime availability without importing heavy modules at
    # module import time. Prefer specific import errors to avoid catching
    # unrelated exceptions.
    import odc.stac  # noqa: F401
    import xarray  # noqa: F401

    ODC_STAC_AVAILABLE = True
except (ImportError, ModuleNotFoundError):  # pragma: no cover - optional dependency
    ODC_STAC_AVAILABLE = False

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
        # Lightweight per-client search cache keyed by a deterministic
        # representation of search parameters. This serves as a session-scoped
        # representation of search parameters. This serves as a session-scoped
        # cache (FastMCP session context maps to a reused STACClient instance
        # via the execution layer) so multiple tools invoked within the same
        # session can reuse search results and avoid duplicate network calls.
        # Key -> (timestamp_seconds, value)
        self._search_cache: dict[
            str, tuple[float, list[Any] | list[dict[str, Any]]]
        ] = {}
        # TTL for cached search results (seconds). Default is 5 minutes but
        # can be tuned via env var STAC_MCP_SEARCH_CACHE_TTL_SECONDS.
        try:
            self.search_cache_ttl_seconds = int(
                os.getenv("STAC_MCP_SEARCH_CACHE_TTL_SECONDS", "300")
            )
        except (TypeError, ValueError):
            self.search_cache_ttl_seconds = 300
        # Catalog URL and request headers for this client instance.
        # If the caller passed None, fall back to the package default so
        # transaction helpers can safely build URLs.
        self.catalog_url = (
            catalog_url
            if catalog_url is not None
            else "https://planetarycomputer.microsoft.com/api/stac/v1"
        )
        self.headers = headers or {}
        # Lazy-initialized underlying pystac-client instance and cached
        # conformance metadata.
        self._client = None
        self._conformance = None
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
        # Lightweight per-client search cache keyed by a deterministic
        # representation of search parameters. This serves as a session-scoped
        # cache (FastMCP session context maps to a reused STACClient instance
        # via the execution layer) so multiple tools invoked within the same
        # session can reuse search results and avoid duplicate network calls.
        # Key -> (timestamp_seconds, value)
        self._search_cache: dict[
            str, tuple[float, list[Any] | list[dict[str, Any]]]
        ] = {}

    def _search_cache_key(
        self,
        collections: list[str] | None,
        bbox: list[float] | None,
        datetime: str | None,
        query: dict[str, Any] | None,
        limit: int,
    ) -> str:
        """Create a deterministic cache key for search parameters."""
        # Include the identity of the underlying client object so that tests
        # which patch `STACClient.client` get distinct cache entries.
        try:
            client_id = id(self.client)
        except Exception:  # noqa: BLE001
            client_id = 0
        key_obj = {
            "collections": collections or [],
            "bbox": bbox,
            "datetime": datetime,
            "query": query,
            "limit": limit,
            "client_id": client_id,
        }
        # Use json.dumps with sort_keys for deterministic serialization.
        return json.dumps(key_obj, sort_keys=True, default=str)

    def _cached_search(
        self,
        collections: list[str] | None = None,
        bbox: list[float] | None = None,
        datetime: str | None = None,
        query: dict[str, Any] | None = None,
        sortby: list[str] | list[dict[str, str]] | None = None,
        limit: int = 10,
    ) -> list[Any]:
        """Run a search and cache the resulting item list per-client.

        Returns a list of pystac.Item objects (as returned by the underlying
        client's search.items()).
        """
        key = self._search_cache_key(collections, bbox, datetime, query, limit)
        now = time.time()
        cached = self._search_cache.get(key)
        if cached is not None:
            ts, val = cached
            # Read TTL from the environment dynamically so tests can adjust
            # the TTL even when a shared client was instantiated earlier.
            try:
                ttl = int(
                    os.getenv(
                        "STAC_MCP_SEARCH_CACHE_TTL_SECONDS",
                        str(self.search_cache_ttl_seconds),
                    )
                )
            except (TypeError, ValueError):
                ttl = getattr(self, "search_cache_ttl_seconds", 300)
            if now - ts <= ttl:
                return val
            # expired
            self._search_cache.pop(key, None)

        search = self.client.search(
            collections=collections,
            bbox=bbox,
            datetime=datetime,
            query=query,
            sortby=sortby,
            limit=limit,
        )
        items = search.items_as_dict()
        # Store the list for reuse within this client/session along with timestamp.
        self._search_cache[key] = (now, items)
        return items

    def _cached_collections(self, limit: int = 10) -> list[dict[str, Any]]:
        key = f"collections:limit={int(limit)}"
        now = time.time()
        cached = self._search_cache.get(key)
        if cached is not None:
            ts, val = cached
            try:
                ttl = int(
                    os.getenv(
                        "STAC_MCP_SEARCH_CACHE_TTL_SECONDS",
                        str(self.search_cache_ttl_seconds),
                    )
                )
            except (TypeError, ValueError):
                ttl = getattr(self, "search_cache_ttl_seconds", 300)
            if now - ts <= ttl:
                return val  # type: ignore[return-value]
            self._search_cache.pop(key, None)

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
                }
            )
            if limit > 0 and len(collections) >= limit:
                break

        self._search_cache[key] = (now, collections)
        return collections

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
        # Use cached collections when possible
        try:
            return self._cached_collections(limit=limit)
        except APIError:  # pragma: no cover - network dependent
            logger.exception("Error fetching collections")
            raise

    def get_collection(self, collection_id: str) -> dict[str, Any]:
        try:
            collection = self.client.get_collection(collection_id)
        except APIError:  # pragma: no cover - network dependent
            logger.exception("Error fetching collection %s", collection_id)
            raise
        else:
            if collection is None:
                return None
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
        sortby: list[str] | list[dict[str, str]] | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        if query:
            self._check_conformance(CONFORMANCE_QUERY)
        if sortby:
            self._check_conformance(CONFORMANCE_SORT)
        try:
            # Use cached search results (per-client) when available.
            items = self._cached_search(
                collections=collections,
                bbox=bbox,
                datetime=datetime,
                query=query,
                sortby=sortby,
                limit=limit,
            )
        except APIError:  # pragma: no cover - network dependent
            logger.exception("Error searching items")
            raise

        if not items:
            return []
        # Normalize items to dicts for consistent output.
        normalized_items = []
        for item in items:
            normalized_items.append(
                {
                    "id": getattr(item, "id", None),
                    "collection": getattr(item, "collection_id", None),
                    "geometry": getattr(item, "geometry", None),
                    "bbox": getattr(item, "bbox", None),
                    "datetime": (
                        item.datetime.isoformat()
                        if getattr(item, "datetime", None)
                        else None
                    ),
                    "properties": getattr(item, "properties", {}) or {},
                    "assets": {
                        k: v.to_dict() for k, v in getattr(item, "assets", {}).items()
                    },
                }
            )
        return normalized_items

    def get_item(self, collection_id: str, item_id: str) -> dict[str, Any]:
        try:
            collection = self.client.get_collection(collection_id)
            if collection is None:
                return None
            item = collection.get_item(item_id)
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
            # Normalize defensively as above
            return {
                "id": getattr(item, "id", None),
                "collection": getattr(item, "collection_id", None),
                "geometry": getattr(item, "geometry", None),
                "bbox": getattr(item, "bbox", None),
                "datetime": (
                    item.datetime.isoformat()
                    if getattr(item, "datetime", None)
                    else None
                ),
                "properties": getattr(item, "properties", {}) or {},
                "assets": {
                    k: v.to_dict() for k, v in getattr(item, "assets", {}).items()
                },
            }

    # ------------------------- Data Size Estimation ----------------------- #
    def estimate_data_size(
        self,
        collections: list[str] | None = None,
        bbox: list[float] | None = None,
        datetime: str | None = None,
        query: dict[str, Any] | None = None,
        aoi_geojson: dict[str, Any] | None = None,
        limit: int = 10,
        force_metadata_only: bool = False,
    ) -> dict[str, Any]:
        """Simplified estimator: prefer odc.stac + xarray to compute eager size.

        This implementation is intentionally minimal: when odc.stac and
        xarray are available it loads the matching items into an
        xarray.Dataset and computes an eager size estimate by summing the
        number of elements across data variables. For simplicity we assume
        1 byte per element (ignore dtype/itemsize). If optional libraries
        are missing we return a helpful message.
        """

        # Retrieve matching items (pystac.Item objects). Keep this small and
        # deterministic. The underlying search may return more items than the
        # requested `limit` due to provider behavior or cached results, so
        # enforce truncation here before any expensive work (odc.stac.load).
        items = self._cached_search(
            collections=collections,
            bbox=bbox,
            datetime=datetime,
            query=query,
            limit=limit,
        )

        # Respect the caller-provided limit strictly.
        if limit and limit > 0 and len(items) > limit:
            items = items[:limit]

        if not items:
            return {
                "item_count": 0,
                "estimated_size_bytes": 0,
                "estimated_size_mb": 0,
                "estimated_size_gb": 0,
                "bbox_used": bbox,
                "temporal_extent": datetime,
                "collections": collections or [],
                "clipped_to_aoi": bool(aoi_geojson),
                "message": "No items found for the given query parameters",
            }

        # If the optional odc.stac/xarray path is not available and the
        # caller did not request metadata-only behaviour, return a helpful
        # message explaining how to enable dataset-based estimates. If the
        # caller requested `force_metadata_only=True` we skip this early
        # return and fall back to metadata/HEAD aggregation below.
        if not ODC_STAC_AVAILABLE and not force_metadata_only:
            return {
                "item_count": len(items),
                "estimated_size_bytes": 0,
                "estimated_size_mb": 0,
                "estimated_size_gb": 0,
                "bbox_used": bbox,
                "temporal_extent": datetime,
                "collections": collections
                or [getattr(item, "collection_id", None) for item in items],
                "clipped_to_aoi": bool(aoi_geojson),
                "message": (
                    "odc.stac/xarray not available; install 'odc-stac' "
                    "and 'xarray' to enable dataset-based estimates"
                ),
            }

        # If the caller requested metadata-only behaviour, skip the odc/xarray
        # eager load path and jump straight to the metadata/HEAD fallback
        # implemented later in this function.
        odc_exc = False
        if not force_metadata_only:
            # Try to perform a per-item odc.stac load and compute sizes.
            try:
                import xarray as xr  # type: ignore[import]  # noqa: PLC0415
                from odc.stac import (  # noqa: PLC0415
                    load as _odc_load,  # type: ignore[import]
                )

                # Load items one-by-one so sensor registry overrides can be
                # applied per-item and to keep memory usage predictable.
                total_bytes = 0
                sensor_native_total_bytes = 0
                data_variables: list[dict[str, Any]] = []
                dtype_registry = SensorDtypeRegistry()

                for item in items:
                    ds_item = _odc_load([item], chunks={})
                    if not isinstance(ds_item, xr.Dataset):
                        continue

                    collection_id = getattr(item, "collection_id", None)
                    sensor_info = dtype_registry.get_info(collection_id)

                    for name, da in ds_item.data_vars.items():
                        try:
                            shape = tuple(int(s) for s in getattr(da, "shape", ()))
                            elems = 1
                            for s in shape:
                                elems *= s

                            underlying = getattr(da, "data", None)
                            nbytes = getattr(underlying, "nbytes", None)
                            method = "computed"
                            override_applied = False
                            if nbytes is not None:
                                size_bytes = int(nbytes)
                                method = "nbytes"
                                # Softer heuristic: if the reported dtype is a
                                # floating type but the sensor registry suggests
                                # an integer native dtype for this asset, produce
                                # both reported and registry-corrected sizes so
                                # callers can see both views and choose.
                                try:
                                    import numpy as np  # type: ignore[import]  # noqa: PLC0415 - guarded import

                                    reported_dtype = getattr(da, "dtype", None)
                                    override_dtype = None
                                    if sensor_info is not None:
                                        try:
                                            override_dtype = (
                                                sensor_info.get_dtype_for_asset(name)
                                            )
                                        except (AttributeError, TypeError, ValueError):
                                            override_dtype = None

                                    # Only consider registry correction when the
                                    # reported dtype is a float and the registry
                                    # suggests an integer dtype for this asset.
                                    if (
                                        reported_dtype is not None
                                        and hasattr(reported_dtype, "kind")
                                        and reported_dtype.kind == "f"
                                        and override_dtype is not None
                                        and np.issubdtype(override_dtype, np.integer)
                                    ):
                                        # Compute registry-corrected bytes (no
                                        # side-effects on total_bytes; we keep the
                                        # estimator's numeric total based on what
                                        # xarray reports unless a caller requests
                                        # otherwise).
                                        try:
                                            sensor_itemsize = int(
                                                np.dtype(override_dtype).itemsize
                                            )
                                        except (TypeError, ValueError):
                                            sensor_itemsize = 1
                                        sensor_native_bytes = int(
                                            elems * sensor_itemsize
                                        )
                                    else:
                                        sensor_native_bytes = None
                                except (ImportError, ModuleNotFoundError):
                                    # If numpy missing, skip registry check.
                                    sensor_native_bytes = None
                            else:
                                override_dtype = None
                                if sensor_info is not None:
                                    try:
                                        override_dtype = (
                                            sensor_info.get_dtype_for_asset(name)
                                        )
                                    except (AttributeError, TypeError, ValueError):
                                        override_dtype = None

                                dtype = getattr(da, "dtype", None)
                                if override_dtype is not None:
                                    dtype = override_dtype
                                    override_applied = True

                                itemsize = getattr(dtype, "itemsize", None)
                                if itemsize is None:
                                    try:
                                        import numpy as np  # type: ignore[import]  # noqa: PLC0415 - guarded import

                                        itemsize = (
                                            np.dtype(dtype).itemsize
                                            if dtype is not None
                                            else 1
                                        )
                                    except (
                                        ImportError,
                                        ModuleNotFoundError,
                                        TypeError,
                                        ValueError,
                                    ):
                                        itemsize = 1
                                size_bytes = int(elems * int(itemsize))

                            total_bytes += size_bytes
                            # sensor_native_total accumulates the sensor-native
                            # bytes when available; otherwise fall back to the
                            # reported/computed size_bytes so the sensor-native
                            # total is a complete estimate.
                            if (
                                "sensor_native_bytes" in locals()
                                and sensor_native_bytes is not None
                            ):
                                sensor_native_total_bytes += int(sensor_native_bytes)
                            else:
                                sensor_native_total_bytes += int(size_bytes)
                            var_entry: dict[str, Any] = {
                                "variable": name,
                                "shape": shape,
                                "elements": elems,
                                "estimated_bytes": int(size_bytes),
                                "dtype": str(getattr(da, "dtype", None)),
                                "method": method,
                                "override_applied": bool(override_applied),
                            }
                            # If we computed a registry-corrected bytes value
                            # for float->integer recommendations, include both
                            # values so callers can inspect and choose.
                            if (
                                "sensor_native_bytes" in locals()
                                and sensor_native_bytes is not None
                            ):
                                var_entry["reported_bytes"] = int(size_bytes)
                                var_entry["sensor_native_bytes"] = int(
                                    sensor_native_bytes
                                )
                                var_entry["sensor_native_dtype"] = str(override_dtype)
                                # Recommend the sensor-native value for
                                # storage/instrument-native use-cases but do not
                                # change the estimator total by default.
                                var_entry["recommended"] = "sensor_native"
                                var_entry["sensor_native_recommended"] = True

                            data_variables.append(var_entry)
                        except Exception as exc:  # noqa: BLE001 - defensive skip
                            # Skip variables we cannot introspect but emit a
                            # debug-level message so failures are visible in
                            # debugging runs while avoiding noisy user logs.
                            logger.debug(
                                "Skipping variable %s due to error: %s", name, exc
                            )
                            continue
                estimated_mb = total_bytes / (1024 * 1024)
                estimated_gb = total_bytes / (1024 * 1024 * 1024)
                sensor_native_estimated_mb = sensor_native_total_bytes / (1024 * 1024)
                sensor_native_estimated_gb = sensor_native_total_bytes / (
                    1024 * 1024 * 1024
                )

                # Summarize how many variables reported native .nbytes and how
                # many have a sensor-native alternative included.
                reported_nbytes_count = sum(
                    1 for v in data_variables if v.get("method") == "nbytes"
                )
                sensor_native_corrections_count = sum(
                    1
                    for v in data_variables
                    if v.get("sensor_native_bytes") is not None
                )

                parts = [
                    "Estimated sizes computed using odc.stac/xarray.",
                    f"Numeric total uses .data.nbytes: {int(total_bytes)} bytes",
                    f"(~{round(estimated_gb, 4)} GB);",
                    "sensor-native total (instrument-native) is",
                    f"{int(sensor_native_total_bytes)} bytes",
                    f"(~{round(sensor_native_estimated_gb, 4)} GB).",
                    f"Reported .data.nbytes count: {reported_nbytes_count};",
                    f"Sensor-native corrections: {sensor_native_corrections_count}.",
                ]
                message = " ".join(parts)

                return {
                    "item_count": len(items),
                    "estimated_size_bytes": int(total_bytes),
                    "estimated_size_mb": round(estimated_mb, 2),
                    "estimated_size_gb": round(estimated_gb, 4),
                    "sensor_native_estimated_size_bytes": int(
                        sensor_native_total_bytes
                    ),
                    "sensor_native_estimated_size_mb": round(
                        sensor_native_estimated_mb, 2
                    ),
                    "sensor_native_estimated_size_gb": round(
                        sensor_native_estimated_gb, 4
                    ),
                    "bbox_used": bbox,
                    "temporal_extent": datetime,
                    "collections": collections
                    or [getattr(item, "collection_id", None) for item in items],
                    "clipped_to_aoi": bool(aoi_geojson),
                    "data_variables": data_variables,
                    "message": message,
                }
            except Exception:  # pragma: no cover - best-effort
                # odc may fail when tests pass in lightweight objects; log and
                # fall back to metadata/HEAD-based aggregation below.
                logger.exception("odc.stac eager estimate failed")
                odc_exc = True

        # Fallback estimator: aggregate sizes from asset metadata (file:size)
        # and, when missing, use HEAD requests to probe Content-Length. This
        # path is exercised by unit tests and serves as a robust fallback
        # when odc/xarray-based introspection is unavailable or fails.
        total_bytes = 0
        assets_analyzed: list[dict[str, Any]] = []
        hrefs_to_probe: list[str] = []

        for item in items:
            # Accept both dict-like and object items (tests use MagicMock)
            assets = getattr(item, "assets", None) or {}
            # assets may be a dict of asset objects or dicts
            for name, asset in assets.items() if isinstance(assets, dict) else []:
                try:
                    a = self._asset_to_dict(asset)
                    # First, try metadata-based size hints
                    meta_size = self._size_from_metadata(a)
                    if meta_size is not None:
                        assets_analyzed.append(
                            {
                                "asset": name,
                                "href": a.get("href"),
                                "method": "metadata",
                                "size": int(meta_size),
                            }
                        )
                        total_bytes += int(meta_size)
                        continue

                    # If no metadata size, and we have an href, queue for HEAD
                    href = a.get("href")
                    if href:
                        hrefs_to_probe.append(href)
                        assets_analyzed.append(
                            {
                                "asset": name,
                                "href": href,
                                "method": "head",
                                "size": None,
                            }
                        )
                        continue

                    # Otherwise we couldn't analyze this asset
                    assets_analyzed.append(
                        {"asset": name, "href": None, "method": "failed", "size": None}
                    )
                except (AttributeError, TypeError, ValueError) as exc:
                    logger.debug("Failed to normalize asset %s: %s", name, exc)
                    assets_analyzed.append(
                        {"asset": name, "href": None, "method": "failed", "size": None}
                    )

        # Probe hrefs in parallel (HEAD requests). _parallel_head_content_lengths
        # returns a mapping href -> size | None.
        if hrefs_to_probe:
            try:
                head_results = self._parallel_head_content_lengths(hrefs_to_probe)
            except Exception as exc:  # pragma: no cover - defensive  # noqa: BLE001
                logger.debug("HEAD probing failed: %s", exc)
                head_results = dict.fromkeys(hrefs_to_probe)

            # Fill in sizes for analyzed assets
            for a in assets_analyzed:
                if a.get("method") == "head" and a.get("href"):
                    size = head_results.get(a["href"])
                    if size is None:
                        a["method"] = "failed"
                        a["size"] = None
                    else:
                        a["size"] = int(size)
                        total_bytes += int(size)

        estimated_mb = total_bytes / (1024 * 1024)
        estimated_gb = total_bytes / (1024 * 1024 * 1024) if total_bytes else 0

        message = (
            "Estimated sizes computed using metadata/HEAD fallback. "
            f"Total (metadata+HEAD) is {int(total_bytes)} bytes "
            f"(~{round(estimated_gb, 4)} GB)."
        )
        return {
            "item_count": len(items),
            "estimated_size_bytes": int(total_bytes),
            "estimated_size_mb": round(estimated_mb, 2),
            "estimated_size_gb": round(estimated_gb, 4),
            "bbox_used": bbox,
            "temporal_extent": datetime,
            "collections": collections
            or [getattr(item, "collection_id", None) for item in items],
            "clipped_to_aoi": bool(aoi_geojson),
            "assets_analyzed": assets_analyzed,
            "message": message,
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
        # Some STAC servers expose a /queryables endpoint via a link on the root
        # document but may omit the exact conformance URI from the conformance
        # list. Try the strict conformance check first; if it fails, fall back
        # to inspecting the root document for an explicit queryables link and
        # allow the call to proceed when such a link is present.
        try:
            self._check_conformance(CONFORMANCE_QUERYABLES)
        except ConformanceError:
            # If the conformance check fails, see if the root advertises a
            # queryables link. If it does, proceed; otherwise re-raise the
            # ConformanceError.
            root = self.get_root_document()
            links = root.get("links", [])
            for link in links:
                rel = link.get("rel")
                href = link.get("href", "")
                # If we find a queryables link, break and allow the call to proceed.
                # We do not validate the href here; the subsequent request may still
                # fail.
                # opengis.net link is preferred, but some servers use custom rels with
                # /queryables in href.
                if rel == "http://www.opengis.net/def/rel/ogc/1.0/queryables" or (
                    isinstance(href, str) and "/queryables" in href
                ):
                    break
            else:
                # No queryables conformance and no link advertised -> fail.
                raise

        path = (
            f"/collections/{collection_id}/queryables"
            if collection_id
            else "/queryables"
        )
        base = self.catalog_url
        if base.endswith("/catalog.json"):
            base = base[: -len("/catalog.json")]
        base = base.rstrip("/")
        url = f"{base}{path}"
        request_headers = self.headers.copy()
        request_headers.setdefault("Accept", "application/json")
        try:
            res = requests.get(url, headers=request_headers, timeout=30)
            # If the collection-scoped endpoint returns 404 and we were trying a
            # collection-specific path, some servers instead expose the root
            # /queryables endpoint and accept a `collection` query parameter.
            # Try that fallback before giving up.
            if not res.ok:
                if res.status_code == HTTP_404 and collection_id is not None:
                    fallback_url = f"{base}/queryables?collection={collection_id}"
                    try:
                        res2 = requests.get(
                            fallback_url, headers=request_headers, timeout=30
                        )
                        if not res2.ok:
                            return {
                                "queryables": {},
                                "collection_id": collection_id,
                                "message": f"Queryables not available (HTTP \
                                    {res2.status_code})",
                            }
                        q = res2.json() if res2.content else {}
                    except requests.RequestException as e:
                        logger.exception("Failed to fetch queryables %s", fallback_url)
                        return {
                            "queryables": {},
                            "collection_id": collection_id,
                            "message": f"Queryables not available \
                                (request failed: {e})",
                        }
                else:
                    return {
                        "queryables": {},
                        "collection_id": collection_id,
                        "message": f"Queryables not available (HTTP {res.status_code})",
                    }
            else:
                q = res.json() if res.content else {}
        except requests.RequestException as e:
            logger.exception("Failed to fetch queryables %s", url)
            return {
                "queryables": {},
                "collection_id": collection_id,
                "message": f"Queryables not available (request failed: {e})",
            }
        props = q.get("properties") or q.get("queryables") or {}
        return {"queryables": props, "collection_id": collection_id}

    def get_aggregations(
        self,
        collections: list[str] | None = None,
        ids: list[str] | None = None,
        bbox: list[float] | None = None,
        intersects: dict[str, Any] | None = None,
        datetime: str | None = None,
        query: dict[str, Any] | None = None,
        filter_lang: str | None = None,  # noqa: ARG002
        filter_expr: dict[str, Any] | None = None,  # noqa: ARG002
        fields: list[str] | None = None,
        sortby: list[dict[str, Any]] | None = None,
        limit: int = 0,
    ) -> dict[str, Any]:
        self._check_conformance(CONFORMANCE_AGGREGATION)
        base = self.catalog_url
        if base.endswith("/catalog.json"):
            base = base[: -len("/catalog.json")]
        base = base.rstrip("/")
        url = f"{base}/search"

        request_headers = self.headers.copy()
        request_headers["Accept"] = "application/json"

        body: dict[str, Any] = {}
        if collections:
            body["collections"] = collections
        if ids:
            body["ids"] = ids
        if bbox:
            body["bbox"] = bbox
        if intersects:
            body["intersects"] = intersects
        if datetime:
            body["datetime"] = datetime
        if query:
            body["query"] = query
        if sortby:
            body["sortby"] = sortby
        if limit and limit > 0:
            body["limit"] = limit

        # Aggregation-specific part of the request
        if fields:
            body["aggregations"] = [{"name": f, "params": {}} for f in fields]

        try:
            resp = requests.post(url, json=body, headers=request_headers, timeout=60)
            if not resp.ok:
                return {
                    "supported": False,
                    "aggregations": {},
                    "message": f"Search endpoint unavailable (HTTP {resp.status_code})",
                    "parameters": body,
                }
            res_json = resp.json() if resp.content else {}
            aggs_result = res_json.get("aggregations") or {}
            return {
                "supported": "aggregations" in res_json,
                "aggregations": aggs_result,
                "meta": res_json.get("meta", {}),
                "links": res_json.get("links", []),
            }
        except requests.RequestException as e:
            logger.exception("Aggregation request failed %s", url)
            return {
                "supported": False,
                "aggregations": {},
                "message": f"Search endpoint unavailable (request failed: {e})",
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

    def _asset_to_dict(self, asset: Any) -> dict[str, Any]:
        """Normalize asset representations to a dict.

        Accepts dicts, objects with to_dict(), or objects with attributes.
        This helper is intentionally permissive to handle multiple STAC
        provider styles and test fixtures.
        """
        if isinstance(asset, dict):
            return asset
        # Try to use a to_dict() method if available
        # Prefer calling a to_dict() method when available, but guard it and
        # log failures rather than silently swallowing them so lint rules
        # (S110) are satisfied while keeping behavior permissive for tests
        # and different provider representations.
        to_dict = getattr(asset, "to_dict", None)
        if callable(to_dict):
            try:
                return to_dict()
            except Exception:  # noqa: BLE001
                logger.debug(
                    "asset.to_dict() failed during normalization", exc_info=True
                )

        # Fallback: extract common attributes
        out: dict[str, Any] = {}
        for k in ("href", "media_type", "type", "extra_fields"):
            v = getattr(asset, k, None)
            if v is not None:
                out[k] = v
        return out

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
        signed_href = self._sign_href(href)
        while attempt <= self.head_retries:
            try:
                resp = self._head_session.request(
                    "HEAD",
                    signed_href,
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
                    # No content-length header present
                    return None
            except requests.RequestException:
                # Transient network error: will retry based on head_retries
                pass

            # Exponential backoff with optional jitter
            attempt += 1
            self._last_retry_attempts = attempt
            if attempt > self.head_retries:
                break
            backoff = self.head_backoff_base * (2 ** (attempt - 1))
            if self.head_backoff_jitter:
                backoff = backoff * (1.0 + random.random())  # noqa: S311
            time.sleep(backoff)

        return None

    def _parallel_head_content_lengths(self, hrefs: list[str]) -> dict[str, int | None]:
        """Run HEAD requests in parallel and return a mapping of href -> bytes or None.

        Respects client.head_max_workers and client.head_timeout_seconds via the
        shared head session and the session.request wrapper.
        """
        if not hrefs:
            return {}
        results: dict[str, int | None] = {}
        with ThreadPoolExecutor(max_workers=self.head_max_workers) as ex:
            future_to_href = {ex.submit(self._head_content_length, h): h for h in hrefs}
            for fut in as_completed(future_to_href):
                href = future_to_href[fut]
                try:
                    results[href] = fut.result()
                except Exception:  # noqa: BLE001
                    # Keep failure modes simple for the estimator; record None
                    results[href] = None
        return results
