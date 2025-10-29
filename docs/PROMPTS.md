# FastMCP Prompts Deep Dive for STAC MCP

**Status**: Technical Guide  
**Last Updated**: 2025-10-18  
**Purpose**: Understand `@mcp.prompt()` and its role in agentic geospatial STAC reasoning

---

## Table of Contents

1. [What Are MCP Prompts?](#what-are-mcp-prompts)
2. [Why Prompts Are Crucial for STAC](#why-prompts-are-crucial-for-stac)
3. [Tools vs Prompts in STAC](#tools-vs-prompts-in-stac)
4. [How Prompts Enable STAC Vision](#how-prompts-enable-stac-vision)
5. [Basic Usage](#basic-usage)
6. [Advanced Patterns](#advanced-patterns)
7. [STAC Geospatial Examples](#stac-geospatial-examples)
8. [Best Practices](#best-practices)

---

## What Are MCP Prompts?

### Definition

**MCP Prompts are reusable message templates that guide AI agents in reasoning about STAC catalog searches and geospatial data discovery.**

Think of them as **conversation starters** that help the AI understand:
- What kind of geospatial problem it's solving
- Which STAC collections are relevant
- What search parameters to use
- What temporal/spatial filters make sense

### Key Concept

```
Tools = STAC search actions the AI can execute
Prompts = Guidance on how to think about STAC searches
```

**Tools answer "what STAC operations can I do?"**  
**Prompts answer "how should I approach this STAC search?"**

---

## Why Prompts Are Crucial for STAC

### The Problem Without Prompts

Without prompts, the AI has to figure out from scratch:
- Which STAC collection to search (hundreds available)
- How to format temporal filters (datetime strings)
- What spatial extent to use (bbox coordinates)
- Which filters to apply (cloud cover, resolution)

**Result**: Random collection choices, malformed queries, poor results

### The Power of Prompts for STAC

With well-designed prompts, you can:

1. **Guide Collection Selection**: "For land cover, use Landsat or Sentinel-2..."
2. **Establish Search Patterns**: "To find recent imagery, start with small time window..."
3. **Encode STAC Knowledge**: "Datetime format is ISO 8601 with Z suffix..."
4. **Ensure Best Practices**: "Before searching, verify collection availability..."

**Result**: Consistent, domain-aware STAC searches that find relevant data

---

## Tools vs Prompts in STAC

### Tools (`@mcp.tool()`)

```python
@mcp.tool()
async def search_items(
    collections: list[str],
    bbox: list[float] | None = None,
    datetime: str | None = None,
    limit: int = 10
) -> dict:
    """Search STAC catalog for items."""
    # Executes a STAC search
    results = await stac_client.search(
        collections=collections,
        bbox=bbox,
        datetime=datetime,
        limit=limit
    )
    return {"items": list(results)}
```

**What it does**: Performs a specific STAC search  
**When used**: AI has already decided search parameters  
**Returns**: Concrete STAC items

### Prompts (`@mcp.prompt()`)

```python
@mcp.prompt()
def stac_search_methodology(
    data_type: str,
    region: str,
    time_period: str
) -> str:
    """Guide the AI in planning a STAC search."""
    return f"""
    You are searching for {data_type} in {region} during {time_period}.
    
    STAC Search Planning:
    
    1. COLLECTION SELECTION
       - Landsat Collection 2: 30m, global, long archive
       - Sentinel-2 L2A: 10-20m, global, recent imagery
       - NAIP: 0.6-1m, USA only, high resolution
       
       Which collection best fits {data_type}?
    
    2. SPATIAL EXTENT
       - Define bbox for {region} as [west, south, east, north]
       - Use EPSG:4326 (WGS84) coordinates
       - Example: [-122.5, 37.7, -122.3, 37.8] for San Francisco
    
    3. TEMPORAL FILTER
       - Parse {time_period} to STAC datetime format
       - Single date: "2023-06-15T00:00:00Z"
       - Range: "2023-01-01T00:00:00Z/2023-12-31T23:59:59Z"
    
    4. ADDITIONAL FILTERS
       - Cloud cover < 20% for optical imagery
       - Consider seasonal effects
    
    What search parameters will you use?
    """
```

**What it does**: Guides thinking and planning  
**When used**: Before AI decides STAC search parameters  
**Returns**: Message that helps AI reason about STAC

---

## How Prompts Enable STAC Vision

### Recall: The Vision

Enable AI agents to **reason about geospatial data discovery**, not just execute STAC searches.

### How Prompts Achieve This

#### 1. **Multi-Step STAC Workflow Composition**

**Without Prompts:**
```
User: "Find satellite images of California wildfires"
AI: → Calls search_items with random collection
    → Gets no results or wrong data
    → Asks user for help
```

**With Prompts:**
```
User: "Find satellite images of California wildfires"
AI: → Uses wildfire_imagery_prompt
    → Understands: Need recent Landsat/Sentinel-2, low cloud cover
    → Determines bbox for California fire region
    → Constructs temporal filter for fire season
    → Executes search_items with proper parameters
    → Returns relevant fire imagery with methodology explanation
```

#### 2. **STAC Specification Understanding**

**Without Prompts:**
```python
# AI doesn't understand STAC datetime format
User: "Find imagery from June 2023"
AI: search_items(datetime="June 2023")  # WRONG FORMAT
```

**With Prompts:**
```python
@mcp.prompt()
def temporal_filter_guide(time_description: str) -> str:
    return f"""
    STAC DATETIME FORMAT GUIDE
    
    User wants: {time_description}
    
    STAC datetime must be ISO 8601 format:
    - Single instant: "2023-06-15T00:00:00Z"
    - Time range: "2023-06-01T00:00:00Z/2023-06-30T23:59:59Z"
    - Open start: "../2023-06-30T23:59:59Z" (everything before)
    - Open end: "2023-06-01T00:00:00Z/.." (everything after)
    
    Convert "{time_description}" to proper STAC datetime format.
    """
```

Now AI understands STAC spec and formats queries correctly.

#### 3. **Collection Selection Expertise**

**Example: Choosing the Right STAC Collection**

```python
@mcp.prompt()
def choose_stac_collection(
    use_case: str,
    resolution_need: str,
    area: str
) -> str:
    """Encode collection selection expertise."""
    return f"""
    STAC COLLECTION SELECTION GUIDE
    
    Use case: {use_case}
    Resolution need: {resolution_need}
    Area: {area}
    
    AVAILABLE COLLECTIONS:
    
    1. Landsat Collection 2 (landsat-c2l2-sr)
       - Resolution: 30 meters
       - Coverage: Global
       - Archive: 1972-present
       - Revisit: 16 days
       - Best for: Long-term change detection, historical analysis
       - Bands: 11 (visible, NIR, SWIR, thermal)
    
    2. Sentinel-2 Level-2A (sentinel-2-l2a)
       - Resolution: 10-20 meters
       - Coverage: Global (land)
       - Archive: 2015-present
       - Revisit: 5 days
       - Best for: Recent imagery, vegetation monitoring, high frequency
       - Bands: 13 (visible, red edge, NIR, SWIR)
    
    3. NAIP (naip)
       - Resolution: 0.6-1 meter
       - Coverage: USA only
       - Archive: 2010-present
       - Revisit: Annual/biennial
       - Best for: High-resolution US mapping, urban analysis
       - Bands: 4 (RGB, NIR)
    
    DECISION MATRIX:
    
    For {use_case}:
    - If need historical data (>10 years) → Landsat
    - If need recent, frequent imagery → Sentinel-2
    - If need very high resolution in USA → NAIP
    - If monitoring vegetation → Sentinel-2 (more bands)
    - If thermal analysis → Landsat (has thermal bands)
    
    For {resolution_need}:
    - <5m → NAIP (USA only)
    - 10-20m → Sentinel-2
    - 30m → Landsat
    
    For {area}:
    - USA → Any collection
    - Global → Landsat or Sentinel-2
    - Europe/Asia/Africa → Sentinel-2 or Landsat
    
    Which collection(s) do you recommend and why?
    """
```

Now AI has collection selection expertise encoded.

#### 4. **Spatial Query Reasoning**

```python
@mcp.prompt()
def construct_bbox(
    location_description: str,
    data_type: str
) -> str:
    """Help AI construct appropriate bounding box."""
    return f"""
    SPATIAL EXTENT (BBOX) CONSTRUCTION
    
    Location: {location_description}
    Data type: {data_type}
    
    BBOX FORMAT: [west, south, east, north] in EPSG:4326
    
    GUIDELINES:
    
    1. Determine approximate coordinates:
       - Look up {location_description} coordinates
       - Use decimal degrees (not DMS)
       - West/East: -180 to 180
       - South/North: -90 to 90
    
    2. Size considerations for {data_type}:
       - Small area (<10km²): Tight bbox for precision
       - Medium area (10-1000km²): Standard bbox
       - Large area (>1000km²): Consider multiple searches
    
    3. Buffer considerations:
       - Add ~0.1° buffer for edge effects
       - Larger buffer for cloud coverage concerns
       - Smaller buffer for precise urban areas
    
    EXAMPLES:
    - San Francisco: [-122.5, 37.7, -122.3, 37.9]
    - Greater London: [-0.5, 51.3, 0.3, 51.7]
    - Manhattan: [-74.02, 40.70, -73.91, 40.88]
    
    Construct bbox for {location_description}.
    """
```

AI can now reason about spatial queries.

---

## Basic Usage

### 1. Simple STAC Search Prompt

```python
from fastmcp import FastMCP

mcp = FastMCP("STAC MCP")

@mcp.prompt()
def ask_about_collection(collection_id: str) -> str:
    """Ask about a STAC collection."""
    return f"Explain the {collection_id} STAC collection and when to use it for geospatial analysis."
```

**Returns**: Simple string converted to user message

### 2. Prompt with Search Parameters

```python
@mcp.prompt()
def plan_stac_search(
    data_need: str,
    location: str,
    time_range: str,
    quality_requirements: str
) -> str:
    """Guide quality assessment of STAC search strategy."""
    return f"""
    STAC SEARCH PLANNING
    
    Data need: {data_need}
    Location: {location}
    Time range: {time_range}
    Quality requirements: {quality_requirements}
    
    Planning steps:
    
    1. COLLECTION SELECTION
       - Match {data_need} to appropriate collections
       - Verify coverage includes {location}
       - Check temporal availability for {time_range}
    
    2. SPATIAL FILTER
       - Define bbox for {location}
       - Consider buffer zones
       - Validate coordinate bounds
    
    3. TEMPORAL FILTER
       - Convert {time_range} to ISO 8601
       - Consider seasonal effects
       - Plan for data gaps
    
    4. QUALITY FILTERS
       - Apply {quality_requirements}
       - Cloud cover thresholds
       - Resolution requirements
    
    5. SEARCH STRATEGY
       - Start with limit=10 to test
       - Iterate if results insufficient
       - Refine parameters based on results
    
    What is your STAC search plan?
    """
```

**Parameters**: Required and optional (with defaults)

---

## Advanced Patterns

### 1. Context Injection for STAC

```python
from fastmcp import Context

@mcp.prompt()
async def guided_catalog_search(
    dataset_type: str,
    ctx: Context
) -> str:
    """Prompt with access to server context."""
    await ctx.info(f"Generating STAC search prompt for {dataset_type}")
    
    return f"""
    Search STAC catalog for {dataset_type}.
    
    You have access to:
    - search_items: Find STAC items
    - get_collection: Get collection details
    - get_queryables: See available filters
    
    Plan a comprehensive search workflow.
    """
```

**Use case**: Logging, progress tracking, dynamic content

### 2. Conditional Logic for STAC Prompts

```python
@mcp.prompt()
def adaptive_search_prompt(
    data_type: str,
    urgency: str,
    budget: str = "normal"
) -> str:
    """Adapt prompt based on search requirements."""
    
    prompt = f"Search for {data_type} with {urgency} urgency\n\n"
    
    if urgency == "high":
        prompt += """
        HIGH URGENCY SEARCH:
        - Prioritize Sentinel-2 (5-day revisit)
        - Accept higher cloud cover if needed
        - Use recent acquisitions only
        - Consider commercial data if available
        """
    
    if budget == "limited":
        prompt += """
        BUDGET-CONSCIOUS SEARCH:
        - Use free/open data (Landsat, Sentinel)
        - Avoid commercial catalogs
        - Optimize search to minimize API calls
        """
    
    return prompt
```

**Use case**: Different guidance based on search context

### 3. Metadata-Rich STAC Prompts

```python
@mcp.prompt(
    name="satellite_imagery_search",
    description="Guide satellite imagery search in STAC catalogs",
    tags={"stac", "satellite", "imagery"},
    meta={"methodology": "standard_eo", "version": "1.0"}
)
def satellite_search_prompt(collection: str, region: str) -> str:
    """Satellite imagery search methodology."""
    return f"Search {collection} for imagery over {region}"
```

**Use case**: Categorization, versioning, discovery

---

## STAC Geospatial Examples

### Example 1: Change Detection Workflow

```python
@mcp.prompt()
def change_detection_methodology(
    before_date: str,
    after_date: str,
    region: str,
    change_type: str
) -> str:
    """Guide temporal change detection in STAC."""
    return f"""
    CHANGE DETECTION WORKFLOW
    
    Before date: {before_date}
    After date: {after_date}
    Region: {region}
    Change type: {change_type}
    
    STAC SEARCH STRATEGY:
    
    1. DATA SELECTION
       - Use same collection for both dates
       - Sentinel-2 recommended for vegetation/land cover
       - Landsat for historical comparisons
    
    2. TEMPORAL QUERIES
       - Before search: datetime="{before_date}/+7days"
       - After search: datetime="{after_date}/+7days"
       - Allow ±7 day window for cloud-free imagery
    
    3. SPATIAL CONSISTENCY
       - Use identical bbox for both searches
       - Ensure complete coverage of {region}
       - Consider scene overlap
    
    4. QUALITY MATCHING
       - Match cloud cover thresholds
       - Similar sun angles if available
       - Same processing levels
    
    5. CHANGE ANALYSIS
       - For {change_type}:
         * Urban growth → Use NIR band
         * Vegetation → Use NDVI
         * Water extent → Use NDWI
         * Fire damage → Use NBR
    
    Plan your STAC searches to detect {change_type} changes.
    """
```

### Example 2: Seasonal Imagery Selection

```python
@mcp.prompt()
def seasonal_imagery_guide(
    location: str,
    season: str,
    purpose: str
) -> str:
    """Guide seasonal STAC imagery selection."""
    return f"""
    SEASONAL IMAGERY SELECTION
    
    Location: {location}
    Season: {season}
    Purpose: {purpose}
    
    TEMPORAL STRATEGY:
    
    For {season} in {location}:
    
    NORTHERN HEMISPHERE:
    - Spring: March-May → Leaf-on transition
    - Summer: June-August → Peak vegetation
    - Fall: September-November → Senescence
    - Winter: December-February → Leaf-off/snow
    
    SOUTHERN HEMISPHERE (reverse):
    - Spring: September-November
    - Summer: December-February
    - Fall: March-May
    - Winter: June-August
    
    CONSIDERATIONS FOR {purpose}:
    
    If vegetation mapping:
    - Use peak growing season imagery
    - Avoid cloud/snow periods
    - Multiple dates for phenology
    
    If land cover classification:
    - Multi-season imagery recommended
    - Captures different spectral signatures
    - Reduces confusion classes
    
    If urban/infrastructure:
    - Leaf-off season preferred
    - Better visibility through trees
    - Less shadow confusion
    
    STAC DATETIME CONSTRUCTION:
    - Single month: "2023-06-01T00:00:00Z/2023-06-30T23:59:59Z"
    - Season range: "2023-06-01T00:00:00Z/2023-08-31T23:59:59Z"
    - Multi-year: Search each year separately
    
    What temporal filter will you use?
    """
```

### Example 3: Cloud Cover Strategy

```python
@mcp.prompt()
def cloud_cover_strategy(
    data_type: str,
    location: str,
    urgency: str
) -> str:
    """Guide cloud cover filtering in STAC searches."""
    return f"""
    CLOUD COVER FILTERING STRATEGY
    
    Data type: {data_type}
    Location: {location}
    Urgency: {urgency}
    
    CLOUD COVER QUERYABLE:
    - Property: "eo:cloud_cover"
    - Range: 0-100 (percentage)
    - Filter: query={{"eo:cloud_cover": {{"lt": threshold}}}}
    
    THRESHOLD SELECTION:
    
    For {data_type}:
    - Vegetation indices (NDVI) → <10% (strict)
    - Land cover classification → <20% (moderate)
    - Visual interpretation → <30% (relaxed)
    - Change detection → <15% (consistent both dates)
    
    For {location}:
    - Tropical regions → Higher threshold (>30%)
      * Persistent cloud cover
      * May need many search iterations
    - Arid regions → Lower threshold (<10%)
      * Typically clear skies
      * Strict quality possible
    - Temperate → Medium threshold (20%)
      * Seasonal variation
      * Winter: more clouds
    
    For {urgency}:
    - High urgency → Relax threshold (accept <50%)
    - Normal → Standard threshold (10-20%)
    - Low urgency → Strict threshold (<5%)
    
    SEARCH STRATEGY:
    1. Start with strict threshold (<10%)
    2. If insufficient results, incrementally increase
    3. Consider temporal window expansion
    4. Use multiple scenes if needed for mosaicking
    
    What cloud cover threshold will you use?
    """
```

### Example 4: Multi-Collection Search

```python
@mcp.prompt()
def multi_collection_search_strategy(
    goal: str,
    priority: str,
    region: str
) -> str:
    """Guide searching across multiple STAC collections."""
    return f"""
    MULTI-COLLECTION SEARCH STRATEGY
    
    Goal: {goal}
    Priority: {priority}
    Region: {region}
    
    WHEN TO USE MULTIPLE COLLECTIONS:
    
    1. TIME SERIES ANALYSIS
       - Combine Landsat (long history) + Sentinel-2 (recent)
       - Increased temporal frequency
       - Gap filling between missions
    
    2. MULTI-RESOLUTION ANALYSIS
       - Sentinel-2 (10-20m) for mapping
       - NAIP (1m) for validation
       - Landsat (30m) for context
    
    3. BAND COMPLEMENTARITY
       - Landsat: Thermal bands
       - Sentinel-2: Red edge bands
       - Combined: Enhanced analysis
    
    SEARCH EXECUTION:
    
    Option A: Sequential Searches
    ```python
    # Search each collection separately
    landsat_items = search_items(
        collections=["landsat-c2l2-sr"],
        bbox=region_bbox,
        datetime=time_range
    )
    
    sentinel_items = search_items(
        collections=["sentinel-2-l2a"],
        bbox=region_bbox,
        datetime=time_range
    )
    
    # Merge and sort results
    ```
    
    Option B: Combined Search
    ```python
    # Search multiple collections together
    all_items = search_items(
        collections=["landsat-c2l2-sr", "sentinel-2-l2a"],
        bbox=region_bbox,
        datetime=time_range,
        sortby=[{"field": "datetime", "direction": "desc"}]
    )
    ```
    
    PRIORITY-BASED SELECTION:
    
    If {priority} == "resolution":
    - Prefer Sentinel-2 (10m) over Landsat (30m)
    - Filter results by gsd (ground sample distance)
    
    If {priority} == "temporal_coverage":
    - Include all available missions
    - Maximize temporal frequency
    
    If {priority} == "spectral_bands":
    - Choose collection with needed bands
    - Check band availability in items
    
    What is your multi-collection search plan?
    """
```

---

## Best Practices

### 1. **Start with Search Strategy, Not Execution**

❌ **Bad**:
```python
@mcp.prompt()
def quick_search(collection: str) -> str:
    return f"Run search_items on {collection}"
```

✅ **Good**:
```python
@mcp.prompt()
def guide_collection_search(
    collection: str,
    intended_use: str
) -> str:
    return f"""
    Before searching {collection} for {intended_use}:
    
    1. Verify collection availability (get_collection)
    2. Check queryable fields (get_queryables)
    3. Plan spatial/temporal filters
    4. Consider quality thresholds
    5. Execute search with small limit first
    
    Start by understanding the collection metadata.
    """
```

### 2. **Encode STAC Specification Knowledge**

Include STAC-specific expertise:

```python
@mcp.prompt()
def stac_datetime_format_guide() -> str:
    return """
    STAC DATETIME FORMAT (RFC 3339)
    
    CRITICAL: Always use ISO 8601 format with UTC timezone
    
    Valid formats:
    ✓ "2023-06-15T00:00:00Z" (UTC timestamp)
    ✓ "2023-06-15T00:00:00.000Z" (with milliseconds)
    ✓ "2023-06-01T00:00:00Z/2023-06-30T23:59:59Z" (range)
    ✓ "../2023-06-30T23:59:59Z" (open start)
    ✓ "2023-06-01T00:00:00Z/.." (open end)
    
    Invalid formats:
    ✗ "2023-06-15" (missing time and timezone)
    ✗ "June 15, 2023" (natural language)
    ✗ "2023-06-15 00:00:00" (missing timezone)
    ✗ "2023-06-15T00:00:00-07:00" (use UTC, not local time)
    
    Always convert to proper format before STAC search.
    """
```

### 3. **Provide Decision Trees**

Help AI make STAC-specific choices:

```python
@mcp.prompt()
def collection_decision_tree(
    use_case: str,
    constraints: dict
) -> str:
    return f"""
    STAC COLLECTION DECISION TREE
    
    Use case: {use_case}
    Constraints: {constraints}
    
    DECISION FLOW:
    
    START
    ├─ Need historical data (>10 years)?
    │  ├─ YES → Landsat Collection 2
    │  └─ NO → Continue
    │
    ├─ Location is USA?
    │  ├─ YES & Need <5m resolution?
    │  │  └─ NAIP
    │  └─ NO → Continue
    │
    ├─ Need recent imagery (<3 months)?
    │  ├─ YES → Sentinel-2 (5-day revisit)
    │  └─ NO → Landsat OK (16-day revisit)
    │
    ├─ Need thermal bands?
    │  ├─ YES → Landsat (has thermal)
    │  └─ NO → Sentinel-2 (more bands, better resolution)
    │
    └─ Default: Sentinel-2 L2A
    
    Apply this decision tree to {use_case}.
    """
```

### 4. **Include Validation Steps**

Guide AI to validate STAC search results:

```python
@mcp.prompt()
def validate_search_results(operation: str) -> str:
    return f"""
    STAC SEARCH VALIDATION
    
    After {operation}:
    
    VALIDATION CHECKLIST:
    [ ] Results returned (count > 0)
    [ ] Items match spatial extent (check bbox)
    [ ] Items match temporal filter (check datetime)
    [ ] Required properties present
    [ ] Assets are accessible
    [ ] Quality filters applied correctly
    [ ] Results sorted as expected
    
    QUALITY CHECKS:
    - Cloud cover within threshold?
    - Resolution meets requirements?
    - Coverage complete for AOI?
    - Processing level appropriate?
    
    Do not proceed until validation passes.
    """
```

### 5. **Make Prompts Composable**

Design prompts to work together in STAC workflows:

```python
@mcp.prompt()
def phase_1_collection_selection(requirements: dict) -> str:
    return "Collection selection methodology..."

@mcp.prompt()
def phase_2_search_planning(collection: str) -> str:
    return "Search planning (assumes collection selected)..."

@mcp.prompt()
def phase_3_result_validation(items: list) -> str:
    return "Result validation (assumes search complete)..."
```

---

## How This Changes STAC MCP Development

### Current State (v1.2.0)

We have **tools** but no **prompts**:
- `search_items` - executes STAC search
- `get_collection` - retrieves collection metadata
- `search_collections` - lists collections

**Result**: AI can execute, but can't reason about STAC methodology

### Next Phase (FastMCP Integration)

Add **prompts** to guide STAC reasoning:

```python
# Prompt to guide search planning
@mcp.prompt()
def plan_stac_search(...)

# Prompt to choose collection
@mcp.prompt()
def choose_collection(...)

# Prompt to construct filters
@mcp.prompt()
def build_search_filters(...)
```

**Result**: AI can plan searches, choose collections, validate results

### End Goal

Prompts become **STAC methodology libraries**:

```python
@mcp.prompt()
def complete_change_detection_workflow(...)

@mcp.prompt()
def multi_temporal_analysis_strategy(...)

@mcp.prompt()
def seasonal_vegetation_monitoring(...)
```

**Result**: AI has geospatial expertise for STAC catalogs

---

## References

- **FastMCP Docs**: [Prompts Guide](https://github.com/jlowin/fastmcp)
- **STAC Specification**: [stacspec.org](https://stacspec.org/)
- **RESOURCES.md**: STAC resource patterns
- **DECORATORS.md**: Decorator reference

---

## Conclusion

**Prompts are how we teach AI agents to reason like geospatial data discovery experts.**

Tools give AI the ability to search STAC catalogs.  
Prompts give AI the knowledge to search them **well**.

By encoding STAC domain methodology in prompts, we transform stac-mcp from a "STAC API wrapper" into a "geospatial data discovery reasoning engine."

**That's the difference between search automation and intelligent data discovery.**

---

**Last Updated**: 2025-10-18  
**Related Docs**: [RESOURCES.md](./RESOURCES.md), [DECORATORS.md](./DECORATORS.md), [GUIDELINES.md](./GUIDELINES.md)
