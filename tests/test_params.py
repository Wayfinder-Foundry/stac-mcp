"""Test parameter preprocessing for various input formats."""

import pytest

from stac_mcp.tools.params import preprocess_parameters


def test_bbox_as_string():
    """Test that bbox as JSON string is converted to list."""
    args = {"bbox": "[-123.27, 49.15, -123.0, 49.35]"}
    result = preprocess_parameters(args)
    assert result["bbox"] == [-123.27, 49.15, -123.0, 49.35]
    assert isinstance(result["bbox"], list)
    assert all(isinstance(x, float) for x in result["bbox"])


def test_bbox_as_list():
    """Test that bbox as list is preserved."""
    args = {"bbox": [-123.27, 49.15, -123.0, 49.35]}
    result = preprocess_parameters(args)
    assert result["bbox"] == [-123.27, 49.15, -123.0, 49.35]
    assert isinstance(result["bbox"], list)


def test_bbox_none():
    """Test that bbox as None is preserved."""
    args = {"bbox": None}
    result = preprocess_parameters(args)
    assert result["bbox"] is None


def test_collections_as_string():
    """Test that collections as JSON string is converted to list."""
    args = {"collections": '["sentinel-2-l2a", "landsat-c2-l2"]'}
    result = preprocess_parameters(args)
    assert result["collections"] == ["sentinel-2-l2a", "landsat-c2-l2"]
    assert isinstance(result["collections"], list)


def test_collections_as_list():
    """Test that collections as list is preserved."""
    args = {"collections": ["sentinel-2-l2a", "landsat-c2-l2"]}
    result = preprocess_parameters(args)
    assert result["collections"] == ["sentinel-2-l2a", "landsat-c2-l2"]


def test_aoi_geojson_as_string():
    """Test that aoi_geojson as JSON string is converted to dict."""
    args = {
        "aoi_geojson": '{"type": "Polygon", "coordinates": [[[-123, 49], [-122, 49], [-122, 50], [-123, 50], [-123, 49]]]}'
    }
    result = preprocess_parameters(args)
    assert isinstance(result["aoi_geojson"], dict)
    assert result["aoi_geojson"]["type"] == "Polygon"


def test_aoi_geojson_as_dict():
    """Test that aoi_geojson as dict is preserved."""
    args = {
        "aoi_geojson": {
            "type": "Polygon",
            "coordinates": [
                [[-123, 49], [-122, 49], [-122, 50], [-123, 50], [-123, 49]]
            ],
        }
    }
    result = preprocess_parameters(args)
    assert isinstance(result["aoi_geojson"], dict)
    assert result["aoi_geojson"]["type"] == "Polygon"


def test_query_as_string():
    """Test that query as JSON string is converted to dict."""
    args = {"query": '{"eo:cloud_cover": {"lt": 10}}'}
    result = preprocess_parameters(args)
    assert isinstance(result["query"], dict)
    assert "eo:cloud_cover" in result["query"]


def test_query_as_dict():
    """Test that query as dict is preserved."""
    args = {"query": {"eo:cloud_cover": {"lt": 10}}}
    result = preprocess_parameters(args)
    assert isinstance(result["query"], dict)
    assert "eo:cloud_cover" in result["query"]


def test_empty_args():
    """Test that empty arguments are handled."""
    result = preprocess_parameters({})
    assert result == {}


def test_none_args():
    """Test that None arguments are handled."""
    result = preprocess_parameters(None)
    assert result is None


def test_invalid_json_string():
    """Test that invalid JSON strings are preserved as-is."""
    args = {"bbox": "not-valid-json"}
    result = preprocess_parameters(args)
    # Invalid JSON should be preserved as string (handler will deal with error)
    assert result["bbox"] == "not-valid-json"


def test_mixed_parameters():
    """Test preprocessing with mixed string and native types."""
    args = {
        "collections": '["sentinel-2-l2a"]',
        "bbox": [-123.27, 49.15, -123.0, 49.35],
        "datetime": "2025-01-01/2025-01-31",
        "limit": 10,
        "query": '{"eo:cloud_cover": {"lt": 10}}',
    }
    result = preprocess_parameters(args)
    assert isinstance(result["collections"], list)
    assert isinstance(result["bbox"], list)
    assert isinstance(result["query"], dict)
    assert result["datetime"] == "2025-01-01/2025-01-31"
    assert result["limit"] == 10
