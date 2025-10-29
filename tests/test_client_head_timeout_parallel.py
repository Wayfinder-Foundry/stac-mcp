import time
from typing import ClassVar

import requests

from stac_mcp.tools.client import STACClient


def test_parallel_head_content_lengths_respects_timeouts(monkeypatch):
    client = STACClient(head_timeout_seconds=1, head_max_workers=4)

    # Simulate three hrefs: two fast, one slow (exceeds timeout)
    hrefs = [
        "http://fast.example/one.tif",
        "http://slow.example/slow.tif",
        "http://fast.example/two.tif",
    ]

    bytes_fast = 1024
    bytes_slow = 4096

    class FakeResp:
        headers: ClassVar[dict]

        def __init__(self, cl: int):
            self.headers = {"Content-Length": str(cl)}

    def fake_request(_method, url, *_args, **_kwargs):
        # fast responses
        if "fast.example" in url:
            return FakeResp(bytes_fast)
        # slow response: sleep longer than client.head_timeout_seconds
        # then return slow bytes
        time.sleep(client.head_timeout_seconds + 0.5)
        return FakeResp(bytes_slow)

    monkeypatch.setattr(requests.Session, "request", staticmethod(fake_request))

    start = time.time()
    results = client._parallel_head_content_lengths(hrefs)  # noqa: SLF001
    elapsed = time.time() - start

    # Ensure we ran in roughly head_timeout_seconds + overhead (parallelism)
    assert elapsed < (client.head_timeout_seconds + 2.0)

    # Fast hrefs should have results; slow href should be None due to timeout
    assert results["http://fast.example/one.tif"] == bytes_fast
    assert results["http://fast.example/two.tif"] == bytes_fast
    assert results["http://slow.example/slow.tif"] in (None, bytes_slow)


def test_head_content_length_handles_bad_headers(monkeypatch):
    client = STACClient()

    class BadResp:
        headers: ClassVar[dict] = {}

    def fake_request(*_, **__):
        return BadResp()

    monkeypatch.setattr(requests.Session, "request", staticmethod(fake_request))
    # accessing private method intentionally in test
    assert client._head_content_length("http://example.com/nocl") is None  # noqa: SLF001
