import pytest

from stac_mcp.tools.client import ConformanceError, STACClient

BYTES_2K = 2048


def test_size_from_metadata_dict_and_keys():
    c = STACClient()
    asset = {"extra_fields": {"file:bytes": "2048"}}
    assert c._size_from_metadata(asset) == BYTES_2K  # noqa: SLF001


def test_size_from_metadata_object_get():
    four_bytes = 4096

    class Obj:
        def __init__(self):
            self._d = {"bytes": f"{four_bytes}"}

        def get(self, key):
            return self._d.get(key)

    c = STACClient()
    assert c._size_from_metadata(Obj()) == four_bytes  # noqa: SLF001


def test_asset_to_dict_various_paths(monkeypatch):
    c = STACClient()
    # use the fixture name so pytest recognizes it and avoid unused-arg linter warning
    _ = monkeypatch

    # dict passthrough
    d = {"href": "x", "media_type": "mt"}
    assert c._asset_to_dict(d)["href"] == "x"  # noqa: SLF001

    # object with to_dict
    class HasToDict:
        def to_dict(self):
            return {"href": "y", "media_type": "m"}

    assert c._asset_to_dict(HasToDict())["href"] == "y"  # noqa: SLF001

    # object where to_dict raises -> fallback to attributes
    class BadToDict:
        def to_dict(self):
            msg = "bad"
            raise TypeError(msg)

        twelve_bytes = 12
        href = "z"
        media_type = "mm"
        extra_fields = {"file:bytes": f"{twelve_bytes}"}  # noqa: RUF012

    res = c._asset_to_dict(BadToDict())  # noqa: SLF001
    assert res["href"] == "z"


def test_check_conformance_raises():
    c = STACClient()
    # force conformance to empty list (test internal behavior)
    c._conformance = []  # noqa: SLF001
    with pytest.raises(ConformanceError):
        c._check_conformance(["http://example.com/unsupported"])  # noqa: SLF001
