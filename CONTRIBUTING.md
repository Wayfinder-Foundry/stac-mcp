# Contributing to STAC MCP Server

Thank you for your interest in contributing to STAC MCP Server! This document provides guidelines for contributing to the project.

## Quick Start

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/Wayfinder-Foundry/stac-mcp.git
   cd stac-mcp
   ```

2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

3. Verify your setup:
   ```bash
   # Format code
   ruff format stac_mcp/ tests/ examples/
   
   # Check for linting issues
   ruff check stac_mcp/ tests/ examples/ --fix
   
   # Run tests
   pytest -v
   
   # Test the server
   python examples/example_usage.py
   ```

## Development Workflow

### Making Changes

1. Create a branch with an appropriate prefix (see [Version Bumping](#version-bumping))
2. Make your changes following our [coding standards](#coding-standards)
3. Format and lint your code:
   ```bash
   ruff format stac_mcp/ tests/ examples/
   ruff check stac_mcp/ tests/ examples/ --fix
   ```
4. Run tests to ensure nothing breaks:
   ```bash
   pytest -v
   ```
5. Commit your changes with clear, descriptive commit messages
6. Push your branch and create a pull request

### Version Bumping

The project uses semantic versioning (SemVer: MAJOR.MINOR.PATCH) with automated version management. Version bumps occur automatically when PRs are merged to `main` based on either PR labels or branch prefixes.

#### For Human Contributors (Branch Prefixes)

Use these branch prefixes to automatically trigger version bumps when your PR is merged:

- **Bug fixes** (patch: 0.1.0 → 0.1.1):
  - `hotfix/*`
  - `fix/*`
  - `copilot/fix-*`
  - `copilot/hotfix/*`
  - Examples: `hotfix/fix-authentication`, `fix/typo-in-docs`

- **New features** (minor: 0.1.0 → 0.2.0):
  - `feature/*`
  - `copilot/feature/*`
  - Examples: `feature/add-stac-search-tool`, `feature/improve-logging`

- **Breaking changes** (major: 0.1.0 → 1.0.0):
  - `release/*`
  - `copilot/release/*`
  - Examples: `release/v2-api-changes`, `release/remove-deprecated-api`

- **No version bump**:
  - `chore/*`, `docs/*`, `test/*`, `ci/*`, etc.
  - Examples: `chore/update-deps`, `docs/improve-readme`

#### For Automated Agents (PR Labels)

Automated tools (like GitHub Copilot Workspace) can use PR labels to control version bumping instead of branch prefixes. Labels take priority over branch prefixes when both are present.

Add one of these labels to your PR:

- **Bug fixes** (patch: 0.1.0 → 0.1.1):
  - `bump:patch` or `bump:hotfix`

- **New features** (minor: 0.1.0 → 0.2.0):
  - `bump:minor` or `bump:feature`

- **Breaking changes** (major: 0.1.0 → 1.0.0):
  - `bump:major` or `bump:release`

**Note**: If neither a recognized branch prefix nor a version bump label is present, no version bump will occur.

### Pull Request Guidelines

1. **Keep PRs focused**: One feature or fix per PR
2. **Write clear descriptions**: Explain what changes you made and why
3. **Reference issues**: Link to related issues using `#issue-number`
4. **Add tests**: Include tests for new functionality
5. **Update documentation**: Update relevant docs (README, AGENTS.md, etc.)
6. **Follow the checklist**: Complete the PR template checklist

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://peps.python.org/pep-0008/) for code style
- Follow [PEP 257](https://peps.python.org/pep-0257/) for docstrings
- Use [PEP 484](https://peps.python.org/pep-0484/) type hints
- Use snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE for constants
- Import generics from `typing` module (List, Dict, Optional, Union, etc.)

### Formatting and Linting

We use [Ruff](https://docs.astral.sh/ruff/) for both formatting and linting:

```bash
# Format code
ruff format stac_mcp/ tests/ examples/

# Fix auto-fixable linting issues
ruff check stac_mcp/ tests/ examples/ --fix
```

**Important**: Run these commands after every code change before committing.

### Testing

- Write tests for all new features and bug fixes
- Prefer parametrized tests for similar cases
- Mock external dependencies (network calls, file system, etc.)
- Keep tests fast and deterministic

```bash
# Run all tests
pytest -v

# Run with coverage
coverage run -m pytest -q
coverage report -m

# Generate HTML coverage report
coverage html
```

### Documentation

- Document all public APIs with clear docstrings
- Update README.md for user-facing changes
- Update AGENTS.md for contributor guidelines
- Add Architecture Decision Records (ADRs) for significant changes

## Architecture Decision Records (ADRs)

For significant architectural decisions or requirements, create an ADR in the `architecture/` directory:

1. Use the naming convention: `NNNN-short-description.md` (e.g., `0013-version-bumping-labels.md`)
2. Follow the ADR or ASR template (see AGENTS.md)
3. Include: Context, Decision/Requirement, Consequences, Alternatives considered
4. Reference the ADR in your PR description
5. Update the Status field to "Accepted" when merged

## Getting Help

- **Questions**: Open a [discussion](https://github.com/Wayfinder-Foundry/stac-mcp/discussions)
- **Bug reports**: Open an [issue](https://github.com/Wayfinder-Foundry/stac-mcp/issues)
- **Security issues**: See [SECURITY.md](SECURITY.md) (if available)

## License

By contributing to STAC MCP Server, you agree that your contributions will be licensed under the project's [Apache 2.0 License](LICENSE).
