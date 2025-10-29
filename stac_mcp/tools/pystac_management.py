"""PySTAC-based CRUDL operations for STAC catalogs, collections, and items.

This module provides Create, Read, Update, Delete, and List operations using
pystac for both local (filesystem) and remote (HTTP/S) STAC resources.
This complements the existing transaction tools (which use pystac-client for
remote API transactions only).

Key differences from transaction tools:
- Uses pystac for direct object manipulation (local and remote)
- Supports local filesystem operations
- Supports STAC_API_KEY environment variable for authenticated remote requests
- Provides full CRUDL operations (including List)
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class PySTACManager:
    """Manager for pystac-based CRUDL operations on STAC resources."""

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize PySTAC manager.

        Args:
            api_key: Optional API key for authenticated remote requests.
                     If not provided, will check STAC_API_KEY env variable.
        """
        self.api_key = api_key or os.getenv("STAC_API_KEY")

    def _get_headers(self) -> dict[str, str]:
        """Get HTTP headers including API key if available."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _is_remote(self, path: str) -> bool:
        """Check if path is a remote URL."""
        return path.startswith(("http://", "https://"))

    def _read_json_file(self, path: str) -> dict[str, Any]:
        """Read JSON from local file or remote URL."""
        if self._is_remote(path):
            req = urllib.request.Request(  # noqa: S310
                path, headers=self._get_headers()
            )
            with urllib.request.urlopen(req) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        else:
            with Path(path).open("r") as f:
                return json.load(f)

    def _write_json_file(self, path: str, data: dict[str, Any]) -> None:
        """Write JSON to local file or remote URL."""
        if self._is_remote(path):
            req = urllib.request.Request(  # noqa: S310
                path,
                data=json.dumps(data).encode("utf-8"),
                headers=self._get_headers(),
                method="PUT",
            )
            urllib.request.urlopen(req)  # noqa: S310
        else:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with Path(path).open("w") as f:
                json.dump(data, f, indent=2)

    def _delete_file(self, path: str) -> None:
        """Delete local file or remote resource."""
        if self._is_remote(path):
            req = urllib.request.Request(  # noqa: S310
                path,
                headers=self._get_headers(),
                method="DELETE",
            )
            urllib.request.urlopen(req)  # noqa: S310
        else:
            Path(path).unlink(missing_ok=True)

    # ======================== Catalog Operations ========================

    def create_catalog(
        self,
        path: str,
        catalog_id: str,
        description: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        """Create a new STAC Catalog.

        Args:
            path: Path to save catalog (local file or remote URL)
            catalog_id: Catalog identifier
            description: Catalog description
            title: Optional catalog title

        Returns:
            Created catalog as dictionary
        """
        try:
            import pystac  # noqa: PLC0415
        except ImportError as e:
            msg = "pystac is required for catalog management operations"
            raise ImportError(msg) from e

        catalog = pystac.Catalog(
            id=catalog_id,
            description=description,
            title=title or catalog_id,
        )
        catalog_dict = catalog.to_dict()

        if self._is_remote(path):
            # For remote, POST to endpoint
            req = urllib.request.Request(  # noqa: S310
                path,
                data=json.dumps(catalog_dict).encode("utf-8"),
                headers=self._get_headers(),
                method="POST",
            )
            with urllib.request.urlopen(req) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        else:
            # For local, save to file
            catalog.normalize_hrefs(str(Path(path).parent))
            catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
            return catalog_dict

    def read_catalog(self, path: str) -> dict[str, Any]:
        """Read a STAC Catalog.

        Args:
            path: Path to catalog (local file or remote URL)

        Returns:
            Catalog as dictionary
        """
        try:
            import pystac  # noqa: PLC0415
        except ImportError as e:
            msg = "pystac is required for catalog management operations"
            raise ImportError(msg) from e

        if self._is_remote(path):
            catalog = pystac.Catalog.from_file(path)
        else:
            catalog = pystac.Catalog.from_file(path)
        return catalog.to_dict()

    def update_catalog(
        self,
        path: str,
        catalog_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a STAC Catalog.

        Args:
            path: Path to catalog (local file or remote URL)
            catalog_dict: Updated catalog dictionary

        Returns:
            Updated catalog as dictionary
        """
        try:
            import pystac  # noqa: PLC0415
        except ImportError as e:
            msg = "pystac is required for catalog management operations"
            raise ImportError(msg) from e

        catalog = pystac.Catalog.from_dict(catalog_dict)

        if self._is_remote(path):
            req = urllib.request.Request(  # noqa: S310
                path,
                data=json.dumps(catalog_dict).encode("utf-8"),
                headers=self._get_headers(),
                method="PUT",
            )
            with urllib.request.urlopen(req) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        else:
            catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
            return catalog.to_dict()

    def delete_catalog(self, path: str) -> dict[str, Any]:
        """Delete a STAC Catalog.

        Args:
            path: Path to catalog (local file or remote URL)

        Returns:
            Success message
        """
        self._delete_file(path)
        return {"status": "success", "message": f"Catalog deleted: {path}"}

    def list_catalogs(self, base_path: str) -> list[dict[str, Any]]:
        """List STAC Catalogs in a directory or remote endpoint.

        Args:
            base_path: Base path to search (local directory or remote URL)

        Returns:
            List of catalog dictionaries
        """
        if self._is_remote(base_path):
            # For remote, fetch catalog list from API
            req = urllib.request.Request(  # noqa: S310
                base_path, headers=self._get_headers()
            )
            with urllib.request.urlopen(req) as response:  # noqa: S310
                data = json.loads(response.read().decode("utf-8"))
                # Handle different API responses
                if "catalogs" in data:
                    return data["catalogs"]
                if "links" in data:
                    # Extract child catalogs from links
                    return [
                        link
                        for link in data["links"]
                        if link.get("rel") in ("child", "catalog")
                    ]
                return [data]
        else:
            # For local, scan directory for catalog.json files
            catalogs = []
            base = Path(base_path)
            if base.is_dir():
                for catalog_file in base.rglob("catalog.json"):
                    try:
                        catalogs.append(self.read_catalog(str(catalog_file)))
                    except Exception as e:  # noqa: BLE001
                        logger.warning("Failed to read catalog %s: %s", catalog_file, e)
            return catalogs

    # ======================== Collection Operations ========================

    def create_collection(
        self,
        path: str,
        collection_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new STAC Collection.

        Args:
            path: Path to save collection (local file or remote URL)
            collection_dict: Collection dictionary following STAC spec

        Returns:
            Created collection as dictionary
        """
        try:
            import pystac  # noqa: PLC0415
        except ImportError as e:
            msg = "pystac is required for collection management operations"
            raise ImportError(msg) from e

        collection = pystac.Collection.from_dict(collection_dict)

        if self._is_remote(path):
            req = urllib.request.Request(  # noqa: S310
                path,
                data=json.dumps(collection_dict).encode("utf-8"),
                headers=self._get_headers(),
                method="POST",
            )
            with urllib.request.urlopen(req) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        else:
            collection.normalize_hrefs(str(Path(path).parent))
            collection.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
            return collection.to_dict()

    def read_collection(self, path: str) -> dict[str, Any]:
        """Read a STAC Collection.

        Args:
            path: Path to collection (local file or remote URL)

        Returns:
            Collection as dictionary
        """
        try:
            import pystac  # noqa: PLC0415
        except ImportError as e:
            msg = "pystac is required for collection management operations"
            raise ImportError(msg) from e

        collection = pystac.Collection.from_file(path)
        return collection.to_dict()

    def update_collection(
        self,
        path: str,
        collection_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a STAC Collection.

        Args:
            path: Path to collection (local file or remote URL)
            collection_dict: Updated collection dictionary

        Returns:
            Updated collection as dictionary
        """
        try:
            import pystac  # noqa: PLC0415
        except ImportError as e:
            msg = "pystac is required for collection management operations"
            raise ImportError(msg) from e

        collection = pystac.Collection.from_dict(collection_dict)

        if self._is_remote(path):
            req = urllib.request.Request(  # noqa: S310
                path,
                data=json.dumps(collection_dict).encode("utf-8"),
                headers=self._get_headers(),
                method="PUT",
            )
            with urllib.request.urlopen(req) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        else:
            collection.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
            return collection.to_dict()

    def delete_collection(self, path: str) -> dict[str, Any]:
        """Delete a STAC Collection.

        Args:
            path: Path to collection (local file or remote URL)

        Returns:
            Success message
        """
        self._delete_file(path)
        return {"status": "success", "message": f"Collection deleted: {path}"}

    def list_collections(self, base_path: str) -> list[dict[str, Any]]:
        """List STAC Collections in a catalog or remote endpoint.

        Args:
            base_path: Base path to search (local directory or remote URL)

        Returns:
            List of collection dictionaries
        """
        if self._is_remote(base_path):
            # For remote, fetch collections from API
            req = urllib.request.Request(  # noqa: S310
                base_path, headers=self._get_headers()
            )
            with urllib.request.urlopen(req) as response:  # noqa: S310
                data = json.loads(response.read().decode("utf-8"))
                if "collections" in data:
                    return data["collections"]
                return [data]
        else:
            # For local, scan directory for collection.json files
            collections = []
            base = Path(base_path)
            if base.is_dir():
                for collection_file in base.rglob("collection.json"):
                    try:
                        collections.append(self.read_collection(str(collection_file)))
                    except Exception as e:  # noqa: BLE001
                        logger.warning(
                            "Failed to read collection %s: %s", collection_file, e
                        )
            return collections

    # ======================== Item Operations ========================

    def create_item(
        self,
        path: str,
        item_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new STAC Item.

        Args:
            path: Path to save item (local file or remote URL)
            item_dict: Item dictionary following STAC spec

        Returns:
            Created item as dictionary
        """
        try:
            import pystac  # noqa: PLC0415
        except ImportError as e:
            msg = "pystac is required for item management operations"
            raise ImportError(msg) from e

        item = pystac.Item.from_dict(item_dict)

        if self._is_remote(path):
            req = urllib.request.Request(  # noqa: S310
                path,
                data=json.dumps(item_dict).encode("utf-8"),
                headers=self._get_headers(),
                method="POST",
            )
            with urllib.request.urlopen(req) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        else:
            item.save_object(dest_href=path)
            return item.to_dict()

    def read_item(self, path: str) -> dict[str, Any]:
        """Read a STAC Item.

        Args:
            path: Path to item (local file or remote URL)

        Returns:
            Item as dictionary
        """
        try:
            import pystac  # noqa: PLC0415
        except ImportError as e:
            msg = "pystac is required for item management operations"
            raise ImportError(msg) from e

        item = pystac.Item.from_file(path)
        return item.to_dict()

    def update_item(
        self,
        path: str,
        item_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a STAC Item.

        Args:
            path: Path to item (local file or remote URL)
            item_dict: Updated item dictionary

        Returns:
            Updated item as dictionary
        """
        try:
            import pystac  # noqa: PLC0415
        except ImportError as e:
            msg = "pystac is required for item management operations"
            raise ImportError(msg) from e

        item = pystac.Item.from_dict(item_dict)

        if self._is_remote(path):
            req = urllib.request.Request(  # noqa: S310
                path,
                data=json.dumps(item_dict).encode("utf-8"),
                headers=self._get_headers(),
                method="PUT",
            )
            with urllib.request.urlopen(req) as response:  # noqa: S310
                return json.loads(response.read().decode("utf-8"))
        else:
            item.save_object(dest_href=path)
            return item.to_dict()

    def delete_item(self, path: str) -> dict[str, Any]:
        """Delete a STAC Item.

        Args:
            path: Path to item (local file or remote URL)

        Returns:
            Success message
        """
        self._delete_file(path)
        return {"status": "success", "message": f"Item deleted: {path}"}

    def list_items(self, base_path: str) -> list[dict[str, Any]]:
        """List STAC Items in a collection or remote endpoint.

        Args:
            base_path: Base path to search (local directory or remote URL)

        Returns:
            List of item dictionaries
        """
        if self._is_remote(base_path):
            # For remote, fetch items from API
            req = urllib.request.Request(  # noqa: S310
                base_path, headers=self._get_headers()
            )
            with urllib.request.urlopen(req) as response:  # noqa: S310
                data = json.loads(response.read().decode("utf-8"))
                if "features" in data:
                    return data["features"]
                if "items" in data:
                    return data["items"]
                return [data]
        else:
            # For local, scan directory for item JSON files
            items = []
            base = Path(base_path)
            if base.is_dir():
                # Look for .json files that are not catalog.json or collection.json
                for item_file in base.rglob("*.json"):
                    if item_file.name not in ("catalog.json", "collection.json"):
                        try:
                            items.append(self.read_item(str(item_file)))
                        except Exception as e:  # noqa: BLE001
                            logger.warning("Failed to read item %s: %s", item_file, e)
            return items


# Global instance for convenience
pystac_manager = PySTACManager()
