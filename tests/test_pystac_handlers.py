"""Tests for pystac-based CRUDL operations."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from stac_mcp.tools.crudl import CRUDL
from stac_mcp.tools.pystac_handlers import (
    handle_create_catalog,
    handle_create_collection,
    handle_create_item,
    handle_delete_catalog,
    handle_delete_collection,
    handle_delete_item,
    handle_list_catalogs,
    handle_list_collections,
    handle_list_items,
    handle_read_catalog,
    handle_read_collection,
    handle_read_item,
    handle_update_catalog,
    handle_update_collection,
    handle_update_item,
)


@pytest.fixture
def crudl_manager():
    """Create a CRUDL instance for testing."""
    return CRUDL(catalog_url="https://example.com/catalog.json")


def test_handle_create_catalog(crudl_manager):
    """Test handle_create_catalog."""
    with patch.object(crudl_manager, "create_catalog") as mock_create_catalog:
        handle_create_catalog(
            crudl_manager,
            {
                "catalog_id": "test-catalog",
                "description": "Test catalog",
                "title": "Test Catalog",
            },
        )
        mock_create_catalog.assert_called_once_with(
            "https://example.com/catalogs",
            "test-catalog",
            "Test catalog",
            "Test Catalog",
        )


def test_handle_read_catalog(crudl_manager):
    """Test handle_read_catalog."""
    with patch.object(crudl_manager, "read_catalog") as mock_read_catalog:
        handle_read_catalog(crudl_manager, {"catalog_id": "test-catalog"})
        mock_read_catalog.assert_called_once_with(
            "https://example.com/catalogs/test-catalog"
        )


def test_handle_update_catalog(crudl_manager):
    """Test handle_update_catalog."""
    with patch.object(crudl_manager, "update_catalog") as mock_update_catalog:
        handle_update_catalog(
            crudl_manager,
            {"catalog_id": "test-catalog", "catalog": {"description": "new"}},
        )
        mock_update_catalog.assert_called_once_with(
            "https://example.com/catalogs/test-catalog", {"description": "new"}
        )


def test_handle_delete_catalog(crudl_manager):
    """Test handle_delete_catalog."""
    with patch.object(crudl_manager, "delete_catalog") as mock_delete_catalog:
        handle_delete_catalog(crudl_manager, {"catalog_id": "test-catalog"})
        mock_delete_catalog.assert_called_once_with(
            "https://example.com/catalogs/test-catalog"
        )


def test_handle_list_catalogs(crudl_manager):
    """Test handle_list_catalogs."""
    with patch.object(crudl_manager, "list_catalogs") as mock_list_catalogs:
        handle_list_catalogs(crudl_manager, {})
        mock_list_catalogs.assert_called_once_with("https://example.com/catalogs")


def test_handle_create_collection(crudl_manager):
    """Test handle_create_collection."""
    with patch.object(crudl_manager, "create_collection") as mock_create_collection:
        handle_create_collection(crudl_manager, {"collection": {"id": "test"}})
        mock_create_collection.assert_called_once_with(
            "https://example.com/collections", {"id": "test"}
        )


def test_handle_read_collection(crudl_manager):
    """Test handle_read_collection."""
    with patch.object(crudl_manager, "read_collection") as mock_read_collection:
        handle_read_collection(crudl_manager, {"collection_id": "test-collection"})
        mock_read_collection.assert_called_once_with(
            "https://example.com/collections/test-collection"
        )


def test_handle_update_collection(crudl_manager):
    """Test handle_update_collection."""
    with patch.object(crudl_manager, "update_collection") as mock_update_collection:
        handle_update_collection(crudl_manager, {"collection": {"id": "test"}})
        mock_update_collection.assert_called_once_with(
            "https://example.com/collections", {"id": "test"}
        )


def test_handle_delete_collection(crudl_manager):
    """Test handle_delete_collection."""
    with patch.object(crudl_manager, "delete_collection") as mock_delete_collection:
        handle_delete_collection(crudl_manager, {"collection_id": "test-collection"})
        mock_delete_collection.assert_called_once_with(
            "https://example.com/collections/test-collection"
        )


def test_handle_list_collections(crudl_manager):
    """Test handle_list_collections."""
    with patch.object(crudl_manager, "list_collections") as mock_list_collections:
        handle_list_collections(crudl_manager, {})
        mock_list_collections.assert_called_once_with("https://example.com/collections")


def test_handle_create_item(crudl_manager):
    """Test handle_create_item."""
    with patch.object(crudl_manager, "create_item") as mock_create_item:
        handle_create_item(
            crudl_manager,
            {"collection_id": "test-collection", "item": {"id": "test"}},
        )
        mock_create_item.assert_called_once_with(
            "https://example.com/collections/test-collection/items", {"id": "test"}
        )


def test_handle_read_item(crudl_manager):
    """Test handle_read_item."""
    with patch.object(crudl_manager, "read_item") as mock_read_item:
        handle_read_item(
            crudl_manager, {"collection_id": "test-collection", "item_id": "test-item"}
        )
        mock_read_item.assert_called_once_with(
            "https://example.com/collections/test-collection/items/test-item"
        )


def test_handle_update_item(crudl_manager):
    """Test handle_update_item."""
    with patch.object(crudl_manager, "update_item") as mock_update_item:
        handle_update_item(
            crudl_manager,
            {
                "item": {
                    "id": "test-item",
                    "collection": "test-collection",
                }
            },
        )
        mock_update_item.assert_called_once_with(
            "https://example.com/collections/test-collection/items/test-item",
            {"id": "test-item", "collection": "test-collection"},
        )


def test_handle_delete_item(crudl_manager):
    """Test handle_delete_item."""
    with patch.object(crudl_manager, "delete_item") as mock_delete_item:
        handle_delete_item(
            crudl_manager, {"collection_id": "test-collection", "item_id": "test-item"}
        )
        mock_delete_item.assert_called_once_with(
            "https://example.com/collections/test-collection/items/test-item"
        )


def test_handle_list_items(crudl_manager):
    """Test handle_list_items."""
    with patch.object(crudl_manager, "list_items") as mock_list_items:
        handle_list_items(crudl_manager, {"collection_id": "test-collection"})
        mock_list_items.assert_called_once_with(
            "https://example.com/collections/test-collection/items"
        )
