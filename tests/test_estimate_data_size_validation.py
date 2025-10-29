# ruff: noqa: SLF001
import pytest

import stac_mcp.tools.estimate_data_size as eds


def test_validate_collections_argument_none_raises():
    with pytest.raises(ValueError, match="Collections argument is required"):
        eds._validate_collections_argument(None)


def test_validate_collections_argument_empty_raises():
    with pytest.raises(ValueError, match="Collections argument cannot be empty"):
        eds._validate_collections_argument([])


def test_validate_collections_argument_valid_returns():
    cols = ["c1", "c2"]
    assert eds._validate_collections_argument(cols) == cols


def test_validate_datetime_argument_none_or_empty_raises():
    # datetime is optional now and should return None when omitted/empty
    assert eds._validate_datetime_argument(None) is None
    assert eds._validate_datetime_argument("") is None


def test_validate_datetime_argument_latest(monkeypatch):
    # Make get_today_date deterministic
    monkeypatch.setattr(eds, "get_today_date", lambda: "2025-10-21")
    res = eds._validate_datetime_argument("latest")
    # implementation returns a single date string for 'latest'
    assert res == "2025-10-21"


def test_validate_datetime_argument_pass_through():
    assert (
        eds._validate_datetime_argument("2020-01-01/2020-01-02")
        == "2020-01-01/2020-01-02"
    )


def test_validate_query_argument_none_raises():
    # query argument is optional and should return None when omitted
    assert eds._validate_query_argument(None) is None


def test_validate_query_argument_valid_returns():
    q = {"eo:cloud_cover": {"lt": 10}}
    assert eds._validate_query_argument(q) == q


def test_validate_bbox_argument_none_raises():
    # bbox is optional and should return None when omitted
    assert eds._validate_bbox_argument(None) is None


def test_validate_bbox_argument_invalid_raises():
    with pytest.raises(ValueError, match="Invalid bbox argument"):
        eds._validate_bbox_argument([0.0, 1.0, 2.0])


def test_validate_bbox_argument_valid_returns():
    bbox = [0.0, 0.0, 1.0, 1.0]
    assert eds._validate_bbox_argument(bbox) == bbox


def test_validate_aoi_geojson_argument_none_raises():
    # aoi_geojson is optional and should return None when omitted
    assert eds._validate_aoi_geojson_argument(None) is None


def test_validate_aoi_geojson_argument_valid_returns():
    geo = {
        "type": "Polygon",
        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 0]]],
    }  # minimal
    assert eds._validate_aoi_geojson_argument(geo) == geo
