"""Observability primitives (ADR 0012).

This module provides:
* Structured logging initialization (stderr only)
* Correlation ID generation per request
* Minimal in-process metrics counters
* Timing utilities and a no-op trace span abstraction

Design goals:
- Zero external dependencies.
- Safe to import early (lazy initialization where possible).
- Does not write to stdout (stdin/stdout reserved for MCP protocol).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from threading import RLock
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover - type checking only
    from collections.abc import Generator

LOG_LEVEL_ENV = "STAC_MCP_LOG_LEVEL"
LOG_FORMAT_ENV = "STAC_MCP_LOG_FORMAT"  # "text" | "json"
ENABLE_METRICS_ENV = "STAC_MCP_ENABLE_METRICS"
ENABLE_TRACE_ENV = "STAC_MCP_ENABLE_TRACE"
LATENCY_BUCKETS_ENV = (
    "STAC_MCP_LATENCY_BUCKETS_MS"  # comma-separated e.g. "5,10,25,50,100,250,500,1000"
)

_logger_state = {"initialized": False}
# Backward compatibility shim: tests (and possibly external code) reference
# observability._logger_initialized. Maintain it as an alias to internal state.
_logger_initialized = False  # historical public alias retained (N816 accepted)
_init_lock = RLock()


def _get_bool(env: str, default: bool) -> bool:
    val = os.getenv(env)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


def init_logging() -> None:
    """Configure the library logger (re-initializable for tests).

    Tests historically flipped `_logger_initialized = False` to force a fresh
    configuration within a stderr/stdout capture context. We preserve that
    behavior by allowing re-init when the shim flag is False even if the
    internal state dict says initialized.
    """

    # Allow re-init when external test code flips alias to False. Avoid using
    # global assignment; we rely on shared mutable state and alias pointer.
    if _logger_state["initialized"] and _logger_initialized:  # pragma: no cover
        return
    with _init_lock:
        if _logger_state["initialized"] and _logger_initialized:  # pragma: no cover
            return
        level_name = os.getenv(LOG_LEVEL_ENV, "WARNING")
        level: int | None
        if level_name is None:
            level = logging.WARNING
        else:
            normalized = level_name.upper()
            level = getattr(logging, normalized, None)
            if not isinstance(level, int):
                level = logging.INFO
        log_format = os.getenv(LOG_FORMAT_ENV, "text").lower()
        handler = logging.StreamHandler(stream=sys.stderr)
        if log_format == "json":
            handler.setFormatter(JSONLogFormatter())
        else:
            handler.setFormatter(
                logging.Formatter("%(levelname)s %(name)s: %(message)s"),
            )
        logger = logging.getLogger("stac_mcp")
        logger.setLevel(level)
        logger.handlers = [handler]
        logger.propagate = False
    _logger_state["initialized"] = True
    # Keep alias in sync (tests may introspect this value)
    globals()["_logger_initialized"] = True


_LOG_RECORD_BASE_KEYS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
}


class JSONLogFormatter(logging.Formatter):
    """Serialize log records as single-line JSON objects (structured logging)."""

    def format(self, record: logging.LogRecord) -> str:  # type: ignore[override]
        base = {
            "timestamp": time.strftime(
                "%Y-%m-%dT%H:%M:%SZ",
                time.gmtime(record.created),
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Attach extra known attributes if present
        for attr in [
            "event",
            "tool_name",
            "duration_ms",
            "error_type",
            "correlation_id",
            "cache_hit",
            "catalog_url",
        ]:
            if hasattr(record, attr):
                base[attr] = getattr(record, attr)
        if record.exc_info:
            try:
                base["exc_info"] = self.formatException(record.exc_info)
            except Exception:  # pragma: no cover - defensive fallback  # noqa: BLE001
                base["exc_info"] = str(record.exc_info)
        for key, value in record.__dict__.items():
            if key in base or key in _LOG_RECORD_BASE_KEYS or key.startswith("_"):
                continue
            base[key] = value
        return json.dumps(base, separators=(",", ":"))


# ---------------------- Metrics Registry ---------------------- #


class MetricsRegistry:
    """In-process metrics counters + latency histograms (thread-safe)."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._counters: dict[str, int] = {}
        # Histogram buckets: parse env or default set (ms)
        self._latency_buckets = self._parse_buckets()
        # Map metric name -> list[counts per bucket + overflow]
        self._histograms: dict[str, list[int]] = {}
        self._latency_stats: dict[str, dict[str, float]] = {}
        self._gauges: dict[str, float] = {}

    def _parse_buckets(self) -> list[float]:
        raw = os.getenv(LATENCY_BUCKETS_ENV)
        if raw:
            try:
                buckets = sorted(
                    {float(x.strip()) for x in raw.split(",") if x.strip()},
                )
                return [b for b in buckets if b > 0]
            except (ValueError, TypeError) as exc:  # pragma: no cover - fallback path
                logging.getLogger("stac_mcp").debug(
                    "Invalid STAC_MCP_LATENCY_BUCKETS_MS value: %s",
                    exc,
                )
        # Sensible default spanning sub-ms to multi-second
        return [1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2000, 5000]

    def inc(self, name: str, amount: int = 1) -> None:
        if not _get_bool(ENABLE_METRICS_ENV, True):
            return
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount

    def increment(self, name: str, amount: int = 1) -> None:
        """Alias for ``inc`` for readability in tests."""

        self.inc(name, amount)

    def observe_latency(self, name: str, value_ms: float) -> None:
        if not _get_bool(ENABLE_METRICS_ENV, True):  # pragma: no cover - simple guard
            return
        with self._lock:
            hist = self._histograms.get(name)
            if hist is None:
                hist = [0] * (len(self._latency_buckets) + 1)  # last bucket = overflow
                self._histograms[name] = hist
            stats = self._latency_stats.setdefault(
                name,
                {"count": 0, "sum": 0.0, "min": float("inf"), "max": float("-inf")},
            )
            stats["count"] += 1
            stats["sum"] += value_ms
            stats["min"] = min(stats["min"], value_ms)
            stats["max"] = max(stats["max"], value_ms)
            # Find first bucket >= value, else overflow
            placed = False
            for idx, upper in enumerate(self._latency_buckets):
                if value_ms <= upper:
                    hist[idx] += 1
                    placed = True
                    break
            if not placed:  # overflow
                hist[-1] += 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def set_gauge(self, name: str, value: float) -> None:
        if not _get_bool(ENABLE_METRICS_ENV, True):
            return
        with self._lock:
            self._gauges[name] = float(value)

    def latency_snapshot(self) -> dict[str, LatencySnapshotEntry]:
        with self._lock:
            snap: dict[str, LatencySnapshotEntry] = {}
            for name, counts in self._histograms.items():
                stats = self._latency_stats.get(
                    name,
                    {"count": 0, "sum": 0.0, "min": 0.0, "max": 0.0},
                )
                bucket_map = {}
                for idx, upper in enumerate(self._latency_buckets):
                    bucket_map[str(int(upper))] = counts[idx]
                bucket_map["overflow"] = counts[-1]
                snap[name] = LatencySnapshotEntry(
                    {
                        "count": int(stats["count"]),
                        "sum": stats["sum"],
                        "min": 0.0 if stats["count"] == 0 else stats["min"],
                        "max": 0.0 if stats["count"] == 0 else stats["max"],
                        "buckets": bucket_map,
                    }
                )
            return snap

    def gauge_snapshot(self) -> dict[str, float]:
        with self._lock:
            return dict(self._gauges)


class LatencySnapshotEntry(dict[str, Any]):
    """Dictionary subclass flattening bucket values when iterating."""

    def values(self):  # type: ignore[override]
        buckets = super().get("buckets")
        if isinstance(buckets, dict):
            return buckets.values()
        return super().values()

    def __len__(self) -> int:  # type: ignore[override]
        buckets = super().get("buckets")
        if isinstance(buckets, dict):
            return len(buckets)
        return super().__len__()


metrics = MetricsRegistry()


def _metric_name(*parts: str) -> str:
    return ".".join(parts)


# ---------------------- Tracing (no-op) ---------------------- #


@contextmanager
def trace_span(name: str, **_attrs: Any) -> Generator[None, None, None]:
    """No-op span context manager placeholder.

    If tracing is enabled (`STAC_MCP_ENABLE_TRACE`), we could log span start/end.
    For now, it's intentionally minimal to avoid overhead.
    """

    enabled = _get_bool(ENABLE_TRACE_ENV, False)
    t0 = time.perf_counter()
    try:
        yield
    finally:  # pragma: no branch - single exit path
        if enabled:
            duration_ms = (time.perf_counter() - t0) * 1000.0
            logging.getLogger("stac_mcp").debug(
                "trace_span",
                extra={
                    "event": "trace_span",
                    "span": name,
                    "duration_ms": round(duration_ms, 2),
                },
            )


# ---------------------- Correlation IDs ---------------------- #


def new_correlation_id() -> str:
    return str(uuid.uuid4())


@dataclass
class ToolExecutionResult:
    """Container for instrumented tool execution output."""

    value: Any
    correlation_id: str
    duration_ms: float
    error_type: str | None = None


def instrument_tool_execution(
    tool_name: str,
    catalog_url: str | None,
    func,
    *args,
    **kwargs,
) -> ToolExecutionResult:
    """Execute a tool handler with logging, timing, metrics, and correlation id.

    Parameters
    ----------
    tool_name: str
        Name of the tool being executed.
    catalog_url: Optional[str]
        Catalog endpoint associated with the execution (may be None).
    func: Callable
        The handler function to execute.
    *args, **kwargs:
        Passed to the handler.
    """

    init_logging()
    correlation_id = new_correlation_id()
    logger = logging.getLogger("stac_mcp")
    invocation_metric = _metric_name("tool_invocations_total", tool_name)
    global_invocation_metric = _metric_name("tool_invocations_total", "_all")
    inflight_metric = _metric_name("tool_inflight_current", tool_name)
    global_inflight_metric = _metric_name("tool_inflight_current", "_all")
    metrics.inc(invocation_metric)
    metrics.inc(global_invocation_metric)
    metrics.inc(inflight_metric)
    metrics.inc(global_inflight_metric)
    t0 = time.perf_counter()
    error_type: str | None = None
    duration_ms = 0.0
    try:
        with trace_span(f"tool.{tool_name}"):
            result = func(*args, **kwargs)
        duration_ms = (time.perf_counter() - t0) * 1000.0
        return ToolExecutionResult(
            value=result,
            correlation_id=correlation_id,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        # Classify error type (simple heuristic)
        etype = type(exc).__name__
        if "timeout" in etype.lower():
            error_type = "TimeoutError"
        elif "network" in etype.lower() or "connection" in etype.lower():
            error_type = "NetworkError"
        else:
            error_type = "UnknownError"
        metrics.inc(_metric_name("tool_errors_total", tool_name, error_type))
        duration_ms = (time.perf_counter() - t0) * 1000.0
        logger.warning(
            "tool_error",
            extra={
                "event": "tool_error",
                "tool_name": tool_name,
                "error_type": error_type,
                "correlation_id": correlation_id,
                "duration_ms": round(duration_ms, 2),
                "catalog_url": catalog_url,
            },
        )
        raise
    finally:
        if duration_ms == 0.0:
            duration_ms = (time.perf_counter() - t0) * 1000.0
        tool_latency_metric = _metric_name("tool_latency_ms", tool_name)
        global_latency_metric = _metric_name("tool_latency_ms", "_all")
        metrics.observe_latency(tool_latency_metric, duration_ms)
        metrics.observe_latency(global_latency_metric, duration_ms)
        metrics.set_gauge(
            _metric_name("tool_last_duration_ms", tool_name),
            duration_ms,
        )
        metrics.set_gauge(
            _metric_name("tool_last_duration_ms", "_all"),
            duration_ms,
        )
        metrics.inc(inflight_metric, -1)
        metrics.inc(global_inflight_metric, -1)
        if error_type is None:
            metrics.inc(_metric_name("tool_success_total", tool_name))
            metrics.inc(_metric_name("tool_success_total", "_all"))
            logger.info(
                "tool_complete",
                extra={
                    "event": "tool_complete",
                    "tool_name": tool_name,
                    "duration_ms": round(duration_ms, 2),
                    "correlation_id": correlation_id,
                    "catalog_url": catalog_url,
                },
            )
        else:
            metrics.inc(_metric_name("tool_failure_total", tool_name))
            metrics.inc(_metric_name("tool_failure_total", "_all"))
            metrics.set_gauge(
                _metric_name("tool_last_error_duration_ms", tool_name),
                duration_ms,
            )
            metrics.set_gauge(
                _metric_name("tool_last_error_duration_ms", "_all"),
                duration_ms,
            )


def metrics_snapshot() -> dict[str, int]:
    """Return a copy of current counter values (for tests)."""

    return metrics.snapshot()


def metrics_latency_snapshot() -> dict[str, LatencySnapshotEntry]:
    """Return current latency histogram snapshots."""

    return metrics.latency_snapshot()


def metrics_gauge_snapshot() -> dict[str, float]:
    """Return current gauge metric values."""

    return metrics.gauge_snapshot()


def record_tool_result_size(tool_name: str, size_bytes: int) -> None:
    """Record aggregate byte size metrics for tool results."""

    metrics.inc(_metric_name("tool_result_bytes_total", tool_name), size_bytes)
    metrics.inc(_metric_name("tool_result_bytes_total", "_all"), size_bytes)
    metrics.set_gauge(
        _metric_name("tool_last_result_bytes", tool_name),
        float(size_bytes),
    )
    metrics.set_gauge(
        _metric_name("tool_last_result_bytes", "_all"),
        float(size_bytes),
    )
