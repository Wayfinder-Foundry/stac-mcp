# ASR 1003: JSON Output Stability and Compatibility

Status: Proposed
Date: 2025-09-18

## Context
Future tools may support a JSON output mode for machine-readable chaining. This introduces a contract that clients can depend on.

## Requirement
- When `output_format=json` is provided, responses must be valid JSON objects.
- Include a minimal, stable subset of fields documented in the tool schema.
- Changes to the JSON schema must be backwards compatible within a major version.
- If breaking changes are necessary, bump the major version and document migration steps.

## Implications
- Add golden tests for JSON responses to detect accidental breaking changes.
- Document the JSON fields and compatibility policy in README/ADR.

## Alternatives considered
- No JSON mode: rejected due to downstream automation use cases.

## Addendums
- 2025-09-18: Proposed alongside ADR 0006.
