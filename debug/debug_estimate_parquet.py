"""
Debug runner: find an item with a .parquet asset and run estimate_data_size
using metadata-only fallback to demonstrate parquet handling.
"""
import asyncio
from pprint import pprint

from stac_mcp.tools.client import STACClient


def find_parquet_item(client: STACClient, limit_per_collection: int = 5):
    # Iterate collections (small limit) and inspect items for parquet assets
    collections = client.search_collections(limit=50)
    for c in collections:
        cid = c.get("id")
        try:
            items = client.search_items(collections=[cid], limit=limit_per_collection)
        except Exception:
            continue
        for it in items:
            assets = it.get("assets") or {}
            for a_name, a in assets.items():
                href = a.get("href") if isinstance(a, dict) else None
                media = (a.get("media_type") or "") if isinstance(a, dict) else ""
                if href and str(href).lower().endswith(".parquet"):
                    # attach matched asset info for caller convenience
                    it.setdefault("_matched_asset", {}).update({"name": a_name, "href": href, "media_type": media})
                    return it
                if media and "parquet" in str(media).lower():
                    it.setdefault("_matched_asset", {}).update({"name": a_name, "href": href, "media_type": media})
                    return it
    return None


async def main():
    client = STACClient()
    print("Searching for an item with a .parquet asset (this queries the catalog)...")
    try:
        item = await asyncio.get_event_loop().run_in_executor(None, lambda: find_parquet_item(client))
    except Exception as e:
        print("Catalog search failed:", e)
        return

    if not item:
        print("No parquet asset found in the first search window.")
        return

    coll = item.get("collection")
    print(f"Found item in collection '{coll}', running metadata-only estimate for parquet...")
    try:
        res = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.estimate_data_size(collections=[coll], limit=1, force_metadata_only=True),
        )
        pprint(res)
    except Exception as e:
        print("Estimate failed:", e)


if __name__ == "__main__":
    asyncio.run(main())
