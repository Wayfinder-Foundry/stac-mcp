"""Example: run the lightweight in-repo STAC test server and load items.

Usage (dev):

python -m uvicorn tests.support.stac_test_server:app --reload --port 8081

Then POST to http://localhost:8081/collections/vancouver-subaoi-collection/items
with X-API-Key: test-secret-key and a FeatureCollection JSON body.
"""

import requests
import json

BASE = "http://localhost:8081"
API_KEY = "test-secret-key"

EXAMPLE_COLLECTION_ID = "vancouver-subaoi-collection"

FEATURE_COLLECTION = {
    "type": "FeatureCollection",
    "features": []
}

if __name__ == "__main__":
    # simple ping
    try:
        r = requests.get(f"{BASE}/catalog.json")
        print("catalog status:", r.status_code)
    except Exception as exc:
        print("Could not reach test server. Start it with:")
        print("  python -m uvicorn tests.support.stac_test_server:app --reload --port 8081")
        raise

    # Example POST
    headers = {"X-API-Key": API_KEY, "Content-Type": "application/json"}
    print("Posting empty feature collection (no-op):")
    r = requests.post(
        f"{BASE}/collections/{EXAMPLE_COLLECTION_ID}/items",
        headers=headers,
        data=json.dumps(FEATURE_COLLECTION),
    )
    print(r.status_code, r.text)
