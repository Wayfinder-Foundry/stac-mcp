import pytest
from fastmcp.client import Client

from stac_mcp.server import app


@pytest.fixture
def test_app():
    """Return a clean app for each test."""
    original_tools = app._tool_manager._tools.copy()  # noqa: SLF001
    yield app
    app._tool_manager._tools = original_tools  # noqa: SLF001


@pytest.mark.asyncio
async def test_list_prompts_exposes__meta_and_schema(test_app):
    """Ensure client.list_prompts() returns Prompt metadata under `_meta`.

    The prompt decorator supplied `meta` (schema/example) which the server
    exposes to clients via the `_meta` field on prompt descriptors.
    """
    client = Client(test_app)
    async with client:
        prompts = await client.list_prompts()

    assert isinstance(prompts, list)
    assert len(prompts) > 0

    # At least one prompt should expose metadata with schema information.
    # Some prompt descriptors expose it as `meta` while prompt messages use `_meta`.
    found_schema = False
    for p in prompts:
        meta = getattr(p, "_meta", None) or getattr(p, "meta", None)
        if meta and isinstance(meta, dict) and "schema" in meta:
            found_schema = True
            break

    assert found_schema, "Expected at least one prompt to expose metadata with a schema"
