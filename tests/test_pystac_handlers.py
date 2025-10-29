from pathlib import Path

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
def temp_catalog_dir(tmp_path):
    """Create a temporary directory for a STAC catalog."""
    return tmp_path / "catalog"


@pytest.fixture
def manager(temp_catalog_dir):
    """Create a CRUDL manager for a temporary catalog directory."""
    return CRUDL(base_path=str(temp_catalog_dir))


def test_handle_create_catalog(manager, temp_catalog_dir):
    """Test creating a catalog via handler."""
    catalog_path = str(temp_catalog_dir / "catalog.json")
    arguments = {
        "path": catalog_path,
        "catalog_id": "test-catalog",
        "description": "description",
    }
    result = handle_create_catalog(manager, arguments)
    assert Path(catalog_path).exists()
    assert result["id"] == "test-catalog"


def test_handle_read_catalog(manager, temp_catalog_dir):
    """Test reading a catalog via handler."""
    catalog_path = str(temp_catalog_dir / "catalog.json")
    handle_create_catalog(
        manager,
        {
            "path": catalog_path,
            "catalog_id": "test-catalog",
            "description": "description",
        },
    )
    result = handle_read_catalog(manager, {"path": catalog_path})
    assert result["id"] == "test-catalog"


def test_handle_update_catalog(manager, temp_catalog_dir):
    """Test updating a catalog via handler."""
    catalog_path = str(temp_catalog_dir / "catalog.json")
    handle_create_catalog(
        manager,
        {
            "path": catalog_path,
            "catalog_id": "test-catalog",
            "description": "initial",
        },
    )
    updated_catalog = {
        "id": "test-catalog",
        "stac_version": "1.0.0",
        "description": "updated",
        "links": [],
        "type": "Catalog",
    }
    result = handle_update_catalog(
        manager, {"path": catalog_path, "catalog": updated_catalog}
    )
    assert result["description"] == "updated"


def test_handle_delete_catalog(manager, temp_catalog_dir):
    """Test deleting a catalog via handler."""
    catalog_path = str(temp_catalog_dir / "catalog.json")
    handle_create_catalog(
        manager,
        {
            "path": catalog_path,
            "catalog_id": "test-catalog",
            "description": "description",
        },
    )
    assert Path(catalog_path).exists()
    handle_delete_catalog(manager, {"path": catalog_path})
    assert not Path(catalog_path).exists()


def test_handle_list_catalogs(manager, temp_catalog_dir):
    """Test listing catalogs via handler."""
    temp_catalog_dir.mkdir(exist_ok=True)
    (temp_catalog_dir / "cat1").mkdir()
    (temp_catalog_dir / "cat2").mkdir()
    handle_create_catalog(
        manager,
        {
            "path": str(temp_catalog_dir / "cat1" / "catalog.json"),
            "catalog_id": "cat1",
            "description": "desc1",
        },
    )
    handle_create_catalog(
        manager,
        {
            "path": str(temp_catalog_dir / "cat2" / "catalog.json"),
            "catalog_id": "cat2",
            "description": "desc2",
        },
    )
    result = handle_list_catalogs(manager, {"base_path": str(temp_catalog_dir)})
    expected_num_catalogs = 2
    assert result["count"] == expected_num_catalogs
    assert {c["id"] for c in result["catalogs"]} == {"cat1", "cat2"}


def test_handle_create_collection(manager, temp_catalog_dir):
    """Test creating a collection via handler."""
    collection_path = str(temp_catalog_dir / "collection.json")
    collection_dict = {
        "id": "test-collection",
        "stac_version": "1.0.0",
        "description": "A test collection",
        "license": "CC0-1.0",
        "extent": {
            "spatial": {"bbox": [[-180, -90, 180, 90]]},
            "temporal": {"interval": [["2024-01-01T00:00:00Z", None]]},
        },
        "links": [],
        "type": "Collection",
    }
    result = handle_create_collection(
        manager, {"path": collection_path, "collection": collection_dict}
    )
    assert Path(collection_path).exists()
    assert result["id"] == "test-collection"


def test_handle_read_collection(manager, temp_catalog_dir):
    """Test reading a collection via handler."""
    collection_path = str(temp_catalog_dir / "collection.json")
    collection_dict = {
        "id": "test-collection",
        "stac_version": "1.0.0",
        "description": "A test collection",
        "license": "CC0-1.0",
        "extent": {
            "spatial": {"bbox": [[-180, -90, 180, 90]]},
            "temporal": {"interval": [["2024-01-01T00:00:00Z", None]]},
        },
        "links": [],
        "type": "Collection",
    }
    handle_create_collection(
        manager, {"path": collection_path, "collection": collection_dict}
    )
    result = handle_read_collection(manager, {"path": collection_path})
    assert result["id"] == "test-collection"
