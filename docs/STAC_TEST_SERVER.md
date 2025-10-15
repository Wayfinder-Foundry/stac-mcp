# STAC Test Server — local and CI

This project provides two approaches for testing STAC interactions:

1. Lightweight in-repo FastAPI test server (fast, file-backed) — useful for local dev and fast tests.
2. Full integration stack using `stac-fastapi` + PostGIS (real STAC API) — useful for CI integration and conformance checks.

## 1) Run the in-repo test server (dev)

Start the server with uvicorn (port 8081 recommended):

```bash
pip install -e ".[dev]"
python -m uvicorn tests.support.stac_test_server:app --reload --port 8081
```

Example usage:

```bash
# POST an empty FeatureCollection (requires X-API-Key)
curl -X POST "http://localhost:8081/collections/vancouver-subaoi-collection/items" \
  -H "X-API-Key: test-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"type":"FeatureCollection","features":[]}'
```

This server reads/writes item JSON files under `test-data/vancouver_subaoi_catalog/items/`.

## 2) Run the full integration stack (CI)

A `docker-compose.stac.yml` stub is provided to run PostGIS and the `stac-fastapi` image.

Start it locally:

```bash
docker-compose -f docker-compose.stac.yml up --build -d
# wait for services to be healthy
```

Load the test data into the live server:

```bash
python scripts/load_test_data.py
```

Run the validator (example):

```bash
docker run --rm stacutils/stac-api-validator --url http://localhost:8080
```

## CI Recommendations
- Add a GitHub Actions job that brings up the docker-compose stack, runs `scripts/load_test_data.py`, runs the validator, then runs a small integration test set.
- Keep most unit tests against mocks for speed; use the in-repo server for integration-like tests in unit suites, and run real stac-fastapi integration checks in CI only.
