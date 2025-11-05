"""STAC MCP Server - An MCP Server for STAC requests.

This package exposes the server version and selected observability helpers
for tests (see ADR 0012).
"""

__version__ = "2.1.0"

from .observability import metrics_latency_snapshot, metrics_snapshot

__all__ = ["__version__", "metrics_latency_snapshot", "metrics_snapshot"]
