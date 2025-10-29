import json
from pathlib import Path

import pytest

from stac_mcp.tools.crudl import CRUDL


@pytest.fixture
def temp_catalog_dir(tmp_path):
    """Create a temporary directory for a STAC catalog."""
    return tmp_path / "catalog"


def test_create_catalog(temp_catalog_dir):
    """Test creating a local STAC catalog."""
    manager = CRUDL(base_path=str(temp_catalog_dir))
    catalog_path = str(temp_catalog_dir / "catalog.json")
    catalog_id = "test-catalog"
    description = "A test catalog"
    title = "Test Catalog"

    result = manager.create_catalog(catalog_path, catalog_id, description, title)

    assert Path(catalog_path).exists()
    with Path(catalog_path).open("r") as f:
        data = json.load(f)
    assert data["id"] == catalog_id
    assert data["description"] == description
    assert data["title"] == title
    assert result["id"] == catalog_id


def test_read_catalog(temp_catalog_dir):
    """Test reading a local STAC catalog."""
    manager = CRUDL(base_path=str(temp_catalog_dir))
    catalog_path = str(temp_catalog_dir / "catalog.json")
    catalog_id = "test-catalog"
    description = "A test catalog"
    manager.create_catalog(catalog_path, catalog_id, description)

    result = manager.read_catalog(catalog_path)
    assert result["id"] == catalog_id


def test_update_catalog(temp_catalog_dir):
    """Test updating a local STAC catalog."""
    manager = CRUDL(base_path=str(temp_catalog_dir))
    catalog_path = str(temp_catalog_dir / "catalog.json")
    catalog_id = "test-catalog"
    description = "Initial description"
    manager.create_catalog(catalog_path, catalog_id, description)

    updated_catalog_dict = {
        "id": catalog_id,
        "stac_version": "1.0.0",
        "description": "Updated description",
        "links": [],
        "type": "Catalog",
    }
    result = manager.update_catalog(catalog_path, updated_catalog_dict)
    assert result["description"] == "Updated description"

    with Path(catalog_path).open("r") as f:
        data = json.load(f)
    assert data["description"] == "Updated description"


def test_delete_catalog(temp_catalog_dir):
    """Test deleting a local STAC catalog."""
    manager = CRUDL(base_path=str(temp_catalog_dir))
    catalog_path = str(temp_catalog_dir / "catalog.json")
    manager.create_catalog(catalog_path, "test-catalog", "description")

    assert Path(catalog_path).exists()
    manager.delete_catalog(catalog_path)
    assert not Path(catalog_path).exists()


def test_list_catalogs(temp_catalog_dir):
    """Test listing local STAC catalogs."""
    manager = CRUDL(base_path=str(temp_catalog_dir))
    temp_catalog_dir.mkdir(exist_ok=True)
    (temp_catalog_dir / "cat1").mkdir()
    (temp_catalog_dir / "cat2").mkdir()
    manager.create_catalog(
        str(temp_catalog_dir / "cat1" / "catalog.json"), "cat1", "desc1"
    )
    manager.create_catalog(
        str(temp_catalog_dir / "cat2" / "catalog.json"), "cat2", "desc2"
    )

    catalogs = manager.list_catalogs(str(temp_catalog_dir))
    expected_num_catalogs = 2
    assert len(catalogs) == expected_num_catalogs
    assert {c["id"] for c in catalogs} == {"cat1", "cat2"}


def test_create_collection(temp_catalog_dir):
    """Test creating a local STAC collection."""
    manager = CRUDL(base_path=str(temp_catalog_dir))
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
    result = manager.create_collection(collection_path, collection_dict)
    assert Path(collection_path).exists()
    assert result["id"] == "test-collection"


def test_read_collection(temp_catalog_dir):
    """Test reading a local STAC collection."""
    manager = CRUDL(base_path=str(temp_catalog_dir))
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
    manager.create_collection(collection_path, collection_dict)
    result = manager.read_collection(collection_path)
    assert result["id"] == "test-collection"


def test_update_collection(temp_catalog_dir):
    """Test updating a local STAC collection."""
    manager = CRUDL(base_path=str(temp_catalog_dir))
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
    manager.create_collection(collection_path, collection_dict)
    collection_dict["description"] = "Updated description"
    result = manager.update_collection(collection_path, collection_dict)
    assert result["description"] == "Updated description"


def test_delete_collection(temp_catalog_dir):
    """Test deleting a local STAC collection."""
    manager = CRUDL(base_path=str(temp_catalog_dir))
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
    manager.create_collection(collection_path, collection_dict)
    assert Path(collection_path).exists()
    manager.delete_collection(collection_path)
    assert not Path(collection_path).exists()


def test_list_collections(temp_catalog_dir):
    """Test listing local STAC collections."""
    manager = CRUDL(base_path=str(temp_catalog_dir))
    temp_catalog_dir.mkdir(exist_ok=True)
    (temp_catalog_dir / "col1").mkdir()
    (temp_catalog_dir / "col2").mkdir()
    collection_dict1 = {
        "id": "col1",
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
    collection_dict2 = {
        "id": "col2",
        "stac_version": "1.0.0",
        "description": "Another test collection",
        "license": "CC0-1.0",
        "extent": {
            "spatial": {"bbox": [[-180, -90, 180, 90]]},
            "temporal": {"interval": [["2024-01-01T00:00:00Z", None]]},
        },
        "links": [],
        "type": "Collection",
    }
    manager.create_collection(
        str(temp_catalog_dir / "col1" / "collection.json"), collection_dict1
    )
    manager.create_collection(
        str(temp_catalog_dir / "col2" / "collection.json"), collection_dict2
    )

    collections = manager.list_collections(str(temp_catalog_dir))
    expected_num_collections = 2
    assert len(collections) == expected_num_collections
    assert {c["id"] for c in collections} == {"col1", "col2"}
