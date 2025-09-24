# ASR 1006: NoData Handling and Memory Efficiency in Size Estimation

Status: Proposed
Date: 2025-09-23

## Context
Current data size estimation assumes uniform data density and treats array bytes as fully utilized. In practice, large proportions of pixels can be "no data" values (e.g., 0 for certain Planetary Computer L2A products, -9999 for ESA Sentinel‑2 conventions). When such nodata regions dominate, naive byte counts overstate effective storage or in‑memory footprint (especially with potential compression or masking strategies). We need a consistent approach to optionally discount nodata to produce a *more realistic working set* estimate without promising compression ratios we cannot guarantee.

## Requirement
* Extend `estimate_data_size` to:
  1. Inspect per‑asset or item metadata for known nodata indicators (common keys: `nodata`, `no_data_value`, STAC raster extension fields, or sentinel values provided via a configuration mapping).
  2. When using `odc.stac.load`, leverage data variable attributes (e.g., `attrs.get('nodata')`) if available; otherwise apply heuristic detection (single repeated extreme value across sample chunks if easily accessible without fully loading entire dataset).
  3. Provide an optional parameter `adjust_for_nodata` (default: false) to enable nodata discounting.
  4. If enabled, compute an estimated *effective data ratio* (e.g., 0.37 meaning 37% of pixels hold meaningful values) and scale the reported byte estimate by that ratio.
  5. Report both raw (unadjusted) and adjusted estimates when adjustment is applied.
  6. Guarantee fast execution: sampling for nodata detection must bound the number of inspected chunks / windows (e.g., limit to first N assets and small spatial windows).
  7. Avoid misrepresentation: always label adjusted values clearly and never hide the raw baseline estimate.
* Provide environment variable overrides (see ADR 0010) e.g. `STAC_MCP_NODATA_SAMPLE_PIXELS`, `STAC_MCP_NODATA_MAX_ASSETS` to tune sampling cost.
* Add tests using synthetic mocked arrays to validate nodata ratio math without network access.

## Implications
* The tool gains additional branching logic; maintain clear separation between baseline size calculation and optional nodata adjustment to keep complexity manageable.
* Requires documenting limitations (e.g., not a compression guarantee; masked rasters vs actual disk layout may differ).
* Future JSON mode must include `raw_estimated_bytes`, `adjusted_estimated_bytes`, and `effective_data_ratio` fields (when applicable) for contract stability.

## Alternatives considered
* Full histogram or sparse encoding simulation — rejected as overkill and potentially slow.
* Automatic always‑on nodata adjustment — rejected; some users prefer raw totals.

## Addendums
* None yet.
