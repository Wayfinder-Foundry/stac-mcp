# ASR 1009: Support for STAC API - Transaction Extension

Status: Proposed
Date: 2025-10-05

## Context

The STAC API specification includes a "Transaction" extension that defines how clients can create, update, and delete Items and Collections on a STAC API endpoint. This is a fundamental capability for any client that intends to not just read, but also manage STAC metadata. Our current client implementation focuses primarily on search and read operations, and lacks support for these transactional capabilities.

## Requirement

The `stac-mcp` client MUST implement methods to support the full lifecycle of STAC Items and Collections, as defined by the STAC API Transaction Extension. This includes:

- **Create**: Add new `Item` or `Collection` objects to the catalog.
- **Update**: Modify existing `Item` or `Collection` objects.
- **Delete**: Remove `Item` or `Collection` objects from the catalog.

The implementation should handle authentication and authorization as required by the target STAC API endpoint.

## Implications

- **Client API**: The `STACClient` will need new methods (e.g., `create_item`, `update_item`, `delete_item`, `create_collection`, `update_collection`, `delete_collection`).
- **Error Handling**: Robust error handling must be implemented to manage API responses for success, failure (e.g., 404 Not Found, 409 Conflict), and authentication/authorization errors.
- **Testing**: The test suite must be expanded to include integration tests against a mock or real STAC API that supports the Transaction extension. This will likely involve creating, updating, and then deleting test resources.

## Alternatives considered

- **Read-only client**: We could choose to keep the client as a read-only tool. This is simpler but severely limits the utility of `stac-mcp` in workflows that involve data generation or management, making it a less complete tool compared to other clients in the ecosystem.
- **External tools**: Users could be instructed to use other tools (like `curl` or other clients) for transactional operations. This creates a fragmented user experience and adds complexity for the user.