"""Focused tests for STACClient wrapper to raise coverage of tool client logic.

These tests avoid real network calls by mocking the internal `client` attribute
and the private `_http_json` helper.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from stac_mcp.tools.client import STACClient


@pytest.fixture
def stac_client():
    return STACClient("https://example.com/stac/v1")


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
    itm.datetime = datetime(2024, 1, 1, 12, 0, 0)
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
    assert len(res) == 2
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


# ---------------- Capability / discovery tests ---------------- #


def test_get_root_document_success(stac_client, monkeypatch):
    monkeypatch.setattr(
        stac_client,
        "_http_json",
        lambda path: {"id": "root1", "title": "R", "links": [], "conformsTo": ["core"]},
    )
    root = stac_client.get_root_document()
    assert root["id"] == "root1"
    assert "conformsTo" in root


def test_get_root_document_empty(stac_client, monkeypatch):
    monkeypatch.setattr(stac_client, "_http_json", lambda path: None)
    root = stac_client.get_root_document()
    assert root["id"] is None
    assert root["conformsTo"] == []


def test_get_conformance_direct(stac_client, monkeypatch):
    monkeypatch.setattr(
        stac_client,
        "_http_json",
        lambda path: {"conformsTo": ["c1", "c2"]} if path == "/conformance" else None,
    )
    res = stac_client.get_conformance(check=["c1", "cX"])
    assert res["checks"] == {"c1": True, "cX": False}


def test_get_conformance_fallback(stac_client, monkeypatch):
    def _http(path):
        if path == "/conformance":
            return None
        return {"conformsTo": ["core"], "id": "r"}

    monkeypatch.setattr(stac_client, "_http_json", _http)
    res = stac_client.get_conformance()
    assert "core" in res["conformsTo"]


def test_get_queryables_missing(stac_client, monkeypatch):
    monkeypatch.setattr(stac_client, "_http_json", lambda path: None)
    res = stac_client.get_queryables()
    assert res["queryables"] == {}
    assert "message" in res


def test_get_queryables_present(stac_client, monkeypatch):
    monkeypatch.setattr(
        stac_client,
        "_http_json",
        lambda path: {"properties": {"eo:cloud_cover": {"type": "number"}}},
    )
    res = stac_client.get_queryables(collection_id="c1")
    assert "eo:cloud_cover" in res["queryables"]


def test_get_aggregations_supported(stac_client, monkeypatch):
    def _http(path, method="GET", payload=None):
        if path == "/search":
            return {"aggregations": {"count": {"value": 10}}}
        return None

    monkeypatch.setattr(stac_client, "_http_json", _http)
    res = stac_client.get_aggregations(collections=["c1"], limit=0)
    assert res["supported"] is True
    assert res["aggregations"]["count"]["value"] == 10


def test_get_aggregations_unsupported(stac_client, monkeypatch):
    monkeypatch.setattr(
        stac_client,
        "_http_json",
        lambda *a, **k: {"aggregations": {}} if a[0] == "/search" else None,
    )
    res = stac_client.get_aggregations(collections=["c1"], limit=0)
    assert res["supported"] is False
    assert res["aggregations"] == {}
    assert "parameters" in res
