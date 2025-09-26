"""Additional observability branch coverage tests."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr

from stac_mcp import observability
from stac_mcp.observability import (
    instrument_tool_execution,
    metrics_latency_snapshot,
    metrics_snapshot,
)


def noop_tool(_c, _a):
    return {"ok": True}


def test_text_log_format(monkeypatch):
    monkeypatch.setenv("STAC_MCP_LOG_LEVEL", "INFO")
    monkeypatch.setenv("STAC_MCP_LOG_FORMAT", "text")
    stderr = io.StringIO()
    with redirect_stderr(stderr):
        observability._logger_initialized = False  # type: ignore[attr-defined]
        observability.init_logging()
        instrument_tool_execution("text_tool", None, noop_tool, None, {})
    out = stderr.getvalue()
    assert "tool_complete" in out  # plain text line
    assert not out.strip().startswith("{")  # Not JSON


def test_metrics_disabled(monkeypatch):
    monkeypatch.setenv("STAC_MCP_ENABLE_METRICS", "false")
    monkeypatch.setenv("STAC_MCP_LOG_FORMAT", "json")
    stderr = io.StringIO()
    with redirect_stderr(stderr):
        observability._logger_initialized = False  # type: ignore[attr-defined]
        observability.init_logging()
        instrument_tool_execution("no_metrics_tool", None, noop_tool, None, {})
    snap = metrics_snapshot()
    # Ensure counter not incremented
    assert not any(
        k.startswith("tool_invocations_total.no_metrics_tool") for k in snap.keys()
    )


def test_trace_enabled(monkeypatch):
    monkeypatch.setenv("STAC_MCP_ENABLE_TRACE", "true")
    monkeypatch.setenv("STAC_MCP_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("STAC_MCP_LOG_FORMAT", "json")
    stderr = io.StringIO()
    with redirect_stderr(stderr):
        observability._logger_initialized = False  # type: ignore[attr-defined]
        observability.init_logging()
        instrument_tool_execution("trace_tool", None, noop_tool, None, {})
    lines = [l for l in stderr.getvalue().splitlines() if l.strip()]
    parsed = [json.loads(l) for l in lines]
    assert any(p.get("event") == "trace_span" for p in parsed)


def test_malformed_latency_buckets_fallback(monkeypatch):
    monkeypatch.setenv("STAC_MCP_LATENCY_BUCKETS_MS", "bad,values")
    monkeypatch.setenv("STAC_MCP_LOG_FORMAT", "json")
    stderr = io.StringIO()
    with redirect_stderr(stderr):
        observability._logger_initialized = False  # type: ignore[attr-defined]
        observability.init_logging()
        instrument_tool_execution("bucket_tool", None, noop_tool, None, {})
    lat = metrics_latency_snapshot()
    # Ensure default buckets were used (> 5 buckets expected)
    key = [k for k in lat.keys() if k.startswith("tool_latency_ms.bucket_tool")][0]
    assert len(lat[key].keys()) > 5
