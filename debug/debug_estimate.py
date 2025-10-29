from types import SimpleNamespace

import odc.stac as odc_stac

from stac_mcp.tools.client import STACClient

# force odc.stac.load to raise

def _raise_no_raster(*_args, **_kwargs):
    raise RuntimeError("no raster")

odc_stac.load = _raise_no_raster

size_bytes = 4096
asset = {
    "href": "https://example.com/data.parquet",
    "media_type": "application/x-parquet",
    "extra_fields": {"file:bytes": str(size_bytes)},
}
item = SimpleNamespace(collection_id="fia", assets={"data": asset}, datetime=None)

client = STACClient()
client._client = SimpleNamespace(search=lambda **_: SimpleNamespace(items=lambda: [item]))

res = client.estimate_data_size(collections=["fia"], limit=10)
print(res)
