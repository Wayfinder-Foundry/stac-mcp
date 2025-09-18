# ADR 0005: Optional Planetary Computer Asset Signing

Status: Proposed
Date: 2025-09-18

## Context
- Planetary Computer assets often require signed URLs for direct access.
- Not all catalogs require signing; must remain optional.

## Decision
- Add sign_assets bool parameter on item-returning tools (default: false).
- If true and catalog host matches Planetary Computer:
  - Try import planetary_computer and sign item/assets.
  - Fail gracefully if package missing; include actionable hint.
- Do not persist signed URLs in state; sign per response.

## Consequences
- Enables immediate asset usability on PC without breaking other catalogs.
- Introduces optional dependency and branching logic.

## Alternatives considered
- Always sign (rejected; breaks non-PC).
- Never sign (rejected; harms usability on PC).
