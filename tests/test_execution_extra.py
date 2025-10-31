import json
from types import SimpleNamespace

import pytest

from stac_mcp.tools import execution


@pytest.mark.asyncio
async def test_execute_tool_unknown():
    with pytest.raises(ValueError):  # noqa: PT011
        _ = [item async for item in execution.execute_tool("this_tool_does_not_exist")]


@pytest.mark.asyncio
async def test_execute_tool_json_modes(monkeypatch):
    # Non-pystac path: monkeypatch instrument_tool_execution to return our value
    def fake_instrument(name, catalog_url, handler, client, arguments):  # noqa: ARG001
        # Simulate the wrapper object with .value
        return SimpleNamespace(value=handler(client, arguments))

    monkeypatch.setattr(execution, "instrument_tool_execution", fake_instrument)

    # Handler returning a list -> text_fallback mode
    def list_handler(client, arguments):  # noqa: ARG001
        return ["a", "b"]

    res = [
        item
        async for item in execution.execute_tool(
            "search_items", arguments={"output_format": "json"}, handler=list_handler
        )
    ]
    assert len(res) == 1
    payload = json.loads(res[0].text)
    assert payload["mode"] == "text_fallback"
    assert isinstance(payload["content"], list)

    # Handler returning a dict -> json mode
    def dict_handler(client, arguments):  # noqa: ARG001
        return {"ok": True}

    res = [
        item
        async for item in execution.execute_tool(
            "search_items", arguments={"output_format": "json"}, handler=dict_handler
        )
    ]
    payload = json.loads(res[0].text)
    assert payload["mode"] == "json"
    assert payload["data"]["ok"] is True
