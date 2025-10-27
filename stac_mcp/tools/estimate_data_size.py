"""Estimate data size for a STAC query."""

import importlib.util
import logging
from typing import Any

from mcp.types import TextContent

from stac_mcp.tools import MAX_ASSET_LIST
from stac_mcp.tools.client import STACClient
from stac_mcp.utils.today import get_today_date

_LOGGER = logging.getLogger(__name__)

# Import advisory prompt text if available. Keep import optional so this module
# remains usable in environments without the prompts module or fastmcp.
try:
    from stac_mcp.fastmcp_prompts.dtype_preferences import (
        dtype_size_preferences,
    )
except (ImportError, ModuleNotFoundError):
    dtype_size_preferences = None

try:
    ODC_STAC_AVAILABLE = (
        importlib.util.find_spec("odc.stac") is not None
    )  # pragma: no cover
except ModuleNotFoundError:  # pragma: no cover
    ODC_STAC_AVAILABLE = False


def _validate_collections_argument(
    collections: list[str] | None,
) -> list[str]:
    match collections:
        case None:
            msg = "Collections argument is required."
            raise ValueError(msg)
        case []:
            msg = "Collections argument cannot be empty."
            raise ValueError(msg)
        case _:
            return collections


def _validate_datetime_argument(dt: str | None) -> str | None:
    """Datetime may be omitted. If 'latest' is provided, return today's date string."""
    if dt is None or dt == "":
        return None
    if dt == "latest":
        return f"{get_today_date()}"
    return dt


def _validate_query_argument(query: dict[str, Any] | None) -> dict[str, Any] | None:
    """Query is optional for estimate; return as-is (may be None)."""
    return query


def _validate_bbox_argument(bbox: list[float] | None) -> list[float] | None:
    """Validate bbox argument.

    BBox is optional for many STAC queries; if omitted, return None. If
    provided, it must be a sequence of four floats [minx, miny, maxx, maxy].
    """
    if bbox is None:
        return None
    bbox_len = 4
    # Accept any sequence of length 4
    if isinstance(bbox, (list, tuple)) and len(bbox) == bbox_len:
        return list(bbox)
    msg = (
        "Invalid bbox argument; must be a list of four floats: [minx, miny, maxx, maxy]"
    )
    raise ValueError(msg)


def _validate_aoi_geojson_argument(
    aoi_geojson: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """AOI GeoJSON is optional; return as-is (may be None)."""
    return aoi_geojson


def handle_estimate_data_size(
    client: STACClient,
    arguments: dict[str, Any],
) -> list[TextContent] | dict[str, Any]:
    collections = _validate_collections_argument(arguments.get("collections"))
    bbox = _validate_bbox_argument(arguments.get("bbox"))
    dt = _validate_datetime_argument(arguments.get("datetime"))
    query = _validate_query_argument(arguments.get("query"))
    aoi_geojson = _validate_aoi_geojson_argument(arguments.get("aoi_geojson"))
    limit = arguments.get("limit", 10)
    force_metadata_only = arguments.get("force_metadata_only", False)

    size_estimate = client.estimate_data_size(
        collections=collections,
        bbox=bbox,
        datetime=dt,
        query=query,
        aoi_geojson=aoi_geojson,
        limit=limit,
        force_metadata_only=force_metadata_only,
    )
    # Note: we do not return JSON here immediately because we want to ensure
    # sensor-native and queried totals are computed and included in the JSON
    # output. The JSON branch is evaluated after computing MB/GB fallbacks.
    result_text = "**Data Size Estimation**\n\n"
    item_count = size_estimate.get("item_count", 0)
    result_text += f"Items analyzed: {item_count}\n"

    # Be defensive: some estimator implementations may omit the
    # pre-computed MB/GB fields. Prefer explicit fields but fall back to
    # reconstructing from bytes when necessary.
    estimated_bytes = size_estimate.get("estimated_size_bytes")
    if estimated_bytes is None:
        # Some older/test fixtures may use 'estimated_bytes' or 'estimated_size'
        estimated_bytes = size_estimate.get("estimated_bytes")

    estimated_mb = size_estimate.get("estimated_size_mb")
    if estimated_mb is None and estimated_bytes is not None:
        try:
            estimated_mb = float(estimated_bytes) / (1024 * 1024)
        except (TypeError, ValueError):
            estimated_mb = None

    estimated_gb = size_estimate.get("estimated_size_gb")
    if estimated_gb is None and estimated_mb is not None:
        try:
            estimated_gb = float(estimated_mb) / 1024.0
        except (TypeError, ValueError):
            estimated_gb = None

    est_mb_str = (
        f"{estimated_mb:.2f} MB" if isinstance(estimated_mb, (int, float)) else "n/a"
    )
    est_gb_str = (
        f"{estimated_gb:.4f} GB" if isinstance(estimated_gb, (int, float)) else "n/a"
    )
    result_text += f"Estimated size: {est_mb_str} ({est_gb_str})\n"

    # Always surface sensor-native totals to the agent and the user.
    # Some estimator implementations compute an instrument-native (sensor) total
    # for narrower dtype suggestions; expose those values explicitly here.
    sensor_bytes = size_estimate.get("sensor_native_estimated_size_bytes")
    if sensor_bytes is None:
        sensor_bytes = size_estimate.get("sensor_native_estimated_bytes")

    sensor_mb = size_estimate.get("sensor_native_estimated_size_mb")
    if sensor_mb is None and sensor_bytes is not None:
        try:
            sensor_mb = float(sensor_bytes) / (1024 * 1024)
        except (TypeError, ValueError):
            sensor_mb = None

    sensor_gb = size_estimate.get("sensor_native_estimated_size_gb")
    if sensor_gb is None and sensor_mb is not None:
        try:
            sensor_gb = float(sensor_mb) / 1024.0
        except (TypeError, ValueError):
            sensor_gb = None

    s_mb_str = f"{sensor_mb:.2f} MB" if isinstance(sensor_mb, (int, float)) else "n/a"
    s_gb_str = f"{sensor_gb:.4f} GB" if isinstance(sensor_gb, (int, float)) else "n/a"
    result_text += f"Sensor-native estimated size: {s_mb_str} ({s_gb_str})\n"
    raw_bytes_str = (
        f"{int(estimated_bytes):,}" if estimated_bytes is not None else "n/a"
    )
    result_text += f"Raw bytes: {raw_bytes_str}\n\n"
    result_text += "**Query Parameters:**\n"
    result_text += "Collections: "
    collections_list = (
        ", ".join(size_estimate["collections"])
        if size_estimate["collections"]
        else "All"
    )
    result_text += f"{collections_list}\n"
    if size_estimate["bbox_used"]:
        b = size_estimate["bbox_used"]
        result_text += (
            f"Bounding box: [{b[0]:.4f}, {b[1]:.4f}, {b[2]:.4f}, {b[3]:.4f}]\n"
        )
    if size_estimate["temporal_extent"]:
        result_text += f"Time range: {size_estimate['temporal_extent']}\n"
    if size_estimate["clipped_to_aoi"]:
        result_text += "Clipped to AOI: Yes (minimized to smallest area)\n"
    if "data_variables" in size_estimate:
        result_text += "\n**Data Variables:**\n"
        for var_info in size_estimate["data_variables"]:
            # Support multiple possible size keys produced by different
            # estimator implementations/tests: prefer explicit 'size_mb',
            # then 'estimated_size_mb', then compute from 'estimated_bytes'.
            size_mb = None
            if "size_mb" in var_info:
                size_mb = var_info["size_mb"]
            elif "estimated_size_mb" in var_info:
                size_mb = var_info["estimated_size_mb"]
            elif (
                "estimated_bytes" in var_info
                and var_info["estimated_bytes"] is not None
            ):
                try:
                    size_mb = var_info["estimated_bytes"] / (1024 * 1024)
                except (TypeError, ValueError):
                    size_mb = None

            size_str = f"{size_mb:.2f}" if isinstance(size_mb, (int, float)) else "n/a"
            result_text += (
                f"  - {var_info.get('variable', 'unknown')}: {size_str} MB, "
                f"shape {var_info.get('shape')}, dtype {var_info.get('dtype')}\n"
            )
    if size_estimate.get("spatial_dims"):
        spatial = size_estimate["spatial_dims"]
        result_text += "\n**Spatial Dimensions:**\n"
        result_text += f"  X (longitude): {spatial.get('x', 0)} pixels\n"
        result_text += f"  Y (latitude): {spatial.get('y', 0)} pixels\n"
    if "assets_analyzed" in size_estimate:
        result_text += "\n**Assets Analyzed (fallback estimation):**\n"
        for asset_info in size_estimate["assets_analyzed"][:MAX_ASSET_LIST]:
            result_text += (
                f"  - {asset_info['asset']}: {asset_info['estimated_size_mb']} MB "
                f"({asset_info['media_type']})\n"
            )
        remaining = len(size_estimate["assets_analyzed"]) - MAX_ASSET_LIST
        if remaining > 0:
            result_text += f"  ... and {remaining} more assets\n"
    result_text += f"\n{size_estimate['message']}\n"
    # If JSON was requested, return a structured payload that includes both
    # the queried totals and the sensor-native totals so agents can rely on
    # a stable schema.
    if arguments.get("output_format") == "json":
        queried_totals = {
            "bytes": estimated_bytes,
            "mb": estimated_mb,
            "gb": estimated_gb,
        }
        sensor_native_totals = {
            "bytes": sensor_bytes,
            "mb": sensor_mb,
            "gb": sensor_gb,
        }
        return {
            "type": "data_size_estimate",
            "estimate": size_estimate,
            "queried_totals": queried_totals,
            "sensor_native_totals": sensor_native_totals,
        }

    # Append advisory guidance from the dtype prompt if available. This helps
    # agents and human users understand how to prefer compact dtypes and avoid
    # overestimation when NaN nodata forces float upcasts.
    if callable(dtype_size_preferences):
        try:
            advisory = dtype_size_preferences()
            if advisory:
                result_text += "\n**Estimator Advisory (dtype preferences)**\n"
                result_text += advisory + "\n"
        except (
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:  # pragma: no cover - best-effort
            _LOGGER.debug("estimate_data_size: advisory generation failed: %s", exc)
    return [TextContent(type="text", text=result_text)]
