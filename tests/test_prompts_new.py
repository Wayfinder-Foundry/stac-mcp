import pytest
from fastmcp.client import Client

from stac_mcp.fast_server import app

NEW_PROMPTS = [
    "catalog_discovery_prompt",
    "collection_alias_resolution_prompt",
    "estimate_size_strategy_prompt",
    "explain_tool_output_prompt",
    "sensor_registry_info_prompt",
]


@pytest.mark.asyncio
async def test_prompts_registered_and_return_machine_payload():
    client = Client(app)
    async with client:
        for name in NEW_PROMPTS:
            # get_prompt expects the registered prompt name (for example,
            # 'catalog_discovery_prompt')
            res = await client.get_prompt(name)
            assert hasattr(res, "messages")
            assert len(res.messages) > 0
            msg = res.messages[0]
            machine_meta = getattr(msg, "_meta", None) or getattr(msg, "meta", None)
            assert machine_meta is not None, f"Prompt {name} should expose _meta/meta"
            assert "machine_payload" in machine_meta, (
                f"Prompt {name} should include machine_payload"
            )
            payload = machine_meta["machine_payload"]
            assert isinstance(payload, dict)
            assert "name" in payload
