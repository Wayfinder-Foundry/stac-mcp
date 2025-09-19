# ASR 1002: STDIO Transport and CLI Behavior

Status: Accepted
Date: 2025-09-18

## Context
The MCP server must communicate over STDIO for compatibility with typical MCP clients. The CLI should offer predictable behavior for local smoke tests.

## Requirement
- Transport: The server uses STDIO (stdin/stdout) for all MCP protocol communication.
- CLI: `stac-mcp` starts the server and blocks awaiting MCP messages on STDIO.
- Manual check: A 5-second timeout run should exit with code 124, confirming blocking behavior.

## Implications
- No HTTP server mode is required at this time.
- Logging must not interfere with STDIO protocol streams (use logging to stderr where applicable).

## Alternatives considered
- HTTP transport for local development: rejected for scope and protocol consistency.

## Addendums
- 2025-09-18: Initial acceptance.
