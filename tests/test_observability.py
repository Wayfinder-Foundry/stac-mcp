"""Tests for observability layer (ADR 0012)."""

import io
import json
from contextlib import redirect_stderr, redirect_stdout

from stac_mcp import observability
from stac_mcp.observability import (
    instrument_tool_execution,
    metrics_latency_snapshot,
    metrics_snapshot,
    new_correlation_id,
)


def dummy_tool(_client, _args):  # pragma: no cover - trivial
    return {"ok": True}


def test_correlation_id_uniqueness():
    ids = {new_correlation_id() for _ in range(20)}
    assert len(ids) == 20


def test_instrument_tool_success_logs_and_metrics(monkeypatch):
    monkeypatch.setenv("STAC_MCP_LOG_LEVEL", "INFO")
    monkeypatch.setenv("STAC_MCP_LOG_FORMAT", "json")
    stderr = io.StringIO()
    stdout = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        # Force re-init inside capture context
        observability._logger_initialized = False  # type: ignore[attr-defined]
        observability.init_logging()
        result = instrument_tool_execution("test_tool", None, dummy_tool, None, {})
    # Ensure result value returned
    assert result.value == {"ok": True}
    # Metrics incremented
    snap = metrics_snapshot()
    assert any(k.startswith("tool_invocations_total.test_tool") for k in snap)
    # Logs should be in stderr only
    assert stdout.getvalue() == ""
    log_text = stderr.getvalue().strip().splitlines()
    assert log_text  # at least one line
    # JSON formatted line should parse
    parsed = json.loads(log_text[-1])
    assert parsed["event"] == "tool_complete"
    assert parsed["tool_name"] == "test_tool"
    # Latency histogram should have at least one bucket increment
    lat = metrics_latency_snapshot()
    key = next(iter(lat))
    total = sum(lat[key].values())
    assert total >= 1


def test_instrument_tool_error(monkeypatch):
    monkeypatch.setenv("STAC_MCP_LOG_LEVEL", "INFO")
    monkeypatch.setenv("STAC_MCP_LOG_FORMAT", "json")

    def failing_tool(_client, _args):  # pragma: no cover - simple failure
        raise TimeoutError("Simulated timeout")

    stderr = io.StringIO()
    with redirect_stderr(stderr):
        observability._logger_initialized = False  # type: ignore[attr-defined]
        observability.init_logging()
        try:
            instrument_tool_execution("timeout_tool", None, failing_tool, None, {})
            assert False, "Expected exception"
        except TimeoutError:
            pass
    lines = [l for l in stderr.getvalue().splitlines() if l.strip()]
    assert lines
    parsed = json.loads(lines[-1])
    # Either tool_error or previous line may be tool_error; search all
    found = False
    for line in lines:
        p = json.loads(line)
        if p.get("event") == "tool_error":
            assert p.get("error_type") == "TimeoutError"
            found = True
    assert found, "Did not find tool_error log line"
    # Latency histogram should record the failing invocation exactly once
    lat = metrics_latency_snapshot()
    # Find tool_latency histogram key
    matching = [k for k in lat.keys() if k.startswith("tool_latency_ms.timeout_tool")]
    assert matching, "Expected latency histogram entry for failing tool"
    counts = lat[matching[0]]
    total = sum(counts.values())
    assert (
        total == 1
    ), f"Expected exactly one latency observation for failure, got {total}"
