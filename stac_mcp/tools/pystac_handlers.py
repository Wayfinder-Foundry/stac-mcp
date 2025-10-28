"""Tool handlers for pystac-based CRUDL operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from stac_mcp.tools.crudl import CRUDL


# ======================== Catalog Handlers ========================


def handle_create_catalog(
    manager: CRUDL,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle creating a STAC Catalog using pystac."""
    path = arguments.get("path")
    if not path and manager.catalog_url:
        base_url = manager.catalog_url.replace("catalog.json", "").rstrip("/")
        path = f"{base_url}/catalogs"
    catalog_id = arguments["catalog_id"]
    description = arguments["description"]
    title = arguments.get("title")
    return manager.create_catalog(path, catalog_id, description, title)


def handle_read_catalog(
    manager: CRUDL,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle reading a STAC Catalog using pystac."""
    path = arguments.get("path")
    if not path and manager.catalog_url:
        base_url = manager.catalog_url.replace("catalog.json", "").rstrip("/")
        catalog_id = arguments["catalog_id"]
        path = f"{base_url}/catalogs/{catalog_id}"
    return manager.read_catalog(path)


def handle_update_catalog(
    manager: CRUDL,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle updating a STAC Catalog using pystac."""
    path = arguments.get("path")
    if not path and manager.catalog_url:
        base_url = manager.catalog_url.replace("catalog.json", "").rstrip("/")
        catalog_id = arguments["catalog_id"]
        path = f"{base_url}/catalogs/{catalog_id}"
    catalog = arguments["catalog"]
    return manager.update_catalog(path, catalog)


def handle_delete_catalog(
    manager: CRUDL,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle deleting a STAC Catalog using pystac."""
    path = arguments.get("path")
    if not path and manager.catalog_url:
        base_url = manager.catalog_url.replace("catalog.json", "").rstrip("/")
        catalog_id = arguments["catalog_id"]
        path = f"{base_url}/catalogs/{catalog_id}"
    return manager.delete_catalog(path)


def handle_list_catalogs(
    manager: CRUDL,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle listing STAC Catalogs using pystac."""
    base_path = arguments.get("base_path")
    if not base_path and manager.catalog_url:
        base_url = manager.catalog_url.replace("catalog.json", "").rstrip("/")
        base_path = f"{base_url}/catalogs"
    catalogs = manager.list_catalogs(base_path)
    return {"catalogs": catalogs, "count": len(catalogs)}


# ======================== Collection Handlers ========================


def handle_create_collection(
    manager: CRUDL,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle creating a STAC Collection using pystac."""
    path = arguments.get("path")
    if not path and manager.catalog_url:
        base_url = manager.catalog_url.replace("catalog.json", "").rstrip("/")
        path = f"{base_url}/collections"
    collection = arguments["collection"]
    return manager.create_collection(path, collection)


def handle_read_collection(
    manager: CRUDL,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle reading a STAC Collection using pystac."""
    path = arguments.get("path")
    if not path and manager.catalog_url:
        base_url = manager.catalog_url.replace("catalog.json", "").rstrip("/")
        collection_id = arguments["collection_id"]
        path = f"{base_url}/collections/{collection_id}"
    return manager.read_collection(path)


def handle_update_collection(
    manager: CRUDL,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle updating a STAC Collection using pystac."""
    path = arguments.get("path")
    if not path and manager.catalog_url:
        base_url = manager.catalog_url.replace("catalog.json", "").rstrip("/")
        path = f"{base_url}/collections"
    collection = arguments["collection"]
    return manager.update_collection(path, collection)


def handle_delete_collection(
    manager: CRUDL,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle deleting a STAC Collection using pystac."""
    path = arguments.get("path")
    if not path and manager.catalog_url:
        base_url = manager.catalog_url.replace("catalog.json", "").rstrip("/")
        collection_id = arguments["collection_id"]
        path = f"{base_url}/collections/{collection_id}"
    return manager.delete_collection(path)


def handle_list_collections(
    manager: CRUDL,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle listing STAC Collections using pystac."""
    base_path = arguments.get("base_path")
    if not base_path and manager.catalog_url:
        base_url = manager.catalog_url.replace("catalog.json", "").rstrip("/")
        base_path = f"{base_url}/collections"
    collections = manager.list_collections(base_path)
    return {"collections": collections, "count": len(collections)}


# ======================== Item Handlers ========================


def handle_create_item(
    manager: CRUDL,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle creating a STAC Item using pystac."""
    path = arguments.get("path")
    if not path and manager.catalog_url:
        base_url = manager.catalog_url.replace("catalog.json", "").rstrip("/")
        collection_id = arguments["collection_id"]
        path = f"{base_url}/collections/{collection_id}/items"
    item = arguments["item"]
    return manager.create_item(path, item)


def handle_read_item(
    manager: CRUDL,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle reading a STAC Item using pystac."""
    path = arguments.get("path")
    if not path and manager.catalog_url:
        base_url = manager.catalog_url.replace("catalog.json", "").rstrip("/")
        collection_id = arguments["collection_id"]
        item_id = arguments["item_id"]
        path = f"{base_url}/collections/{collection_id}/items/{item_id}"
    return manager.read_item(path)


def handle_update_item(
    manager: CRUDL,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle updating a STAC Item using pystac."""
    path = arguments.get("path")
    if not path and manager.catalog_url:
        base_url = manager.catalog_url.replace("catalog.json", "").rstrip("/")
        item = arguments["item"]
        collection_id = item.get("collection")
        item_id = item.get("id")
        path = f"{base_url}/collections/{collection_id}/items/{item_id}"
    item = arguments["item"]
    return manager.update_item(path, item)


def handle_delete_item(
    manager: CRUDL,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle deleting a STAC Item using pystac."""
    path = arguments.get("path")
    if not path and manager.catalog_url:
        base_url = manager.catalog_url.replace("catalog.json", "").rstrip("/")
        collection_id = arguments["collection_id"]
        item_id = arguments["item_id"]
        path = f"{base_url}/collections/{collection_id}/items/{item_id}"
    return manager.delete_item(path)


def handle_list_items(
    manager: CRUDL,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle listing STAC Items using pystac."""
    base_path = arguments.get("base_path")
    if not base_path and manager.catalog_url:
        base_url = manager.catalog_url.replace("catalog.json", "").rstrip("/")
        collection_id = arguments["collection_id"]
        base_path = f"{base_url}/collections/{collection_id}/items"
    items = manager.list_items(base_path)
    return {"items": items, "count": len(items)}
