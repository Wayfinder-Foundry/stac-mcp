# ADR 0009: Data Size Estimation Tool

Status: Proposed
Date: 2025-09-23

## Context
Users often need a fast, order‑of‑magnitude estimate of the volume of data (bytes, MB, GB) implied by a STAC query before committing to downstream processing or download steps. The baseline server (ADR 0001) did not include any resource planning utilities. The new `estimate_data_size` tool provides a value‑add planning primitive while keeping within the repository constraints (fast, offline‑testable, no mandatory heavy dependencies beyond those already selected).

Key goals:
* Provide quick, lazy estimation using `odc.stac` + `xarray` when available.
* Offer a deterministic fallback that requires only item metadata (works without fully loading raster assets; remains testable offline).
* Allow optional spatial subsetting via an AOI geometry to refine estimates to the *effective* area of interest.
* Preserve performance bounds — avoid unbounded iteration (respect a `limit`).

## Decision
Introduce a fifth tool `estimate_data_size` with parameters:
* `collections` (optional list[str])
* `bbox` (optional list[float] — WGS84 [west, south, east, north])
* `datetime` (optional ISO 8601 interval or timestamp)
* `query` (optional object for property filtering)
* `aoi_geojson` (optional GeoJSON geometry; used to derive a tighter effective bounding box when present)
* `limit` (int, default 100, max 500) — safeguards runtime and memory
* `catalog_url` (optional override)

Behavior:
1. Perform a STAC search (respecting the provided limit) and collect items.
2. If `odc.stac` is installed:
   * Attempt a lazy `odc.stac.load` call with `bbox` or AOI‑derived bbox and empty dask chunks to avoid pulling full data eagerly.
   * Derive per‑variable `nbytes` and aggregate total estimated size.
3. If the lazy load fails OR `odc.stac` is not installed:
   * Fallback estimation iterates assets and derives a heuristic size using (a) explicit `file:size` extra fields when present, otherwise (b) inferred size rules by media type and approximate area.
4. Return a text (current) or future JSON (ADR 0006) response summarizing item count, size in bytes/MB/GB, spatial/temporal context, variable or asset breakdown, and a message noting which method was used (lazy vs fallback).

## Consequences
* Adds planning capability without modifying existing search functionality.
* Requires two additional dependencies already accepted (`odc-stac`, `xarray`, `rasterio`) — tool still degrades gracefully if `odc.stac` import fails.
* Slightly increases code surface; future refactors (error handling, JSON mode, nodata handling) must include this tool.
* Fallback heuristics are approximate and documented as such — not a guarantee of precise on‑disk size.

## Alternatives considered
* Always eager download assets to compute exact size — rejected (slow, network heavy, violates ASR 1001 fast tests).
* Omit capability entirely — rejected (reduces user guidance; low effort incremental value).
* Require `odc.stac` as a hard dependency — rejected (allow installations that only need baseline search tools).

## Addendums
* 2025-09-23: Future enhancement planned (see ASR 1006) to account for `nodata` / `_FillValue` compression or sparsity heuristics.
