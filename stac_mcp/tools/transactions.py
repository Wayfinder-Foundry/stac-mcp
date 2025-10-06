"""Tool handlers for STAC Transaction operations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from stac_mcp.tools.client import STACClient


def handle_create_item(
    client: STACClient,
    arguments: dict[str, Any],
) -> dict[str, Any] | None:
    """Handle creating a STAC Item."""
    collection_id = arguments["collection_id"]
    item = arguments["item"]
    return client.create_item(collection_id, item)


def handle_update_item(
    client: STACClient,
    arguments: dict[str, Any],
) -> dict[str, Any] | None:
    """Handle updating a STAC Item."""
    item = arguments["item"]
    return client.update_item(item)


def handle_delete_item(
    client: STACClient,
    arguments: dict[str, Any],
) -> dict[str, Any] | None:
    """Handle deleting a STAC Item."""
    collection_id = arguments["collection_id"]
    item_id = arguments["item_id"]
    return client.delete_item(collection_id, item_id)


def handle_create_collection(
    client: STACClient,
    arguments: dict[str, Any],
) -> dict[str, Any] | None:
    """Handle creating a STAC Collection."""
    collection = arguments["collection"]
    return client.create_collection(collection)


def handle_update_collection(
    client: STACClient,
    arguments: dict[str, Any],
) -> dict[str, Any] | None:
    """Handle updating a STAC Collection."""
    collection = arguments["collection"]
    return client.update_collection(collection)


def handle_delete_collection(
    client: STACClient,
    arguments: dict[str, Any],
) -> dict[str, Any] | None:
    """Handle deleting a STAC Collection."""
    collection_id = arguments["collection_id"]
    return client.delete_collection(collection_id)
