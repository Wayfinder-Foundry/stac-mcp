"""Tests for STACClient low-level HTTP error handling and APIError branch.

These focus on branches previously un-covered:
 - _http_json 404 returns None
 - _http_json 500 raises HTTPError
 - _http_json propagates URLError
 - search_collections APIError path (logged then re-raised)
"""

from __future__ import annotations

import json
from io import BytesIO
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest
from pystac_client.exceptions import APIError

from stac_mcp.tools.client import STACClient


class _FakeResponse:
    def __init__(self, body: dict[str, object] | None, code: int = 200):
        self._body = body
        self.code = code

    def read(self):
        return json.dumps(self._body or {}).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _mk_http_error(code: int) -> HTTPError:
    return HTTPError(
        url="https://example.com",
        code=code,
        msg="err",
        hdrs=None,
        fp=BytesIO(),
    )


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_http_json_404_returns_none(mock_urlopen):
    client = STACClient("https://example.com")

    def raise_404(*_, **__):
        raise _mk_http_error(404)

    mock_urlopen.side_effect = raise_404
    # 404 should yield None
    assert client._http_json("/missing") is None  # noqa: SLF001


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_http_json_500_raises(mock_urlopen):
    client = STACClient("https://example.com")

    def raise_500(*_, **__):
        raise _mk_http_error(500)

    mock_urlopen.side_effect = raise_500
    with pytest.raises(HTTPError):
        client._http_json("/boom")  # noqa: SLF001


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_http_json_url_error(mock_urlopen):
    client = STACClient("https://example.com")
    mock_urlopen.side_effect = URLError("down")
    with pytest.raises(URLError):
        client._http_json("/boom")  # noqa: SLF001


def test_search_collections_api_error(monkeypatch):
    # Simulate underlying client raising APIError
    client = STACClient("https://example.com")

    # Inject fake underlying client
    class _FakeInner:
        def get_collections(self):
            msg = "api failure"
            raise APIError(msg)

    monkeypatch.setattr(client, "_client", _FakeInner())
    with pytest.raises(APIError, match="api failure"):
        client.search_collections(limit=1)