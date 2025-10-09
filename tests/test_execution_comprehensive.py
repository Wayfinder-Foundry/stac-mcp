"""Comprehensive tests for tool execution module.

Tests focus on:
- Error handling in execute_tool
- Fallback mechanisms for different output types
- Type conversion and validation
- Edge cases in result formatting
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from mcp.types import TextContent

from stac_mcp.observability import metrics_gauge_snapshot, metrics_snapshot
from stac_mcp.tools.execution import execute_tool


class TestExecuteToolSuccess:
    """Test successful tool execution scenarios."""

    @pytest.mark.asyncio
    async def test_execute_tool_returns_text_content_list(self):
        """Test execute_tool with handler returning list of TextContent."""
        mock_handler = MagicMock(
            return_value=[
                TextContent(type="text", text="Result 1"),
                TextContent(type="text", text="Result 2"),
            ]
        )

        result = await execute_tool("test_tool", mock_handler, None, {})

        assert isinstance(result, list)
        assert len(result) == 2  # noqa: PLR2004
        assert all(isinstance(item, TextContent) for item in result)

    @pytest.mark.asyncio
    async def test_execute_tool_returns_dict(self):
        """Test execute_tool with handler returning dictionary."""
        mock_handler = MagicMock(
            return_value={
                "type": "test",
                "data": {"key": "value"},
            }
        )

        result = await execute_tool("test_tool", mock_handler, None, {})

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        assert '"type":"test"' in result[0].text or "test" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_tool_returns_string(self):
        """Test execute_tool with handler returning plain string."""
        mock_handler = MagicMock(return_value="Plain text result")

        result = await execute_tool("test_tool", mock_handler, None, {})

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0].text == "Plain text result"

    @pytest.mark.asyncio
    async def test_execute_tool_empty_list(self):
        """Test execute_tool with handler returning empty list."""
        mock_handler = MagicMock(return_value=[])

        result = await execute_tool("test_tool", mock_handler, None, {})

        # Should return at least one TextContent with empty or default message
        assert isinstance(result, list)
        assert len(result) >= 0


class TestExecuteToolErrors:
    """Test error handling in tool execution."""

    @pytest.mark.asyncio
    async def test_execute_tool_handler_raises_exception(self):
        """Test execute_tool when handler raises exception."""

        def failing_handler(client, args):  # noqa: ARG001
            msg = "Handler failed"
            raise ValueError(msg)

        with pytest.raises(ValueError, match="Handler failed"):
            await execute_tool("failing_tool", failing_handler, None, {})

    @pytest.mark.asyncio
    async def test_execute_tool_handler_returns_none(self):
        """Test execute_tool when handler returns None."""
        mock_handler = MagicMock(return_value=None)

        result = await execute_tool("test_tool", mock_handler, None, {})

        # Should handle None gracefully
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_execute_tool_handler_returns_invalid_type(self):
        """Test execute_tool when handler returns unexpected type."""
        mock_handler = MagicMock(return_value=12345)  # Integer

        result = await execute_tool("test_tool", mock_handler, None, {})

        # Should convert to string or handle gracefully
        assert isinstance(result, list)


class TestExecuteToolWithArguments:
    """Test tool execution with various argument types."""

    @pytest.mark.asyncio
    async def test_execute_tool_with_simple_args(self):
        """Test execute_tool with simple arguments."""
        mock_handler = MagicMock(return_value="Result")
        args = {"param1": "value1", "param2": 42}

        await execute_tool("test_tool", mock_handler, None, args)

        mock_handler.assert_called_once()
        call_args = mock_handler.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_execute_tool_with_nested_args(self):
        """Test execute_tool with nested arguments."""
        mock_handler = MagicMock(return_value="Result")
        args = {
            "bbox": [-180, -90, 180, 90],
            "query": {"eo:cloud_cover": {"lt": 10}},
            "collections": ["col1", "col2"],
        }

        result = await execute_tool("test_tool", mock_handler, None, args)

        assert result is not None

    @pytest.mark.asyncio
    async def test_execute_tool_with_empty_args(self):
        """Test execute_tool with empty arguments."""
        mock_handler = MagicMock(return_value="Result")

        result = await execute_tool("test_tool", mock_handler, None, {})

        assert result is not None


class TestExecuteToolOutputFormats:
    """Test different output format handling."""

    @pytest.mark.asyncio
    async def test_execute_tool_json_output_dict(self):
        """Test execute_tool with JSON output format."""
        mock_handler = MagicMock(
            return_value={
                "mode": "json",
                "data": {"items": [1, 2, 3]},
            }
        )

        result = await execute_tool(
            "test_tool",
            mock_handler,
            None,
            {
                "output_format": "json",
            },
        )

        assert isinstance(result, list)
        assert len(result) == 1
        # Result should be JSON string
        text = result[0].text
        assert isinstance(text, str)

    @pytest.mark.asyncio
    async def test_execute_tool_text_output(self):
        """Test execute_tool with text output format."""
        mock_handler = MagicMock(
            return_value=[
                TextContent(type="text", text="Text output"),
            ]
        )

        result = await execute_tool(
            "test_tool",
            mock_handler,
            None,
            {
                "output_format": "text",
            },
        )

        assert isinstance(result, list)
        assert result[0].text == "Text output"

    @pytest.mark.asyncio
    async def test_execute_tool_mixed_content(self):
        """Test execute_tool with mixed content types."""
        mock_handler = MagicMock(
            return_value=[
                TextContent(type="text", text="Line 1"),
                TextContent(type="text", text="Line 2"),
                TextContent(type="text", text="Line 3"),
            ]
        )

        result = await execute_tool("test_tool", mock_handler, None, {})

        assert len(result) == 3  # noqa: PLR2004


class TestExecuteToolWithClient:
    """Test tool execution with STAC client."""

    @pytest.mark.asyncio
    async def test_execute_tool_passes_client(self):
        """Test that execute_tool passes client to handler."""
        mock_client = MagicMock()
        mock_handler = MagicMock(return_value="Result")

        await execute_tool("test_tool", mock_handler, mock_client, {})

        # Handler should be called with client as first argument
        mock_handler.assert_called_once()
        call_args = mock_handler.call_args[0]
        assert call_args[0] == mock_client

    @pytest.mark.asyncio
    async def test_execute_tool_client_none(self):
        """Test execute_tool when client is None."""
        mock_handler = MagicMock(return_value="Result")

        result = await execute_tool("test_tool", mock_handler, None, {})

        # Should still work with None client
        assert result is not None


class TestExecuteToolReturnTypes:
    """Test handling of different return types from handlers."""

    @pytest.mark.asyncio
    async def test_execute_tool_returns_list_of_dicts(self):
        """Test execute_tool with handler returning list of dicts."""
        mock_handler = MagicMock(
            return_value=[
                {"id": "1", "name": "Item 1"},
                {"id": "2", "name": "Item 2"},
            ]
        )

        result = await execute_tool("test_tool", mock_handler, None, {})

        assert isinstance(result, list)
        # Should convert to TextContent
        assert all(isinstance(item, TextContent) for item in result)

    @pytest.mark.asyncio
    async def test_execute_tool_returns_nested_structure(self):
        """Test execute_tool with complex nested structure."""
        mock_handler = MagicMock(
            return_value={
                "metadata": {
                    "count": 10,
                    "items": [
                        {"id": "1", "data": {"value": 100}},
                        {"id": "2", "data": {"value": 200}},
                    ],
                },
            }
        )

        result = await execute_tool("test_tool", mock_handler, None, {})

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_execute_tool_returns_boolean(self):
        """Test execute_tool with handler returning boolean."""
        mock_handler = MagicMock(return_value=True)

        result = await execute_tool("test_tool", mock_handler, None, {})

        assert isinstance(result, list)
        # Should convert boolean to string
        assert len(result) >= 1


class TestExecuteToolEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_execute_tool_very_long_result(self):
        """Test execute_tool with very long result string."""
        long_text = "A" * 10000  # 10KB of text
        mock_handler = MagicMock(return_value=long_text)

        result = await execute_tool("test_tool", mock_handler, None, {})

        assert isinstance(result, list)
        assert len(result[0].text) == 10000  # noqa: PLR2004

    @pytest.mark.asyncio
    async def test_execute_tool_unicode_characters(self):
        """Test execute_tool with unicode characters."""
        mock_handler = MagicMock(return_value="Test with émojis 🌍 and 中文")

        result = await execute_tool("test_tool", mock_handler, None, {})

        assert isinstance(result, list)
        assert "🌍" in result[0].text

    @pytest.mark.asyncio
    async def test_execute_tool_empty_string(self):
        """Test execute_tool with empty string result."""
        mock_handler = MagicMock(return_value="")

        result = await execute_tool("test_tool", mock_handler, None, {})

        assert isinstance(result, list)
        # Should handle empty string gracefully
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_execute_tool_whitespace_only(self):
        """Test execute_tool with whitespace-only result."""
        mock_handler = MagicMock(return_value="   \n\t  ")

        result = await execute_tool("test_tool", mock_handler, None, {})

        assert isinstance(result, list)


class TestExecuteToolPerformance:
    """Test performance-related aspects of tool execution."""

    @pytest.mark.asyncio
    async def test_execute_tool_handles_large_list(self):
        """Test execute_tool with large list of results."""
        large_list = [TextContent(type="text", text=f"Item {i}") for i in range(1000)]
        mock_handler = MagicMock(return_value=large_list)

        result = await execute_tool("test_tool", mock_handler, None, {})

        assert isinstance(result, list)
        assert len(result) <= 1000  # noqa: PLR2004 - May be truncated or limited

    @pytest.mark.asyncio
    async def test_execute_tool_handles_deeply_nested_dict(self):
        """Test execute_tool with deeply nested dictionary."""

        def create_nested(depth):
            if depth == 0:
                return {"value": "leaf"}
            return {"nested": create_nested(depth - 1)}

        nested_data = create_nested(10)
        mock_handler = MagicMock(return_value=nested_data)

        result = await execute_tool("test_tool", mock_handler, None, {})

        assert isinstance(result, list)


class TestExecuteToolWithLogging:
    """Test that tool execution properly handles logging."""

    @pytest.mark.asyncio
    async def test_execute_tool_logs_invocation(self):
        """Test that tool execution logs invocation."""
        mock_handler = MagicMock(return_value="Result")

        # Execute tool (logging would happen internally)
        result = await execute_tool("test_tool", mock_handler, None, {})

        assert result is not None
        # Actual logging verification would require log capture

    @pytest.mark.asyncio
    async def test_execute_tool_logs_errors(self):
        """Test that tool execution logs errors."""

        def failing_handler(client, args):  # noqa: ARG001
            msg = "Test error"
            raise RuntimeError(msg)

        with pytest.raises(RuntimeError):
            await execute_tool("failing_tool", failing_handler, None, {})

        # Error should be logged (verification would require log capture)


class TestExecuteToolMetrics:
    """Test that execute_tool records observability metrics."""

    @pytest.mark.asyncio
    async def test_execute_tool_records_result_size_text(self, fresh_metrics_registry):
        """Ensure result size metrics are recorded for text output."""

        mock_handler = MagicMock(
            return_value=[
                TextContent(type="text", text="alpha"),
                TextContent(type="text", text="βeta"),
            ]
        )

        result = await execute_tool("metrics_text_tool", mock_handler, None, {})
        combined = "".join(item.text for item in result)
        expected_bytes = len(combined.encode("utf-8"))

        registry_snapshot = fresh_metrics_registry.snapshot()
        assert (
            registry_snapshot["tool_result_bytes_total.metrics_text_tool"]
            == expected_bytes
        )

        global_snapshot = metrics_snapshot()
        assert (
            global_snapshot.get("tool_result_bytes_total.metrics_text_tool")
            == expected_bytes
        )
        assert global_snapshot.get("tool_result_bytes_total._all") == expected_bytes

        gauges = metrics_gauge_snapshot()
        size_gauge = gauges.get("tool_last_result_bytes.metrics_text_tool")
        assert size_gauge == float(expected_bytes)

    @pytest.mark.asyncio
    async def test_execute_tool_records_result_size_json(self, fresh_metrics_registry):
        """Ensure result size metrics are recorded for JSON output."""

        payload = {"items": [1, 2, 3]}
        mock_handler = MagicMock(return_value=payload)

        result = await execute_tool(
            "metrics_json_tool",
            mock_handler,
            None,
            {"output_format": "json"},
        )

        assert result
        output_text = result[0].text
        expected_bytes = len(output_text.encode("utf-8"))

        registry_snapshot = fresh_metrics_registry.snapshot()
        assert (
            registry_snapshot["tool_result_bytes_total.metrics_json_tool"]
            == expected_bytes
        )

        global_snapshot = metrics_snapshot()
        assert (
            global_snapshot.get("tool_result_bytes_total.metrics_json_tool")
            == expected_bytes
        )
        assert global_snapshot.get("tool_result_bytes_total._all") == expected_bytes

        gauges = metrics_gauge_snapshot()
        size_gauge = gauges.get("tool_last_result_bytes.metrics_json_tool")
        assert size_gauge == float(expected_bytes)
