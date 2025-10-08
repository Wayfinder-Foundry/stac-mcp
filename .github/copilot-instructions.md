# STAC MCP Server Development Guide

STAC MCP Server is a Python-based Model Context Protocol (MCP) server that provides access to STAC (SpatioTemporal Asset Catalog) APIs for geospatial data discovery and access. It enables AI assistants to search for satellite imagery, weather data, and other geospatial datasets.

**Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Working Effectively

### Bootstrap, Build, and Test Repository
Run these commands in order to set up a working development environment:

```bash
# Install dependencies (takes ~15 seconds, NEVER CANCEL, set timeout to 120+ seconds)
# May fail due to network timeouts in sandbox environments
pip install -e ".[dev]"

# Run tests (takes ~1 second, NEVER CANCEL, set timeout to 30+ seconds)
pytest

# Run formatting and linting (takes ~0.2 seconds total)
ruff format stac_mcp/ tests/ examples/
ruff check stac_mcp/ tests/ examples/ --fix
```

- After ANY code edit (even small), re-run `ruff format` and `ruff check --fix` locally before committing to keep diffs clean and surface issues early.

### Run the MCP Server
```bash
# Run as MCP server (stdin/stdout transport, waits for MCP protocol messages)
stac-mcp

# Test server functionality with example script (takes ~1 second)
python examples/example_usage.py
```

### Key Timing Expectations
- **NEVER CANCEL**: Set timeout to 120+ seconds for pip install (may timeout due to network issues)
- **NEVER CANCEL**: Set timeout to 30+ seconds for pytest (runs in ~1 second)
- Ruff formatting: ~0.2 seconds
- Ruff linting: ~0.02 seconds
- Example script: ~0.6 seconds
- MCP server timeout test: 5 seconds (expected timeout with exit code 124)

## Validation

### Always Run These Validation Steps After Making Changes
1. **Format and lint code** (required for CI to pass):
   ```bash
  # Format code (takes ~0.2 seconds)
  ruff format stac_mcp/ tests/ examples/

   # Fix auto-fixable linting issues (takes ~0.02 seconds)
   ruff check stac_mcp/ tests/ examples/ --fix
   
   # Note: Some ruff issues require manual fixes (62 issues currently exist)
   # Focus on critical issues like unused imports and formatting
   ```

2. **Run all tests** (takes ~1 second, NEVER CANCEL, set timeout to 30+ seconds):
   ```bash
   pytest -v
   ```

3. **Test MCP server functionality** (takes ~0.6 seconds):
   ```bash
   python examples/example_usage.py
   ```

4. **Manual MCP server test** (optional, server will wait for input):
   ```bash
   timeout 5s stac-mcp || true  # Should timeout after 5s (exit code 124), indicating server is running
   ```

### End-to-End Validation Scenarios
After making changes, always test these core workflows:

1. **Tool Discovery**: Verify all 4 tools are available
   - search_collections
   - get_collection  
   - search_items
   - get_item

2. **Basic Functionality**: Run example script to ensure MCP protocol works correctly

3. **Network Scenarios**: The server handles network errors gracefully (no real network access needed for testing)

## Project Structure

### Repository Root
```
.
├── .github/                 # GitHub configuration
├── .gitignore              # Python gitignore
├── LICENSE                 # Apache 2.0 license  
├── README.md               # User documentation
├── examples/               # Usage examples
│   ├── example_usage.py    # Demonstrates MCP server usage
│   └── mcp_config_example.json  # MCP client configuration
├── pyproject.toml          # Python project configuration
├── stac_mcp/              # Main package
│   ├── __init__.py        # Package init
│   └── server.py          # MCP server implementation
└── tests/                 # Test suite
    ├── __init__.py        # Test package init
    ├── test_mcp_protocol.py  # MCP protocol tests
    └── test_server.py     # Server functionality tests
```

### Key Files
- **stac_mcp/server.py**: Main MCP server implementation with 4 STAC tools
- **pyproject.toml**: Defines dependencies, build system, and tool configuration
- **examples/example_usage.py**: Demonstrates all server functionality
- **tests/**: Comprehensive test suite with 9 tests covering MCP protocol and server functionality

## Dependencies and Requirements

### Python Requirements
- Python 3.8+ (supports 3.8, 3.9, 3.10, 3.11, 3.12)
- Main dependencies: mcp>=1.0.0, pystac-client>=0.7.0, pystac>=1.8.0, anyio>=3.7.0
- Dev dependencies: pytest, pytest-asyncio, ruff, jsonschema

### Network Requirements
- **Internet access required** for real STAC API calls to:
  - Microsoft Planetary Computer (default): https://planetarycomputer.microsoft.com/api/stac/v1  
  - AWS Earth Search: https://earth-search.aws.element84.com/v1
  - Custom STAC catalogs
- **No network required** for testing - mocked in test suite

## Common Tasks

### Development Workflow
```bash
# 1. Install in development mode
pip install -e ".[dev]"

# 2. Make your changes

# 3. Format and lint
ruff format stac_mcp/ tests/ examples/
ruff check stac_mcp/ tests/ examples/ --fix

# 4. Run tests
pytest -v

# 5. Test functionality  
python examples/example_usage.py
```

### Testing Different STAC Catalogs
The server supports any STAC-compliant catalog. Examples:
- Microsoft Planetary Computer (default)
- AWS Earth Search
- Custom catalogs via catalog_url parameter

### MCP Integration
Configure MCP clients with:
```json
{
  "mcpServers": {
    "stac": {
      "command": "stac-mcp"
    }
  }
}
```

## Troubleshooting

### Common Issues
1. **Import errors**: Run `pip install -e ".[dev]"` to install in development mode
2. **Linting failures**: Run `ruff format` and `ruff check --fix` before committing  
3. **Network timeouts**: Expected in sandbox environments, real network needed for STAC APIs
4. **MCP protocol errors**: Test with `python examples/example_usage.py` first

### Build/Test Failures
- **Ruff formatting**: Must pass for CI - run `ruff format stac_mcp/ tests/ examples/`
- **Ruff linting**: Must pass for CI - run `ruff check --fix stac_mcp/ tests/ examples/` (62 issues currently exist, many auto-fixable)
- **Pytest failures**: All 9 tests must pass - investigate specific test failures
- **Network issues**: pip install may timeout in sandbox environments (expected)

### Known Limitations
- Requires network access for real STAC data (gracefully handles network errors)
- MCP server uses stdio transport (not HTTP)
- No CI/CD workflows currently configured
- **Current linting issues**: 62 ruff issues exist (many auto-fixable, some require manual fixes):
  - Long lines in formatting strings
  - Exception handling patterns
  - Logging format recommendations
  - Import organization
  - Magic numbers in tests

## Architecture Notes

### MCP Server Implementation
- **Transport**: stdio (stdin/stdout) for MCP protocol communication
- **Tools**: 4 async tools implementing STAC operations
- **Client**: Wraps pystac-client for STAC API interactions
- **Error Handling**: Graceful degradation when network unavailable

### STAC Integration
- **Default Catalog**: Microsoft Planetary Computer
- **Supported Operations**: Collection search, item search, metadata retrieval
- **Query Types**: Spatial (bbox), temporal (datetime), attribute-based
- **Asset Access**: Metadata only (no direct asset download)

Always validate your changes with the complete workflow above before committing to ensure compatibility and prevent CI failures.

## Semantic Versioning & Release Management

### Version Management
The project uses semantic versioning (SemVer) with centralized version management:

```bash
# Show current version
python scripts/version.py current

# Increment version based on change type
python scripts/version.py patch    # Bug fixes (0.1.0 -> 0.1.1)
python scripts/version.py minor    # New features (0.1.0 -> 0.2.0)  
python scripts/version.py major    # Breaking changes (0.1.0 -> 1.0.0)

# Set specific version
python scripts/version.py set 1.2.3
```

### Version Guidelines for PRs
Use branch prefixes to control automatic version increments when PRs are merged into main:
- **hotfix/** or **copilot/fix-** branches: Trigger patch version increments (0.1.0 -> 0.1.1)
  - Bug fixes, security patches, documentation updates, minor improvements
- **feature/** branches: Trigger minor version increments (0.1.0 -> 0.2.0)  
  - New features, new tools, non-breaking API changes, performance improvements
- **release/** branches: Trigger major version increments (0.1.0 -> 1.0.0)
  - Breaking changes, major architecture changes, incompatible API changes
- Other prefixes (chore/, docs/, copilot/): No automatic version increment

Examples:
- `hotfix/fix-authentication-bug`
- `copilot/fix-nodata-dtype-handling`
- `feature/add-stac-search-tool`
- `release/v2-breaking-api-changes`

### Container Release Process
1. **Development**: Create PR from appropriately prefixed branch
2. **Merge to Main**: Automatic version increment based on branch prefix
3. **Container Build**: GitHub Actions automatically:
   - Increments version in all files
   - Creates git tag (e.g., v1.2.3)
   - Builds and pushes containers with semantic tags:
     - `ghcr.io/bnjam/stac-mcp:1.2.3` (exact version)
     - `ghcr.io/bnjam/stac-mcp:1.2` (major.minor)
     - `ghcr.io/bnjam/stac-mcp:1` (major)
     - `ghcr.io/bnjam/stac-mcp:latest` (for main branch)

### Version Synchronization
The version management script maintains consistency across:
- `pyproject.toml` (project version)
- `stac_mcp/__init__.py` (__version__)
- `stac_mcp/server.py` (server_version in MCP initialization)

Never manually edit versions in individual files - always use the script to ensure synchronization.