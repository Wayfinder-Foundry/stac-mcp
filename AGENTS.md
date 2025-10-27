# Agents / Contributor Guide — Python best practices & PEP adherence

Purpose
- Provide concise, actionable guidance for contributors and automated agents working on this repository.
- Emphasize adherence to Python PEPs (style, typing, docstrings) and the project's tooling.

Core principles
- Follow PEP 8 for style and naming (use snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE for constants).
- Use PEP 257 docstrings for modules, classes, and public functions/methods.
- Prefer type hints (PEP 484). Keep signatures explicit and avoid overly broad Any where a concrete type helps readability.
- Always import generics from the `typing` module (List, Dict, Optional, Union, Tuple, Set, Iterable, Callable, etc.) instead of using builtin collection annotations like `list[str]` unless an ADR supersedes this rule. This maintains consistency across the codebase and clarifies intent for contributors and automated agents.
- Keep functions small and single-responsibility. Favor composition over inheritance when appropriate.

Public-API-first rule
- Prefer using public, documented APIs of third-party libraries. Do not reach into private or underscore-prefixed attributes or functions (for example, avoid accessing objects like `client._stac_io`, `session._pool`, or other internals).
- When interacting with STAC libraries prefer the public Client/IO abstractions (for example, `pystac_client.Client` and `pystac.stac_io.StacIO`/`StacApiIO`) or perform explicit HTTP calls with `requests` rather than reading or mutating private internals.
- If you need custom IO behavior (signing, caching, alternative transports), implement a public `StacIO` subclass and pass it into the public `Client` constructor rather than monkey-patching internal attributes.
- Prefer dependency injection for testability: accept an explicit `requests.Session`, `stac_io`, or client object via a constructor parameter or execution wrapper so tests can provide fakes/mocks without touching internals.
- Example (preferred):
  - Use the public Client API:

    ```py
    from pystac_client import Client
    from pystac_client.stac_api_io import StacApiIO

    stac_io = StacApiIO(headers={"X-API-Key": "..."})
    client = Client.open("https://example.com/stac", stac_io=stac_io)
    # call public methods like client.search(), client.get_collection(), etc.
    ```

  - If you need to make a direct HTTP call for a feature not exposed by the client, use `requests` and pass explicit headers/timeouts instead of poking into private attributes:

    ```py
    import requests

    resp = requests.post("https://example.com/stac/search", json=body, headers={"Accept": "application/json"}, timeout=30)
    ```

These rules keep behavior stable across upstream library upgrades and make code easier to test and maintain.

**Formatting & Linting: Pre-Commit/Pre-Push Checklist**

**MUST** run these commands and ensure they pass before every `git commit` and `git push`.

1.  **Format Code:**
    ```bash
    uv run ruff format stac_mcp/ tests/ examples/
    ```
2.  **Lint and Auto-Fix:**
    ```bash
    uv run ruff check stac_mcp/ tests/ examples/ --fix --no-cache
    ```
3.  **Run Tests:**
    ```bash
    uv run pytest -q
    ```
4.  **Verify Test Coverage:**
    ```bash
    uv run coverage run -m pytest -v
    uv run coverage report --fail-below=85
    ```

**IMPORTANT:** Run the `ruff format` and `ruff check` commands multiple times in sequence to ensure all issues are resolved, as auto-fixing can sometimes introduce new formatting needs.

Testing & validation
- Write tests for behavior, not implementation; prefer parametrized tests for similar cases.
- Run the full test suite locally:
  - pytest -v
- Ensure all tests pass before pushing.
- Follow the repository's Validation checklist:
  - Ruff format and lint pass.
  - All tests pass.
- Validate MCP server functionality (example usage):
  - python examples/example_usage.py
  - Debug runners and short scripts were moved into the `debug/` directory; use those when present (e.g., `python debug/debug_estimate_run_pc.py`).

Logging & errors
- Use the standard logging module; configure logging at entrypoints only.
- Do not swallow exceptions silently. Surface useful context and wrap exceptions only when adding helpful information.
- Avoid print() for diagnostics in library code.

Async & IO
- Prefer async APIs when interacting with network or IO in the MCP server; follow standard asyncio patterns.
- Avoid blocking calls in async code. Use run_in_executor for CPU-bound or blocking work.

Dependencies & environment
- Use virtual environments or tox for isolation.
- Pin dev dependencies in pyproject.toml where appropriate.
- Install in editable mode during development: pip install -e ".[dev]"

Commit & PR guidance
- Write clear commit messages with intent and scope.
- Run formatting and tests before pushing.
- Keep PRs focused and small; include a brief description of changes and validation steps.

## Architecture records (ADRs and ASRs)

- Location: keep all Architecture Decision Records (ADRs) and Architecture Significant Requirements (ASRs) under the `architecture/` directory.
- Scope:
  - ADRs document important architectural decisions and their rationale.
  - ASRs capture significant requirements (often non-functional) that drive architectural choices (e.g., performance SLOs, availability, security, offline behavior).
- Naming & format:
  - Filename: zero-padded ordinal and a short kebab-case slug, e.g., `0009-support-aggregations.md`.
  - Title: start with `# ADR <NNNN>: …` or `# ASR <NNNN>: …` to clearly distinguish the type.
  - Status lifecycle: Proposed → Accepted → (optionally) Superseded.
  - Recommended sections: Context, Decision (for ADR) or Requirement (for ASR), Consequences, Alternatives considered, and an Addendums section for incremental updates.
- Process:
  - When to write/update: new features, API or protocol changes, dependency/infra shifts, performance/security goals, behavior or contract changes visible to users/clients.
  - How:
    - Create a new file in `architecture/` for new decisions/requirements and link it in your PR description.
    - If changing an existing decision/requirement, either add a dated Addendum section in the same file, or create a new ADR that supersedes the previous one and cross-reference with `Supersedes`/`Superseded by` notes.
    - Update the `Status` field upon merge.
- Minimal templates:

  ADR template
  ```markdown
  # ADR NNNN: Title
  
  Status: Proposed | Accepted | Superseded
  Date: YYYY-MM-DD
  
  ## Context
  ...
  
  ## Decision
  ...
  
  ## Consequences
  ...
  
  ## Alternatives considered
  ...
  
  ## Addendums
  - YYYY-MM-DD: ...
  ```

  ASR template
  ```markdown
  # ASR NNNN: Title
  
  Status: Proposed | Accepted | Superseded
  Date: YYYY-MM-DD
  
  ## Context
  ...
  
  ## Requirement
  ... (measurable criteria if applicable)
  
  ## Implications
  ... (impact on architecture, testing, ops)
  
  ## Alternatives considered
  ...
  
  ## Addendums
  - YYYY-MM-DD: ...
  ```

Branch naming conventions & version bumping
- **For automated agents (Copilot)**: Use PR labels to control automatic version increments:
  - **bump:patch** or **bump:hotfix** for bug fixes (triggers patch version increment: 0.1.0 -> 0.1.1)
  - **bump:minor** or **bump:feature** for new features (triggers minor version increment: 0.1.0 -> 0.2.0)
  - **bump:major** or **bump:release** for breaking changes (triggers major version increment: 0.1.0 -> 1.0.0)
  - Labels take priority over branch prefixes when both are present
- **For human contributors**: Use branch prefixes to control automatic version increments:
  - **hotfix/**, **copilot/fix-**, or **copilot/hotfix/** for bug fixes (triggers patch version increment: 0.1.0 -> 0.1.1)
  - **feature/** or **copilot/feature/** for new features (triggers minor version increment: 0.1.0 -> 0.2.0)
  - **release/** or **copilot/release/** for breaking changes (triggers major version increment: 0.1.0 -> 1.0.0)
- Examples:
  - Branch prefixes: hotfix/fix-authentication, copilot/fix-nodata-dtype, copilot/hotfix/authentication, feature/add-new-stac-tool, copilot/feature/new-tool, release/v2-api-changes, copilot/release/v2-breaking-changes
  - Labels: Add bump:patch, bump:minor, or bump:major to your PR
- Other branch prefixes (e.g., chore/, docs/, copilot/chore/, copilot/docs/) will not trigger automatic version increments unless a bump label is present
- Version increments happen automatically when PRs are merged to main

Semantic versioning & releases
- Follow semantic versioning (SemVer) for all releases: MAJOR.MINOR.PATCH
- Use the version management script to maintain consistency across files:
  - python scripts/version.py current  # Show current version
  - python scripts/version.py patch    # Bug fixes (0.1.0 -> 0.1.1)
  - python scripts/version.py minor    # New features (0.1.0 -> 0.2.0)
  - python scripts/version.py major    # Breaking changes (0.1.0 -> 1.0.0)
- Automatic version increments when PRs are merged (labels take priority over branch prefixes):
  - **Patch** (0.1.0 -> 0.1.1): Bug fixes, security patches, minor improvements
    - Labels: bump:patch or bump:hotfix
    - Branch prefixes: hotfix/*, copilot/fix-*, or copilot/hotfix/*
  - **Minor** (0.1.0 -> 0.2.0): New features, non-breaking API changes, performance improvements
    - Labels: bump:minor or bump:feature
    - Branch prefixes: feature/* or copilot/feature/*
  - **Major** (0.1.0 -> 1.0.0): Breaking changes, major architecture changes, incompatible API changes
    - Labels: bump:major or bump:release
    - Branch prefixes: release/* or copilot/release/*
- Container images are automatically tagged with semantic versions on version bump
- Never push non-semantic tags like "cache" or "main" for production containers

CI & pre-merge checks
- Ensure Ruff format and linting pass.
- Ensure all tests pass locally and in the CI.
- Follow the repository's Validation checklist (format, lint, tests, example run).

Quick contributor checklist
1. Install dev deps:
   - pip install -e ".[dev]"
2. Format & lint:
  - ruff format stac_mcp/ tests/ examples/
  - ruff check stac_mcp/ tests/ examples/ --fix
  - (Repeat these two commands after every change before staging/committing.)
3. Run tests:
   - pytest -v
4. Smoke test example:
   - python examples/example_usage.py
5. ADR/ASR hygiene:
   - Before coding: review `architecture/` for relevant ADRs/ASRs.
   - If your change is architecture-significant, add a new ADR/ASR in `architecture/`.
   - If you modify a previous decision/requirement, add a dated Addendum or create a new ADR that supersedes the old one (and cross-reference both).
   - Reference the ADR/ASR IDs in your PR description and update their Status upon merge.

References
- PEP 8 — Style Guide for Python Code: https://peps.python.org/pep-0008/
- PEP 257 — Docstring Conventions: https://peps.python.org/pep-0257/
- PEP 484 — Type Hints: https://peps.python.org/pep-0484/

Notes
- This project standardizes on Ruff (formatting + linting) and pytest — prefer those tools and the commands above.
- Keep changes minimal, test-driven, and well-documented in PR descriptions.

## GDAL/rasterio compatibility notes

- Avoid depending directly on the `gdal` Python binding unless strictly necessary; it requires a matching system libgdal and often breaks in containers with version mismatches.
- Prefer `rasterio` wheels for raster IO (pulled in by `odc-stac` indirectly); wheels bundle compatible GDAL and avoid system-level conflicts.
- Container guidance:
  - Use Debian/Ubuntu slim bases to benefit from manylinux wheels. Alpine (musl) often lacks compatible wheels for `rasterio`/`GDAL` and forces system GDAL installs.
  - If you must use system GDAL, ensure `libgdal` and Python GDAL bindings are the same minor version (e.g., 3.11.x), and set `GDAL_DATA`/`PROJ_LIB` appropriately.
  - Keep system packages minimal to reduce the risk of ABI mismatches.
