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
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from threading import RLock
from typing import Any

LOG_LEVEL_ENV = "STAC_MCP_LOG_LEVEL"
LOG_FORMAT_ENV = "STAC_MCP_LOG_FORMAT"  # "text" | "json"
ENABLE_METRICS_ENV = "STAC_MCP_ENABLE_METRICS"
ENABLE_TRACE_ENV = "STAC_MCP_ENABLE_TRACE"
LATENCY_BUCKETS_ENV = (
    "STAC_MCP_LATENCY_BUCKETS_MS"  # comma-separated e.g. "5,10,25,50,100,250,500,1000"
)

_logger_initialized = False
_init_lock = RLock()


def _get_bool(env: str, default: bool) -> bool:
    val = os.getenv(env)
    if val is None:
        return default
    return val.lower() in {"1", "true", "yes", "on"}


def init_logging() -> None:
    """Idempotently configure the library logger.

    Logging always goes to stderr to avoid MCP protocol interference.
    """

    global _logger_initialized
    if _logger_initialized:  # pragma: no cover - guard path
        return
    with _init_lock:
        if _logger_initialized:  # pragma: no cover
            return
        level_name = os.getenv(LOG_LEVEL_ENV, "WARNING").upper()
        level = getattr(logging, level_name, logging.WARNING)
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
        _logger_initialized = True


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

    def _parse_buckets(self) -> list[float]:
        raw = os.getenv(LATENCY_BUCKETS_ENV)
        if raw:
            try:
                buckets = sorted(
                    {float(x.strip()) for x in raw.split(",") if x.strip()},
                )
                return [b for b in buckets if b > 0]
            except Exception:  # pragma: no cover - fallback path
                pass
        # Sensible default spanning sub-ms to multi-second
        return [1, 2, 5, 10, 25, 50, 100, 250, 500, 1000, 2000, 5000]

    def inc(self, name: str, amount: int = 1) -> None:
        if not _get_bool(ENABLE_METRICS_ENV, True):
            return
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + amount

    def observe_latency(self, name: str, value_ms: float) -> None:
        if not _get_bool(ENABLE_METRICS_ENV, True):  # pragma: no cover - simple guard
            return
        with self._lock:
            hist = self._histograms.get(name)
            if hist is None:
                hist = [0] * (len(self._latency_buckets) + 1)  # last bucket = overflow
                self._histograms[name] = hist
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

    def latency_snapshot(self) -> dict[str, dict[str, int]]:
        with self._lock:
            snap: dict[str, dict[str, int]] = {}
            for name, counts in self._histograms.items():
                bucket_labels = [f"<= {int(b)}ms" for b in self._latency_buckets] + [
                    "> overflow",
                ]
                snap[name] = {bucket_labels[i]: counts[i] for i in range(len(counts))}
            return snap


metrics = MetricsRegistry()


def _metric_name(*parts: str) -> str:
    return ".".join(parts)


# ---------------------- Tracing (no-op) ---------------------- #


@contextmanager
def trace_span(name: str, **attrs: Any) -> Generator[None, None, None]:
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
    metrics.inc(_metric_name("tool_invocations_total", tool_name))
    t0 = time.perf_counter()
    error_type: str | None = None
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
        # Record latency exactly once (success or failure) and log success if applicable
        duration_ms = (time.perf_counter() - t0) * 1000.0
        metrics.observe_latency(_metric_name("tool_latency_ms", tool_name), duration_ms)
        if error_type is None:
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


def metrics_snapshot() -> dict[str, int]:
    """Return a copy of current counter values (for tests)."""

    return metrics.snapshot()


def metrics_latency_snapshot() -> dict[str, dict[str, int]]:
    """Return current latency histogram snapshots."""

    return metrics.latency_snapshot()
