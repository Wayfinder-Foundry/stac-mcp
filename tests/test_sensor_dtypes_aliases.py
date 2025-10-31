from stac_mcp.tools.sensor_dtypes import SensorDtypeRegistry


def test_resolve_direct_match():
    cid, info = SensorDtypeRegistry.resolve_for_catalog("sentinel-2-l2a", None)
    assert cid == "sentinel-2-l2a"
    assert info is not None
    assert info.default_dtype.name == "uint16"


def test_resolve_catalog_alias_aws():
    # AWS Earth Search uses the sentinel-2-c1-l2a id; resolver should map
    # that alias back to the canonical registry entry.
    aws_url = "https://earth-search.aws.element84.com/v1"
    cid, info = SensorDtypeRegistry.resolve_for_catalog("sentinel-2-c1-l2a", aws_url)
    assert cid in ("sentinel-2-c1-l2a", "sentinel-2-l2a")
    assert info is not None
    assert info.default_dtype.name == "uint16"


def test_resolve_alias_case_insensitive():
    # Provide alias in mixed case and a catalog URL with/without trailing slash
    aws_url = "https://earth-search.aws.element84.com/v1/"
    cid, info = SensorDtypeRegistry.resolve_for_catalog("SENTINEL-2-C1-L2A", aws_url)
    assert cid is not None
    assert info is not None
    assert info.default_dtype.name == "uint16"


def test_resolve_unknown_collection_returns_none():
    cid, info = SensorDtypeRegistry.resolve_for_catalog(
        "this-collection-does-not-exist", None
    )
    assert cid is None
    assert info is None


def test_resolve_none_collection_returns_none():
    cid, info = SensorDtypeRegistry.resolve_for_catalog(None, None)
    assert cid is None
    assert info is None
