import requests

from stac_mcp.tools.client import STACClient

BYTES_SMALL = 42
BYTES_LARGE = 100


def _raise_transient_exc():
    msg = "transient"
    raise requests.RequestException(msg)


def test_backoff_jitter_applied(monkeypatch):
    c = STACClient()
    c.head_retries = 1
    c.head_backoff_base = 0.01
    c.head_backoff_jitter = True

    calls = {"count": 0, "slept": []}

    class Resp:
        def __init__(self, headers=None):
            self.headers = headers or {}

    def fake_request(_method, _url, *_, **__):
        calls["count"] += 1
        if calls["count"] == 1:
            _raise_transient_exc()
        return Resp({"Content-Length": str(BYTES_SMALL)})

    # Accessing private session is intentional for unit testing
    monkeypatch.setattr(c._head_session, "request", fake_request)  # noqa: SLF001

    # Make jitter deterministic
    monkeypatch.setattr("random.uniform", lambda a, b: (a + b) / 2)

    def fake_sleep(d):
        calls["slept"].append(d)

    monkeypatch.setattr("time.sleep", fake_sleep)

    val = c._head_content_length("http://example.com/x")  # noqa: SLF001
    assert val == BYTES_SMALL
    assert len(calls["slept"]) >= 1


def test_backoff_no_jitter(monkeypatch):
    c = STACClient()
    c.head_retries = 1
    c.head_backoff_base = 0.01
    c.head_backoff_jitter = False

    calls = {"count": 0, "slept": []}

    class Resp:
        def __init__(self, headers=None):
            self.headers = headers or {}

    def fake_request(_method, _url, *_, **__):
        calls["count"] += 1
        if calls["count"] == 1:
            _raise_transient_exc()
        return Resp({"Content-Length": str(BYTES_LARGE)})

    monkeypatch.setattr(c._head_session, "request", fake_request)  # noqa: SLF001

    monkeypatch.setattr("time.sleep", lambda d: calls["slept"].append(d))

    val = c._head_content_length("http://example.com/x")  # noqa: SLF001
    assert val == BYTES_LARGE
    assert len(calls["slept"]) == 1
