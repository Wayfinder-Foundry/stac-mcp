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

- **Method-Level Behavioral Contracts**:
  - `create_item(collection_id, item)`:
    - **Verb**: `POST /collections/{collection_id}/items`
    - **Return**: The full created Item resource, including server-assigned fields.
    - **Errors**: Raises `APIError` on failure (e.g., 400 Bad Request, 401/403 Unauthorized, 409 Conflict if item ID exists).
  - `update_item(item)`:
    - **Verb**: `PUT /collections/{item.collection}/items/{item.id}`
    - **Behavior**: Full replacement of the item. Idempotent.
    - **Return**: The full updated Item resource.
    - **Errors**: Raises `APIError` on failure (e.g., 404 Not Found, 400 Bad Request).
  - `delete_item(collection_id, item_id)`:
    - **Verb**: `DELETE /collections/{collection_id}/items/{item_id}`
    - **Return**: A minimal success acknowledgment (e.g., `None` or a status object).
    - **Errors**: Raises `APIError` on failure (e.g., 404 Not Found).
  - `create_collection(collection)`:
    - **Verb**: `POST /collections`
    - **Return**: The full created Collection resource.
    - **Errors**: Raises `APIError` on failure (e.g., 409 Conflict if collection ID exists).
  - `update_collection(collection)`:
    - **Verb**: `PUT /collections`
    - **Behavior**: Full replacement of the collection. Idempotent.
    - **Return**: The full updated Collection resource.
    - **Errors**: Raises `APIError` on failure.
  - `delete_collection(collection_id)`:
    - **Verb**: `DELETE /collections/{collection_id}`
    - **Return**: A minimal success acknowledgment.
    - **Errors**: Raises `APIError` on failure (e.g., 404 Not Found).

- **Error Handling**: The `APIError` from `pystac-client` should be the primary exception type to signal failures from the STAC API, clearly indicating the HTTP status code and any error message from the server. This provides a consistent error surface for callers.

- **Testing**: The test suite must be expanded to include integration tests against a mock or real STAC API that supports the Transaction extension. This will likely involve creating, updating, and then deleting test resources, and verifying correct error handling for different HTTP status codes.

## Alternatives considered

- **Read-only client**: We could choose to keep the client as a read-only tool. This is simpler but severely limits the utility of `stac-mcp` in workflows that involve data generation or management, making it a less complete tool compared to other clients in the ecosystem.
- **External tools**: Users could be instructed to use other tools (like `curl` or other clients) for transactional operations. This creates a fragmented user experience and adds complexity for the user.