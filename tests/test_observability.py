"""Tests for observability layer (ADR 0012)."""

import io
import json
from contextlib import redirect_stderr, redirect_stdout

import pytest

from stac_mcp import observability
from stac_mcp.observability import (
    instrument_tool_execution,
    metrics_latency_snapshot,
    metrics_snapshot,
    new_correlation_id,
)


def dummy_tool(_client, _args):  # pragma: no cover - trivial
    return {"ok": True}


NUM_IDS = 20


def test_correlation_id_uniqueness():
    ids = {new_correlation_id() for _ in range(NUM_IDS)}
    assert len(ids) == NUM_IDS


def test_instrument_tool_success_logs_and_metrics(monkeypatch):
    monkeypatch.setenv("STAC_MCP_LOG_LEVEL", "INFO")
    monkeypatch.setenv("STAC_MCP_LOG_FORMAT", "json")
    stderr = io.StringIO()
    stdout = io.StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        # Force re-init inside capture context
        observability._logger_initialized = False  # noqa: SLF001
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
        msg = "Simulated timeout"
        raise TimeoutError(msg)

    stderr = io.StringIO()
    with redirect_stderr(stderr):
        # Force re-init inside capture context
        observability._logger_initialized = False  # noqa: SLF001
        observability.init_logging()
        with pytest.raises(TimeoutError):
            instrument_tool_execution("timeout_tool", None, failing_tool, None, {})

    lines = [line for line in stderr.getvalue().splitlines() if line.strip()]
    assert lines
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
    key_filter = (
        k for k in lat if k.startswith("tool_latency_ms.timeout_tool")
    )
    matching_key = next(key_filter, None)
    assert matching_key, "Expected latency histogram entry for failing tool"
    counts = lat[matching_key]
    total = sum(counts.values())
    assert (
        total == 1
    ), f"Expected exactly one latency observation for failure, got {total}"
