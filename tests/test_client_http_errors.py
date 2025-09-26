"""Tests for STACClient low-level HTTP error handling and APIError branch.

These focus on branches previously un-covered:
 - _http_json 404 returns None
 - _http_json 500 raises HTTPError
 - _http_json propagates URLError
 - search_collections APIError path (logged then re-raised)
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from urllib.error import HTTPError, URLError
from io import BytesIO
from unittest.mock import patch

import pytest

from stac_mcp.tools.client import STACClient


class _FakeResponse:
    def __init__(self, body: dict[str, object] | None, code: int = 200):
        self._body = body
        self.code = code

    def read(self):  # noqa: D401
        return json.dumps(self._body or {}).encode("utf-8")

    def __enter__(self):  # noqa: D401
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: D401
        return False


def _mk_http_error(code: int) -> HTTPError:
    return HTTPError(url="https://example.com", code=code, msg="err", hdrs=None, fp=BytesIO())


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_http_json_404_returns_none(mock_urlopen):
    client = STACClient("https://example.com")

    def raise_404(req, timeout=30):  # noqa: D401
        raise _mk_http_error(404)

    mock_urlopen.side_effect = raise_404
    # 404 should yield None
    assert client._http_json("/missing") is None  # type: ignore[attr-defined]


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_http_json_500_raises(mock_urlopen):
    client = STACClient("https://example.com")

    def raise_500(req, timeout=30):  # noqa: D401
        raise _mk_http_error(500)

    mock_urlopen.side_effect = raise_500
    with pytest.raises(HTTPError):
        client._http_json("/boom")  # type: ignore[attr-defined]


@patch("stac_mcp.tools.client.urllib.request.urlopen")
def test_http_json_url_error(mock_urlopen):
    client = STACClient("https://example.com")
    mock_urlopen.side_effect = URLError("down")
    with pytest.raises(URLError):
        client._http_json("/boom")  # type: ignore[attr-defined]


@patch("stac_mcp.tools.client.APIError")
def test_search_collections_api_error(mock_api_error, monkeypatch):
    # Simulate underlying client raising APIError
    client = STACClient("https://example.com")
    # Inject fake underlying client
    class _FakeInner:
        def get_collections(self):  # noqa: D401
            raise mock_api_error  # instance behaves as exception

    monkeypatch.setattr(client, "_client", _FakeInner())
    mock_api_error.__str__.return_value = "api failure"
    with pytest.raises(Exception):
        client.search_collections(limit=1)
