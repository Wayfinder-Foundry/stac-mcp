from stac_mcp.tools import execution


def test_get_cached_client_singleton_per_key():
    # Ensure the client cache returns the same instance for the same key
    execution._CLIENT_CACHE.clear()

    c1 = execution._get_cached_client(None, None)
    c2 = execution._get_cached_client(None, None)
    assert c1 is c2

    # Different headers should produce a different cached client
    c3 = execution._get_cached_client(None, {"x": "1"})
    assert c3 is not c1
