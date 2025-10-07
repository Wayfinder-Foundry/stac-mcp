# Dev Container Configuration

This directory contains the development container configuration for the STAC MCP Server project, optimized for GitHub Codespaces and VS Code Remote Containers.

## What's Included

### Base Image
- **Python 3.12** on Debian Bookworm (mcr.microsoft.com/devcontainers/python:3.12-bookworm)
- Matches the project's production container environment

### System Dependencies
- **GDAL** (gdal-bin, libgdal-dev) - Geospatial Data Abstraction Library
- **PROJ** (libproj-dev) - Cartographic projections library
- **Build tools** (build-essential) - Required for compiling Python packages
- **Git** - Latest version via PPA
- **GitHub CLI** (gh) - For GitHub integration

### Python Environment
- Project installed in editable mode: `pip install -e ".[dev]"`
- All development dependencies (pytest, black, ruff, etc.)
- Additional tools: ipython, coverage

### VS Code Extensions
The following extensions are automatically installed:
- **Python** (ms-python.python) - Python language support
- **Pylance** (ms-python.vscode-pylance) - Fast Python language server
- **Black Formatter** (ms-python.black-formatter) - Code formatting
- **Ruff** (charliermarsh.ruff) - Fast Python linter
- **Jupyter** (ms-toolsai.jupyter) - Notebook support
- **GitHub Copilot** (GitHub.copilot) - AI pair programming
- **GitLens** (eamodio.gitlens) - Git supercharged
- **Docker** (ms-azuretools.vscode-docker) - Container support
- **YAML** (redhat.vscode-yaml) - YAML language support
- **Even Better TOML** (tamasfe.even-better-toml) - TOML support

### VS Code Settings
Pre-configured settings for optimal development:
- **Black** as default Python formatter (88 char line length)
- **Ruff** for linting with auto-fix on save
- **Pytest** as test framework
- **Format on save** enabled
- **Import organization** on save
- Zsh as default terminal shell

## Getting Started

### Using GitHub Codespaces

1. **Create a Codespace**:
   - Navigate to the repository on GitHub
   - Click the green "Code" button
   - Select the "Codespaces" tab
   - Click "Create codespace on main" (or your branch)

2. **Wait for Setup**:
   - The container will build and run the postCreate script
   - System dependencies and Python packages will be installed
   - This takes ~2-3 minutes on first creation

3. **Start Developing**:
   - The terminal will display a welcome message with quick commands
   - Run `pytest -v` to verify the setup
   - Use `stac-mcp` to start the MCP server

### Using VS Code Remote Containers

1. **Prerequisites**:
   - Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
   - Install [VS Code](https://code.visualstudio.com/)
   - Install the [Remote - Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)

2. **Open in Container**:
   - Clone the repository locally
   - Open the folder in VS Code
   - Click the green button in the bottom-left corner
   - Select "Reopen in Container"

3. **Wait for Build**:
   - The container will build (first time takes longer)
   - Dependencies will be installed automatically

## Quick Commands

Once the container is running, use these commands:

### Testing
```bash
# Run all tests with verbose output
pytest -v

# Run with coverage
coverage run -m pytest -q
coverage report -m

# Generate HTML coverage report
coverage html
```

### Code Quality
```bash
# Format code with Black
black stac_mcp/ tests/ examples/

# Lint with Ruff
ruff check stac_mcp/ tests/ examples/

# Auto-fix linting issues
ruff check stac_mcp/ tests/ examples/ --fix
```

### Running the Server
```bash
# Start MCP server (stdio transport)
stac-mcp

# Test the server with example script
python examples/example_usage.py
```

### Container Development
```bash
# Build development container
docker build -f Containerfile -t stac-mcp:dev .

# Test the container
docker run --rm -i stac-mcp:dev
```

## Environment Variables

The devcontainer sets these environment variables by default:

| Variable | Value | Description |
|----------|-------|-------------|
| `PYTHONUNBUFFERED` | `1` | Disable Python output buffering |
| `STAC_MCP_LOG_LEVEL` | `INFO` | Set logging level |
| `STAC_MCP_LOG_FORMAT` | `text` | Use text format for logs |

You can override these in your Codespace settings or by modifying `.devcontainer/devcontainer.json`.

## Customization

### Adding VS Code Extensions

Edit `devcontainer.json` and add extension IDs to the `extensions` array:

```json
"extensions": [
  "existing.extension",
  "your.new-extension"
]
```

### Modifying Python Dependencies

The container uses the project's `pyproject.toml` for dependencies. To add development dependencies:

1. Edit `pyproject.toml` under `[project.optional-dependencies]`
2. Rebuild the container or run `pip install -e ".[dev]"`

### Changing System Packages

Edit `.devcontainer/postCreate.sh` to add or modify system packages:

```bash
sudo apt-get install -y your-package
```

Then rebuild the container.

## Troubleshooting

### Container Build Fails

If the container fails to build:
1. Check your internet connection
2. Try rebuilding: "Rebuild Container" from the Command Palette
3. Check Docker Desktop is running (for local development)

### Dependencies Installation Fails

If `pip install` fails during postCreate:
1. Check the build logs in the terminal
2. Try running `pip install -e ".[dev]"` manually
3. Verify system dependencies are installed: `dpkg -l | grep gdal`

### GDAL/Rasterio Issues

If you encounter GDAL-related errors:
1. Verify GDAL is installed: `gdalinfo --version`
2. Check GDAL Python bindings: `python -c "from osgeo import gdal"`
3. Reinstall rasterio if needed: `pip install --no-binary rasterio rasterio`

### Performance Issues

If the Codespace is slow:
1. Choose a larger machine type in Codespace settings
2. Close unused browser tabs
3. Restart the Codespace

## References

- [Development Containers Specification](https://containers.dev/)
- [VS Code Remote Containers Documentation](https://code.visualstudio.com/docs/remote/containers)
- [GitHub Codespaces Documentation](https://docs.github.com/en/codespaces)
- [Project README](../README.md)
- [Contributor Guide](../AGENTS.md)
