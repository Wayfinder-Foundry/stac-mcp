# ASR 1010: Support for STAC API - Sort Extension

Status: Proposed
Date: 2025-10-05

## Context

The STAC API specification includes a "Sort" extension that allows clients to specify the sort order of the results of a search query. This is a common feature in APIs and is particularly useful in geospatial queries for sorting by properties like date, cloud cover, or other metadata fields. Our current client's search functionality does not expose this capability, limiting its flexibility.

## Requirement

The `stac-mcp` client's search methods MUST be updated to support the STAC API Sort Extension. This means:

- The client should be able to accept a list of fields to sort by, along with the desired direction (ascending or descending) for each field.
- This sorting information must be correctly encoded and sent to the STAC API as part of the search request.
- The client should be able to handle responses from APIs that both support and do not support the Sort extension gracefully.

## Implications

- **Client API**: The `search` method in the `STACClient` will need to be updated to accept a new parameter, e.g., `sortby`. The type of this parameter should be designed to be intuitive for the user, for example, a list of tuples like `[("properties.datetime", "desc")]`.
- **Request Formation**: The client will need to be able to construct the correct JSON request body to send to the STAC API, including the `sortby` field as defined in the Sort extension.
- **Testing**: New tests will be needed to verify that the client correctly constructs sort parameters and can correctly parse the (unchanged) response. Tests should also cover the case where the API does not support sorting.

## Alternatives considered

- **Client-side sorting**: The client could fetch all results and then sort them locally. This is inefficient, especially for large result sets, and loses the performance benefits of server-side sorting. It also doesn't work for paginated results, as the full dataset is not available at once.
- **No sorting support**: We could continue to omit this feature. This would make the client less powerful than other available tools and would not meet the expectations of users familiar with STAC APIs.