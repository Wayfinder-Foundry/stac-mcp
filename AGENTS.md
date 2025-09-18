# Agents / Contributor Guide — Python best practices & PEP adherence

Purpose
- Provide concise, actionable guidance for contributors and automated agents working on this repository.
- Emphasize adherence to Python PEPs (style, typing, docstrings) and the project's tooling.

Core principles
- Follow PEP 8 for style and naming (use snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE for constants).
- Use PEP 257 docstrings for modules, classes, and public functions/methods.
- Prefer type hints (PEP 484). Keep signatures explicit and avoid overly broad Any where a concrete type helps readability.
- Keep functions small and single-responsibility. Favor composition over inheritance when appropriate.

Formatting & linting
- Use Black for formatting; accept its defaults (88-char line length).
- Use Ruff for linting and auto-fixes; resolve remaining issues manually.
- Commands:
  - pip install -e ".[dev]"
  - black stac_mcp/ tests/ examples/
  - ruff check stac_mcp/ tests/ examples/ --fix

Testing & validation
- Write tests for behavior, not implementation; prefer parametrized tests for similar cases.
- Run the full test suite locally:
  - pytest -v
- Validate MCP server functionality (example usage):
  - python examples/example_usage.py

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

Semantic versioning & releases
- Follow semantic versioning (SemVer) for all releases: MAJOR.MINOR.PATCH
- Use the version management script to maintain consistency across files:
  - python scripts/version.py current  # Show current version
  - python scripts/version.py patch    # Bug fixes (0.1.0 -> 0.1.1)
  - python scripts/version.py minor    # New features (0.1.0 -> 0.2.0)
  - python scripts/version.py major    # Breaking changes (0.1.0 -> 1.0.0)
- For each PR merged into main, increment version based on content:
  - Patch: Bug fixes, documentation updates, minor improvements
  - Minor: New features, non-breaking API changes
  - Major: Breaking changes, major architecture changes
- Container images are automatically tagged with semantic versions on git tag push
- Never push non-semantic tags like "cache" or "main" for production containers

CI & pre-merge checks
- Ensure Black and Ruff pass.
- Ensure all tests pass locally and in the CI.
- Follow the repository's Validation checklist (format, lint, tests, example run).

Quick contributor checklist
1. Install dev deps:
   - pip install -e ".[dev]"
2. Format & lint:
   - black stac_mcp/ tests/ examples/
   - ruff check stac_mcp/ tests/ examples/ --fix
3. Run tests:
   - pytest -v
4. Smoke test example:
   - python examples/example_usage.py

References
- PEP 8 — Style Guide for Python Code: https://peps.python.org/pep-0008/
- PEP 257 — Docstring Conventions: https://peps.python.org/pep-0257/
- PEP 484 — Type Hints: https://peps.python.org/pep-0484/

Notes
- This project already standardizes on Black, Ruff, and pytest — prefer those tools and the commands above.
- Keep changes minimal, test-driven, and well-documented in PR descriptions.
