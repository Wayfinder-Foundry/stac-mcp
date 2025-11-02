"""Unit tests for small STACClient helpers.

These tests intentionally exercise private helpers; ruff warnings for
private access are suppressed for this module.
"""

# ruff: noqa: SLF001

import json
from types import SimpleNamespace

import pytest

from stac_mcp.tools.client import ConformanceError, STACClient


def test_search_cache_key_deterministic():
    client = STACClient()
    k1 = client._search_cache_key(
        ["c1"], [0, 0, 1, 1], "2020-01-01/2020-01-02", {"q": 1}, 3
    )
    k2 = client._search_cache_key(
        ["c1"], [0, 0, 1, 1], "2020-01-01/2020-01-02", {"q": 1}, 3
    )
    assert k1 == k2
    # ensure it's valid JSON and contains the collections key
    obj = json.loads(k1)
    assert obj["collections"] == ["c1"]


def test_cached_search_expiry_and_refresh():
    client = STACClient()

    class FakeSearch:
        def __init__(self, items):
            self._items = items

        def items(self):
            return iter(self._items)

        def items_as_dict(self):
            # Return items in the form the client expects from a real
            # ItemSearch when items_as_dict() is called (list of objects)
            return self._items

    def _search_a(**_kw):
        return FakeSearch([SimpleNamespace(id="a")])

    client._client = SimpleNamespace(search=_search_a)
    items1 = client._cached_search(collections=["c1"], limit=1)
    assert items1[0].id == "a"

    # Force cached timestamp to be old so next call triggers refresh
    key = client._search_cache_key(["c1"], None, None, None, 1)
    old_ts, val = client._search_cache[key]
    client._search_cache[key] = (old_ts - 10000, val)

    def _search_b(**_kw):
        return FakeSearch([SimpleNamespace(id="b")])

    client._client = SimpleNamespace(search=_search_b)
    items2 = client._cached_search(collections=["c1"], limit=1)
    assert items2[0].id == "b"


def test_check_conformance_raises():
    client = STACClient()
    # set conformance to an empty list to force error
    client._conformance = []
    with pytest.raises(ConformanceError, match="does not support"):
        client._check_conformance(["https://example.com/capability"])


def test_asset_to_dict():
    client = STACClient()

    # Test with a dictionary
    asset_dict = {"href": "http://example.com/asset.tif"}
    assert client._asset_to_dict(asset_dict) == asset_dict

    # Test with an object with to_dict()
    class AssetObject:
        def to_dict(self):
            return {"href": "http://example.com/asset.tif"}

    asset_obj = AssetObject()
    assert client._asset_to_dict(asset_obj) == {"href": "http://example.com/asset.tif"}

    # Test with a simple object
    simple_obj = SimpleNamespace(href="http://example.com/asset.tif")
    assert client._asset_to_dict(simple_obj) == {
        "href": "http://example.com/asset.tif"
    }


def test_size_from_metadata():
    client = STACClient()
    size1 = 123
    size2 = 456
    size3 = 789
    size4 = 1024

    # Test with different keys in extra_fields
    asset1 = {"extra_fields": {"file:size": size1}}
    assert client._size_from_metadata(asset1) == size1

    asset2 = {"extra_fields": {"file:bytes": size2}}
    assert client._size_from_metadata(asset2) == size2

    # Test with keys directly in the asset
    asset3 = {"size": size3}
    assert client._size_from_metadata(asset3) == size3

    # Test with a non-integer value
    asset4 = {"size": "not-a-number"}
    assert client._size_from_metadata(asset4) is None

    # Test with no size information
    asset5 = {"href": "http://example.com"}
    assert client._size_from_metadata(asset5) is None

    # Test with an object instead of a dict
    asset_obj = SimpleNamespace(extra_fields={"file:size": size4})
    assert client._size_from_metadata(asset_obj) == size4


def test_sign_href(monkeypatch):
    client = STACClient()
    href = "https://example.com/item.tif"

    # Test when planetary_computer is not available
    monkeypatch.setitem(__import__("sys").modules, "planetary_computer", None)
    assert client._sign_href(href) == href

    # Test when planetary_computer is available and returns a string
    pc_mock_str = SimpleNamespace(sign=lambda _: "signed-url")
    monkeypatch.setitem(__import__("sys").modules, "planetary_computer", pc_mock_str)
    assert client._sign_href(href) == "signed-url"

    # Test when planetary_computer is available and returns a dict
    pc_mock_dict = SimpleNamespace(sign=lambda _: {"url": "signed-url-from-dict"})
    monkeypatch.setitem(__import__("sys").modules, "planetary_computer", pc_mock_dict)
    assert client._sign_href(href) == "signed-url-from-dict"

    # Test with an empty href
    assert client._sign_href("") == ""
