import pytest

from fastmcp.client import Client

from stac_mcp.fast_server import app


@pytest.fixture
def test_app():
    """Return a clean app for each test."""
    original_tools = app._tool_manager._tools.copy()  # noqa: SLF001
    yield app
    app._tool_manager._tools = original_tools  # noqa: SLF001


@pytest.mark.asyncio
async def test_get_prompt_messages_include_machine_payload_for_all_prompts(test_app):
    """For each registered prompt, get_prompt() returns a PromptMessage with
    `_meta['machine_payload']` available so agents may call tools programmatically.
    """
    client = Client(test_app)
    async with client:
        prompts = await client.list_prompts()

        # Collect prompt names
        names = [getattr(p, "name", None) for p in prompts]

        assert len(names) > 0

        # Ensure each prompt's rendered message includes _meta.machine_payload
        for name in names:
            if not name:
                continue
            result = await client.get_prompt(name)
            assert hasattr(result, "messages") and len(result.messages) > 0
            msg = result.messages[0]
            # PromptMessage should expose machine_payload on either `_meta` or `meta`
            machine_meta = getattr(msg, "_meta", None) or getattr(msg, "meta", None)
            assert machine_meta is not None, f"Prompt {name} did not include _meta or meta"
            assert "machine_payload" in machine_meta, f"Prompt {name} missing machine_payload in _meta/meta"


@pytest.mark.asyncio
async def test_list_prompts_descriptor_exposes_decorator_meta(test_app):
    """Ensure prompt descriptors returned by list_prompts expose the
    decorator-provided metadata as `.meta` so clients can discover schemas.
    """
    client = Client(test_app)
    async with client:
        prompts = await client.list_prompts()

    assert isinstance(prompts, list) and len(prompts) > 0

    # Every prompt descriptor should at least have a `.meta` attribute (may be empty)
    for p in prompts:
        meta = getattr(p, "meta", None)
        assert meta is not None, f"Prompt descriptor {getattr(p,'name', '<no-name>')} missing .meta"
