"""A unified class for STAC transactional operations."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CRUDL:
    """A unified interface for all transactional operations."""

    def __init__(
        self,
        base_path: str,
    ) -> None:
        """Initialize the CRUDL class."""
        self.base_path = Path(base_path)

    def _read_json_file(self, path: str) -> dict[str, Any]:
        """Read JSON from local file."""
        with Path(path).open("r") as f:
            return json.load(f)

    def _write_json_file(self, path: str, data: dict[str, Any]) -> None:
        """Write JSON to local file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with Path(path).open("w") as f:
            json.dump(data, f, indent=2)

    def _delete_file(self, path: str) -> None:
        """Delete local file."""
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
            path: Path to save catalog
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
        catalog.set_self_href(path)
        catalog.normalize_hrefs(str(Path(path).parent))
        catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
        return catalog.to_dict()

    def read_catalog(self, path: str) -> dict[str, Any]:
        """Read a STAC Catalog.

        Args:
            path: Path to catalog

        Returns:
            Catalog as dictionary
        """
        try:
            import pystac  # noqa: PLC0415
        except ImportError as e:
            msg = "pystac is required for catalog management operations"
            raise ImportError(msg) from e

        catalog = pystac.Catalog.from_file(path)
        return catalog.to_dict()

    def update_catalog(
        self,
        path: str,
        catalog_dict: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a STAC Catalog.

        Args:
            path: Path to catalog
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
        catalog.set_self_href(path)
        catalog.normalize_hrefs(str(Path(path).parent))
        catalog.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
        return catalog.to_dict()

    def delete_catalog(self, path: str) -> dict[str, Any]:
        """Delete a STAC Catalog.

        Args:
            path: Path to catalog

        Returns:
            Success message
        """
        self._delete_file(path)
        return {"status": "success", "message": f"Catalog deleted: {path}"}

    def list_catalogs(self, base_path: str) -> list[dict[str, Any]]:
        """List STAC Catalogs in a directory.

        Args:
            base_path: Base path to search

        Returns:
            List of catalog dictionaries
        """
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
            path: Path to save collection
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
        collection.set_self_href(path)
        collection.normalize_hrefs(str(Path(path).parent))
        collection.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
        return collection.to_dict()

    def read_collection(self, path: str) -> dict[str, Any]:
        """Read a STAC Collection.

        Args:
            path: Path to collection

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
            path: Path to collection
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
        collection.set_self_href(path)
        collection.normalize_hrefs(str(Path(path).parent))
        collection.save(catalog_type=pystac.CatalogType.SELF_CONTAINED)
        return collection.to_dict()

    def delete_collection(self, path: str) -> dict[str, Any]:
        """Delete a STAC Collection.

        Args:
            path: Path to collection

        Returns:
            Success message
        """
        self._delete_file(path)
        return {"status": "success", "message": f"Collection deleted: {path}"}

    def list_collections(self, base_path: str) -> list[dict[str, Any]]:
        """List STAC Collections in a catalog.

        Args:
            base_path: Base path to search

        Returns:
            List of collection dictionaries
        """
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
            path: Path to save item
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
        item.set_self_href(path)
        item.save_object()
        return item.to_dict()

    def read_item(self, path: str) -> dict[str, Any]:
        """Read a STAC Item.

        Args:
            path: Path to item

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
            path: Path to item
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
        item.set_self_href(path)
        item.save_object()
        return item.to_dict()

    def delete_item(self, path: str) -> dict[str, Any]:
        """Delete a STAC Item.

        Args:
            path: Path to item

        Returns:
            Success message
        """
        self._delete_file(path)
        return {"status": "success", "message": f"Item deleted: {path}"}

    def list_items(self, base_path: str) -> list[dict[str, Any]]:
        """List STAC Items in a collection.

        Args:
            base_path: Base path to search

        Returns:
            List of item dictionaries
        """
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
crudl_manager = CRUDL(base_path=".")
