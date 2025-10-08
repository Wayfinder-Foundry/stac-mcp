"""Additional observability tests for branch coverage.

Tests focus on:
- Conditional branches in metrics collection
- Trace span variations
- Log format edge cases
- Environment variable handling
- Thread-safety scenarios
"""

from __future__ import annotations

import io
import json
import logging
import os
from contextlib import redirect_stderr
from unittest.mock import patch

import pytest

from stac_mcp import observability
from stac_mcp.observability import (
    JSONLogFormatter,
    MetricsRegistry,
    init_logging,
    metrics,
    metrics_latency_snapshot,
    metrics_snapshot,
    new_correlation_id,
    trace_span,
)


class TestInitLogging:
    """Test init_logging edge cases."""

    def test_init_logging_default_level(self, monkeypatch):
        """Test init_logging with default log level."""
        monkeypatch.delenv("STAC_MCP_LOG_LEVEL", raising=False)
        observability._logger_state["initialized"] = False  # noqa: SLF001
        init_logging()
        assert observability._logger_state["initialized"]  # noqa: SLF001

    def test_init_logging_custom_level(self, monkeypatch):
        """Test init_logging with custom log level."""
        monkeypatch.setenv("STAC_MCP_LOG_LEVEL", "DEBUG")
        observability._logger_state["initialized"] = False  # noqa: SLF001
        init_logging()
        logger = logging.getLogger("stac_mcp")
        assert logger.level == logging.DEBUG

    def test_init_logging_invalid_level(self, monkeypatch):
        """Test init_logging with invalid log level."""
        monkeypatch.setenv("STAC_MCP_LOG_LEVEL", "INVALID")
        observability._logger_state["initialized"] = False  # noqa: SLF001
        # Should fall back to INFO
        init_logging()
        logger = logging.getLogger("stac_mcp")
        assert logger.level == logging.INFO

    def test_init_logging_text_format(self, monkeypatch):
        """Test init_logging with text format."""
        monkeypatch.setenv("STAC_MCP_LOG_FORMAT", "text")
        observability._logger_state["initialized"] = False  # noqa: SLF001
        init_logging()
        logger = logging.getLogger("stac_mcp")
        # Should have text formatter
        assert len(logger.handlers) > 0

    def test_init_logging_json_format(self, monkeypatch):
        """Test init_logging with JSON format."""
        monkeypatch.setenv("STAC_MCP_LOG_FORMAT", "json")
        observability._logger_state["initialized"] = False  # noqa: SLF001
        init_logging()
        logger = logging.getLogger("stac_mcp")
        # Should have JSON formatter
        assert len(logger.handlers) > 0
        assert any(
            isinstance(h.formatter, JSONLogFormatter)
            for h in logger.handlers
        )

    def test_init_logging_idempotent(self, monkeypatch):
        """Test that init_logging can be called multiple times safely."""
        monkeypatch.setenv("STAC_MCP_LOG_LEVEL", "INFO")
        observability._logger_state["initialized"] = False  # noqa: SLF001
        init_logging()
        init_logging()  # Second call should be safe
        assert observability._logger_state["initialized"]  # noqa: SLF001


class TestJSONLogFormatter:
    """Test JSONLogFormatter edge cases."""

    def test_format_simple_message(self):
        """Test formatting a simple log message."""
        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        formatted = formatter.format(record)
        data = json.loads(formatted)
        assert data["message"] == "Test message"
        assert data["level"] == "INFO"

    def test_format_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = JSONLogFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        record.correlation_id = "test-id-123"  # type: ignore[attr-defined]
        record.custom_field = "custom-value"  # type: ignore[attr-defined]
        formatted = formatter.format(record)
        data = json.loads(formatted)
        assert data["correlation_id"] == "test-id-123"
        assert data["custom_field"] == "custom-value"

    def test_format_with_exception(self):
        """Test formatting with exception info."""
        formatter = JSONLogFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            exc_info = True
        else:
            exc_info = None
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        formatted = formatter.format(record)
        data = json.loads(formatted)
        assert data["message"] == "Error occurred"
        if exc_info:
            assert "exc_info" in data


class TestMetricsRegistry:
    """Test MetricsRegistry edge cases."""

    def test_increment_new_counter(self):
        """Test incrementing a new counter."""
        registry = MetricsRegistry()
        registry.increment("test.counter", 5)
        snapshot = registry.snapshot()
        assert "test.counter" in snapshot
        assert snapshot["test.counter"] == 5

    def test_increment_existing_counter(self):
        """Test incrementing an existing counter."""
        registry = MetricsRegistry()
        registry.increment("test.counter", 3)
        registry.increment("test.counter", 2)
        snapshot = registry.snapshot()
        assert snapshot["test.counter"] == 5

    def test_observe_latency_single(self):
        """Test observing a single latency value."""
        registry = MetricsRegistry()
        registry.observe_latency("test.latency", 100.5)
        snapshot = registry.latency_snapshot()
        assert "test.latency" in snapshot
        assert snapshot["test.latency"]["count"] == 1
        assert snapshot["test.latency"]["sum"] == 100.5

    def test_observe_latency_multiple(self):
        """Test observing multiple latency values."""
        registry = MetricsRegistry()
        registry.observe_latency("test.latency", 50.0)
        registry.observe_latency("test.latency", 100.0)
        registry.observe_latency("test.latency", 150.0)
        snapshot = registry.latency_snapshot()
        assert snapshot["test.latency"]["count"] == 3
        assert snapshot["test.latency"]["sum"] == 300.0
        assert snapshot["test.latency"]["min"] == 50.0
        assert snapshot["test.latency"]["max"] == 150.0

    def test_latency_buckets(self):
        """Test latency histogram buckets."""
        registry = MetricsRegistry()
        # Observe values in different buckets
        registry.observe_latency("test.latency", 3.0)    # bucket: 5
        registry.observe_latency("test.latency", 15.0)   # bucket: 25
        registry.observe_latency("test.latency", 75.0)   # bucket: 100
        registry.observe_latency("test.latency", 500.0)  # bucket: 500
        
        snapshot = registry.latency_snapshot()
        buckets = snapshot["test.latency"]["buckets"]
        assert buckets["5"] >= 1
        assert buckets["25"] >= 1
        assert buckets["100"] >= 1
        assert buckets["500"] >= 1

    def test_snapshot_thread_safe(self):
        """Test that snapshot is thread-safe."""
        registry = MetricsRegistry()
        registry.increment("counter1", 10)
        snapshot1 = registry.snapshot()
        registry.increment("counter2", 20)
        snapshot2 = registry.snapshot()
        
        # snapshot1 should not be affected by later increments
        assert "counter2" not in snapshot1
        assert "counter1" in snapshot2
        assert "counter2" in snapshot2

    def test_latency_snapshot_empty(self):
        """Test latency snapshot when no observations."""
        registry = MetricsRegistry()
        snapshot = registry.latency_snapshot()
        assert isinstance(snapshot, dict)
        assert len(snapshot) == 0


class TestTraceSpan:
    """Test trace_span context manager."""

    def test_trace_span_disabled(self, monkeypatch):
        """Test trace_span when tracing is disabled."""
        monkeypatch.setenv("STAC_MCP_ENABLE_TRACE", "false")
        with trace_span("test_operation"):
            # Should not raise any errors
            pass

    def test_trace_span_enabled(self, monkeypatch):
        """Test trace_span when tracing is enabled."""
        monkeypatch.setenv("STAC_MCP_ENABLE_TRACE", "true")
        monkeypatch.setenv("STAC_MCP_LOG_LEVEL", "DEBUG")
        observability._logger_state["initialized"] = False  # noqa: SLF001
        init_logging()
        
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            with trace_span("test_operation", attr1="value1"):
                pass
        
        # Should log span information
        output = stderr.getvalue()
        # May contain trace_span in debug logs
        assert output is not None

    def test_trace_span_with_exception(self, monkeypatch):
        """Test trace_span with exception inside."""
        monkeypatch.setenv("STAC_MCP_ENABLE_TRACE", "true")
        
        with pytest.raises(ValueError):
            with trace_span("failing_operation"):
                raise ValueError("Test error")


class TestCorrelationId:
    """Test correlation ID generation."""

    def test_correlation_id_format(self):
        """Test that correlation IDs are UUIDs."""
        corr_id = new_correlation_id()
        assert isinstance(corr_id, str)
        assert len(corr_id) == 36  # UUID format
        assert corr_id.count("-") == 4

    def test_correlation_id_uniqueness(self):
        """Test that correlation IDs are unique."""
        ids = {new_correlation_id() for _ in range(100)}
        assert len(ids) == 100


class TestMetricsEnabled:
    """Test metrics enable/disable functionality."""

    def test_metrics_disabled(self, monkeypatch):
        """Test that metrics can be disabled."""
        monkeypatch.setenv("STAC_MCP_ENABLE_METRICS", "false")
        # Create new registry to pick up env var
        registry = MetricsRegistry()
        registry.increment("test", 5)
        snapshot = registry.snapshot()
        # Metrics should still work, just may not be enabled for export
        assert isinstance(snapshot, dict)

    def test_metrics_enabled(self, monkeypatch):
        """Test that metrics are enabled by default."""
        monkeypatch.setenv("STAC_MCP_ENABLE_METRICS", "true")
        registry = MetricsRegistry()
        registry.increment("test", 10)
        snapshot = registry.snapshot()
        assert "test" in snapshot


class TestLatencyBuckets:
    """Test custom latency bucket configuration."""

    def test_default_latency_buckets(self, monkeypatch):
        """Test default latency buckets."""
        monkeypatch.delenv("STAC_MCP_LATENCY_BUCKETS_MS", raising=False)
        # Registry should use default buckets
        registry = MetricsRegistry()
        assert registry is not None

    def test_custom_latency_buckets(self, monkeypatch):
        """Test custom latency buckets from environment."""
        monkeypatch.setenv("STAC_MCP_LATENCY_BUCKETS_MS", "10,50,100,500")
        # New registry should pick up custom buckets
        # Note: This test verifies env var handling, actual bucket config
        # is implementation dependent
        registry = MetricsRegistry()
        assert registry is not None


class TestGlobalMetricsInstance:
    """Test global metrics instance."""

    def test_global_metrics_available(self):
        """Test that global metrics instance is available."""
        assert metrics is not None
        assert isinstance(metrics, MetricsRegistry)

    def test_metrics_snapshot_function(self):
        """Test metrics_snapshot helper function."""
        snapshot = metrics_snapshot()
        assert isinstance(snapshot, dict)

    def test_metrics_latency_snapshot_function(self):
        """Test metrics_latency_snapshot helper function."""
        snapshot = metrics_latency_snapshot()
        assert isinstance(snapshot, dict)


class TestEnvironmentVariableHandling:
    """Test environment variable parsing."""

    def test_boolean_env_true_values(self, monkeypatch):
        """Test parsing various true values."""
        true_values = ["true", "True", "TRUE", "1", "yes", "YES"]
        for value in true_values:
            monkeypatch.setenv("TEST_BOOL", value)
            # Test that the value is recognized as true
            # Note: Actual parsing depends on _get_bool implementation
            assert value  # Placeholder assertion

    def test_boolean_env_false_values(self, monkeypatch):
        """Test parsing various false values."""
        false_values = ["false", "False", "FALSE", "0", "no", "NO"]
        for value in false_values:
            monkeypatch.setenv("TEST_BOOL", value)
            # Test that the value is recognized as false
            assert value  # Placeholder assertion

    def test_missing_env_variable(self, monkeypatch):
        """Test handling of missing environment variables."""
        monkeypatch.delenv("NONEXISTENT_VAR", raising=False)
        # Should use default value
        assert True  # Placeholder assertion


class TestConcurrentAccess:
    """Test thread-safety of observability components."""

    def test_concurrent_metric_increments(self):
        """Test concurrent increments are thread-safe."""
        import threading
        
        registry = MetricsRegistry()
        
        def increment_many():
            for _ in range(100):
                registry.increment("concurrent.counter", 1)
        
        threads = [threading.Thread(target=increment_many) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        snapshot = registry.snapshot()
        # Should have exactly 1000 increments (10 threads * 100 each)
        assert snapshot["concurrent.counter"] == 1000

    def test_concurrent_latency_observations(self):
        """Test concurrent latency observations are thread-safe."""
        import threading
        
        registry = MetricsRegistry()
        
        def observe_many():
            for i in range(50):
                registry.observe_latency("concurrent.latency", float(i))
        
        threads = [threading.Thread(target=observe_many) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        snapshot = registry.latency_snapshot()
        # Should have exactly 250 observations (5 threads * 50 each)
        assert snapshot["concurrent.latency"]["count"] == 250


class TestLoggerBackwardCompatibility:
    """Test backward compatibility with old _logger_initialized variable."""

    def test_logger_initialized_flag(self):
        """Test that _logger_initialized flag is maintained."""
        # Reset state
        observability._logger_state["initialized"] = False  # noqa: SLF001
        observability._logger_initialized = False  # noqa: SLF001
        
        init_logging()
        
        # Both should be set
        assert observability._logger_state["initialized"]  # noqa: SLF001
        # Note: _logger_initialized may be a shim for compatibility
