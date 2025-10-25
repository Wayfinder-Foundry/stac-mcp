"""Tests for the sensor dtype registry."""

import numpy as np

from stac_mcp.tools.sensor_dtypes import SensorDtypeRegistry, SensorInfo


def test_sensor_info_get_dtype_for_asset():
    """Tests that SensorInfo.get_dtype_for_asset returns the correct dtype."""
    sensor_info = SensorInfo(
        default_dtype=np.dtype("uint16"),
        band_overrides={"scl": np.dtype("int8")},
    )
    assert sensor_info.get_dtype_for_asset("B02") == np.dtype("uint16")
    assert sensor_info.get_dtype_for_asset("SCL") == np.dtype("int8")
    assert sensor_info.get_dtype_for_asset("some_scl_band") == np.dtype("int8")
    assert sensor_info.get_dtype_for_asset(None) is None


def test_sensor_info_should_ignore_asset():
    """Tests that SensorInfo.should_ignore_asset identifies assets to ignore."""
    sensor_info = SensorInfo(default_dtype=np.dtype("uint16"))
    assert sensor_info.should_ignore_asset("preview")
    assert sensor_info.should_ignore_asset("thumbnail")
    assert sensor_info.should_ignore_asset("browse")
    assert sensor_info.should_ignore_asset("rgb")
    assert not sensor_info.should_ignore_asset("B02")
    assert sensor_info.should_ignore_asset(None, "image/jpeg")
    assert sensor_info.should_ignore_asset(None, "image/png")
    assert not sensor_info.should_ignore_asset(None, "image/tiff")


def test_sensor_dtype_registry_get_info():
    """Tests that SensorDtypeRegistry.get_info returns the correct SensorInfo."""
    info = SensorDtypeRegistry.get_info("sentinel-2-l2a")
    assert info is not None
    assert info.default_dtype == np.dtype("uint16")
    assert info.band_overrides["scl"] == np.dtype("int8")

    assert SensorDtypeRegistry.get_info("non-existent-collection") is None
    assert SensorDtypeRegistry.get_info(None) is None


def test_sensor_dtype_registry_get_dtype_for_collection():
    """Tests SensorDtypeRegistry.get_dtype_for_collection returns the correct dtype."""
    assert SensorDtypeRegistry.get_dtype_for_collection("sentinel-2-l2a") == np.dtype(
        "uint16"
    )
    assert (
        SensorDtypeRegistry.get_dtype_for_collection("non-existent-collection") is None
    )
    assert SensorDtypeRegistry.get_dtype_for_collection(None) is None
