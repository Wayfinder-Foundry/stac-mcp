from stac_mcp.tools.client import STACClient
from stac_mcp.tools.execution import handle_search_items

if __name__ == "__main__":
    stac_url = "https://planetarycomputer.microsoft.com/api/stac/v1"
    client = STACClient(catalog_url=stac_url)
    items = handle_search_items(
        client,
        arguments={
            "collections": ["sentinel-2-l2a"],
            "datetime": "2023-01-01/2023-01-31",
            "bbox": [-123.0, 45.0, -122.0, 46.0],
            "sortby": ["properties.datetime", "desc"],
            "limit": 3,
            "output_type": "text",
        },
    )
    # items = client._cached_search(
    # items = client.search_items(
    #     collections=["sentinel-2-l2a"],
    #     datetime="2023-01-01/2023-01-31",
    #     bbox=[-123.0, 45.0, -122.0, 46.0],
    #     # sortby=["properties.datetime", "desc"],
    #     limit=3,
    # )
    # print(items)
    for item in items:
        print(item)
        break
