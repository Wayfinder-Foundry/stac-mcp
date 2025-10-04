# ADR 0016: Security & Credential Isolation Strategy

Status: Proposed  
Date: 2025-09-26

## Context
The server may interact with multiple STAC catalogs, some of which require API keys, SAS tokens (e.g., Planetary Computer signing, ADR 0005), or future OAuth tokens. Upcoming federation (ADR 0013) and plugin extensibility (ADR 0014) increase the risk of:
- Credential leakage across unrelated catalogs or plugins
- Accidental logging of secrets (observability ADR 0012)
- Shared mutable state leading to privilege escalation

A clear isolation and handling strategy is required before introducing more dynamic or third-party code paths.

## Decision
Adopt a layered credential management approach emphasizing least privilege, redaction, and scoping.

### Credential Sources
- Environment variables (e.g., `STAC_MCP_API_KEY_<ALIAS>`)
- Future: explicit configuration file (not in scope here)
- External secret managers (deferred; may be loaded into environment prior to launch)

### Naming & Discovery
- For each configured catalog alias (ADR 0013), a credential may be supplied via `STAC_MCP_API_KEY_<UPPER_ALIAS>`.
- Planetary Computer optional signing key remains as previously defined (ADR 0005); unified pattern may be adopted in a follow-up.

### Storage & Lifecycle
- Credentials loaded once at startup into an in-memory immutable mapping: `{ alias: CredentialInfo(token: str, type: 'api_key'|'sas'|...) }`.
- Mapping not exposed to plugins directly; plugins must request an ephemeral credential via registry API: `get_credential(alias)` which returns a read-only wrapper object.
- No credential persistence to disk; no caching beyond process memory.

### Usage Scoping
- Network client creation for a catalog receives only that catalog's credential (dependency-injected parameter), avoiding global ambient credentials.
- Federation layer spawns per-catalog client instances with their scoped token.

### Redaction & Logging
- Observability layer (ADR 0012) applies redaction filter:
  - Any value matching loaded credential strings replaced with `***`.
  - Environment variable names with `API_KEY` truncated after 4 visible chars (`ABCD****`).
- Plugin attempts to log a credential string (exact match) are automatically redacted.

### Plugin Boundary Controls (ADR 0014 Alignment)
- Plugin registry exposes only `get_credential(alias)`; if alias not whitelisted for plugins (default: none), raises `PluginAccessDenied`.
- Administrators enable plugin access via env var: `STAC_MCP_PLUGIN_CREDENTIAL_ACCESS=<alias1,alias2>`.

### Future OAuth / Refresh Tokens (Out of Scope)
- Placeholder interface includes optional `refresh()` method; not implemented until needed.

### Error Handling
- Missing credential for a required catalog results in a clear validation error at startup (`CredentialConfigurationError`).
- Runtime missing credential (should not happen) raises internal error and logs security warning.

### Testing Strategy
- Unit tests verifying: redaction, per-alias isolation, plugin denial by default, allowed access when configured.
- Negative test ensuring secrets never appear in captured logs.

## Consequences
Pros:
- Minimizes accidental credential leakage and cross-catalog misuse.
- Establishes baseline controls before more dynamic features roll out.
- Provides extensibility path (OAuth) without premature complexity.

Cons / Trade-offs:
- Slightly more boilerplate for client creation (explicit injection).
- Admin must manage more env vars for multiple catalogs.

## Alternatives Considered
- Global ambient credential used across catalogs: rejected (violates least privilege).
- Plugins full access to env: rejected (security risk, hard to audit).
- Encrypting credentials at rest in memory: unnecessary overhead given process boundary trust assumptions.

## Open Questions / Follow-ups
- Need for auditing tool to list which plugins accessed which credentials? (Could integrate with observability events.)
- Consider secret rotation hooks if long-running processes become common.
- Unify Planetary Computer signing key naming with alias-based scheme?

## Addendums
- None yet.
