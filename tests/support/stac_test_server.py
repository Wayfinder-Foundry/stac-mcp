import json
import logging
import uuid
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="stac-mcp-test-server")

BASE = Path(__file__).resolve().parents[2] / "test-data" / "vancouver_subaoi_catalog"
ITEMS_DIR = BASE / "items"
COLLECTION_FILE = BASE / "collection.json"
CATALOG_FILE = BASE / "catalog.json"

API_KEY = "test-secret-key"


# Simple auth dependency
async def check_api_key(x_api_key: str | None = Header(None)):
    if x_api_key is None:
        return False
    return x_api_key == API_KEY


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text())


@app.get("/catalog.json")
async def get_catalog():
    try:
        return load_json(CATALOG_FILE)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="catalog not found") from None


@app.get("/collection.json")
async def get_collection():
    try:
        return load_json(COLLECTION_FILE)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="collection not found") from None


@app.get("/collections")
async def list_collections():
    try:
        collection = load_json(COLLECTION_FILE)
        return {"collections": [collection]}
    except FileNotFoundError:
        return {"collections": []}


@app.get("/collections/{collection_id}")
async def get_collection_by_id(collection_id: str):  # noqa: ARG001
    # This test server only serves one collection, so ignore the ID check
    try:
        return load_json(COLLECTION_FILE)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404, detail=f"No collection with id '{collection_id}' found!"
        ) from None


@app.get("/collections/{collection_id}/items")
async def list_items(collection_id: str):  # noqa: ARG001
    # naive listing of items directory
    logger = logging.getLogger("stac_mcp.testserver")
    items = []
    if not ITEMS_DIR.exists():
        return {"type": "FeatureCollection", "features": []}
    for p in ITEMS_DIR.glob("*.json"):
        try:
            obj = load_json(p)
            items.append(obj)
        except (JSONDecodeError, OSError) as err:
            logger.debug("skipping item %s: %s", p, err)
            continue
    return {"type": "FeatureCollection", "features": items}


@app.get("/collections/{collection_id}/items/{item_id}")
async def get_item(collection_id: str, item_id: str):  # noqa: ARG001
    p = ITEMS_DIR / f"{item_id}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="item not found") from None
    return load_json(p)


@app.post("/collections/{collection_id}/items")
async def create_item(
    collection_id: str,  # noqa: ARG001
    request: Request,
    x_api_key: str | None = Header(None),
):
    # simple API key check
    allowed = await check_api_key(x_api_key)
    if not allowed:
        raise HTTPException(status_code=401, detail="unauthorized")

    body = await request.json()
    # accept either full Feature or ItemCollection
    if isinstance(body, dict) and body.get("type") == "FeatureCollection":
        created = []
        for feat in body.get("features", []):
            item_id = feat.get("id") or str(uuid.uuid4())
            p = ITEMS_DIR / f"{item_id}.json"
            p.write_text(json.dumps(feat, indent=2))
            created.append(item_id)
        return {"created": created}

    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="invalid item")

    item_id = body.get("id") or str(uuid.uuid4())
    p = ITEMS_DIR / f"{item_id}.json"
    p.write_text(json.dumps(body, indent=2))
    return JSONResponse(status_code=201, content={"id": item_id})


@app.put("/collections/{collection_id}/items/{item_id}")
async def update_item(
    collection_id: str,  # noqa: ARG001
    item_id: str,
    request: Request,
    x_api_key: str | None = Header(None),
):
    allowed = await check_api_key(x_api_key)
    if not allowed:
        raise HTTPException(status_code=401, detail="unauthorized")
    body = await request.json()
    p = ITEMS_DIR / f"{item_id}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="item not found")
    p.write_text(json.dumps(body, indent=2))
    return {"updated": item_id}


@app.delete("/collections/{collection_id}/items/{item_id}")
async def delete_item(
    collection_id: str,  # noqa: ARG001
    item_id: str,
    x_api_key: str | None = Header(None),
):
    allowed = await check_api_key(x_api_key)
    if not allowed:
        raise HTTPException(status_code=401, detail="unauthorized")
    p = ITEMS_DIR / f"{item_id}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="item not found") from None
    p.unlink()
    return {"deleted": item_id}
