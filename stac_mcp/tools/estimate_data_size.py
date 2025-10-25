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
    if arguments.get("output_format") == "json":
        return {"type": "data_size_estimate", "estimate": size_estimate}
    result_text = "**Data Size Estimation**\n\n"
    result_text += f"Items analyzed: {size_estimate['item_count']}\n"
    result_text += (
        f"Estimated size: {size_estimate['estimated_size_mb']:.2f} MB "
        f"({size_estimate['estimated_size_gb']:.4f} GB)\n"
    )
    result_text += f"Raw bytes: {size_estimate['estimated_size_bytes']:,}\n\n"
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
            result_text += (
                f"  - {var_info['variable']}: {var_info['size_mb']} MB, "
                f"shape {var_info['shape']}, dtype {var_info['dtype']}\n"
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
