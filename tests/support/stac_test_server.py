from fastapi import FastAPI, HTTPException, Request, Header, Response
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
from pathlib import Path
import json
import uuid

app = FastAPI(title="stac-mcp-test-server")

BASE = Path(__file__).resolve().parents[2] / "test-data" / "vancouver_subaoi_catalog"
ITEMS_DIR = BASE / "items"
COLLECTION_FILE = BASE / "collection.json"
CATALOG_FILE = BASE / "catalog.json"

API_KEY = "test-secret-key"

# Simple auth dependency
async def check_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key is None:
        return False
    return x_api_key == API_KEY


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    return json.loads(path.read_text())


@app.get("/catalog.json")
async def get_catalog():
    try:
        return load_json(CATALOG_FILE)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="catalog not found")


@app.get("/collection.json")
async def get_collection():
    try:
        return load_json(COLLECTION_FILE)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="collection not found")


@app.get("/collections/{collection_id}/items")
async def list_items(collection_id: str):
    # naive listing of items directory
    items = []
    if not ITEMS_DIR.exists():
        return {"type": "FeatureCollection", "features": []}
    for p in ITEMS_DIR.glob("*.json"):
        try:
            obj = load_json(p)
            items.append(obj)
        except Exception:
            continue
    return {"type": "FeatureCollection", "features": items}


@app.get("/collections/{collection_id}/items/{item_id}")
async def get_item(collection_id: str, item_id: str):
    p = ITEMS_DIR / f"{item_id}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="item not found")
    return load_json(p)


@app.post("/collections/{collection_id}/items")
async def create_item(collection_id: str, request: Request, x_api_key: Optional[str] = Header(None)):
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
async def update_item(collection_id: str, item_id: str, request: Request, x_api_key: Optional[str] = Header(None)):
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
async def delete_item(collection_id: str, item_id: str, x_api_key: Optional[str] = Header(None)):
    allowed = await check_api_key(x_api_key)
    if not allowed:
        raise HTTPException(status_code=401, detail="unauthorized")
    p = ITEMS_DIR / f"{item_id}.json"
    if not p.exists():
        raise HTTPException(status_code=404, detail="item not found")
    p.unlink()
    return {"deleted": item_id}
