"""Tests exercising tool handler text formatting branches via handle_call_tool.

These focus on optional field inclusion and loop sections to raise coverage.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from stac_mcp.server import handle_call_tool


class FakeAsset(dict):
    def to_dict(self):
        return self


class FakeItem(SimpleNamespace):
    pass


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_get_item_text_and_json(mock_client):
    item = SimpleNamespace(
        id="item-1",
        collection_id="col-1",
        geometry=None,
        bbox=[0, 0, 10, 5],
        datetime=datetime(2024, 1, 1, 12, 0, 0),
        properties={"eo:cloud_cover": 12, "ignore_dict": {"a": 1}},
        assets={
            "B01": {"title": "Blue", "type": "image/tiff", "href": "http://x"},
            "B02": {"title": "Green", "type": "image/tiff"},
        },
    )
    mock_client.get_item.return_value = {
        "id": item.id,
        "collection": item.collection_id,
        "geometry": item.geometry,
        "bbox": item.bbox,
        "datetime": item.datetime.isoformat(),
        "properties": item.properties,
        "assets": item.assets,
    }
    # Text format
    txt = await handle_call_tool(
        "get_item",
        {"collection_id": "col-1", "item_id": "item-1"},
    )
    assert any("Blue" in c.text for c in txt)
    # JSON format
    js = await handle_call_tool(
        "get_item",
        {
            "collection_id": "col-1",
            "item_id": "item-1",
            "output_format": "json",
        },
    )
    assert '"type":"item"' in js[0].text or "item-1" in js[0].text


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_get_collection_text_and_json(mock_client):
    # Return dictionary shaped like STACClient.get_collection output
    mock_client.get_collection.return_value = {
        "id": "col-1",
        "title": "Collection One",
        "description": "Desc",
        "extent": {"spatial": {"bbox": [[0, 0, 10, 5]]}},
        "license": "CC-BY",
        "providers": [
            {"name": "Provider A", "roles": ["producer"]},
            {"name": "Provider B", "roles": ["licensor"]},
        ],
        "summaries": {"s": 1},
        "assets": {"a": {"href": "u"}},
    }
    # Text path
    txt = await handle_call_tool(
        "get_collection",
        {"collection_id": "col-1"},
    )
    assert any("Collection One" in c.text for c in txt)
    # JSON path
    js = await handle_call_tool(
        "get_collection",
        {"collection_id": "col-1", "output_format": "json"},
    )
    assert "collection" in js[0].text or "Collection One" in js[0].text


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_get_collection_text_with_temporal_and_providers(mock_client):
    # Cover temporal interval formatting + providers loop branches
    mock_client.get_collection.return_value = {
        "id": "col-2",
        "title": "Col2",
        "description": "Desc2",
        "extent": {
            "spatial": {"bbox": [[10, 20, 30, 40]]},
            "temporal": {"interval": [["2020-01-01T00:00:00Z", None]]},
        },
        "license": "CC0",
        "providers": [
            {"name": "P1", "roles": ["host"]},
            {"name": "P2", "roles": ["producer"]},
        ],
        "summaries": {},
        "assets": {},
    }
    txt = await handle_call_tool("get_collection", {"collection_id": "col-2"})
    t = txt[0].text
    assert "Temporal Extent" in t
    assert "Providers" in t


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_search_items_text_and_json(mock_client):
    mock_client.search_items.return_value = [
        {
            "id": "i1",
            "collection": "col-1",
            "geometry": None,
            "bbox": [0, 0, 1, 1],
            "datetime": datetime(2024, 1, 1).isoformat(),
            "properties": {},
            "assets": {},
        },
    ]
    # text
    txt = await handle_call_tool("search_items", {"collections": ["col-1"]})
    assert "i1" in txt[0].text
    # json
    js = await handle_call_tool(
        "search_items",
        {"collections": ["col-1"], "output_format": "json"},
    )
    assert '"item_list"' in js[0].text or '"count"' in js[0].text


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_get_root_text_and_json(mock_client):
    mock_client.get_root_document.return_value = {
        "id": "root",
        "title": "Root Title",
        "description": "Root desc",
        "links": [1, 2],
        "conformsTo": ["a", "b", "c", "d", "e", "f"],
    }
    txt = await handle_call_tool("get_root", {})
    assert any("Root Title" in t.text for t in txt)
    js = await handle_call_tool("get_root", {"output_format": "json"})
    assert '"root"' in js[0].text


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_get_conformance_text_and_json(mock_client):
    mock_client.get_conformance.return_value = {
        "conformsTo": ["c1", "c2", "c3"],
        "checks": {"c1": True, "cX": False},
    }
    txt = await handle_call_tool("get_conformance", {"check": ["c1", "cX"]})
    assert "c1" in txt[0].text and "cX" in txt[0].text
    js = await handle_call_tool(
        "get_conformance",
        {"check": ["c1"], "output_format": "json"},
    )
    assert '"conformance"' in js[0].text or '"conformsTo"' in js[0].text


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_get_queryables_text_and_json(mock_client):
    mock_client.get_queryables.return_value = {
        "queryables": {"eo:cloud_cover": {"type": "number"}},
        "collection_id": None,
    }
    txt = await handle_call_tool("get_queryables", {})
    assert "eo:cloud_cover" in txt[0].text
    js = await handle_call_tool("get_queryables", {"output_format": "json"})
    assert '"queryables"' in js[0].text


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_get_queryables_not_available(mock_client):
    # Exercise branch where queryables not available
    mock_client.get_queryables.return_value = {
        "queryables": {},
        "collection_id": "c1",
        "message": "Queryables not available",
    }
    txt = await handle_call_tool("get_queryables", {"collection_id": "c1"})
    assert "not available" in txt[0].text.lower()


@pytest.mark.asyncio
@patch("stac_mcp.server.stac_client")
async def test_get_aggregations_text_and_json(mock_client):
    mock_client.get_aggregations.return_value = {
        "supported": True,
        "aggregations": {"count": {"value": 5}},
        "message": "OK",
        "parameters": {"collections": ["c1"]},
    }
    txt = await handle_call_tool(
        "get_aggregations",
        {"collections": ["c1"], "fields": ["eo:cloud_cover"], "operations": ["count"]},
    )
    assert "count" in txt[0].text
    js = await handle_call_tool(
        "get_aggregations",
        {"collections": ["c1"], "output_format": "json"},
    )
    assert '"aggregations"' in js[0].text
