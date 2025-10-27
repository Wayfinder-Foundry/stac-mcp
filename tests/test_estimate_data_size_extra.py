
"""Extra tests for stac_mcp/tools/estimate_data_size.py."""

from unittest.mock import MagicMock

import pytest
from mcp.types import TextContent

from stac_mcp.tools.estimate_data_size import (
    _validate_aoi_geojson_argument,
    _validate_bbox_argument,
    _validate_collections_argument,
    _validate_datetime_argument,
    _validate_query_argument,
    handle_estimate_data_size,
)


def test_validate_collections_argument_none():
    """Test _validate_collections_argument with None."""
    with pytest.raises(ValueError, match="Collections argument is required."):
        _validate_collections_argument(None)


def test_validate_collections_argument_empty():
    """Test _validate_collections_argument with empty list."""
    with pytest.raises(ValueError, match="Collections argument cannot be empty."):
        _validate_collections_argument([])


def test_validate_collections_argument_valid():
    """Test _validate_collections_argument with a valid list."""
    assert _validate_collections_argument(["collection1"]) == ["collection1"]


def test_validate_datetime_argument_none():
    """Test _validate_datetime_argument with None."""
    assert _validate_datetime_argument(None) is None


def test_validate_datetime_argument_empty():
    """Test _validate_datetime_argument with an empty string."""
    assert _validate_datetime_argument("") is None


def test_validate_datetime_argument_latest():
    """Test _validate_datetime_argument with 'latest'."""
    assert _validate_datetime_argument("latest") is not None


def test_validate_datetime_argument_valid():
    """Test _validate_datetime_argument with a valid datetime string."""
    assert _validate_datetime_argument("2022-01-01T00:00:00Z") == "2022-01-01T00:00:00Z"


def test_validate_query_argument():
    """Test _validate_query_argument."""
    assert _validate_query_argument(None) is None
    assert _validate_query_argument({"key": "value"}) == {"key": "value"}


def test_validate_bbox_argument_none():
    """Test _validate_bbox_argument with None."""
    assert _validate_bbox_argument(None) is None


def test_validate_bbox_argument_invalid_length():
    """Test _validate_bbox_argument with an invalid length."""
    with pytest.raises(ValueError, match="Invalid bbox argument"):
        _validate_bbox_argument([1.0, 2.0, 3.0])


def test_validate_bbox_argument_valid():
    """Test _validate_bbox_argument with a valid bbox."""
    assert _validate_bbox_argument([1.0, 2.0, 3.0, 4.0]) == [1.0, 2.0, 3.0, 4.0]


def test_validate_aoi_geojson_argument():
    """Test _validate_aoi_geojson_argument."""
    assert _validate_aoi_geojson_argument(None) is None
    assert _validate_aoi_geojson_argument({"type": "Polygon"}) == {"type": "Polygon"}


class FakeClient:
    """Fake STACClient for testing."""

    def estimate_data_size(self, **kwargs):  # noqa: ARG002
        """Fake estimate_data_size."""
        return {
            "item_count": 1,
            "estimated_size_bytes": 1024 * 1024,
            "collections": ["collection1"],
            "bbox_used": [0, 0, 1, 1],
            "temporal_extent": "2022-01-01/2022-01-02",
            "clipped_to_aoi": False,
            "message": "Success",
        }


def test_handle_estimate_data_size_text_output():
    """Test handle_estimate_data_size with text output."""
    client = FakeClient()
    arguments = {"collections": ["collection1"]}
    result = handle_estimate_data_size(client, arguments)
    assert isinstance(result, list)
    assert len(result) == 1
    assert isinstance(result[0], TextContent)
    assert "Data Size Estimation" in result[0].text


def test_handle_estimate_data_size_json_output():
    """Test handle_estimate_data_size with json output."""
    client = FakeClient()
    arguments = {"collections": ["collection1"], "output_format": "json"}
    result = handle_estimate_data_size(client, arguments)
    assert isinstance(result, dict)
    assert result["type"] == "data_size_estimate"

def test_handle_estimate_data_size_no_bbox_used():
    """Test handle_estimate_data_size when bbox_used is not in the response."""
    client = FakeClient()
    # Modify the estimate_data_size to return a response without bbox_used
    client.estimate_data_size = lambda **kwargs: {
        "item_count": 1,
        "estimated_size_bytes": 1024 * 1024,
        "collections": ["collection1"],
        "temporal_extent": "2022-01-01/2022-01-02",
        "clipped_to_aoi": False,
        "message": "Success",
    }
    arguments = {"collections": ["collection1"]}
    result = handle_estimate_data_size(client, arguments)
    assert "Bounding box" not in result[0].text

def test_handle_estimate_data_size_no_temporal_extent():
    """Test handle_estimate_data_size when temporal_extent is not in the response."""
    client = FakeClient()
    client.estimate_data_size = lambda **kwargs: {
        "item_count": 1,
        "estimated_size_bytes": 1024 * 1024,
        "collections": ["collection1"],
        "bbox_used": [0, 0, 1, 1],
        "clipped_to_aoi": False,
        "message": "Success",
    }
    arguments = {"collections": ["collection1"]}
    result = handle_estimate_data_size(client, arguments)
    assert "Time range" not in result[0].text
