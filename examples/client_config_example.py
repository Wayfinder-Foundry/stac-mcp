#!/usr/bin/env python
"""Example demonstrating ADR 0007 client configuration options.

This example shows how to use the STACClient programmatically with custom
timeout and headers configuration.

Note: These configuration options are for programmatic use. When using the
MCP server, tools use the default client configuration.
"""

from stac_mcp.tools.client import (
    ConnectionFailedError,
    STACClient,
    STACTimeoutError,
)


def example_timeout_configuration():
    """Demonstrate custom timeout configuration."""
    print("=== Timeout Configuration Example ===\n")

    # Default client (30 second timeout)
    client = STACClient("https://planetarycomputer.microsoft.com/api/stac/v1")
    print("1. Using default timeout (30s)...")
    try:
        result = client._http_json("/conformance")  # noqa: SLF001
        if result:
            conforms_count = len(result.get("conformsTo", []))
            print(f"   ✓ Success: got {conforms_count} conformance classes")
    except (STACTimeoutError, ConnectionFailedError) as e:
        print(f"   ✗ Error: {e}")

    # Custom timeout for slow networks
    print("\n2. Using custom timeout (60s) for slow connection...")
    try:
        result = client._http_json("/conformance", timeout=60)  # noqa: SLF001
        if result:
            print("   ✓ Success with extended timeout")
    except (STACTimeoutError, ConnectionFailedError) as e:
        print(f"   ✗ Error: {e}")

    # Disable timeout (wait indefinitely)
    print("\n3. Using timeout=0 (no timeout) for very slow operations...")
    try:
        # Note: timeout=0 means no timeout - use with caution!
        result = client._http_json("/conformance", timeout=0)  # noqa: SLF001
        if result:
            print("   ✓ Success with no timeout limit")
    except (STACTimeoutError, ConnectionFailedError) as e:
        print(f"   ✗ Error: {e}")


def example_headers_configuration():
    """Demonstrate custom headers configuration."""
    print("\n\n=== Headers Configuration Example ===\n")

    # Instance-level headers (apply to all requests)
    print("1. Using instance-level headers...")
    client = STACClient(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        headers={
            "User-Agent": "MyApp/1.0 (ADR-0007-Example)",
            "X-Custom-Header": "instance-value",
        },
    )

    try:
        result = client._http_json("/conformance")  # noqa: SLF001
        if result:
            print("   ✓ Request sent with custom headers")
    except (STACTimeoutError, ConnectionFailedError) as e:
        print(f"   ✗ Error: {e}")

    # Per-call headers (override instance headers)
    print("\n2. Using per-call headers override...")
    try:
        result = client._http_json(  # noqa: SLF001
            "/conformance",
            headers={"X-Custom-Header": "override-value"},
        )
        if result:
            print("   ✓ Request sent with overridden header")
    except (STACTimeoutError, ConnectionFailedError) as e:
        print(f"   ✗ Error: {e}")


def example_error_handling():
    """Demonstrate error handling with actionable messages."""
    print("\n\n=== Error Handling Example ===\n")

    # Example 1: Timeout error
    print("1. Handling timeout errors...")
    client = STACClient("https://planetarycomputer.microsoft.com/api/stac/v1")
    try:
        # Simulate timeout with very short timeout
        result = client._http_json("/conformance", timeout=0.001)  # noqa: SLF001
    except STACTimeoutError as e:
        print("   ✓ Caught STACTimeoutError:")
        print(f"     Message: {e}")
        print("     → Remediation: Increase timeout parameter or check network")

    # Example 2: Connection error (invalid URL)
    print("\n2. Handling connection errors...")
    bad_client = STACClient("https://invalid-stac-catalog-example.com")
    try:
        result = bad_client._http_json("/conformance", timeout=5)  # noqa: SLF001
    except ConnectionFailedError as e:
        print("   ✓ Caught ConnectionFailedError:")
        error_msg = str(e)
        # Show first 150 chars of error message
        print(f"     Message: {error_msg[:150]}...")
        if "DNS lookup failed" in error_msg:
            print("     → Error type: DNS failure")
        elif "Connection refused" in error_msg:
            print("     → Error type: Connection refused")
        elif "Network unreachable" in error_msg:
            print("     → Error type: Network unreachable")


def example_combined_configuration():
    """Demonstrate combining timeout and headers."""
    print("\n\n=== Combined Configuration Example ===\n")

    client = STACClient(
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        headers={"User-Agent": "MyApp/1.0"},
    )

    print("Making request with custom timeout AND headers...")
    try:
        result = client._http_json(  # noqa: SLF001
            "/conformance",
            timeout=45,
            headers={"X-Request-ID": "example-request-123"},
        )
        if result:
            print("   ✓ Success with combined configuration")
            print(f"   ✓ Got {len(result.get('conformsTo', []))} conformance classes")
    except (STACTimeoutError, ConnectionFailedError) as e:
        print(f"   ✗ Error: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("ADR 0007: Client Configuration and Error Handling Examples")
    print("=" * 70)

    try:
        example_timeout_configuration()
        example_headers_configuration()
        example_error_handling()
        example_combined_configuration()

        print("\n\n" + "=" * 70)
        print("Examples completed!")
        print("=" * 70 + "\n")

    except Exception as e:
        print(f"\nUnexpected error: {e}")
        import traceback

        traceback.print_exc()
