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
        sortby: list[dict[str, str]] | None = None,
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
        items = list(search.items())
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

    def _invalidate_cache(self, affected_collections: list[str] | None = None) -> None:
        if not self._search_cache:
            return
        if not affected_collections:
            self._search_cache.clear()
            return
        to_remove = []
        for k in list(self._search_cache.keys()):
            for coll in affected_collections:
                if coll and coll in k:
                    to_remove.append(k)
                    break
        for k in to_remove:
            self._search_cache.pop(k, None)

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
            # Use cached search results (per-client) when available.
            pystac_items = self._cached_search(
                collections=collections,
                bbox=bbox,
                datetime=datetime,
                query=query,
                sortby=sortby,
                limit=limit,
            )
            items = []
            for item in pystac_items:
                # Be permissive when normalizing items: tests and alternate
                # client implementations may provide SimpleNamespace-like
                # objects without all attributes. Use getattr with sensible
                # defaults to avoid AttributeError during normalization.
                items.append(
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
                            k: v.to_dict()
                            for k, v in getattr(item, "assets", {}).items()
                        },
                    }
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
            # Prefer using the underlying session used by pystac_client when
            # available (tests monkeypatch that session). Fall back to using
            # requests.request when no underlying session is present.
            session = None
            try:
                session = getattr(self.client, "_stac_io", None)
                session = getattr(session, "session", None)
            except Exception:  # noqa: BLE001
                session = None

            if session is not None and hasattr(session, "request"):
                response = session.request(
                    method, url, headers=request_headers, timeout=timeout, **kwargs
                )
            else:
                response = requests.request(
                    method, url, headers=request_headers, timeout=timeout, **kwargs
                )
            if response.status_code == HTTP_404:
                return None
            response.raise_for_status()
            # If this transaction modified server state, invalidate cache.
            if method.lower() in ("post", "put", "delete"):
                affected = None
                try:
                    # Try to extract a collection id from the URL when present
                    # e.g., .../collections/{collection_id}/items
                    # or .../collections/{collection_id}
                    base = self.catalog_url.replace("catalog.json", "")
                    path = url.split(base, 1)[-1]
                    if "/collections/" in path:
                        tail = path.split("/collections/", 1)[1]
                        coll = tail.split("/", 1)[0]
                        if coll:
                            affected = [coll]
                except Exception:  # noqa: BLE001
                    affected = None
                try:
                    self._invalidate_cache(affected)
                except Exception:  # noqa: BLE001
                    # Invalidation is best-effort; don't fail the transaction on
                    # cache errors
                    logger.debug("Cache invalidation failed", exc_info=True)
            # Some endpoints may return no content (204) — treat as None
            if not getattr(response, "content", None):
                return None
            # Prefer a native .json() method when present but fall back to
            # decoding the response content when tests provide simple fakes
            # that implement 'content' but not .json(). This keeps tests
            # lightweight while remaining robust for real HTTP responses.
            try:
                return response.json()
            except Exception:  # noqa: BLE001
                try:
                    raw = response.content
                    if isinstance(raw, (bytes, bytearray)):
                        import json as _json  # noqa: PLC0415

                        return _json.loads(raw.decode("utf-8"))
                    if isinstance(raw, str):
                        import json as _json  # noqa: PLC0415

                        return _json.loads(raw)
                except Exception:  # noqa: BLE001
                    # Final fallback: return a simple dict indicating raw
                    # content was present but could not be parsed as JSON.
                    return {"raw_content": getattr(response, "content", None)}
        except requests.exceptions.Timeout as exc:  # pragma: no cover - network
            logger.exception("Request timed out %s %s", method, url)
            raise STACTimeoutError(str(exc)) from exc
        except requests.exceptions.ConnectionError as exc:  # pragma: no cover - network
            logger.exception("Failed to connect %s %s", method, url)
            raise ConnectionFailedError(str(exc)) from exc
        except requests.exceptions.RequestException:
            # Keep logging/raise behavior consistent with previous implementation
            logger.exception("Transaction failed %s %s", method, url)
            raise

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
        limit: int = 10,
    ) -> dict[str, Any]:
        """Unified data size estimator.

        This version uses a unified approach to estimate data size for all asset
        types. It prioritizes explicit metadata, then falls back to parallel
        HTTP HEAD requests to get Content-Length.
        """
        items = self._cached_search(
            collections=collections,
            bbox=bbox,
            datetime=datetime,
            query=query,
            limit=limit,
        )

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
        hrefs_to_head: list[str] = []
        asset_map: dict[str, dict[str, Any]] = {}

        dtype_registry = SensorDtypeRegistry()

        for item in items:
            collection_id = getattr(item, "collection_id", None)
            sensor_info = (
                dtype_registry.get_info(collection_id) if dtype_registry else None
            )

            for name, asset in getattr(item, "assets", {}).items():
                asset_dict = self._asset_to_dict(asset)
                media_type = (
                    asset_dict.get("media_type") or asset_dict.get("type") or ""
                ).lower()

                if sensor_info and sensor_info.should_ignore_asset(name, media_type):
                    continue

                bytes_found = self._size_from_metadata(asset_dict)
                href = asset_dict.get("href")

                if bytes_found is not None:
                    total_bytes += bytes_found
                    assets_info.append(
                        {
                            "asset": name,
                            "media_type": media_type,
                            "href": href,
                            "estimated_size_bytes": bytes_found,
                            "estimated_size_mb": round(bytes_found / (1024 * 1024), 2),
                            "method": "metadata",
                        }
                    )
                elif href:
                    hrefs_to_head.append(href)
                    asset_map[href] = {"name": name, "media_type": media_type}

        if hrefs_to_head:
            head_results = self._parallel_head_content_lengths(hrefs_to_head)
            for href, size in head_results.items():
                asset_details = asset_map[href]
                if size is not None:
                    total_bytes += size
                    assets_info.append(
                        {
                            "asset": asset_details["name"],
                            "media_type": asset_details["media_type"],
                            "href": href,
                            "estimated_size_bytes": size,
                            "estimated_size_mb": round(size / (1024 * 1024), 2),
                            "method": "head",
                        }
                    )
                else:
                    assets_info.append(
                        {
                            "asset": asset_details["name"],
                            "media_type": asset_details["media_type"],
                            "href": href,
                            "estimated_size_bytes": 0,
                            "estimated_size_mb": 0,
                            "method": "failed",
                        }
                    )

        estimated_mb = total_bytes / (1024 * 1024)
        estimated_gb = total_bytes / (1024 * 1024 * 1024)

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
            "assets_analyzed": assets_info,
            "message": "Successfully estimated data size.",
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
        base = self.catalog_url.replace("catalog.json", "").rstrip("/")
        url = f"{base}{path}"
        request_headers = self.headers.copy()
        request_headers.setdefault("Accept", "application/json")
        try:
            res = requests.get(url, headers=request_headers, timeout=30)
            if res.status_code == HTTP_404 or not res.ok:
                return {
                    "queryables": {},
                    "collection_id": collection_id,
                    "message": "Queryables not available",
                }
            q = res.json() if res.content else {}
        except requests.RequestException:
            logger.exception("Failed to fetch queryables %s", url)
            return {
                "queryables": {},
                "collection_id": collection_id,
                "message": "Queryables not available",
            }
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
        # Use the STAC API search endpoint via requests rather than relying on
        # private pystac_client IO helpers. This uses the public HTTP contract.
        # Ensure the server advertises aggregation capability
        self._check_conformance(CONFORMANCE_AGGREGATION)
        base = self.catalog_url.replace("catalog.json", "").rstrip("/")
        url = f"{base}/search"
        request_headers = self.headers.copy()
        request_headers["Accept"] = "application/json"
        # Construct the search request body according to STAC Search API
        body: dict[str, Any] = {}
        if collections:
            body["collections"] = collections
        if bbox:
            body["bbox"] = bbox
        if datetime:
            body["datetime"] = datetime
        if query:
            body["query"] = query
        if limit and limit > 0:
            body["limit"] = limit

        # Aggregation request shape is not strictly standardized across
        # implementations; include a simple aggregations object when fields
        # or operations are provided. Servers supporting aggregation will
        # respond with an `aggregations` field in the search response.
        if fields or operations:
            body["aggregations"] = {
                "fields": fields or [],
                "operations": operations or [],
            }

        try:
            resp = requests.post(url, json=body, headers=request_headers, timeout=30)
            if not resp.ok:
                return {
                    "supported": False,
                    "aggregations": {},
                    "message": "Search endpoint unavailable",
                    "parameters": body,
                }
            res_json = resp.json() if resp.content else {}
            aggs_result = res_json.get("aggregations") or {}
            return {
                "supported": bool(aggs_result),
                "aggregations": aggs_result,
                # any additional metadata preserved
            }
        except requests.RequestException:
            logger.exception("Aggregation request failed %s", url)
            return {
                "supported": False,
                "aggregations": {},
                "message": "Search endpoint unavailable",
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
