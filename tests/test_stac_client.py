"""Focused tests for STACClient wrapper to raise coverage of tool client logic.

These tests avoid real network calls by mocking the internal `client` attribute
and the private `_http_json` helper.
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from stac_mcp.tools.client import (
    CONFORMANCE_QUERY,
    CONFORMANCE_QUERYABLES,
    CONFORMANCE_SORT,
    ConformanceError,
    STACClient,
)

NUM_ITEMS = 2
AGG_COUNT = 10


@pytest.fixture
def stac_client(request):
    """Yield a STACClient and clear its conformance cache on teardown."""
    client = STACClient("https://example.com/stac/v1")

    def teardown():
        # Clear cached property to ensure test isolation for conformance checks
        if hasattr(client, "_conformance"):
            delattr(client, "_conformance")

    request.addfinalizer(teardown)  # noqa: PT021
    return client


def _mk_collection(id_: str):
    c = SimpleNamespace()
    c.id = id_
    c.title = f"Title {id_}"
    c.description = f"Description {id_}"
    c.extent = SimpleNamespace(to_dict=lambda: {"spatial": id_})
    c.license = "CC-BY"
    c.providers = []
    c.summaries = SimpleNamespace(to_dict=lambda: {"a": 1})
    c.assets = {"asset1": SimpleNamespace(to_dict=lambda: {"href": "u"})}
    return c


def _mk_item(id_: str, collection_id: str):
    itm = SimpleNamespace()
    itm.id = id_
    itm.collection_id = collection_id
    itm.geometry = None
    itm.bbox = [0, 0, 1, 1]
    itm.datetime = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    itm.properties = {"eo:cloud_cover": 10}
    itm.assets = {
        "B01": SimpleNamespace(to_dict=lambda: {"href": "u", "type": "image/tiff"}),
    }
    return itm


def test_search_collections(stac_client, monkeypatch):
    mock_client = MagicMock()
    mock_client.get_collections.return_value = [
        _mk_collection("c1"),
        _mk_collection("c2"),
    ]
    monkeypatch.setattr(stac_client, "_client", mock_client)
    res = stac_client.search_collections(limit=1)
    assert len(res) == 1
    assert res[0]["id"] == "c1"


def test_get_collection(stac_client, monkeypatch):
    mock_client = MagicMock()
    mock_client.get_collection.return_value = _mk_collection("c9")
    monkeypatch.setattr(stac_client, "_client", mock_client)
    res = stac_client.get_collection("c9")
    assert res["id"] == "c9"
    assert "assets" in res


def test_search_items(stac_client, monkeypatch):
    search_mock = MagicMock()
    search_mock.items.return_value = [_mk_item("i1", "c1"), _mk_item("i2", "c1")]
    mock_client = MagicMock()
    mock_client.search.return_value = search_mock
    monkeypatch.setattr(stac_client, "_client", mock_client)
    res = stac_client.search_items(collections=["c1"], limit=5)
    assert len(res) == NUM_ITEMS
    assert res[0]["id"] == "i1"


def test_get_item(stac_client, monkeypatch):
    collection_mock = MagicMock()
    collection_mock.get_item.return_value = _mk_item("i100", "c9")
    mock_client = MagicMock()
    mock_client.get_collection.return_value = collection_mock
    monkeypatch.setattr(stac_client, "_client", mock_client)
    res = stac_client.get_item("c9", "i100")
    assert res["id"] == "i100"
    assert res["collection"] == "c9"


def test_get_item_not_found(stac_client, monkeypatch):
    """Test that get_item returns None when the item is not found."""
    collection_mock = MagicMock()
    collection_mock.get_item.return_value = None
    mock_client = MagicMock()
    mock_client.get_collection.return_value = collection_mock
    monkeypatch.setattr(stac_client, "_client", mock_client)
    item = stac_client.get_item(collection_id="test-collection", item_id="not-found")
    assert item is None


def test_update_item_missing_id_raises_error(stac_client):
    """Test that updating an item with a missing ID raises a ValueError."""
    with pytest.raises(ValueError, match="Item must have 'collection' and 'id'"):
        stac_client.update_item(item={"collection": "test-collection"})


def test_update_item_missing_collection_raises_error(stac_client):
    """Test that updating an item with a missing collection raises a ValueError."""
    with pytest.raises(ValueError, match="Item must have 'collection' and 'id'"):
        stac_client.update_item(item={"id": "test-item"})


# ---------------- Conformance-aware method tests ---------------- #


def test_search_items_with_query_checks_conformance(stac_client, monkeypatch):
    # Mock underlying search and conformance check
    search_mock = MagicMock()
    search_mock.items.return_value = []
    mock_client = MagicMock()
    mock_client.search.return_value = search_mock
    monkeypatch.setattr(stac_client, "_client", mock_client)
    # Set supported conformance
    monkeypatch.setattr(stac_client, "_conformance", CONFORMANCE_QUERY)

    # Should not raise
    stac_client.search_items(query={"proj:epsg": {"eq": 4326}})

    # Check that it fails without the right conformance
    monkeypatch.setattr(stac_client, "_conformance", ["core"])
    with pytest.raises(ConformanceError):
        stac_client.search_items(query={"proj:epsg": {"eq": 4326}})


def test_search_items_with_sortby_checks_conformance(stac_client, monkeypatch):
    # Mock underlying search and conformance check
    search_mock = MagicMock()
    search_mock.items.return_value = []
    mock_client = MagicMock()
    mock_client.search.return_value = search_mock
    monkeypatch.setattr(stac_client, "_client", mock_client)
    # Set supported conformance
    monkeypatch.setattr(stac_client, "_conformance", CONFORMANCE_SORT)

    # Should not raise
    sort_spec = [("properties.datetime", "desc")]
    stac_client.search_items(sortby=sort_spec)
    mock_client.search.assert_called_with(
        collections=None,
        bbox=None,
        datetime=None,
        query=None,
        sortby=sort_spec,
        limit=10,
    )

    # Check that it fails without the right conformance
    monkeypatch.setattr(stac_client, "_conformance", ["core"])
    with pytest.raises(ConformanceError):
        stac_client.search_items(sortby=sort_spec)


def test_get_queryables_raises_if_unsupported(stac_client, monkeypatch):
    monkeypatch.setattr(stac_client, "_conformance", ["core"])
    with pytest.raises(ConformanceError):
        stac_client.get_queryables()


def test_get_aggregations_raises_if_unsupported(stac_client, monkeypatch):
    monkeypatch.setattr(stac_client, "_conformance", ["core"])
    with pytest.raises(ConformanceError):
        stac_client.get_aggregations()


def test_check_conformance_raises_error_if_missing(stac_client, monkeypatch):
    monkeypatch.setattr(stac_client, "_conformance", ["core"])
    with pytest.raises(ConformanceError, match="does not support"):
        stac_client._check_conformance(  # noqa: SLF001
            ["non-existent-capability"],
        )


def test_check_conformance_handles_older_uri_versions(stac_client, monkeypatch):
    """Verify that an older but compatible conformance URI is accepted."""
    # Server advertises an older RC version of the Queryables spec
    monkeypatch.setattr(
        stac_client,
        "_conformance",
        ["core", "https://api.stacspec.org/v1.0.0-rc.1/item-search#queryables"],
    )

    # Client should not raise an error because the older URI is in its list
    # of acceptable URIs for Queryables.
    try:
        stac_client._check_conformance(CONFORMANCE_QUERYABLES)  # noqa: SLF001
    except ConformanceError:
        pytest.fail(
            "Conformance check failed for a valid (older) URI",
        )
