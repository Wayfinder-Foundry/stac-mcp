# ADR 0018: Session Context Management and Propagation

Status: Proposed  
Date: 2025-10-18

## Context

As stac-mcp expands to support more advanced agent- and copilot-driven interactions, robust session context management has become critical. Current implementation provides correlation IDs (ADR 0012 observability) and caching with optional workspace scoping (ADR 0011), but lacks a unified session context abstraction that could enable:

- **Multi-step workflows**: Chained agent actions requiring state continuity (e.g., search → filter → analyze → export)
- **Personalization & authorization**: User-specific data filtering, permissions, quota tracking
- **Enhanced observability**: Request tracing across distributed calls, user journey analytics
- **Performance optimizations**: Session-scoped connection pooling, query result caching with user context
- **Compliance & auditing**: Per-user activity logs, data access auditing, PII handling

### Current State Analysis

**Existing session-related features:**
1. **Correlation IDs** (observability.py): Per-request UUID tracking for log correlation
2. **Workspace scoping** (ADR 0011): Optional cache key derivation from working directory
3. **Credential isolation** (ADR 0016): Per-catalog credential management, no user/session binding
4. **Stateless MCP protocol**: stdio transport, no inherent session persistence

**Gaps:**
- No unified session abstraction or lifecycle management
- No user identity tracking or authentication integration
- No session state persistence across MCP requests
- No cross-tool session context propagation beyond correlation IDs
- Limited support for long-running agent workflows
- No quota or rate limiting per session/user

### Architectural Considerations

**MCP Protocol Constraints:**
- stdio transport: stateless by design, no built-in session management
- Each tool invocation is independent
- No HTTP headers/cookies for session propagation
- Server process lifetime may span multiple logical user sessions (in hosted scenarios)

**FastMCP Migration Consideration:**
The issue mentions "Consider leveraging or migrating to FastMCP." FastMCP is a framework that simplifies MCP server development with enhanced routing, dependency injection, and middleware capabilities. While FastMCP could provide infrastructure benefits, this ADR focuses on session context design principles applicable to both current implementation and potential FastMCP migration. A separate ADR should evaluate FastMCP migration costs/benefits.

## Decision

Implement a **lightweight, layered session context framework** that extends existing observability and caching infrastructure while remaining compatible with MCP's stateless nature.

### 1. Session Context Model

Define a minimal session context structure:

```python
@dataclass
class SessionContext:
    """Session context for request correlation and state management."""
    
    # Core identifiers (required)
    session_id: str          # Unique session identifier (UUID)
    correlation_id: str      # Per-request correlation (from ADR 0012)
    
    # User/agent identity (optional)
    user_id: str | None = None           # User identifier (if authenticated)
    agent_id: str | None = None          # AI agent/copilot identifier
    workspace_path: str | None = None    # Working directory (from ADR 0011)
    
    # Lifecycle metadata
    created_at: datetime      # Session creation timestamp
    last_active: datetime     # Last request timestamp
    ttl_seconds: int = 3600   # Time-to-live (default 1 hour)
    
    # Security & authorization
    auth_token_hash: str | None = None   # Hashed auth token (never log plaintext)
    permissions: set[str] = field(default_factory=set)  # Permission strings
    
    # Custom attributes (extensible)
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Design principles:**
- Immutable after creation (except `last_active` updates)
- No PII in standard fields (user_id is opaque identifier)
- Extensible via `metadata` dict for future features
- Compatible with existing correlation ID system

### 2. Session Lifecycle Management

**Creation:**
- Generate session_id at first tool invocation or explicit session initialization
- For stdio MCP: derive from environment variable `STAC_MCP_SESSION_ID` if provided, otherwise generate new UUID
- For future HTTP transport: derive from header, cookie, or JWT
- Initialize with current timestamp, default TTL

**Propagation:**
- **Within process**: Thread-local storage or async context variables (contextvars)
- **Across MCP requests**: Client-provided session_id via environment variable or future protocol extension
- **Tool invocations**: Inject SessionContext into tool handlers via dependency injection pattern

**Updates:**
- Refresh `last_active` on each request
- Validate TTL; reject expired sessions with clear error

**Invalidation:**
- Explicit session termination (future capability)
- Automatic expiry after TTL
- Server restart (in-memory sessions cleared)

**Persistence Strategy:**
- **Phase 1 (current)**: In-memory only, suitable for single-process stdio server
- **Phase 2 (future)**: Optional file-based persistence when `STAC_MCP_SESSION_STORE_DIR` set
- **Phase 3 (future)**: External session store (Redis, database) for multi-process/distributed deployments

### 3. Context Propagation Mechanisms

**A. Async Context Variables (Python 3.7+)**

Use `contextvars.ContextVar` for thread-safe, async-safe propagation:

```python
from contextvars import ContextVar

_session_context: ContextVar[SessionContext | None] = ContextVar(
    "stac_mcp_session_context",
    default=None
)

def get_current_session() -> SessionContext | None:
    """Retrieve current session context."""
    return _session_context.get()

def set_current_session(ctx: SessionContext) -> None:
    """Set session context for current execution."""
    _session_context.set(ctx)
```

**B. Tool Handler Integration**

Update tool execution infrastructure to inject session context:

```python
# In stac_mcp/tools/execution.py
async def execute_tool(tool_name: str, arguments: dict):
    # 1. Retrieve or create session context
    session = get_or_create_session(arguments)
    set_current_session(session)
    
    # 2. Update correlation_id in observability
    correlation_id = session.correlation_id
    
    # 3. Execute tool with context available
    result = await _execute_tool_impl(tool_name, arguments)
    
    # 4. Optionally return session info in response meta
    if include_session_meta():
        result["meta"]["session_id"] = session.session_id
        result["meta"]["correlation_id"] = correlation_id
    
    return result
```

**C. Client-Side Session ID Provision**

For clients managing persistent sessions:
- Set environment variable: `STAC_MCP_SESSION_ID=<uuid>`
- Server reads on startup/request and reuses session
- Enables continuity across multiple tool invocations

### 4. Integration with Existing Features

**Observability (ADR 0012):**
- Session context extends correlation ID concept
- Correlation ID becomes per-request within a session
- Structured logs include both `session_id` and `correlation_id`
- Metrics track session duration, tool invocations per session

**Caching (ADR 0011):**
- Enhance cache key composition: `(tool, catalog_url, args, session_id)`
- Session-scoped cache isolation prevents cross-session data leakage
- Workspace path in session context aligns with existing workspace scoping

**Security & Credentials (ADR 0016):**
- Session context carries user_id for per-user credential selection
- Permissions set enables authorization checks before tool execution
- Auth token hash enables session validation without storing plaintext
- Redaction rules apply to session_id logging (show first 8 chars: `abc12345...`)

**Federation (ADR 0013):**
- Session context propagated to federated catalog requests
- Per-catalog credentials selected based on session user_id
- Session quotas enforced across federated searches

### 5. Security and Privacy

**PII Minimization:**
- No direct PII storage in session context (use opaque identifiers)
- User details retrieved from external identity service when needed
- Metadata dict monitored for accidental PII inclusion

**Authentication Integration (Future):**
- Session context designed to support OAuth, API keys, JWT
- Initial phase: unauthenticated sessions with optional user_id
- Future: validate auth_token_hash against token store

**Logging & Redaction:**
- Never log full session_id (truncate to first 8 characters)
- Never log auth_token_hash except in security audit logs
- Permissions list logged only in debug mode
- Custom metadata scrubbed for credential patterns

**Session Hijacking Prevention:**
- TTL enforcement prevents indefinite session reuse
- Future: IP binding, request signature validation
- Session invalidation on security events

### 6. Configuration

Environment variables (backward compatible):

```bash
# Session management
STAC_MCP_SESSION_ID=<uuid>                    # Client-provided session ID
STAC_MCP_SESSION_TTL_SECONDS=3600             # Default 1 hour
STAC_MCP_SESSION_STORE_DIR=<path>             # Optional persistence (future)
STAC_MCP_SESSION_INCLUDE_META=true            # Return session info in responses

# User/agent identity (optional)
STAC_MCP_USER_ID=<opaque-id>                  # User identifier
STAC_MCP_AGENT_ID=<agent-name>                # AI agent identifier

# Existing (enhanced with session awareness)
STAC_MCP_CACHE_DIR=<path>                     # Session-scoped cache
```

### 7. Performance & Resource Bounds

**Memory:**
- In-memory session store: bounded LRU cache (max 1000 sessions by default)
- Per-session metadata size limit: 10KB
- Automatic cleanup of expired sessions

**Latency:**
- Session lookup: O(1) hash table
- Context propagation overhead: negligible (contextvars)
- Cache key composition: +1-2ms for session_id hashing

**Scalability:**
- Single-process stdio: thousands of sessions
- Future multi-process: external store required (Redis)

### 8. Migration & Implementation Strategy

**Phase 1: Foundation (Minimal Viable Session)**
- Implement SessionContext dataclass
- Add ContextVar-based propagation
- Integrate with existing correlation_id system
- Update tool execution to create/retrieve sessions
- Environment variable configuration
- Unit tests for session lifecycle

**Phase 2: Feature Integration**
- Enhance caching with session-scoped keys
- Add session metrics and logging
- Implement TTL validation and expiry
- Security redaction rules
- Integration tests

**Phase 3: Advanced Capabilities**
- Persistent session store (file-based)
- User authentication integration
- Permission-based authorization
- Session management tools (list, invalidate)
- External session store support

**Phase 4: Future Enhancements**
- FastMCP integration (if migration occurs)
- Distributed session coordination
- Advanced security features (IP binding, signatures)
- Session analytics and telemetry

### 9. Testing Strategy

**Unit tests:**
- Session creation, retrieval, expiry
- Context variable propagation in async code
- Session ID generation and validation
- TTL enforcement
- Metadata serialization/deserialization

**Integration tests:**
- Multi-tool workflow with shared session
- Session-scoped cache isolation
- Correlation ID continuity within session
- Credential selection based on session user_id

**Negative tests:**
- Expired session rejection
- Invalid session_id handling
- Session hijacking attempts (future)
- PII leakage in logs

## Consequences

**Pros:**
- Enables advanced agent workflows with state continuity
- Provides foundation for user authentication and authorization
- Improves observability with session-level tracing
- Enhances caching effectiveness with session scoping
- Maintains backward compatibility (optional adoption)
- Positions for future distributed deployments

**Cons / Trade-offs:**
- Added complexity in request handling pipeline
- Memory overhead for session storage (bounded)
- Potential for session-related bugs if not carefully tested
- Learning curve for developers understanding session vs correlation IDs

**Compatibility:**
- Backward compatible: existing code works without session context
- Graceful degradation: sessions optional, correlation IDs remain functional
- Protocol agnostic: works with stdio, future HTTP transport

## Alternatives Considered

### Alternative 1: Stateless Tokens Only
**Approach**: Encode all session state in JWT tokens passed via environment variables.

**Rejected because:**
- Limited token size (environment variable limits)
- Performance overhead of token validation per request
- Difficult to manage session expiry and revocation
- No in-memory caching of session state

### Alternative 2: External Session Store from Day One
**Approach**: Require Redis or database for all session management.

**Rejected because:**
- Over-engineering for current single-process stdio server
- Adds operational complexity and dependencies
- Unnecessary for initial use cases
- Can be added later (Phase 3+)

### Alternative 3: MCP Protocol Extension
**Approach**: Propose session management extension to MCP protocol specification.

**Deferred because:**
- Long standardization timeline
- Uncertainty about adoption
- Can implement proprietary approach now, standardize later
- Environment variable approach provides immediate solution

### Alternative 4: Rely Solely on Correlation IDs
**Approach**: Extend correlation ID concept instead of new session abstraction.

**Rejected because:**
- Correlation IDs are per-request, not per-session
- Overloading correlation IDs conflates concerns
- Limits future session-specific features
- Less clear semantics for multi-step workflows

## Open Questions / Follow-ups

1. **FastMCP Migration**: Should we create a separate ADR to evaluate FastMCP adoption and its session management capabilities?
   
2. **Session Management Tools**: Should we expose MCP tools for session introspection (list sessions, get session info, invalidate session)?

3. **Multi-tenant Hosting**: If stac-mcp becomes a hosted service, how should session isolation enforce tenant boundaries?

4. **Session Events**: Should we emit session lifecycle events (created, expired, invalidated) for external monitoring?

5. **Backward Compatibility Timeline**: How long should we maintain support for sessionless operation?

6. **Cross-Server Session Sharing**: If multiple stac-mcp processes run, should sessions be shareable? (Requires external store)

## Implementation Checklist

**Phase 1 (Foundation):**
- [ ] Create `stac_mcp/session.py` module with SessionContext dataclass
- [ ] Implement ContextVar-based session propagation
- [ ] Update `stac_mcp/tools/execution.py` to create/retrieve sessions
- [ ] Integrate session_id into observability logging
- [ ] Add environment variable configuration
- [ ] Write unit tests for session lifecycle
- [ ] Update documentation

**Phase 2 (Integration):**
- [ ] Enhance cache key composition with session_id
- [ ] Add session metrics (duration, tool count)
- [ ] Implement TTL validation and cleanup
- [ ] Add session-aware redaction rules
- [ ] Write integration tests
- [ ] Update ADR 0011 (caching) for session integration
- [ ] Update ADR 0012 (observability) for session metrics

**Phase 3 (Persistence):**
- [ ] Implement file-based session store
- [ ] Add session serialization/deserialization
- [ ] Implement session recovery on server restart
- [ ] Add session store configuration tests
- [ ] Document operational considerations

**Phase 4 (Advanced):**
- [ ] Authentication integration interface
- [ ] Permission-based authorization checks
- [ ] Session management MCP tools
- [ ] External store adapter (Redis)
- [ ] Performance benchmarking
- [ ] Security audit and penetration testing

## Addendums

### Addendum A: Relationship with Other ADRs

- **ADR 0011 (Caching)**: Session context provides additional cache key dimension
- **ADR 0012 (Observability)**: Session extends correlation ID hierarchy
- **ADR 0013 (Federation)**: Session propagated to federated catalogs
- **ADR 0016 (Security)**: Session carries authentication/authorization metadata
- **ADR 0017 (PySTAC CRUDL)**: Future write operations may require session authentication

### Addendum B: Example Usage

```python
# Client sets session ID before invoking MCP server
os.environ["STAC_MCP_SESSION_ID"] = "550e8400-e29b-41d4-a716-446655440000"
os.environ["STAC_MCP_USER_ID"] = "user_12345"

# Server-side: Tool handler automatically has session context
from stac_mcp.session import get_current_session

def my_tool_handler(arguments: dict):
    session = get_current_session()
    logger.info(f"Processing request for session {session.session_id[:8]}...")
    
    # Session-scoped operations
    if session.user_id:
        apply_user_permissions(session.permissions)
    
    # Session context automatically propagates to nested calls
    result = perform_search(arguments)
    return result
```

### Addendum C: Security Considerations Summary

1. **Never log full session identifiers** - truncate to first 8 characters
2. **Never store PII directly** - use opaque identifiers with external lookups
3. **Enforce TTL strictly** - reject expired sessions immediately
4. **Redact auth tokens** - never log plaintext or even hashes in normal logs
5. **Sanitize metadata** - scan for accidental credential or PII inclusion
6. **Rate limit per session** - prevent abuse of long-lived sessions
7. **Audit session access** - log session creation, expiry, and invalidation events

## References

- MCP Protocol Specification: https://spec.modelcontextprotocol.io/
- Python contextvars: https://docs.python.org/3/library/contextvars.html
- ADR 0011: Caching Layer for Session & Workspace Reuse
- ADR 0012: Observability & Telemetry Strategy
- ADR 0013: Multi-Catalog Federation Strategy
- ADR 0016: Security & Credential Isolation Strategy
- OAuth 2.0 RFC 6749: https://datatracker.ietf.org/doc/html/rfc6749
- JWT Best Practices: https://datatracker.ietf.org/doc/html/rfc8725
