"""Parameter preprocessing utilities for handling various input formats."""

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def preprocess_parameters(arguments: dict[str, Any]) -> dict[str, Any]:
    """Preprocess tool parameters to handle various input formats.

    This function normalizes parameters that may come in as strings but should be
    other types (arrays, objects, etc.). This is particularly useful when MCP clients
    serialize parameters as strings.

    Args:
        arguments: Raw arguments dictionary from MCP client

    Returns:
        Preprocessed arguments with proper types
    """
    if not arguments:
        return arguments

    processed = arguments.copy()

    # Handle bbox parameter - should be a list of 4 floats
    if "bbox" in processed and processed["bbox"] is not None:
        bbox = processed["bbox"]
        if isinstance(bbox, str):
            try:
                # Try to parse as JSON
                parsed = json.loads(bbox)
                if isinstance(parsed, list) and len(parsed) == 4:  # noqa: PLR2004
                    processed["bbox"] = [float(x) for x in parsed]
                    logger.debug(
                        "Converted bbox from string to list: %s", processed["bbox"]
                    )
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                logger.warning("Failed to parse bbox string: %s, error: %s", bbox, e)

    # Handle collections parameter - should be a list of strings
    if "collections" in processed and processed["collections"] is not None:
        collections = processed["collections"]
        if isinstance(collections, str):
            try:
                parsed = json.loads(collections)
                if isinstance(parsed, list):
                    processed["collections"] = parsed
                    logger.debug(
                        "Converted collections from string to list: %s",
                        processed["collections"],
                    )
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                logger.warning(
                    "Failed to parse collections string: %s, error: %s", collections, e
                )

    # Handle aoi_geojson parameter - should be a dict/object
    if "aoi_geojson" in processed and processed["aoi_geojson"] is not None:
        aoi = processed["aoi_geojson"]
        if isinstance(aoi, str):
            try:
                parsed = json.loads(aoi)
                if isinstance(parsed, dict):
                    processed["aoi_geojson"] = parsed
                    logger.debug("Converted aoi_geojson from string to dict")
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                logger.warning(
                    "Failed to parse aoi_geojson string: %s, error: %s", aoi, e
                )

    # Handle query parameter - should be a dict/object
    if "query" in processed and processed["query"] is not None:
        query = processed["query"]
        if isinstance(query, str):
            try:
                parsed = json.loads(query)
                if isinstance(parsed, dict):
                    processed["query"] = parsed
                    logger.debug("Converted query from string to dict")
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                logger.warning("Failed to parse query string: %s, error: %s", query, e)

    if "limit" in processed and processed["limit"] is not None:
        limit = processed["limit"]
        if isinstance(limit, str):
            try:
                processed["limit"] = int(limit)
                logger.debug(
                    "Converted limit from string to int: %d", processed["limit"]
                )
            except ValueError as e:
                logger.warning(
                    "Failed to convert limit string to int: %s, error: %s", limit, e
                )

    return processed
