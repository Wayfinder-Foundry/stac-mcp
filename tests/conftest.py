"""Shared pytest fixtures for STAC MCP test suite."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterator  # noqa: TC003
from io import BytesIO
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock
from urllib.error import HTTPError

import pytest

from stac_mcp import observability
from stac_mcp.tools.client import STACClient


@pytest.fixture
def default_catalog_url() -> str:
    """Return the default STAC catalog URL used in tests."""

    return "https://example.com"


@pytest.fixture
def stac_client_factory(
    default_catalog_url: str,
) -> Callable[
    [str | None, dict[str, str] | None, list[str] | None],
    tuple[STACClient, MagicMock],
]:
    """Factory creating a ``STACClient`` with a mocked underlying client."""

    def _factory(
        url: str | None = None,
        headers: dict[str, str] | None = None,
        conformance: list[str] | None = None,
    ) -> tuple[STACClient, MagicMock]:
        client = STACClient(url or default_catalog_url, headers=headers)
        inner_client = MagicMock()
        client._client = inner_client  # noqa: SLF001 - tests intentionally inject mocks
        if conformance is not None:
            client._conformance = list(conformance)  # noqa: SLF001 - tests control cache
        return client, inner_client

    return _factory


@pytest.fixture
def stac_transactions_client(
    stac_client_factory: Callable[
        [str | None, dict[str, str] | None, list[str] | None],
        tuple[STACClient, MagicMock],
    ],
) -> STACClient:
    """Return a ``STACClient`` pre-configured for transaction operations."""

    conformance = ["https://api.stacspec.org/v1.0.0/collections#transaction"]
    client, _ = stac_client_factory(conformance=conformance)
    return client


@pytest.fixture
def reset_observability_logger(monkeypatch) -> Iterator[logging.Logger]:
    """Reset observability logger state and return the logger for assertions."""

    logger = logging.getLogger("stac_mcp")
    existing_handlers = list(logger.handlers)
    for handler in existing_handlers:
        logger.removeHandler(handler)
    monkeypatch.setitem(observability._logger_state, "initialized", False)  # noqa: SLF001
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
