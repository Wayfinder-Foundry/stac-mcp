"""Tool handlers for pystac-based CRUDL operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from stac_mcp.tools.pystac_management import PySTACManager


# ======================== Catalog Handlers ========================


def handle_pystac_create_catalog(
    manager: PySTACManager,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle creating a STAC Catalog using pystac."""
    path = arguments["path"]
    catalog_id = arguments["catalog_id"]
    description = arguments["description"]
    title = arguments.get("title")
    return manager.create_catalog(path, catalog_id, description, title)


def handle_pystac_read_catalog(
    manager: PySTACManager,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle reading a STAC Catalog using pystac."""
    path = arguments["path"]
    return manager.read_catalog(path)


def handle_pystac_update_catalog(
    manager: PySTACManager,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle updating a STAC Catalog using pystac."""
    path = arguments["path"]
    catalog = arguments["catalog"]
    return manager.update_catalog(path, catalog)


def handle_pystac_delete_catalog(
    manager: PySTACManager,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle deleting a STAC Catalog using pystac."""
    path = arguments["path"]
    return manager.delete_catalog(path)


def handle_pystac_list_catalogs(
    manager: PySTACManager,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle listing STAC Catalogs using pystac."""
    base_path = arguments["base_path"]
    catalogs = manager.list_catalogs(base_path)
    return {"catalogs": catalogs, "count": len(catalogs)}


# ======================== Collection Handlers ========================


def handle_pystac_create_collection(
    manager: PySTACManager,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle creating a STAC Collection using pystac."""
    path = arguments["path"]
    collection = arguments["collection"]
    return manager.create_collection(path, collection)


def handle_pystac_read_collection(
    manager: PySTACManager,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle reading a STAC Collection using pystac."""
    path = arguments["path"]
    return manager.read_collection(path)


def handle_pystac_update_collection(
    manager: PySTACManager,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle updating a STAC Collection using pystac."""
    path = arguments["path"]
    collection = arguments["collection"]
    return manager.update_collection(path, collection)


def handle_pystac_delete_collection(
    manager: PySTACManager,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle deleting a STAC Collection using pystac."""
    path = arguments["path"]
    return manager.delete_collection(path)


def handle_pystac_list_collections(
    manager: PySTACManager,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle listing STAC Collections using pystac."""
    base_path = arguments["base_path"]
    collections = manager.list_collections(base_path)
    return {"collections": collections, "count": len(collections)}


# ======================== Item Handlers ========================


def handle_pystac_create_item(
    manager: PySTACManager,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle creating a STAC Item using pystac."""
    path = arguments["path"]
    item = arguments["item"]
    return manager.create_item(path, item)


def handle_pystac_read_item(
    manager: PySTACManager,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle reading a STAC Item using pystac."""
    path = arguments["path"]
    return manager.read_item(path)


def handle_pystac_update_item(
    manager: PySTACManager,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle updating a STAC Item using pystac."""
    path = arguments["path"]
    item = arguments["item"]
    return manager.update_item(path, item)


def handle_pystac_delete_item(
    manager: PySTACManager,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle deleting a STAC Item using pystac."""
    path = arguments["path"]
    return manager.delete_item(path)


def handle_pystac_list_items(
    manager: PySTACManager,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle listing STAC Items using pystac."""
    base_path = arguments["base_path"]
    items = manager.list_items(base_path)
    return {"items": items, "count": len(items)}
