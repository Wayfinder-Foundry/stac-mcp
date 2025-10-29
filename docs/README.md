# FastMCP Documentation for STAC MCP

This directory contains comprehensive documentation for using FastMCP concepts and patterns in STAC MCP. These guides provide a foundation for understanding how to design and implement MCP decorators, resources, tools, and prompts for geospatial STAC workflows.

## Documentation Files

### [DECORATORS.md](./DECORATORS.md)
Quick reference guide for choosing the right MCP decorator (`@mcp.resource()`, `@mcp.tool()`, `@mcp.prompt()`) in STAC MCP contexts. Includes:
- Decision trees for decorator selection
- STAC-specific examples for each decorator type
- URI scheme recommendations
- Best practices and anti-patterns

### [GUIDELINES.md](./GUIDELINES.md)
Comprehensive guide to FastMCP usage in STAC MCP, covering:
- Current MCP architecture and future FastMCP integration plans
- STAC MCP tool categories and design principles
- Environment configuration and testing strategies
- Migration path from MCP 1.0 to FastMCP

### [PROMPTS.md](./PROMPTS.md)
Deep dive into using prompts for agentic STAC reasoning:
- How prompts enable intelligent geospatial data discovery
- STAC search methodology guidance
- Collection selection and temporal filtering strategies
- Multi-step workflow composition examples
- Best practices for encoding STAC domain knowledge

### [RESOURCES.md](./RESOURCES.md)
Guide to implementing resources for STAC catalog discovery:
- Resource types (catalog, collection, item, reference, workspace)
- STAC-specific resource patterns and examples
- Resource hierarchy and URI schemes
- Caching strategies and error handling
- Integration with tools and prompts

### [CONTEXT.md](./CONTEXT.md)
Technical guide for using the FastMCP `Context` object:
- Where and how to inject Context
- Allowed vs prohibited operations
- Logging patterns for STAC operations
- Progress reporting for long-running tasks
- Migration guide from current architecture

## Purpose

These documents serve multiple purposes:

1. **Developer Guide**: Help developers understand how to structure STAC MCP code following FastMCP patterns
2. **Agent Guidelines**: Provide AI agents with understanding of how to interact with STAC MCP resources, tools, and prompts
3. **Architecture Reference**: Document the design principles and patterns used in STAC MCP
4. **Migration Plan**: Outline the path from current MCP implementation to future FastMCP integration

## Relationship to Issues

This documentation supports:
- **Issue #69**: FastMCP integration - provides architectural foundation
- **Issue #78**: FastMCP doc/architecture implementation - documents patterns and usage

## Adaptation from GDAL MCP

These documents are adapted from the `gdal-mcp` repository's `docs/fastmcp/` directory, tailored specifically for:
- STAC catalog operations (search, discovery, metadata access)
- Geospatial data discovery workflows
- Temporal and spatial filtering patterns
- Collection and item management
- PySTAC CRUDL operations

## Usage

### For Developers

When implementing new STAC MCP features:
1. Start with **DECORATORS.md** to choose the right decorator type
2. Reference **GUIDELINES.md** for overall architecture patterns
3. Use **PROMPTS.md** to add intelligent reasoning capabilities
4. Consult **RESOURCES.md** for discoverable information patterns
5. Follow **CONTEXT.md** for logging and progress tracking

### For AI Agents

When interacting with STAC MCP:
1. Read **PROMPTS.md** to understand how to reason about STAC searches
2. Reference **RESOURCES.md** to discover available catalogs and collections
3. Use **DECORATORS.md** to understand tool capabilities
4. Follow **GUIDELINES.md** for workflow best practices

## Current Status

**Version**: 1.0 (Initial documentation)  
**Last Updated**: 2025-10-18  
**Architecture**: MCP 1.0 (planning for FastMCP 2.0 integration)

## Future Enhancements

As STAC MCP evolves, these documents will be updated to include:
- Actual FastMCP decorator implementations (when issues #69, #78 are complete)
- Real-world prompt examples tested with AI agents
- Resource templates for common STAC patterns
- Advanced context usage patterns
- Integration examples with popular STAC catalogs

## Contributing

When adding new STAC MCP features, please:
1. Update relevant documentation files
2. Add examples demonstrating the pattern
3. Include decision trees or guidelines for when to use the feature
4. Reference STAC specification where applicable

## References

- **FastMCP Documentation**: [gofastmcp.com](https://gofastmcp.com)
- **STAC Specification**: [stacspec.org](https://stacspec.org/)
- **MCP Protocol**: [spec.modelcontextprotocol.io](https://spec.modelcontextprotocol.io/)
- **GDAL MCP FastMCP Docs**: [github.com/Wayfinder-Foundry/gdal-mcp/tree/main/docs/fastmcp](https://github.com/Wayfinder-Foundry/gdal-mcp/tree/main/docs/fastmcp)

---

**Last Updated**: 2025-10-18  
**Maintained By**: Wayfinder Foundry STAC MCP Team
