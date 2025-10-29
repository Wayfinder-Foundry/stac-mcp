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
