"""Tests for pystac-based CRUDL tool handlers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from stac_mcp.tools.pystac_handlers import (
    handle_pystac_create_catalog,
    handle_pystac_create_collection,
    handle_pystac_create_item,
    handle_pystac_delete_catalog,
    handle_pystac_delete_collection,
    handle_pystac_delete_item,
    handle_pystac_list_catalogs,
    handle_pystac_list_collections,
    handle_pystac_list_items,
    handle_pystac_read_catalog,
    handle_pystac_read_collection,
    handle_pystac_read_item,
    handle_pystac_update_catalog,
    handle_pystac_update_collection,
    handle_pystac_update_item,
)


@pytest.fixture
def pystac_manager():
    """Create a mock PySTACManager for testing."""
    return MagicMock()


# ======================== Catalog Handler Tests ========================


def test_handle_pystac_create_catalog(pystac_manager):
    """Test create catalog handler."""

    pystac_manager.create_catalog.return_value = {"id": "test-catalog"}

    arguments = {
        "path": "/path/to/catalog.json",
        "catalog_id": "test-catalog",
        "description": "Test catalog",
        "title": "Test Catalog",
    }

    result = handle_pystac_create_catalog(pystac_manager, arguments)

    assert result == {"id": "test-catalog"}
    pystac_manager.create_catalog.assert_called_once_with(
        "/path/to/catalog.json",
        "test-catalog",
        "Test catalog",
        "Test Catalog",
    )


def test_handle_pystac_read_catalog(pystac_manager):
    """Test read catalog handler."""

    pystac_manager.read_catalog.return_value = {"id": "test-catalog"}

    arguments = {"path": "/path/to/catalog.json"}

    result = handle_pystac_read_catalog(pystac_manager, arguments)

    assert result == {"id": "test-catalog"}
    pystac_manager.read_catalog.assert_called_once_with("/path/to/catalog.json")


def test_handle_pystac_update_catalog(pystac_manager):
    """Test update catalog handler."""

    catalog_dict = {"id": "test-catalog", "description": "Updated"}
    pystac_manager.update_catalog.return_value = catalog_dict

    arguments = {
        "path": "/path/to/catalog.json",
        "catalog": catalog_dict,
    }

    result = handle_pystac_update_catalog(pystac_manager, arguments)

    assert result == catalog_dict
    pystac_manager.update_catalog.assert_called_once_with(
        "/path/to/catalog.json", catalog_dict
    )


def test_handle_pystac_delete_catalog(pystac_manager):
    """Test delete catalog handler."""

    pystac_manager.delete_catalog.return_value = {"status": "success"}

    arguments = {"path": "/path/to/catalog.json"}

    result = handle_pystac_delete_catalog(pystac_manager, arguments)

    assert result == {"status": "success"}
    pystac_manager.delete_catalog.assert_called_once_with("/path/to/catalog.json")


def test_handle_pystac_list_catalogs(pystac_manager):
    """Test list catalogs handler."""

    catalogs = [{"id": "catalog1"}, {"id": "catalog2"}]
    pystac_manager.list_catalogs.return_value = catalogs

    arguments = {"base_path": "/path/to/catalogs"}

    result = handle_pystac_list_catalogs(pystac_manager, arguments)

    assert result["catalogs"] == catalogs
    assert result["count"] == len(catalogs)
    pystac_manager.list_catalogs.assert_called_once_with("/path/to/catalogs")


# ======================== Collection Handler Tests ========================


def test_handle_pystac_create_collection(pystac_manager):
    """Test create collection handler."""

    collection_dict = {"id": "test-collection"}
    pystac_manager.create_collection.return_value = collection_dict

    arguments = {
        "path": "/path/to/collection.json",
        "collection": collection_dict,
    }

    result = handle_pystac_create_collection(pystac_manager, arguments)

    assert result == collection_dict
    pystac_manager.create_collection.assert_called_once_with(
        "/path/to/collection.json", collection_dict
    )


def test_handle_pystac_read_collection(pystac_manager):
    """Test read collection handler."""

    pystac_manager.read_collection.return_value = {"id": "test-collection"}

    arguments = {"path": "/path/to/collection.json"}

    result = handle_pystac_read_collection(pystac_manager, arguments)

    assert result == {"id": "test-collection"}
    pystac_manager.read_collection.assert_called_once_with("/path/to/collection.json")


def test_handle_pystac_update_collection(pystac_manager):
    """Test update collection handler."""

    collection_dict = {"id": "test-collection", "description": "Updated"}
    pystac_manager.update_collection.return_value = collection_dict

    arguments = {
        "path": "/path/to/collection.json",
        "collection": collection_dict,
    }

    result = handle_pystac_update_collection(pystac_manager, arguments)

    assert result == collection_dict
    pystac_manager.update_collection.assert_called_once_with(
        "/path/to/collection.json", collection_dict
    )


def test_handle_pystac_delete_collection(pystac_manager):
    """Test delete collection handler."""

    pystac_manager.delete_collection.return_value = {"status": "success"}

    arguments = {"path": "/path/to/collection.json"}

    result = handle_pystac_delete_collection(pystac_manager, arguments)

    assert result == {"status": "success"}
    pystac_manager.delete_collection.assert_called_once_with("/path/to/collection.json")


def test_handle_pystac_list_collections(pystac_manager):
    """Test list collections handler."""

    collections = [{"id": "collection1"}, {"id": "collection2"}]
    pystac_manager.list_collections.return_value = collections

    arguments = {"base_path": "/path/to/collections"}

    result = handle_pystac_list_collections(pystac_manager, arguments)

    assert result["collections"] == collections
    assert result["count"] == len(collections)
    pystac_manager.list_collections.assert_called_once_with("/path/to/collections")


# ======================== Item Handler Tests ========================


def test_handle_pystac_create_item(pystac_manager):
    """Test create item handler."""

    item_dict = {"id": "test-item"}
    pystac_manager.create_item.return_value = item_dict

    arguments = {
        "path": "/path/to/item.json",
        "item": item_dict,
    }

    result = handle_pystac_create_item(pystac_manager, arguments)

    assert result == item_dict
    pystac_manager.create_item.assert_called_once_with("/path/to/item.json", item_dict)


def test_handle_pystac_read_item(pystac_manager):
    """Test read item handler."""

    pystac_manager.read_item.return_value = {"id": "test-item"}

    arguments = {"path": "/path/to/item.json"}

    result = handle_pystac_read_item(pystac_manager, arguments)

    assert result == {"id": "test-item"}
    pystac_manager.read_item.assert_called_once_with("/path/to/item.json")


def test_handle_pystac_update_item(pystac_manager):
    """Test update item handler."""

    item_dict = {"id": "test-item", "properties": {"updated": True}}
    pystac_manager.update_item.return_value = item_dict

    arguments = {
        "path": "/path/to/item.json",
        "item": item_dict,
    }

    result = handle_pystac_update_item(pystac_manager, arguments)

    assert result == item_dict
    pystac_manager.update_item.assert_called_once_with("/path/to/item.json", item_dict)


def test_handle_pystac_delete_item(pystac_manager):
    """Test delete item handler."""

    pystac_manager.delete_item.return_value = {"status": "success"}

    arguments = {"path": "/path/to/item.json"}

    result = handle_pystac_delete_item(pystac_manager, arguments)

    assert result == {"status": "success"}
    pystac_manager.delete_item.assert_called_once_with("/path/to/item.json")


def test_handle_pystac_list_items(pystac_manager):
    """Test list items handler."""

    items = [{"id": "item1"}, {"id": "item2"}]
    pystac_manager.list_items.return_value = items

    arguments = {"base_path": "/path/to/items"}

    result = handle_pystac_list_items(pystac_manager, arguments)

    assert result["items"] == items
    assert result["count"] == len(items)
    pystac_manager.list_items.assert_called_once_with("/path/to/items")
