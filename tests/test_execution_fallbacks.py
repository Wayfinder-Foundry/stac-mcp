"""Tests for execution fallback branches in tools.execution."""

from __future__ import annotations

import json

import pytest
from mcp.types import TextContent

from stac_mcp import server as _server
from stac_mcp.tools import execution


class DummyClient:
    pass


@pytest.mark.asyncio
async def test_json_fallback_mode(monkeypatch):
    def handler(_client, _args):
        return [
            TextContent(type="text", text="Line1"),
            TextContent(type="text", text="Line2"),
        ]

    monkeypatch.setitem(
        execution._TOOL_HANDLERS,  # noqa: SLF001
        "dummy_tool",
        handler,
    )

    monkeypatch.setattr(_server, "stac_client", DummyClient())
    result = await execution.execute_tool("dummy_tool", {"output_format": "json"})
    assert len(result) == 1
    payload = json.loads(result[0].text)
    assert payload["mode"] == "text_fallback"
    assert payload["content"] == ["Line1", "Line2"]


@pytest.mark.asyncio
async def test_dict_to_text_conversion(monkeypatch):
    def handler(_client, _args):
        return {"a": 1, "b": 2}

    monkeypatch.setitem(
        execution._TOOL_HANDLERS,  # noqa: SLF001
        "dict_tool",
        handler,
    )

    monkeypatch.setattr(_server, "stac_client", DummyClient())
    result = await execution.execute_tool("dict_tool", {"output_format": "text"})
    assert isinstance(result, list)
    assert "\n" in result[0].text or result[0].text.startswith("{")
    assert '"a"' in result[0].text or "'a'" in result[0].text
