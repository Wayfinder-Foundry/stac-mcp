# ADR 0014: Pluggable Tool Extension Model

Status: Proposed  
Date: 2025-09-26

## Context
The current MCP server exposes a fixed set of tools compiled into the codebase. Emerging use cases:
- Organization- or domain-specific STAC post-processing (cloud cover stats, asset filtering heuristics)
- Experimental tools (e.g., raster previews, derived indices) without bloating the core distribution
- Vendor / integrator contributions that should not fork core

Constraints:
- Must preserve core tool stability (ADR 1003 JSON output stability, ADR 0002 schema consistency)
- Avoid arbitrary code execution risks (security isolation concerns—see ADR 0016 follow-up)
- Maintain discoverability via MCP tool list without breaking clients expecting only the baseline tools

## Decision
Introduce an optional plugin mechanism that loads additional tool implementations at startup from well-defined entrypoints or a configured directory while enforcing a minimal contract.

### Plugin Loading Modes
1. Python Entry Points (preferred):
   - Define a new `stac_mcp.plugins` entry point group.
   - Each entry provides an import path to a `register(plugin_registry)` function.
2. Filesystem Directory (optional fallback):
   - If env var `STAC_MCP_PLUGIN_DIR` is set, import `*.py` modules within it (non-recursive) that expose `register(plugin_registry)`.

### Registration Contract
`register(plugin_registry)` must:
- Call `plugin_registry.add_tool(tool_def)` for each tool, where `tool_def` matches internal tool schema (name, description, input schema, callable).
- Optionally declare capabilities (future use) via `plugin_registry.add_capability(name, metadata)`.

### Isolation & Namespacing
- Plugin tool names must be globally unique; enforced by registry with collision error.
- Recommended naming convention: prefix with organization or purpose (e.g., `acme_cloud_mask`, `exp_preview_raster`).
- Core tools remain unprefixed.

### Error Containment
- Failure to load an individual plugin logs a warning (per ADR 0012) and does not abort server startup unless `STAC_MCP_STRICT_PLUGINS=true`.
- Plugin execution errors surface as standard tool errors without revealing internal stack traces unless DEBUG logging enabled.

### Version & Compatibility
- Plugins can query `stac_mcp.__version__` to assert minimum version; if incompatible, they may raise `IncompatiblePluginError` (caught and logged).

### Security Considerations
- By default, plugins run in-process (trusted environment assumption). ADR 0016 will explore sandboxing / credential scoping for untrusted code.

### Testing Strategy
- Add a test fixture plugin in `tests/plugins/` loaded via directory mode.
- Test: successful registration, collision detection, error isolation.

### Minimal Registry API Sketch (non-binding)
```python
class PluginRegistry:
    def add_tool(self, tool_def): ...  # validates schema & uniqueness
    def add_capability(self, name: str, metadata: dict): ...
```

## Consequences
Pros:
- Decouples experimental & domain-specific tools from core release cadence.
- Encourages community contributions with reduced merge pressure.
- Enables internal proprietary extensions without forking.

Cons / Trade-offs:
- Increases startup complexity & potential failure modes.
- Security surface expands (needs governance for production deployment).
- Harder to guarantee ecosystem-wide consistency in UX & schema quality.

## Alternatives Considered
- Dynamic runtime code upload via MCP messages: rejected (high security risk, protocol scope creep).
- Separate sidecar MCP servers: increases operational overhead vs. simple plugin layering.
- Monkeypatch registration in user code before launch: brittle and undocumented.

## Incremental Rollout Plan
1. Implement registry + entrypoint loading.
2. Add directory loading fallback.
3. Provide example plugin + documentation section.
4. Add tests for collisions and failure isolation.
5. (Future) Evaluate optional sandboxing.

## Open Questions / Follow-ups
- Should plugin metadata (version, author) be exposed via a capability tool?
- Need signing / integrity verification for distributed plugin packages?
- Standardize plugin tool naming guidelines formally?

## Addendums
- None yet.
