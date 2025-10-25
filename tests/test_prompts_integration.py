import pytest

from fastmcp.client import Client
import mcp.types

from stac_mcp.fast_server import app


@pytest.fixture
def test_app():
    """Return a clean app for each test."""
    original_tools = app._tool_manager._tools.copy()  # noqa: SLF001
    yield app
    app._tool_manager._tools = original_tools  # noqa: SLF001


@pytest.mark.asyncio
async def test_get_prompt_returns_promptmessage_and_machine_payload(test_app):
    """Ensure get_prompt returns PromptMessage with human text and meta payload."""
    client = Client(test_app)
    async with client:
        result = await client.get_prompt("tool_get_root_prompt")

    # Result should be a GetPromptResult-like object with messages
    assert hasattr(result, "messages")
    assert isinstance(result.messages, list) and len(result.messages) > 0

    msg = result.messages[0]
    # message should have human text
    assert hasattr(msg, "content") and hasattr(msg.content, "text")
    assert isinstance(msg.content.text, str)

    # meta may be exposed on the PromptMessage as `_meta` or as `meta`; accept either
    machine_meta = getattr(msg, "_meta", None) or getattr(msg, "meta", None)
    assert machine_meta is not None, "PromptMessage should expose _meta or meta"
    assert "machine_payload" in machine_meta, "machine_payload should be present in _meta/meta"
    payload = machine_meta["machine_payload"]
    assert isinstance(payload, dict)
    assert payload.get("name") == "get_root"
