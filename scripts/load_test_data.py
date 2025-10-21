"""Load local `test-data/vancouver_subaoi_catalog/items/` into a running STAC API using the Transactions /bulk endpoint if available, or POST /collections/{id}/items as fallback."""
import json
from pathlib import Path
import requests

import os

BASE_URL = os.environ.get("STAC_API_BASE_URL", "http://localhost:8081")
COLLECTION_ID = os.environ.get("STAC_API_COLLECTION_ID", "vancouver-subaoi-collection")
API_KEY = os.environ.get("STAC_API_KEY", "test-secret-key")
ITEMS_DIR = Path(__file__).resolve().parents[1] / "test-data" / "vancouver_subaoi_catalog" / "items"


def build_feature_collection():
    features = []
    for p in ITEMS_DIR.glob("*.json"):
        try:
            features.append(json.loads(p.read_text()))
        except Exception:
            continue
    return {"type": "FeatureCollection", "features": features}


if __name__ == "__main__":
    fc = build_feature_collection()
    # try bulk endpoint
    bulk_url = f"{BASE_URL}/bulk"
    try:
        r = requests.post(bulk_url, json={"method": "upsert", "items": fc["features"]}, timeout=30)
        print("bulk status", r.status_code, r.text)
        if r.status_code == 200:
            print("Loaded via /bulk")
            raise SystemExit(0)
    except Exception as exc:
        print("bulk failed, falling back to collection endpoint", exc)

    # fallback: POST FeatureCollection to collection items endpoint
    items_url = f"{BASE_URL}/collections/{COLLECTION_ID}/items"
    headers = {"Content-Type": "application/json", "X-API-Key": API_KEY}
    try:
        r = requests.post(items_url, json=fc, timeout=30, headers=headers)
        print(r.status_code, r.text)
    except Exception as exc:  # pragma: no cover - best-effort script used in CI
        print("Failed to POST items to collection endpoint", exc)
