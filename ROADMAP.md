# Project Roadmap: `stac-mcp`

This document outlines the development roadmap for `stac-mcp`, prioritizing work to incrementally enhance the client's capabilities and align it with the STAC specification and user needs.

## Phase 1: Foundational Enhancements

The first phase focuses on building a more robust and intelligent client that can adapt to the capabilities of different STAC APIs.

1.  **Implement Conformance Class Discovery (ASR 1011)**
    -   **Goal**: Make the client aware of the features supported by a connected STAC API.
    -   **Rationale**: This is a prerequisite for gracefully handling different API capabilities and providing clear, actionable error messages to users. It prevents the client from making invalid requests to APIs that do not support certain extensions.
    -   **Priority**: High. This should be implemented before other features that rely on optional extensions.

## Phase 2: Expanding Core Functionality

With a solid foundation, the next phase is to implement key STAC API features that are currently missing, focusing on the most common and impactful user workflows.

1.  **Support for the Sort Extension (ASR 1010)**
    -   **Goal**: Allow users to specify the sort order of search results.
    -   **Rationale**: Sorting is a fundamental requirement for users who need to process or prioritize STAC Items based on metadata fields like date, cloud cover, or resolution.
    -   **Priority**: High. This is a widely used feature in STAC APIs.

2.  **Support for the Transaction Extension (ASR 1009)**
    -   **Goal**: Enable users to create, update, and delete STAC Items and Collections.
    -   **Rationale**: This transforms the client from a read-only tool into a full-fledged management client, unlocking new use cases in data publishing and maintenance workflows.
    -   **Priority**: Medium. While a major feature, it is a larger effort than sorting and serves a more advanced set of use cases.

## Phase 3: Future Work and Advanced Features

This phase looks beyond the immediate gaps and considers features that will make `stac-mcp` a best-in-class client. These items are not yet fully scoped into ASRs but represent the future direction of the project.

-   **Advanced Filtering (CQL2)**: Implement support for the STAC API - Filter extension with CQL2-JSON for more expressive queries.
-   **Client-Side Configuration**: Allow for more advanced client configuration, such as custom headers, retry policies, and timeout settings, as outlined in ADR-0007.
-   **Caching**: Implement a caching layer for API responses to improve performance and reduce redundant requests, as described in ADR-0011.
-   **Support for Additional STAC Extensions**: Systematically add support for other common STAC extensions, such as the Fields, Query, and Aggregation extensions.

This roadmap will be reviewed and updated as the project evolves and new requirements are identified. Each major feature will be tracked through its corresponding ADR or ASR document.