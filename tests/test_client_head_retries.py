import requests

from stac_mcp.tools.client import STACClient

BYTES_RESPONSE = 12345


def test_head_retries_success_after_transient(monkeypatch):
    client = STACClient(head_timeout_seconds=1, head_max_workers=2)
    # Ensure at least 1 retry
    client.head_retries = 1

    class Resp:
        def __init__(self, headers=None):
            self.headers = headers or {}

    calls = {"count": 0}

    def fake_request(_method, _url, *_, **__):
        calls["count"] += 1
        if calls["count"] == 1:
            msg = "transient"
            raise requests.RequestException(msg)
        return Resp({"Content-Length": "12345"})

    monkeypatch.setattr(client._head_session, "request", fake_request)  # noqa: SLF001
    val = client._head_content_length("http://example.com/test.tif")  # noqa: SLF001
    assert val == BYTES_RESPONSE


def test_head_retries_exhausted_returns_none(monkeypatch):
    client = STACClient(head_timeout_seconds=1, head_max_workers=2)
    client.head_retries = 2

    def always_fail(*_, **__):
        msg = "dead"
        raise requests.RequestException(msg)

    monkeypatch.setattr(client._head_session, "request", always_fail)  # noqa: SLF001
    val = client._head_content_length("http://example.com/test.tif")  # noqa: SLF001
    assert val is None
