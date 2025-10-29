import sys
from types import SimpleNamespace

# Create fake odc.stac module to match tests behavior
fake_odc = type(sys)("odc")
fake_stac = SimpleNamespace(load=lambda *_, **__: (_ for _ in ()).throw(RuntimeError("no raster")))
fake_odc.stac = fake_stac
sys.modules["odc"] = fake_odc
sys.modules["odc.stac"] = fake_stac

from stac_mcp.tools.client import STACClient

size_bytes = 4096
asset = {
    "href": "https://example.com/data.parquet",
    "media_type": "application/x-parquet",
    "extra_fields": {"file:bytes": str(size_bytes)},
}
from types import SimpleNamespace

item = SimpleNamespace(collection_id="fia", assets={"data": asset}, datetime=None)

client = STACClient()
client._client = SimpleNamespace(search=lambda **_: SimpleNamespace(items=lambda: [item]))

res = client.estimate_data_size(collections=["fia"], limit=10)
print("result:", res)
print("assets_analyzed:", res.get("assets_analyzed"))
