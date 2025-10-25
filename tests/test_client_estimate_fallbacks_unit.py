from typing import ClassVar

import requests

from stac_mcp.tools.client import STACClient

# Constants used in tests to avoid magic numbers
BYTES_1K = 1024
BYTES_2K = 2048
BYTES_4K = 4096
BYTES_8K = 8192


class FakeAsset:
    def __init__(self, href=None, media_type=None, extra=None):
        self.href = href
        self.media_type = media_type
        self.extra_fields = extra or {}


class FakeItem:
    def __init__(self, id_="i1", assets=None):
        self.id = id_
        self.assets = assets or {}
        self.collection_id = "c1"
        self.datetime = None


def test_size_from_metadata_prefers_extra_fields():
    client = STACClient()
    asset = {"extra_fields": {"file:bytes": "1024"}}
    assert client._size_from_metadata(asset) == BYTES_1K  # noqa: SLF001


def test_size_from_metadata_handles_missing_keys():
    client = STACClient()
    asset = {"href": "http://example.com/file.tif"}
    assert client._size_from_metadata(asset) is None  # noqa: SLF001


def test_head_content_length_calls_requests(monkeypatch):
    client = STACClient()

    class FakeResp:
        headers: ClassVar[dict[str, str]] = {"Content-Length": str(BYTES_2K)}

    def fake_request(*_, **__):
        # We don't need the explicit args in this test
        return FakeResp()

    monkeypatch.setattr(requests.Session, "request", staticmethod(fake_request))
    # accessing private method in test is intentional
    assert client._head_content_length("http://example.com/file.tif") == BYTES_2K  # noqa: SLF001


def test_fallback_estimate_aggregates_metadata():
    client = STACClient()
    # asset has metadata size
    assets = {"a1": {"href": "http://x", "extra_fields": {"bytes": BYTES_4K}}}
    item = FakeItem(assets=assets)
    res = client._fallback_estimate([item], None, None, ["c1"], False)  # noqa: SLF001
    assert res["item_count"] == 1
    assert res["estimated_size_bytes"] == BYTES_4K
    assert res["assets_analyzed"][0]["estimated_size_bytes"] == BYTES_4K


def test_fallback_estimate_uses_head_when_needed(monkeypatch):
    client = STACClient()
    assets = {"a1": {"href": "http://x.parquet", "media_type": "application/parquet"}}
    item = FakeItem(assets=assets)

    class FakeResp:
        headers: ClassVar[dict[str, str]] = {"Content-Length": str(BYTES_8K)}

    def fake_request(*_, **__):
        return FakeResp()

    monkeypatch.setattr(requests.Session, "request", staticmethod(fake_request))
    res = client._fallback_estimate([item], None, None, ["c1"], False)  # noqa: SLF001
    assert res["estimated_size_bytes"] == BYTES_8K
