"""Simple registry for sensor native band dtypes.

This module provides a tiny dataclass used by the simplified
`estimate_data_size` to map collection/sensor identifiers to their
native per-band numpy dtypes. It's intentionally small and easy to
extend; it does not attempt to be exhaustive.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence


from dataclasses import dataclass, field
from typing import ClassVar

import numpy as np


def handle_sensor_registry_info(
    _client: Any,
    _arguments: dict[str, Any],
) -> dict[str, Any]:
    """Handle the sensor_registry_info tool.

    Returns a mapping of collection ids to their sensor dtype info.
    """
    registry_info: dict[str, Any] = {}
    for collection_id, sensor_info in SensorDtypeRegistry.registry.items():
        registry_info[collection_id] = {
            "default_dtype": str(sensor_info.default_dtype),
            "band_overrides": {
                k: str(v) for k, v in sensor_info.band_overrides.items()
            },
            "ignore_asset_name_substrings": sensor_info.ignore_asset_name_substrings,
        }
    return {"sensor_registry": registry_info}


@dataclass
class SensorInfo:
    """Information about a sensor/collection's native dtypes.

    - default_dtype: a numpy dtype used for the main image bands.
    - band_overrides: optional mapping of asset-name-substring -> dtype
      for special bands (e.g., 'scl' -> int8).
    - ignore_asset_name_substrings: list of substrings; if an asset name
      contains any of these, the estimator should skip it (e.g. previews).
    """

    default_dtype: np.dtype
    band_overrides: dict[str, np.dtype] = field(default_factory=dict)
    ignore_asset_name_substrings: Sequence[str] = field(
        default_factory=lambda: ["preview", "thumbnail", "browse", "rgb"]
    )  # common preview hints
    # Optional mapping of catalog base URL (or short provider key) -> collection id
    # used by that catalog. This allows alias resolution when different STAC
    # providers use slightly different collection ids for the same sensor.
    catalog_aliases: dict[str, str] = field(default_factory=dict)

    def get_dtype_for_asset(self, asset_name: str | None) -> np.dtype | None:
        """Return the preferred dtype for an asset given its name.

        The lookup is substring-based and case-insensitive. Returns the
        default_dtype when no override matches; returns None if asset_name
        is None.
        """
        if asset_name is None:
            return None
        an = asset_name.lower()
        for key, dt in self.band_overrides.items():
            if key.lower() in an:
                return dt
        return self.default_dtype

    def should_ignore_asset(
        self, asset_name: str | None, media_type: str | None = None
    ) -> bool:
        """Return True if the asset should be ignored based on name or media type."""
        if asset_name:
            an = asset_name.lower()
            for s in self.ignore_asset_name_substrings:
                if s.lower() in an:
                    return True
        if media_type:
            mt = media_type.lower()
            # Some thumbnails/previews are provided as image/jpeg, image/png
            if "thumbnail" in mt or "preview" in mt or "jpeg" in mt or "png" in mt:
                return True
        return False


def _make_si(
    default: str,
    band_overrides: dict | None = None,
    ignore: list[str] | None = None,
    aliases: dict[str, str] | None = None,
) -> SensorInfo:
    return SensorInfo(
        default_dtype=np.dtype(default),
        band_overrides={k: np.dtype(v) for k, v in (band_overrides or {}).items()},
        ignore_asset_name_substrings=ignore
        or ["preview", "thumbnail", "browse", "rgb"],
        catalog_aliases=aliases or {},
    )


class SensorDtypeRegistry:
    """Registry that maps exact collection ids (lower-cased) to SensorInfo.

    Edit the `registry` dict to add explicit, exact collection id mappings.
    """

    registry: ClassVar[dict[str, SensorInfo]] = {
        # Sentinel / Copernicus
        "sentinel-2-l2a": _make_si("uint16", {"scl": "int8"}),
        "sentinel-2-l1c": _make_si("uint16"),
        # AWS Earth Search uses the 'collection 1' ids (sentinel-2-c1-l2a). The
        # Planetary Computer uses the simpler 'sentinel-2-l2a' id. Provide
        # catalog_aliases so callers can resolve catalog-specific ids.
        "sentinel-2-c1-l2a": _make_si(
            "uint16",
            {"scl": "int8"},
            None,
            {"https://earth-search.aws.element84.com/v1": "sentinel-2-c1-l2a"},
        ),
        "sentinel-2-pre-c1-l2a": _make_si(
            "uint16",
            {"scl": "int8"},
            None,
            {"https://earth-search.aws.element84.com/v1": "sentinel-2-pre-c1-l2a"},
        ),
        "sentinel-1-grd": _make_si("float32"),
        "sentinel-1-rtc": _make_si("float32"),
        "sentinel-3-olci-lfr-l2-netcdf": _make_si("float32"),
        "sentinel-5p-l2-netcdf": _make_si("float32"),
        # Landsat
        "landsat-c2-l2": _make_si("uint16", {"qa": "uint16"}),
        "landsat-c2-l1": _make_si("uint16", {"qa": "uint16"}),
        # HLS
        "hls2-s30": _make_si("uint16", {"scl": "int8"}),
        "hls2-l30": _make_si("uint16", {"scl": "int8"}),
        # MODIS
        "modis-09a1-061": _make_si("int16"),
        "modis-09q1-061": _make_si("int16"),
        # NAIP
        "naip": _make_si("uint8"),
        # Climate / gridded
        "daymet-daily-pr": _make_si("float32"),
        "daymet-daily-na": _make_si("float32"),
        "daymet-annual-na": _make_si("float32"),
        "daymet-monthly-na": _make_si("float32"),
        "gridmet": _make_si("float32"),
        "terraclimate": _make_si("float32"),
        "era5-pds": _make_si("float32"),
        # DEMs
        "cop-dem-glo-30": _make_si("float32"),
        "cop-dem-glo-90": _make_si("float32"),
        "3dep-seamless": _make_si("float32"),
        "3dep-lidar-dsm": _make_si("float32"),
        "3dep-lidar-dtm": _make_si("float32"),
        "3dep-lidar-intensity": _make_si("float32"),
        # Misc
        "gpm-imerg-hhr": _make_si("float32"),
        "nasadem": _make_si("float32"),
        "hgb": _make_si("float32"),
        "ms-buildings": _make_si("uint8"),
        "io-lulc": _make_si("uint8"),
        "us-census": _make_si("uint8"),
    }

    @classmethod
    def get_info(cls, collection_id: str | None) -> SensorInfo | None:
        if not collection_id:
            return None
        return cls.registry.get(collection_id.lower())

    @classmethod
    def resolve_for_catalog(
        cls, collection_id: str | None, catalog_url: str | None
    ) -> tuple[str | None, SensorInfo | None]:
        """Resolve a potentially catalog-specific collection id to the
        registry's canonical collection id and SensorInfo.

        Returns (canonical_collection_id, SensorInfo) or (None, None) when
        resolution fails.
        """
        if not collection_id:
            return None, None
        cid = collection_id.lower()
        # direct match
        if cid in cls.registry:
            return cid, cls.registry[cid]

        # If a catalog_url is provided, try to match against catalog_aliases
        if catalog_url:
            cul = catalog_url.rstrip("/").lower()
            for canonical_id, info in cls.registry.items():
                for key, alias in info.catalog_aliases.items():
                    if key.rstrip("/").lower() == cul:
                        if alias.lower() == cid:
                            return canonical_id, info
                        # also allow matching when caller provided canonical id
                        if canonical_id == cid:
                            return canonical_id, info

        # As a last resort, try to match the provided id to any known alias
        for canonical_id, info in cls.registry.items():
            for alias in info.catalog_aliases.values():
                if alias.lower() == cid:
                    return canonical_id, info

        return None, None

    @classmethod
    def get_dtype_for_collection(cls, collection_id: str | None) -> np.dtype | None:
        info = cls.get_info(collection_id)
        return info.default_dtype if info is not None else None
