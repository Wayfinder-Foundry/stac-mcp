from stac_mcp.tools.client import STACClient

HEAD_RETRIES_ENV = 3


def test_head_retries_envvar(monkeypatch):
    monkeypatch.setenv("STAC_MCP_HEAD_RETRIES", str(HEAD_RETRIES_ENV))
    c = STACClient()
    assert c.head_retries == HEAD_RETRIES_ENV


def test_parallel_head_empty_list_returns_empty():
    c = STACClient()
    # intentional private member usage for unit testing
    res = c._parallel_head_content_lengths([])  # noqa: SLF001
    assert res == {}
