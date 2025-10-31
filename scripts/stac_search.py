
from pystac_client import Client as STACClient

if __name__ == "__main__":
    stac_url = "https://planetarycomputer.microsoft.com/api/stac/v1"
    client = STACClient.open(stac_url)
    search = client.search(
        collections=["sentinel-2-l2a"],
        datetime="2023-01-01/2023-01-31",
        bbox=[-123.0, 45.0, -122.0, 46.0],
        sortby=["properties.datetime", "desc"],
        limit=10,
    )
    for item in search.items_as_dicts():
        print(item.get("id"))