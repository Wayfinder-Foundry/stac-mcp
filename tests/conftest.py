"""Shared pytest fixtures for STAC MCP test suite."""

import json
import logging
import subprocess
import time
from collections.abc import Callable, Iterator
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from urllib.error import HTTPError

import pytest
from fastmcp import Client

from stac_mcp import observability
from stac_mcp.fast_server import app


@pytest.fixture(scope="session", autouse=True)
def prepare_test_data_dir() -> None:
    """Ensure test data directory and files exist before any tests run."""
    base_dir = (
        Path(__file__).resolve().parent.parent
        / "test-data"
        / "vancouver_subaoi_catalog"
    )
    items_dir = base_dir / "items"
    items_dir.mkdir(exist_ok=True, parents=True)

    collection_file = base_dir / "collection.json"
    if not collection_file.exists():
        collection_file.write_text(
            json.dumps(
                {
                    "id": "vancouver-subaoi-collection",
                    "type": "Collection",
                    "stac_version": "1.0.0",
                    "description": "Test collection for integration tests.",
                    "license": "proprietary",
                    "links": [{"rel": "items", "href": "./items"}],
                    "extent": {
                        "spatial": {"bbox": [[-123.3, 49.0, -122.0, 49.5]]},
                        "temporal": {
                            "interval": [
                                ["2020-01-01T00:00:00Z", "2020-02-01T00:00:00Z"]
                            ]
                        },
                    },
                    "summaries": {},
                }
            )
        )

    catalog_file = base_dir / "catalog.json"
    if not catalog_file.exists():
        catalog_file.write_text(
            json.dumps(
                {
                    "id": "vancouver-subaoi-catalog",
                    "type": "Catalog",
                    "stac_version": "1.0.0",
                    "description": "Test catalog for integration tests.",
                    "links": [{"rel": "child", "href": "./collection.json"}],
                    "conformsTo": [
                        "https://api.stacspec.org/v1.0.0/core",
                        "https://api.stacspec.org/v1.0.0/collections",
                        "https://api.stacspec.org/v1.0.0/item-search",
                        "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core",
                        "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/oas30",
                        "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/html",
                        "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/geojson",
                        "https://api.stacspec.org/v1.0.0/collections#transaction",
                    ],
                }
            )
        )


@pytest.fixture(scope="session")
def default_catalog_url() -> str:
    """Return the default STAC catalog URL used in tests."""
    return "http://localhost:8888/catalog.json"


@pytest.fixture
def reset_observability_logger(monkeypatch) -> Iterator[logging.Logger]:
    """Reset observability logger state and return the logger for assertions."""
    logger = logging.getLogger("stac_mcp")
    existing_handlers = list(logger.handlers)
    for handler in existing_handlers:
        logger.removeHandler(handler)
    monkeypatch.setitem(observability._logger_state, "initialized", False)
    monkeypatch.setattr(observability, "_logger_initialized", False, raising=False)
    yield logger
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    for handler in existing_handlers:
        logger.addHandler(handler)


@pytest.fixture
def fresh_metrics_registry(monkeypatch):
    """Provide an isolated metrics registry for observability tests."""
    registry = observability.MetricsRegistry()
    monkeypatch.setattr(observability, "metrics", registry)
    return registry


@pytest.fixture
def make_collection() -> Callable[..., MagicMock]:
    """Fixture returning a configurable collection stub."""

    def _factory(**overrides: Any) -> MagicMock:
        collection = MagicMock()
        collection.id = overrides.get("id", "collection-id")
        collection.title = overrides.get("title")
        collection.description = overrides.get("description", "")
        collection.extent = overrides.get("extent")
        collection.license = overrides.get("license", "")
        collection.providers = overrides.get("providers", [])
        collection.summaries = overrides.get("summaries")
        collection.assets = overrides.get("assets", {})
        return collection

    return _factory


@pytest.fixture
def make_item() -> Callable[..., SimpleNamespace]:
    """Fixture returning a configurable item stub."""

    def _factory(**overrides: Any) -> SimpleNamespace:
        return SimpleNamespace(
            id=overrides.get("id", "item-id"),
            collection_id=overrides.get("collection_id", "collection-id"),
            geometry=overrides.get("geometry"),
            bbox=overrides.get("bbox"),
            datetime=overrides.get("datetime"),
            properties=overrides.get("properties", {}),
            assets=overrides.get("assets", {}),
        )

    return _factory


@pytest.fixture
def collection_payload_factory() -> Callable[..., dict[str, Any]]:
    """Fixture returning a STAC Collection payload dictionary."""

    def _factory(**overrides: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "id": "test-collection",
            "title": "Test Collection",
            "description": "Test collection description",
            "license": "proprietary",
        }
        payload.update(overrides)
        return payload

    return _factory


@pytest.fixture
def item_payload_factory() -> Callable[..., dict[str, Any]]:
    """Fixture returning a STAC Item payload dictionary."""

    def _factory(**overrides: Any) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "collection": overrides.get("collection", "test-collection"),
            "id": overrides.get("id", "test-item"),
        }
        payload.update(overrides)
        return payload

    return _factory


@pytest.fixture
def http_response_factory() -> Callable[[Any, int], MagicMock]:
    """Build a context-manager mock emulating ``urllib`` JSON responses."""

    def _factory(payload: Any, status_code: int = 200) -> MagicMock:
        response = MagicMock()
        body = b"" if payload is None else json.dumps(payload).encode("utf-8")
        response.read.return_value = body
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.status = status_code
        response.code = status_code
        return response

    return _factory


@pytest.fixture
def http_error_factory() -> Callable[[int, str | None], HTTPError]:
    """Factory creating ``HTTPError`` instances for testing."""

    def _factory(status_code: int, url: str | None = None) -> HTTPError:
        return HTTPError(
            url or "https://example.com", status_code, "HTTP Error", {}, BytesIO()
        )

    return _factory


@pytest.fixture(scope="session")
def stac_test_server_process() -> Iterator[subprocess.Popen]:
    """Run the test STAC server in a background process."""
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "uvicorn",
            "tests.support.stac_test_server:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8888",
        ]
    )
    time.sleep(2)  # Give the server a moment to start
    yield process
    process.terminate()
    process.wait()


@pytest.fixture
def stac_test_server(stac_test_server_process) -> Iterator[dict[str, Any]]:
    """Mock HTTP requests to the test STAC server."""
    api_key = "test-secret-key"
    mcp_client = Client(app)
    return {"client": mcp_client, "api_key": api_key}
