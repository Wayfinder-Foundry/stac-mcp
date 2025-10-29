"""
Debug runner: find an item with a .zarr asset and run estimate_data_size to exercise zarr inspection.
"""
import asyncio
from pprint import pprint
from stac_mcp.tools.client import STACClient


def find_zarr_item(client: STACClient, limit: int = 200):
    collections = client.search_collections(limit=50)
    for c in collections:
        cid = c.get("id")
        try:
            items = client.search_items(collections=[cid], limit=5)
        except Exception:
            continue
        for it in items:
            assets = it.get("assets") or {}
            for a_name, a in assets.items():
                href = a.get("href") if isinstance(a, dict) else None
                media = (a.get("media_type") or "") if isinstance(a, dict) else ""
                if href and str(href).lower().endswith(".zarr"):
                    it.setdefault("_matched_asset", {}).update({"name": a_name, "href": href, "media_type": media})
                    return it
                if media and "zarr" in str(media).lower():
                    it.setdefault("_matched_asset", {}).update({"name": a_name, "href": href, "media_type": media})
                    return it
    return None


async def main():
    client = STACClient()
    print("Searching for an item with a .zarr asset (this queries the catalog)...")
    try:
        item = await asyncio.get_event_loop().run_in_executor(None, lambda: find_zarr_item(client))
    except Exception as e:
        print("Catalog search failed:", e)
        return

    if not item:
        print("No zarr asset found in the first search window.")
        return

    coll = item.get("collection")
    matched = item.get("_matched_asset") or {}
    print(f"Found item in collection '{coll}', matched asset: {matched}")

    # Perform a cheap metadata probe of the zarr store root (list top-level
    # entries) before doing any expensive inspection. Use fsspec if available
    # to list the store; fall back gracefully on any error.
    href = matched.get("href")
    if href:
        try:
            import urllib.parse
            import fsspec

            parsed = urllib.parse.urlsplit(href)
            scheme = parsed.scheme or ""
            # Correctly preserve the container (netloc) and path
            container = parsed.netloc
            relpath = parsed.path.lstrip("/")
            container_and_path = f"{container}/{relpath}" if container else relpath

            # Attempt to extract storage_options from the item's matched asset
            storage_options = None
            try:
                assets = item.get("assets") or {}
                matched_name = matched.get("name")
                if matched_name and matched_name in assets:
                    a_obj = assets[matched_name]
                    extra = a_obj.get("extra_fields") or {}
                    # STAC often stores xarray storage options under this key
                    storage_options = extra.get("xarray:storage_options") or extra.get("storage_options")
                    # Also allow direct key if present
                    if storage_options is None:
                        storage_options = a_obj.get("xarray:storage_options")
            except Exception:
                storage_options = None

            print(f"Attempting cheap metadata probe on zarr store: abfs://{container_and_path}")
            if storage_options:
                print("Using storage_options from asset:", storage_options)

            try:
                fs = fsspec.filesystem(scheme, **(storage_options or {}))
                # List top-level entries in the zarr store root (may be keys)
                entries = fs.ls(container_and_path)
                print("Top-level entries (sample):", entries[:20])
                cheap_probe_ok = True
            except Exception as e:
                print("fsspec listing failed:", e)
                cheap_probe_ok = False
        except Exception as e:  # pragma: no cover - optional deps / env
            print("Metadata probe skipped (fsspec unavailable or parse error):", e)
            cheap_probe_ok = False
    else:
        print("No href available for matched asset; skipping metadata probe.")
        cheap_probe_ok = False

    # Default to metadata-only for safety; allow full inspection via CLI flag
    import sys
    inspect_mode = "--inspect" in sys.argv
    print(f"Running estimate (inspect zarr: {inspect_mode})...")
    try:
        res = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: client.estimate_data_size(collections=[coll], limit=1, force_metadata_only=not inspect_mode),
        )
        pprint(res)
    except Exception as e:
        print("Estimate failed:", e)


if __name__ == "__main__":
    asyncio.run(main())
