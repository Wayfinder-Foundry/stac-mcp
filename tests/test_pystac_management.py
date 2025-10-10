"""Tests for pystac-based CRUDL operations."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from stac_mcp.tools.pystac_management import PySTACManager


def _get_pystac_from_sys():
    """Get pystac module from sys.modules when mocked."""
    return sys.modules.get("pystac", MagicMock())


@pytest.fixture
def pystac_manager():
    """Create a PySTACManager instance for testing."""

    return PySTACManager()


@pytest.fixture
def pystac_manager_with_key():
    """Create a PySTACManager instance with API key."""

    return PySTACManager(api_key="test-api-key")


@pytest.fixture
def sample_catalog():
    """Sample STAC Catalog for testing."""
    return {
        "type": "Catalog",
        "id": "test-catalog",
        "stac_version": "1.0.0",
        "description": "Test catalog",
        "links": [],
    }


@pytest.fixture
def sample_collection():
    """Sample STAC Collection for testing."""
    return {
        "type": "Collection",
        "id": "test-collection",
        "stac_version": "1.0.0",
        "description": "Test collection",
        "license": "MIT",
        "extent": {
            "spatial": {"bbox": [[-180, -90, 180, 90]]},
            "temporal": {"interval": [[None, None]]},
        },
        "links": [],
    }


@pytest.fixture
def sample_item():
    """Sample STAC Item for testing."""
    return {
        "type": "Feature",
        "stac_version": "1.0.0",
        "id": "test-item",
        "properties": {"datetime": "2023-01-01T00:00:00Z"},
        "geometry": {
            "type": "Point",
            "coordinates": [0.0, 0.0],
        },
        "links": [],
        "assets": {},
    }


# ======================== Catalog Tests ========================


@patch.dict("sys.modules", {"pystac": MagicMock()})
def test_create_catalog_local(pystac_manager, tmp_path):
    """Test creating a local STAC Catalog."""
    mock_catalog = MagicMock()
    mock_catalog.to_dict.return_value = {"id": "test-catalog"}
    sys.modules["pystac"].Catalog.return_value = mock_catalog
    sys.modules["pystac"].CatalogType.SELF_CONTAINED = "SELF_CONTAINED"

    catalog_path = str(tmp_path / "catalog.json")
    result = pystac_manager.create_catalog(
        path=catalog_path,
        catalog_id="test-catalog",
        description="Test catalog",
        title="Test Catalog",
    )

    assert result == {"id": "test-catalog"}
    sys.modules["pystac"].Catalog.assert_called_once_with(
        id="test-catalog",
        description="Test catalog",
        title="Test Catalog",
    )
    mock_catalog.normalize_hrefs.assert_called_once()
    mock_catalog.save.assert_called_once()


@patch("stac_mcp.tools.pystac_management.urllib.request.urlopen")
@patch.dict("sys.modules", {"pystac": MagicMock()})
def test_create_catalog_remote(
    mock_pystac, mock_urlopen, pystac_manager_with_key, sample_catalog
):
    """Test creating a remote STAC Catalog with API key."""
    mock_catalog = MagicMock()
    mock_catalog.to_dict.return_value = sample_catalog
    pystac.Catalog.return_value = mock_catalog

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(sample_catalog).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    result = pystac_manager_with_key.create_catalog(
        path="https://example.com/catalogs",
        catalog_id="test-catalog",
        description="Test catalog",
    )

    mock_pystac.Catalog.assert_called_once_with(
        id="test-catalog",
        description="Test catalog",
        title=None,
    )

    assert result == sample_catalog
    mock_urlopen.assert_called_once()


@patch.dict("sys.modules", {"pystac": MagicMock()})
def test_read_catalog_local(pystac_manager, sample_catalog):
    """Test reading a local STAC Catalog."""
    mock_catalog = MagicMock()
    mock_catalog.to_dict.return_value = sample_catalog
    sys.modules["pystac"].Catalog.from_file.return_value = mock_catalog

    result = pystac_manager.read_catalog("/path/to/catalog.json")

    assert result == sample_catalog
    sys.modules["pystac"].Catalog.from_file.assert_called_once_with(
        "/path/to/catalog.json"
    )


@patch.dict("sys.modules", {"pystac": MagicMock()})
def test_read_catalog_remote(pystac_manager, sample_catalog):
    """Test reading a remote STAC Catalog."""
    mock_catalog = MagicMock()
    mock_catalog.to_dict.return_value = sample_catalog
    sys.modules["pystac"].Catalog.from_file.return_value = mock_catalog

    result = pystac_manager.read_catalog("https://example.com/catalog.json")

    assert result == sample_catalog
    sys.modules["pystac"].Catalog.from_file.assert_called_once()


@patch.dict("sys.modules", {"pystac": MagicMock()})
def test_update_catalog_local(pystac_manager, sample_catalog):
    """Test updating a local STAC Catalog."""
    mock_catalog = MagicMock()
    mock_catalog.to_dict.return_value = sample_catalog
    sys.modules["pystac"].Catalog.from_dict.return_value = mock_catalog
    sys.modules["pystac"].CatalogType.SELF_CONTAINED = "SELF_CONTAINED"

    result = pystac_manager.update_catalog("/path/to/catalog.json", sample_catalog)

    assert result == sample_catalog
    mock_catalog.save.assert_called_once()


@patch("stac_mcp.tools.pystac_management.urllib.request.urlopen")
@patch.dict("sys.modules", {"pystac": MagicMock()})
def test_update_catalog_remote(mock_urlopen, pystac_manager, sample_catalog):
    """Test updating a remote STAC Catalog."""
    mock_catalog = MagicMock()
    sys.modules["pystac"].Catalog.from_dict.return_value = mock_catalog

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(sample_catalog).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    result = pystac_manager.update_catalog(
        "https://example.com/catalog.json", sample_catalog
    )

    assert result == sample_catalog
    mock_urlopen.assert_called_once()


def test_delete_catalog_local(pystac_manager, tmp_path):
    """Test deleting a local STAC Catalog."""
    catalog_file = tmp_path / "catalog.json"
    catalog_file.write_text('{"id": "test"}')

    result = pystac_manager.delete_catalog(str(catalog_file))

    assert result["status"] == "success"
    assert not catalog_file.exists()


@patch("stac_mcp.tools.pystac_management.urllib.request.urlopen")
def test_delete_catalog_remote(mock_urlopen, pystac_manager):
    """Test deleting a remote STAC Catalog."""
    mock_response = MagicMock()
    mock_urlopen.return_value = mock_response

    result = pystac_manager.delete_catalog("https://example.com/catalog.json")

    assert result["status"] == "success"
    mock_urlopen.assert_called_once()


@patch("stac_mcp.tools.pystac_management.urllib.request.urlopen")
def test_list_catalogs_remote(mock_urlopen, pystac_manager, sample_catalog):
    """Test listing remote STAC Catalogs."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        {"catalogs": [sample_catalog]}
    ).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    result = pystac_manager.list_catalogs("https://example.com/catalogs")

    assert len(result) == 1
    assert result[0] == sample_catalog


# ======================== Collection Tests ========================


@patch.dict("sys.modules", {"pystac": MagicMock()})
def test_create_collection_local(pystac_manager, sample_collection):
    """Test creating a local STAC Collection."""
    mock_collection = MagicMock()
    mock_collection.to_dict.return_value = sample_collection
    sys.modules["pystac"].Collection.from_dict.return_value = mock_collection
    sys.modules["pystac"].CatalogType.SELF_CONTAINED = "SELF_CONTAINED"

    result = pystac_manager.create_collection(
        "/path/to/collection.json", sample_collection
    )

    assert result == sample_collection
    mock_collection.normalize_hrefs.assert_called_once()
    mock_collection.save.assert_called_once()


@patch("stac_mcp.tools.pystac_management.urllib.request.urlopen")
@patch.dict("sys.modules", {"pystac": MagicMock()})
def test_create_collection_remote(
    mock_pystac, mock_urlopen, pystac_manager, sample_collection
):
    """Test creating a remote STAC Collection."""
    mock_coll = MagicMock()
    pystac.Collection.from_dict.return_value = mock_coll

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(sample_collection).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    result = pystac_manager.create_collection(
        "https://example.com/collections", sample_collection
    )

    mock_pystac.Collection.from_dict.assert_called_once_with(sample_collection)

    assert result == sample_collection
    mock_urlopen.assert_called_once()


@patch.dict("sys.modules", {"pystac": MagicMock()})
def test_read_collection(pystac_manager, sample_collection):
    """Test reading a STAC Collection."""
    mock_coll = MagicMock()
    mock_coll.to_dict.return_value = sample_collection
    sys.modules["pystac"].Collection.from_file.return_value = mock_coll

    result = pystac_manager.read_collection("/path/to/collection.json")

    assert result == sample_collection


@patch.dict("sys.modules", {"pystac": MagicMock()})
def test_update_collection_local(pystac_manager, sample_collection):
    """Test updating a local STAC Collection."""
    mock_coll = MagicMock()
    mock_coll.to_dict.return_value = sample_collection
    sys.modules["pystac"].Collection.from_dict.return_value = mock_coll
    sys.modules["pystac"].CatalogType.SELF_CONTAINED = "SELF_CONTAINED"

    result = pystac_manager.update_collection(
        "/path/to/collection.json", sample_collection
    )

    assert result == sample_collection
    mock_coll.save.assert_called_once()


def test_delete_collection_local(pystac_manager, tmp_path):
    """Test deleting a local STAC Collection."""
    coll_file = tmp_path / "collection.json"
    coll_file.write_text('{"id": "test"}')

    result = pystac_manager.delete_collection(str(coll_file))

    assert result["status"] == "success"
    assert not coll_file.exists()


@patch("stac_mcp.tools.pystac_management.urllib.request.urlopen")
def test_list_collections_remote(mock_urlopen, pystac_manager, sample_collection):
    """Test listing remote STAC Collections."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        {"collections": [sample_collection]}
    ).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    result = pystac_manager.list_collections("https://example.com/collections")

    assert len(result) == 1
    assert result[0] == sample_collection


# ======================== Item Tests ========================


@patch.dict("sys.modules", {"pystac": MagicMock()})
def test_create_item_local(pystac_manager, sample_item):
    """Test creating a local STAC Item."""
    mock_item = MagicMock()
    mock_item.to_dict.return_value = sample_item
    sys.modules["pystac"].Item.from_dict.return_value = mock_item

    result = pystac_manager.create_item("/path/to/item.json", sample_item)

    assert result == sample_item
    mock_item.save_object.assert_called_once_with(dest_href="/path/to/item.json")


@patch("stac_mcp.tools.pystac_management.urllib.request.urlopen")
@patch.dict("sys.modules", {"pystac": MagicMock()})
def test_create_item_remote(mock_urlopen, pystac_manager, sample_item):
    """Test creating a remote STAC Item."""
    mock_item_obj = MagicMock()
    sys.modules["pystac"].Item.from_dict.return_value = mock_item_obj

    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(sample_item).encode("utf-8")
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    result = pystac_manager.create_item("https://example.com/items", sample_item)

    assert result == sample_item
    mock_urlopen.assert_called_once()


@patch.dict("sys.modules", {"pystac": MagicMock()})
def test_read_item(pystac_manager, sample_item):
    """Test reading a STAC Item."""
    mock_item = MagicMock()
    mock_item.to_dict.return_value = sample_item
    sys.modules["pystac"].Item.from_file.return_value = mock_item

    result = pystac_manager.read_item("/path/to/item.json")

    assert result == sample_item


@patch.dict("sys.modules", {"pystac": MagicMock()})
def test_update_item_local(pystac_manager, sample_item):
    """Test updating a local STAC Item."""
    mock_item = MagicMock()
    mock_item.to_dict.return_value = sample_item
    sys.modules["pystac"].Item.from_dict.return_value = mock_item

    result = pystac_manager.update_item("/path/to/item.json", sample_item)

    assert result == sample_item
    mock_item.save_object.assert_called_once_with(dest_href="/path/to/item.json")


def test_delete_item_local(pystac_manager, tmp_path):
    """Test deleting a local STAC Item."""
    item_file = tmp_path / "item.json"
    item_file.write_text('{"id": "test"}')

    result = pystac_manager.delete_item(str(item_file))

    assert result["status"] == "success"
    assert not item_file.exists()


@patch("stac_mcp.tools.pystac_management.urllib.request.urlopen")
def test_list_items_remote(mock_urlopen, pystac_manager, sample_item):
    """Test listing remote STAC Items."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"features": [sample_item]}).encode(
        "utf-8"
    )
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    result = pystac_manager.list_items("https://example.com/items")

    assert len(result) == 1
    assert result[0] == sample_item


# ======================== API Key Tests ========================


def test_manager_with_api_key(pystac_manager_with_key):
    """Test PySTACManager with API key."""
    headers = pystac_manager_with_key._get_headers()  # noqa: SLF001
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer test-api-key"


@patch.dict("os.environ", {"STAC_API_KEY": "env-api-key"})
def test_manager_with_env_api_key():
    """Test PySTACManager with API key from environment."""

    manager = PySTACManager()
    headers = manager._get_headers()  # noqa: SLF001
    assert "Authorization" in headers
    assert headers["Authorization"] == "Bearer env-api-key"


def test_manager_without_api_key(pystac_manager):
    """Test PySTACManager without API key."""
    headers = pystac_manager._get_headers()  # noqa: SLF001
    assert "Authorization" not in headers


# ======================== Error Handling Tests ========================


def test_import_error_on_missing_pystac(pystac_manager, monkeypatch):
    """Test error handling when pystac is not installed."""

    def mock_import(name, *args, **kwargs):
        if name == "pystac":
            _no_pystac_error = "No module named 'pystac'"
            raise ImportError(_no_pystac_error)
        return __builtins__.__import__(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", mock_import)

    with pytest.raises(ImportError, match="pystac is required"):
        pystac_manager.create_catalog("/path/to/catalog.json", "test", "Test catalog")
