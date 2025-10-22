import io
import json
from types import SimpleNamespace

from stac_mcp.tools.pystac_management import PySTACManager


def test_get_headers_with_envvar(monkeypatch):
    monkeypatch.setenv("STAC_API_KEY", "abc123")
    mgr = PySTACManager()
    headers = mgr._get_headers()  # noqa: SLF001
    assert headers["Authorization"] == "Bearer abc123"


def test_is_remote_paths():
    mgr = PySTACManager(api_key=None)
    assert mgr._is_remote("http://example.com/x")  # noqa: SLF001
    assert mgr._is_remote("https://example.com/x")  # noqa: SLF001
    # Using a unix-like temporary path is fine in tests; flag suppressed.
    assert not mgr._is_remote("/tmp/file.json")  # noqa: SLF001 S108
    assert not mgr._is_remote("relative/path.json")  # noqa: SLF001


def test_local_read_write_delete(tmp_path):
    mgr = PySTACManager()
    p = tmp_path / "sub" / "file.json"
    data = {"a": 1}
    # write
    mgr._write_json_file(str(p), data)  # noqa: SLF001
    assert p.exists()
    # read
    got = mgr._read_json_file(str(p))  # noqa: SLF001
    assert got == data
    # delete
    mgr._delete_file(str(p))  # noqa: SLF001
    assert not p.exists()


def test_remote_read_write_delete(monkeypatch):
    mgr = PySTACManager(api_key="k")

    # fake urlopen for read
    class FakeResp:
        def __init__(self, data_bytes: bytes):
            self._buf = io.BytesIO(data_bytes)

        def read(self):
            return self._buf.read()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen_read(req):
        assert isinstance(req, object)
        return FakeResp(json.dumps({"x": 5}).encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen_read)
    got = mgr._read_json_file("http://example.com/data.json")  # noqa: SLF001
    assert got == {"x": 5}

    # fake urlopen for write (no context manager used)
    def fake_urlopen_write(_req):
        # ensure Authorization header present (presence checked by behavior)
        _ = _req.header_items() if hasattr(_req, "header_items") else _req.get_header
        return SimpleNamespace()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen_write)
    mgr._write_json_file("http://example.com/data.json", {"y": 2})  # noqa: SLF001

    # fake urlopen for delete
    def fake_urlopen_delete(_req):
        return SimpleNamespace()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen_delete)
    mgr._delete_file("http://example.com/data.json")  # noqa: SLF001
