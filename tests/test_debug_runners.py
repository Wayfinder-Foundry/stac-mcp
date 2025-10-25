"""Unit tests for debug finder helpers (parquet/zarr)."""

import importlib.util
import pathlib

_HERE = pathlib.Path(__file__).resolve().parent.parent
_DEBUG = _HERE / "debug"


def _load_mod(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


dp = _load_mod("debug_estimate_parquet", _DEBUG / "debug_estimate_parquet.py")
dz = _load_mod("debug_estimate_zarr", _DEBUG / "debug_estimate_zarr.py")


class _MockClient:
    def __init__(self, collections, items_by_collection):
        self._collections = collections
        self._items = items_by_collection

    def search_collections(self, limit=50):
        return [{"id": c} for c in self._collections][:limit]

    def search_items(self, collections=None, limit=5):
        cid = collections[0]
        return self._items.get(cid, [])[:limit]


def test_find_parquet_item_attaches_match():
    items = [
        {
            "id": "i1",
            "collection": "c1",
            "assets": {
                "a": {
                    "href": "http://x/file.parquet",
                    "media_type": "application/x-parquet",
                }
            },
        }
    ]
    client = _MockClient(["c1"], {"c1": items})
    found = dp.find_parquet_item(client)
    assert found is not None
    assert found.get("_matched_asset")


def test_find_zarr_item_attaches_match():
    items = [
        {
            "id": "i2",
            "collection": "c2",
            "assets": {
                "b": {"href": "http://x/store.zarr", "media_type": "application/x-zarr"}
            },
        }
    ]
    client = _MockClient(["c2"], {"c2": items})
    found = dz.find_zarr_item(client)
    assert found is not None
    assert found.get("_matched_asset")
