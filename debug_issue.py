#!/usr/bin/env python3

import asyncio
from mcp.types import CallToolRequest
from stac_mcp.server import handle_call_tool

async def test_incorrect_params():
    """Test the incorrect CallToolRequest.Params usage."""
    try:
        # This is the problematic code from examples/example_usage.py
        request = CallToolRequest(
            params=CallToolRequest.Params(
                name="search_collections",
                arguments={"limit": 1}
            )
        )
        result = await handle_call_tool(request)
        print("Success:", result)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

async def test_correct_params():
    """Test the correct CallToolRequestParams usage."""
    try:
        from mcp.types import CallToolRequestParams
        # This is the correct approach used in tests
        request = CallToolRequest(
            params=CallToolRequestParams(
                name="search_collections",
                arguments={"limit": 1}
            )
        )
        result = await handle_call_tool(request)
        print("Success:", result)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

async def main():
    print("Testing incorrect params (CallToolRequest.Params):")
    await test_incorrect_params()
    print("\nTesting correct params (CallToolRequestParams):")
    await test_correct_params()

if __name__ == "__main__":
    asyncio.run(main())