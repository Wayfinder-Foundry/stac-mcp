# FastMCP Resources Deep Dive for STAC MCP

**Status**: Technical Guide  
**Last Updated**: 2025-10-18  
**Purpose**: Understand `@mcp.resource()` and its role in agentic STAC catalog reasoning

---

## What Are MCP Resources?

**MCP Resources are read-only data sources that AI agents can access to gather STAC catalog context, collection metadata, and geospatial reference information.**

Think of them as **knowledge repositories**:
- STAC catalog structure and capabilities
- Collection metadata and extents
- Item properties and asset information
- Geospatial reference data (CRS, formats, specifications)

### Key Concept

```
Resources = STAC information the AI can READ
Tools = STAC operations the AI can EXECUTE
Prompts = Guidance on how to THINK about STAC searches
```

---

## The Three Pillars for STAC

| Aspect | Resources | Tools | Prompts |
|--------|-----------|-------|---------|
| **Purpose** | Provide STAC metadata | Execute searches | Guide catalog reasoning |
| **Direction** | AI reads catalogs | AI searches/creates | AI plans workflows |
| **Nature** | Read-only catalog data | Search/CRUD operations | Search methodologies |
| **Example** | Collection list | Search items | Collection selection guide |

---

## Why Resources Are Crucial for STAC Vision

### 1. Catalog Knowledge Access

**Without Resources:**
```
User: "Search for satellite imagery"
AI: → Asks which collection to search
    → Doesn't know what's available
```

**With Resources:**
```python
@mcp.resource("catalog://collections")
def get_collections() -> dict:
    return {
        "collections": [
            {"id": "landsat-c2l2-sr", "title": "Landsat Collection 2"},
            {"id": "sentinel-2-l2a", "title": "Sentinel-2 Level-2A"},
            {"id": "naip", "title": "NAIP Aerial Imagery"}
        ]
    }
```
```
AI: → Reads collection list resource
    → Chooses Sentinel-2 for recent high-res imagery
    → No user question needed
```

### 2. STAC Catalog Awareness

```python
@mcp.resource("catalog://root")
def get_catalog_root() -> dict:
    """Discover catalog capabilities."""
    return {
        "id": "planetary-computer",
        "title": "Microsoft Planetary Computer",
        "conformsTo": [
            "https://api.stacspec.org/v1.0.0/core",
            "https://api.stacspec.org/v1.0.0/item-search"
        ],
        "links": [...]
    }
```

**Result**: AI knows catalog capabilities before searching

### 3. Collection Context

```python
@mcp.resource("collection://{collection_id}/metadata")
def get_collection_metadata(collection_id: str) -> dict:
    """Get detailed collection information."""
    collection = stac_client.get_collection(collection_id)
    return {
        "id": collection.id,
        "title": collection.title,
        "spatial_extent": collection.extent.spatial.bboxes,
        "temporal_extent": collection.extent.temporal.intervals,
        "license": collection.license
    }
```

**Result**: AI understands collection coverage and constraints

---

## Resource Types for STAC

### 1. Catalog Resources (Dynamic)

```python
@mcp.resource("catalog://root")
def get_catalog_root() -> dict:
    """STAC catalog root document."""
    return stac_client.get_root()

@mcp.resource("catalog://conformance")
def get_conformance() -> dict:
    """STAC API conformance classes."""
    return stac_client.get_conformance()

@mcp.resource("catalog://queryables")
def get_queryables() -> dict:
    """Available query parameters."""
    return stac_client.get_queryables()
```

### 2. Collection Resources

```python
@mcp.resource("collection://{collection_id}/metadata")
def get_collection_metadata(collection_id: str) -> dict:
    """Collection metadata and extents."""
    collection = stac_client.get_collection(collection_id)
    return {
        "id": collection.id,
        "description": collection.description,
        "extent": collection.extent,
        "summaries": collection.summaries
    }

@mcp.resource("collection://{collection_id}/queryables")
def get_collection_queryables(collection_id: str) -> dict:
    """Collection-specific queryable fields."""
    return stac_client.get_queryables(collection_id)
```

### 3. Reference Resources (Static)

```python
@mcp.resource("reference://stac-extensions")
def get_stac_extensions() -> dict:
    """STAC extension reference."""
    return {
        "eo": {
            "name": "Electro-Optical",
            "description": "Band and cloud cover information",
            "properties": ["eo:cloud_cover", "eo:bands"]
        },
        "proj": {
            "name": "Projection",
            "description": "CRS and geotransform",
            "properties": ["proj:epsg", "proj:transform"]
        },
        "raster": {
            "name": "Raster",
            "description": "Raster band metadata",
            "properties": ["raster:bands"]
        }
    }

@mcp.resource("reference://datetime-formats")
def get_datetime_formats() -> dict:
    """STAC datetime format reference."""
    return {
        "single": "2023-06-15T00:00:00Z",
        "range": "2023-01-01T00:00:00Z/2023-12-31T23:59:59Z",
        "open_start": "../2023-12-31T23:59:59Z",
        "open_end": "2023-01-01T00:00:00Z/.."
    }
```

### 4. Workspace Resources

```python
@mcp.resource("workspace://recent-searches")
def get_search_history() -> list:
    """Recent STAC search history."""
    return [
        {
            "timestamp": "2025-10-18T10:30:00Z",
            "collections": ["sentinel-2-l2a"],
            "bbox": [-122.5, 37.7, -122.3, 37.9],
            "items_found": 15
        }
    ]

@mcp.resource("workspace://catalogs")
def list_configured_catalogs() -> dict:
    """Available STAC catalogs."""
    return {
        "catalogs": [
            {
                "id": "planetary-computer",
                "url": "https://planetarycomputer.microsoft.com/api/stac/v1",
                "default": True
            },
            {
                "id": "earth-search",
                "url": "https://earth-search.aws.element84.com/v1"
            }
        ]
    }
```

---

## STAC Geospatial Examples

### Example 1: Collection Discovery Service

```python
@mcp.resource("catalog://collections")
def list_collections() -> dict:
    """List all available STAC collections."""
    collections = stac_client.get_collections()
    
    return {
        "collections": [
            {
                "id": col.id,
                "title": col.title,
                "description": col.description,
                "license": col.license,
                "spatial_extent": col.extent.spatial.bboxes[0],
                "temporal_extent": col.extent.temporal.intervals[0],
                "item_count": col.summaries.get("count", "unknown")
            }
            for col in collections
        ],
        "count": len(collections)
    }
```

### Example 2: Collection Capability Matrix

```python
@mcp.resource("reference://collection-capabilities")
def get_collection_capabilities() -> dict:
    """Matrix of collection capabilities and use cases."""
    return {
        "landsat-c2l2-sr": {
            "resolution": "30m",
            "bands": 11,
            "archive": "1972-present",
            "revisit": "16 days",
            "coverage": "global",
            "use_cases": [
                "long-term change detection",
                "historical analysis",
                "thermal analysis"
            ],
            "strengths": ["long archive", "thermal bands", "consistent processing"],
            "limitations": ["coarser resolution", "less frequent revisit"]
        },
        "sentinel-2-l2a": {
            "resolution": "10-20m",
            "bands": 13,
            "archive": "2015-present",
            "revisit": "5 days",
            "coverage": "global land",
            "use_cases": [
                "vegetation monitoring",
                "recent imagery",
                "high-frequency analysis"
            ],
            "strengths": ["better resolution", "red edge bands", "frequent revisit"],
            "limitations": ["shorter archive", "no thermal bands"]
        },
        "naip": {
            "resolution": "0.6-1m",
            "bands": 4,
            "archive": "2010-present",
            "revisit": "annual/biennial",
            "coverage": "USA only",
            "use_cases": [
                "high-resolution mapping",
                "urban analysis",
                "infrastructure monitoring"
            ],
            "strengths": ["very high resolution", "US coverage"],
            "limitations": ["USA only", "infrequent updates"]
        }
    }
```

### Example 3: STAC Specification Glossary

```python
@mcp.resource("reference://stac-glossary")
def get_stac_glossary() -> dict:
    """STAC terminology reference."""
    return {
        "catalog": {
            "definition": "Top-level STAC entity organizing collections",
            "example": "Microsoft Planetary Computer STAC API",
            "spec": "https://github.com/radiantearth/stac-spec/blob/master/catalog-spec/"
        },
        "collection": {
            "definition": "Group of STAC items with common properties",
            "example": "Landsat Collection 2 Level-2",
            "spec": "https://github.com/radiantearth/stac-spec/blob/master/collection-spec/"
        },
        "item": {
            "definition": "Single spatiotemporal asset (e.g., one satellite scene)",
            "example": "Landsat scene LC08_L2SP_...",
            "spec": "https://github.com/radiantearth/stac-spec/blob/master/item-spec/"
        },
        "asset": {
            "definition": "Actual data file referenced by STAC item",
            "example": "GeoTIFF, COG, NetCDF file",
            "types": ["data", "metadata", "thumbnail"]
        },
        "extent": {
            "definition": "Spatial and temporal coverage of collection",
            "spatial": "bbox in EPSG:4326",
            "temporal": "ISO 8601 datetime range"
        },
        "link": {
            "definition": "Relationships between STAC entities",
            "types": ["self", "root", "parent", "child", "item"]
        }
    }
```

### Example 4: Queryable Fields Reference

```python
@mcp.resource("reference://common-queryables")
def get_common_queryables() -> dict:
    """Common STAC queryable properties."""
    return {
        "core": {
            "datetime": {
                "type": "string",
                "format": "date-time",
                "description": "Acquisition time",
                "example": "2023-06-15T00:00:00Z/2023-06-30T23:59:59Z"
            },
            "bbox": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Bounding box [west, south, east, north]",
                "example": [-122.5, 37.7, -122.3, 37.9]
            }
        },
        "eo_extension": {
            "eo:cloud_cover": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
                "description": "Cloud cover percentage",
                "filter_example": {"eo:cloud_cover": {"lt": 20}}
            }
        },
        "proj_extension": {
            "proj:epsg": {
                "type": "integer",
                "description": "EPSG code",
                "example": 32610
            }
        }
    }
```

### Example 5: Collection Extent Summary

```python
@mcp.resource("collection://{collection_id}/extent")
def get_collection_extent(collection_id: str) -> dict:
    """Spatial and temporal extent of collection."""
    collection = stac_client.get_collection(collection_id)
    
    return {
        "collection_id": collection_id,
        "spatial": {
            "bbox": collection.extent.spatial.bboxes,
            "description": "Global coverage" if is_global(collection.extent.spatial.bboxes[0]) else "Regional coverage"
        },
        "temporal": {
            "interval": collection.extent.temporal.intervals,
            "start": collection.extent.temporal.intervals[0][0],
            "end": collection.extent.temporal.intervals[0][1] or "ongoing",
            "duration_years": calculate_duration(collection.extent.temporal.intervals[0])
        }
    }
```

---

## Best Practices for STAC Resources

### 1. Clear URI Schemes

✅ **Good**:
```python
@mcp.resource("catalog://collections")
@mcp.resource("collection://{collection_id}/metadata")
@mcp.resource("reference://stac-extensions")
```

❌ **Bad**:
```python
@mcp.resource("resource://data1")
@mcp.resource("resource://stuff")
```

### 2. Rich STAC Metadata

```python
@mcp.resource(
    uri="collection://{collection_id}/summary",
    name="Collection Summary",
    description="Complete collection metadata and statistics",
    tags={"stac", "collection", "metadata"},
    meta={"version": "1.0", "cache_ttl": 3600}
)
def get_collection_summary(collection_id: str) -> dict:
    return {...}
```

### 3. Cache Expensive STAC Calls

```python
import functools
import time

@functools.lru_cache(maxsize=10)
def _get_collections_cached(cache_key: int):
    """Cache collection list for 5 minutes."""
    return stac_client.get_collections()

@mcp.resource("catalog://collections")
def get_collections() -> dict:
    cache_key = int(time.time() / 300)  # 5 min cache
    collections = _get_collections_cached(cache_key)
    return format_collections(collections)
```

### 4. Handle STAC Errors Gracefully

```python
@mcp.resource("collection://{collection_id}/metadata")
def get_collection_metadata(collection_id: str) -> dict:
    try:
        collection = stac_client.get_collection(collection_id)
        return format_collection(collection)
    except Exception as e:
        return {
            "error": f"Collection {collection_id} not found",
            "available_collections": [
                col.id for col in stac_client.get_collections()
            ],
            "suggestion": "Choose from available collections"
        }
```

### 5. Provide Context, Not Just Data

✅ **Good**:
```python
return {
    "collection": "landsat-c2l2-sr",
    "title": "Landsat Collection 2 Level-2",
    "resolution": "30m",
    "bands": 11,
    "coverage": "global",
    "archive": "1972-present",
    "best_for": "long-term change detection, historical analysis",
    "limitations": "16-day revisit, coarser than Sentinel-2"
}
```

❌ **Bad**:
```python
return {"id": "landsat-c2l2-sr", "bands": 11}
```

---

## Resource Hierarchy for STAC

```
reference://                  # Static STAC reference
├── stac-spec
├── extensions
├── glossary
├── datetime-formats
└── common-queryables

catalog://                    # Catalog-level resources
├── root
├── conformance
├── collections
└── queryables

collection://                 # Collection-specific
└── {collection_id}/
    ├── metadata
    ├── extent
    ├── queryables
    ├── summaries
    └── schema

item://                       # Item-level resources
└── {collection_id}/{item_id}/
    ├── properties
    ├── assets
    ├── geometry
    └── links

workspace://                  # Workspace info
├── catalogs
├── recent-searches
└── configuration

history://                    # Search history
└── searches
```

---

## Advanced STAC Resource Patterns

### Pattern 1: Hierarchical Collection Navigation

```python
@mcp.resource("catalog://collections/tree")
def get_collection_tree() -> dict:
    """Hierarchical view of collections by category."""
    return {
        "optical": {
            "high_resolution": ["sentinel-2-l2a", "naip"],
            "medium_resolution": ["landsat-c2l2-sr"],
            "low_resolution": ["modis"]
        },
        "radar": {
            "c_band": ["sentinel-1-grd"],
            "l_band": ["alos-palsar"]
        },
        "other": {
            "elevation": ["cop-dem-glo-30"],
            "weather": ["era5-land"]
        }
    }
```

### Pattern 2: Collection Comparison Matrix

```python
@mcp.resource("reference://collection-comparison")
def compare_collections() -> dict:
    """Side-by-side collection comparison."""
    return {
        "comparison_table": [
            {
                "attribute": "Resolution",
                "landsat-c2l2-sr": "30m",
                "sentinel-2-l2a": "10-20m",
                "naip": "0.6-1m"
            },
            {
                "attribute": "Revisit Time",
                "landsat-c2l2-sr": "16 days",
                "sentinel-2-l2a": "5 days",
                "naip": "1-2 years"
            },
            {
                "attribute": "Archive Start",
                "landsat-c2l2-sr": "1972",
                "sentinel-2-l2a": "2015",
                "naip": "2010"
            }
        ]
    }
```

### Pattern 3: Search Template Library

```python
@mcp.resource("reference://search-templates")
def get_search_templates() -> dict:
    """Common STAC search patterns."""
    return {
        "recent_imagery": {
            "description": "Find recent satellite imagery",
            "collections": ["sentinel-2-l2a"],
            "datetime": "../" + datetime.utcnow().isoformat() + "Z",
            "limit": 10,
            "sortby": [{"field": "datetime", "direction": "desc"}]
        },
        "cloud_free": {
            "description": "Find cloud-free optical imagery",
            "collections": ["landsat-c2l2-sr", "sentinel-2-l2a"],
            "query": {"eo:cloud_cover": {"lt": 10}},
            "limit": 10
        },
        "time_series": {
            "description": "Build time series dataset",
            "collections": ["landsat-c2l2-sr"],
            "datetime": "2020-01-01T00:00:00Z/2023-12-31T23:59:59Z",
            "limit": 100,
            "sortby": [{"field": "datetime", "direction": "asc"}]
        }
    }
```

---

## Integration with STAC MCP Tools

### Resource + Tool Pattern

```python
# Resource: AI discovers available collections
@mcp.resource("catalog://collections")
def list_collections() -> dict:
    return {"collections": [...]}

# Tool: AI executes search on chosen collection
@mcp.tool()
async def search_items(collections: list[str], ...) -> dict:
    return await stac_client.search(...)
```

### Resource + Prompt + Tool Pattern

```python
# 1. Resource: What collections are available
@mcp.resource("catalog://collections")
def list_collections() -> dict: ...

# 2. Prompt: How to choose collection
@mcp.prompt()
def choose_collection(requirements: dict) -> str: ...

# 3. Tool: Execute search
@mcp.tool()
async def search_items(...) -> dict: ...
```

---

## Action Items for STAC MCP

### Immediate (Current Phase)

1. **Create core STAC resources**:
```python
@mcp.resource("catalog://root")
@mcp.resource("catalog://collections")
@mcp.resource("reference://stac-extensions")
```

2. **Test with MCP clients**:
   - Verify AI can discover resources
   - Validate resource content

### Short-term (Next Phase)

3. **Add collection resources**:
   - Collection metadata
   - Collection extents
   - Queryable fields

4. **Build reference resources**:
   - STAC glossary
   - DateTime format guide
   - Extension documentation

### Long-term (Future)

5. **Complete resource ecosystem**:
   - Search history
   - Workspace catalogs
   - Search templates

6. **Documentation**:
   - Resource discovery guide
   - URI scheme reference
   - Integration examples

---

## Conclusion

**Resources give AI agents the knowledge infrastructure to operate autonomously with STAC catalogs.**

Without resources, AI agents:
- Ask repetitive questions about collections
- Make uninformed collection choices
- Don't understand STAC capabilities
- Operate without catalog context

With resources, AI agents:
- Discover available collections autonomously
- Understand collection capabilities
- Learn STAC specification details
- Make informed search decisions
- Navigate catalog hierarchies

**This transforms stac-mcp from "STAC API executor" to "informed geospatial data discovery assistant."**

---

## References

- **STAC Specification**: [stacspec.org](https://stacspec.org/)
- **FastMCP Docs**: [Resources Guide](https://github.com/jlowin/fastmcp)
- **PROMPTS.md**: How prompts guide STAC reasoning
- **DECORATORS.md**: Decorator reference
- **MCP Spec**: [Resources](https://spec.modelcontextprotocol.io/specification/server/resources/)

---

**Last Updated**: 2025-10-18  
**Related Docs**: [PROMPTS.md](./PROMPTS.md), [DECORATORS.md](./DECORATORS.md), [GUIDELINES.md](./GUIDELINES.md), [CONTEXT.md](./CONTEXT.md)
