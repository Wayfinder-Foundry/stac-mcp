from stac_mcp.tools.client import STACClient

client = STACClient(catalog_url="https://planetarycomputer.microsoft.com/api/stac/v1")
res = client.get_queryables(collection_id="sentinel-2-l2a")
print(res.keys())
print(list(res.get("queryables", {}).keys())[:20])
