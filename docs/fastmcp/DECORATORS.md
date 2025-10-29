# FastMCP Decorators Reference for STAC MCP

**Purpose**: Quick reference for choosing the right decorator in STAC MCP  
**Last Updated**: 2025-10-18

---

## The Three Decorators

```python
@mcp.resource()   # Information to READ (catalogs, collections, items)
@mcp.tool()       # Actions to EXECUTE (search, create, update, delete)
@mcp.prompt()     # Guidance for THINKING (STAC workflows, catalog selection)
```

---

## Quick Decision Guide

### **Ask These Questions:**

1. **"Does this change anything in the STAC catalog or filesystem?"**
   - YES → `@mcp.tool()`
   - NO → Continue to question 2

2. **"Is this information or guidance?"**
   - Information (catalog data, collection metadata, item properties) → `@mcp.resource()`
   - Guidance (search strategy, temporal filtering methodology) → `@mcp.prompt()`

---

## Detailed Comparison

| Aspect | Resource | Tool | Prompt |
|--------|----------|------|--------|
| **Purpose** | Provide STAC information | Execute STAC operations | Guide catalog reasoning |
| **AI Action** | Reads catalogs/collections | Executes searches/CRUD | Reasons about STAC workflows |
| **Side Effects** | None (read-only) | Yes (creates/modifies/deletes) | None |
| **Return Type** | STAC data (dict/str/bytes) | Operation result | Message(s) |
| **User Approval** | Not needed | Required | Not needed |
| **When Called** | During catalog discovery | During data operations | Before planning search |
| **Caching** | Can cache | Don't cache | Can cache |

---

## @mcp.resource() - Information to READ

### **Use When:**
- ✅ Reading STAC catalog metadata without modification
- ✅ Discovering available collections and items
- ✅ Getting collection or item properties
- ✅ Providing STAC specification reference
- ✅ Checking catalog conformance or capabilities
- ✅ Computing read-only spatial/temporal analysis

### **Don't Use When:**
- ❌ Creating or modifying STAC catalogs/collections/items
- ❌ Changing catalog configuration
- ❌ Executing STAC API searches (use tool instead)
- ❌ Triggering side effects

### **Signature:**
```python
@mcp.resource(uri: str)
def function_name([parameters], [ctx: Context]) -> dict | str | bytes:
    """Docstring describing the STAC resource."""
    return stac_data
```

### **URI Patterns:**
```python
# Static STAC reference
@mcp.resource("reference://stac-spec-version")

# Dynamic with catalog parameters
@mcp.resource("catalog://{catalog_url}/conformance")

# Collection metadata
@mcp.resource("collection://{collection_id}/metadata")

# Item properties
@mcp.resource("item://{collection_id}/{item_id}/properties")
```

### **Examples:**

#### STAC Catalog Discovery
```python
@mcp.resource("catalog://root")
def get_catalog_root() -> dict:
    """Fetch STAC catalog root document."""
    return {
        "id": "planetary-computer",
        "title": "Microsoft Planetary Computer STAC API",
        "description": "STAC API for Planetary Computer",
        "links": [...],
        "conformsTo": [...]
    }
```

#### Collection List
```python
@mcp.resource("catalog://collections")
def list_collections() -> dict:
    """List all available STAC collections."""
    return {
        "collections": [
            {"id": "landsat-c2l2-sr", "title": "Landsat Collection 2"},
            {"id": "sentinel-2-l2a", "title": "Sentinel-2 Level-2A"}
        ],
        "count": 2
    }
```

#### STAC Specification Reference
```python
@mcp.resource("reference://stac-extensions")
def get_stac_extensions() -> dict:
    """Reference guide to STAC extensions."""
    return {
        "eo": "Electro-Optical extension for band information",
        "proj": "Projection extension for CRS and transform",
        "raster": "Raster band metadata extension",
        "datacube": "Data cube dimension metadata"
    }
```

#### Queryable Fields
```python
@mcp.resource("catalog://{catalog_url}/queryables")
def get_queryables(catalog_url: str) -> dict:
    """Get queryable fields for STAC search."""
    return {
        "properties": {
            "datetime": {"type": "string", "format": "date-time"},
            "eo:cloud_cover": {"type": "number", "minimum": 0, "maximum": 100}
        }
    }
```

---

## @mcp.tool() - Actions to EXECUTE

### **Use When:**
- ✅ Searching STAC catalogs for items
- ✅ Creating STAC catalogs/collections/items (CRUDL operations)
- ✅ Updating or deleting STAC resources
- ✅ Executing operations with API side effects
- ✅ Making persistent changes to catalogs
- ✅ Estimating data sizes or downloading assets

### **Don't Use When:**
- ❌ Just reading catalog metadata
- ❌ Providing STAC specification reference
- ❌ Computing read-only statistics without persistence

### **Signature:**
```python
@mcp.tool()
async def function_name(
    param1: type,
    param2: type = default,
    ctx: Context | None = None
) -> ResultType:
    """Docstring with USE WHEN, REQUIRES, OUTPUT, SIDE EFFECTS."""
    # Perform STAC operation
    return result
```

### **Examples:**

#### STAC Item Search
```python
@mcp.tool()
async def search_items(
    collections: list[str],
    bbox: list[float] | None = None,
    datetime: str | None = None,
    limit: int = 10
) -> dict:
    """
    Search STAC catalog for items matching criteria.
    
    USE WHEN: Need to find geospatial datasets by location/time
    REQUIRES: Valid STAC catalog connection
    OUTPUT: List of matching STAC items
    SIDE EFFECTS: None (read-only search)
    """
    results = await stac_client.search(
        collections=collections,
        bbox=bbox,
        datetime=datetime,
        limit=limit
    )
    return {"type": "item_list", "items": list(results)}
```

#### Create STAC Collection
```python
@mcp.tool()
async def pystac_create_collection(
    collection_id: str,
    title: str,
    description: str,
    spatial_extent: dict,
    temporal_extent: dict,
    output_path: str
) -> dict:
    """
    Create a new STAC Collection.
    
    USE WHEN: Need to create a new collection on disk or remote API
    REQUIRES: Valid spatial and temporal extents
    OUTPUT: Created STAC Collection
    SIDE EFFECTS: Creates collection file or API resource
    """
    collection = pystac.Collection(
        id=collection_id,
        title=title,
        description=description,
        extent=pystac.Extent(spatial_extent, temporal_extent)
    )
    collection.save_object(output_path)
    return {"id": collection_id, "path": output_path}
```

#### Data Size Estimation
```python
@mcp.tool()
async def estimate_data_size(
    collections: list[str],
    bbox: list[float] | None = None,
    datetime: str | None = None,
    limit: int = 50
) -> dict:
    """
    Estimate data size for STAC items using lazy loading.
    
    USE WHEN: Need to know dataset size before downloading
    REQUIRES: Items with accessible assets
    OUTPUT: Size estimates and metadata
    SIDE EFFECTS: None (lazy loading, no download)
    """
    items = await search_items(collections, bbox, datetime, limit)
    size_estimate = calculate_lazy_size(items)
    return {"estimated_bytes": size_estimate, "item_count": len(items)}
```

---

## @mcp.prompt() - Guidance for THINKING

### **Use When:**
- ✅ Guiding AI in STAC search strategy
- ✅ Providing temporal filtering methodology
- ✅ Encoding STAC specification knowledge
- ✅ Establishing catalog selection best practices
- ✅ Helping AI choose search parameters
- ✅ Structuring multi-step STAC workflows

### **Don't Use When:**
- ❌ Executing STAC searches
- ❌ Reading catalog metadata
- ❌ Providing static STAC facts (use resource instead)

### **Signature:**
```python
@mcp.prompt()
def function_name(
    param1: type,
    param2: type = default
) -> str | PromptMessage | list[PromptMessage]:
    """Docstring describing the prompt's purpose."""
    return message_content
```

### **Examples:**

#### STAC Search Strategy
```python
@mcp.prompt()
def stac_search_methodology(
    data_type: str,
    region: str,
    time_period: str
) -> str:
    """Guide AI through STAC search planning."""
    return f"""
    STAC SEARCH STRATEGY: {data_type} in {region}
    
    Time period: {time_period}
    
    Recommended workflow:
    1. Identify appropriate STAC collections for {data_type}
    2. Define spatial extent (bbox) for {region}
    3. Parse temporal range {time_period} to STAC datetime format
    4. Consider cloud cover filters for optical data
    5. Start with small limit (10) to validate query
    6. Expand search if needed
    
    What collections and parameters will you use?
    """
```

#### Temporal Filter Selection
```python
@mcp.prompt()
def choose_temporal_filter(
    analysis_type: str,
    season: str | None = None
) -> str:
    """Help AI choose appropriate temporal filtering."""
    return f"""
    TEMPORAL FILTERING FOR STAC SEARCH
    
    Analysis type: {analysis_type}
    Season preference: {season or "any"}
    
    Decision guide:
    - Change detection → Use specific dates with before/after
    - Seasonal analysis → Filter by month/season
    - Time series → Use open-ended range with sorting
    - Single scene → Use precise datetime
    
    STAC datetime formats:
    - Single instant: "2023-06-15T00:00:00Z"
    - Range: "2023-01-01T00:00:00Z/2023-12-31T23:59:59Z"
    - Open start: "../2023-12-31T23:59:59Z"
    - Open end: "2023-01-01T00:00:00Z/.."
    
    Recommend a datetime filter and explain your reasoning.
    """
```

#### Collection Selection Guide
```python
@mcp.prompt()
def choose_stac_collection(
    data_needs: str,
    resolution_requirement: str,
    coverage_area: str
) -> str:
    """Guide AI in selecting appropriate STAC collection."""
    return f"""
    STAC COLLECTION SELECTION
    
    Data needs: {data_needs}
    Resolution: {resolution_requirement}
    Coverage: {coverage_area}
    
    Available collections:
    
    Landsat Collection 2 (landsat-c2l2-sr):
    - Resolution: 30m
    - Coverage: Global (16-day revisit)
    - Best for: Long-term change detection, large area mapping
    
    Sentinel-2 Level-2A (sentinel-2-l2a):
    - Resolution: 10-20m
    - Coverage: Global (5-day revisit)
    - Best for: Recent imagery, vegetation monitoring
    
    NAIP (naip):
    - Resolution: 0.6-1m
    - Coverage: USA only (annual/biennial)
    - Best for: High-resolution US mapping
    
    Consider:
    - Resolution matches requirement?
    - Coverage includes area of interest?
    - Temporal availability meets needs?
    
    Which collection(s) do you recommend and why?
    """
```

---

## Common Patterns for STAC MCP

### **Pattern 1: Catalog Info as Both Resource and Tool**

```python
# Resource: AI can query catalog metadata freely
@mcp.resource("catalog://{catalog_url}/conformance")
def get_conformance(catalog_url: str) -> dict:
    return fetch_conformance(catalog_url)

# Tool: User explicitly requests conformance check
@mcp.tool()
async def get_conformance_tool(catalog_url: str) -> dict:
    """Verify STAC API conformance classes."""
    return fetch_conformance(catalog_url)
```

### **Pattern 2: Resource + Prompt + Tool**

Complete STAC workflow guidance:

```python
# 1. Resource: What collections are available
@mcp.resource("catalog://collections")
def list_collections() -> dict: ...

# 2. Prompt: How to choose collection and parameters
@mcp.prompt()
def plan_collection_search(requirements: dict) -> str: ...

# 3. Tool: Execute the STAC search
@mcp.tool()
async def search_items(collections: list[str], **params) -> dict: ...
```

### **Pattern 3: Parametric STAC Resources**

Resources that adapt based on STAC parameters:

```python
@mcp.resource("collection://{collection_id}/schema")
def get_collection_schema(collection_id: str) -> dict:
    """Different schema per collection."""
    return lookup_collection_schema(collection_id)
```

---

## Decision Examples for STAC

### **Scenario 1: "Get collection metadata"**

**Question**: Get details about landsat-c2l2-sr collection

**Answer**: Resource
```python
@mcp.resource("collection://{collection_id}/metadata")
def get_collection_metadata(collection_id: str) -> dict:
    # Read-only, no changes
```

**Why**: Just reading information, no side effects

---

### **Scenario 2: "Search for satellite imagery"**

**Question**: Find Landsat scenes over California in June 2023

**Answer**: Tool
```python
@mcp.tool()
async def search_items(collections: list[str], bbox: list[float], datetime: str) -> dict:
    # Executes STAC search
```

**Why**: Executes operation (even though read-only, it's an action)

---

### **Scenario 3: "How to filter by cloud cover"**

**Question**: Guide AI in using cloud cover filters

**Answer**: Prompt
```python
@mcp.prompt()
def cloud_cover_filter_guide(data_type: str) -> str:
    # Methodology guidance
```

**Why**: Provides reasoning guidance, not data or action

---

### **Scenario 4: "List available catalogs"**

**Question**: What STAC catalogs are configured

**Answer**: Resource
```python
@mcp.resource("catalog://available")
def list_catalogs() -> dict:
    # Read-only discovery
```

**Why**: Just reading configuration, no changes

---

## URI Scheme Recommendations for STAC

Use descriptive, hierarchical URI schemes:

```
reference://           # Static STAC reference
├── spec-versions/
├── extensions/
└── glossary/

catalog://            # STAC catalog access
├── root
├── conformance
├── collections
└── queryables

collection://         # Collection resources
└── {collection_id}/
    ├── metadata
    ├── schema
    └── extent

item://              # Item resources
└── {collection_id}/{item_id}/
    ├── properties
    ├── assets
    └── geometry

workspace://         # Workspace info
├── catalogs
└── configuration

history://           # Search history
└── recent-searches
```

---

## Best Practices for STAC MCP

### **For Resources:**

1. **Use clear URI schemes** - `catalog://`, `collection://`, `item://`
2. **Keep responses focused** - One STAC resource per function
3. **Cache expensive catalog calls** - Use `@lru_cache` for static catalogs
4. **Provide rich metadata** - Include STAC specification links
5. **Handle errors gracefully** - Return error objects for missing collections

### **For Tools:**

1. **Document side effects** - Note if creating/modifying STAC resources
2. **Use descriptive names** - Action verbs (search, create, update, delete)
3. **Validate STAC inputs** - Check bbox format, datetime strings, collection IDs
4. **Return operation metadata** - Include search parameters used
5. **Support output formats** - Provide both text and JSON modes

### **For Prompts:**

1. **Focus on methodology** - "How to search", not "what to search"
2. **Include decision trees** - Help AI choose collections and parameters
3. **Reference STAC spec** - Link to specification documentation
4. **Be domain-specific** - Encode geospatial search expertise
5. **End with questions** - Prompt AI to plan before executing

---

## Summary

**Think of it as:**

- **Resources** = 📚 STAC Catalog Library (collections/items to browse)
- **Tools** = 🔍 STAC Search Engine (operations to execute)
- **Prompts** = 📖 Geospatial Search Guide (how to think about STAC)

**The golden rule:**

> If it changes STAC resources → Tool  
> If it provides STAC information → Resource  
> If it guides STAC reasoning → Prompt

---

**Last Updated**: 2025-10-18  
**Related Docs**: [PROMPTS.md](./PROMPTS.md), [RESOURCES.md](./RESOURCES.md), [GUIDELINES.md](./GUIDELINES.md)
