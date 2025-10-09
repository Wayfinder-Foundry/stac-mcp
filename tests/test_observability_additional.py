"""Additional observability branch coverage tests."""

from __future__ import annotations

import io
import json
from contextlib import redirect_stderr

import pytest

from stac_mcp import observability
from stac_mcp.observability import (
    instrument_tool_execution,
    metrics_gauge_snapshot,
    metrics_latency_snapshot,
    metrics_snapshot,
)

MIN_DEFAULT_BUCKETS = 5


def noop_tool(_c, _a):
    return {"ok": True}


def failing_tool(_c, _a):
    msg = "boom"
    raise RuntimeError(msg)


@pytest.mark.usefixtures("reset_observability_logger")
def test_text_log_format(monkeypatch):
    monkeypatch.setenv("STAC_MCP_LOG_LEVEL", "INFO")
    monkeypatch.setenv("STAC_MCP_LOG_FORMAT", "text")
    stderr = io.StringIO()
    with redirect_stderr(stderr):
        observability.init_logging()
        instrument_tool_execution("text_tool", None, noop_tool, None, {})
    out = stderr.getvalue()
    assert "tool_complete" in out  # plain text line
    assert not out.strip().startswith("{")  # Not JSON


@pytest.mark.usefixtures("reset_observability_logger")
def test_metrics_disabled(monkeypatch, fresh_metrics_registry):
    monkeypatch.setenv("STAC_MCP_ENABLE_METRICS", "false")
    monkeypatch.setenv("STAC_MCP_LOG_FORMAT", "json")
    stderr = io.StringIO()
    with redirect_stderr(stderr):
        observability.init_logging()
        instrument_tool_execution("no_metrics_tool", None, noop_tool, None, {})
    snap = metrics_snapshot()
    # Ensure counter not incremented
    assert not any(k.startswith("tool_invocations_total.no_metrics_tool") for k in snap)
    assert fresh_metrics_registry.snapshot() == snap


@pytest.mark.usefixtures("reset_observability_logger", "fresh_metrics_registry")
def test_trace_enabled(monkeypatch):
    monkeypatch.setenv("STAC_MCP_ENABLE_TRACE", "true")
    monkeypatch.setenv("STAC_MCP_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("STAC_MCP_LOG_FORMAT", "json")
    stderr = io.StringIO()
    with redirect_stderr(stderr):
        observability.init_logging()
        instrument_tool_execution("trace_tool", None, noop_tool, None, {})
    lines = [line for line in stderr.getvalue().splitlines() if line.strip()]
    parsed = [json.loads(line) for line in lines]
    assert any(p.get("event") == "trace_span" for p in parsed)


@pytest.mark.usefixtures("reset_observability_logger", "fresh_metrics_registry")
def test_malformed_latency_buckets_fallback(monkeypatch):
    monkeypatch.setenv("STAC_MCP_LATENCY_BUCKETS_MS", "bad,values")
    monkeypatch.setenv("STAC_MCP_LOG_FORMAT", "json")
    stderr = io.StringIO()
    with redirect_stderr(stderr):
        observability.init_logging()
        instrument_tool_execution("bucket_tool", None, noop_tool, None, {})
    lat = metrics_latency_snapshot()
    # Ensure default buckets were used (> 5 buckets expected)
    key = next(k for k in lat if k.startswith("tool_latency_ms.bucket_tool"))
    assert len(lat[key]) > MIN_DEFAULT_BUCKETS


def test_tool_success_metrics(monkeypatch, fresh_metrics_registry):
    monkeypatch.delenv("STAC_MCP_ENABLE_METRICS", raising=False)
    instrument_tool_execution("metrics_tool", None, noop_tool, None, {})

    snap = metrics_snapshot()
    assert snap.get("tool_invocations_total.metrics_tool") == 1
    assert snap.get("tool_success_total.metrics_tool") == 1
    assert snap.get("tool_invocations_total._all", 0) >= 1
    assert snap.get("tool_inflight_current.metrics_tool") == 0

    gauges = metrics_gauge_snapshot()
    duration_gauge = gauges.get("tool_last_duration_ms.metrics_tool")
    assert duration_gauge is not None
    assert duration_gauge >= 0.0
    assert fresh_metrics_registry.snapshot() == snap


def test_tool_failure_metrics(monkeypatch, fresh_metrics_registry):
    monkeypatch.delenv("STAC_MCP_ENABLE_METRICS", raising=False)
    with pytest.raises(RuntimeError, match="boom"):
        instrument_tool_execution("failing_tool", None, failing_tool, None, {})

    snap = metrics_snapshot()
    assert snap.get("tool_failure_total.failing_tool") == 1
    assert snap.get("tool_errors_total.failing_tool.UnknownError") == 1

    gauges = metrics_gauge_snapshot()
    error_gauge = gauges.get("tool_last_error_duration_ms.failing_tool")
    assert error_gauge is not None
    assert error_gauge >= 0.0
    assert fresh_metrics_registry.snapshot() == snap
